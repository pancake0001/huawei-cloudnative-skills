"""Read-only CCE capacity, allocation, and cost-efficiency analysis."""

from __future__ import annotations

import html
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, Optional
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from . import aom, cce


_GIB = 1024 ** 3
_SYSTEM_NAMESPACES = {"kube-system", "monitoring"}


def _number(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _values(row: Dict[str, Any]) -> list[float]:
    return [number for point in row.get("values") or [] if len(point) > 1 and (number := _number(point[1])) is not None]


def _latest(rows: Iterable[Dict[str, Any]]) -> Optional[float]:
    values = [series[-1] for row in rows if (series := _values(row))]
    return values[-1] if values else None


def _minimum(values: list[float]) -> Optional[float]:
    return min(values) if values else None


def _samples_by_timestamp(row: Dict[str, Any]) -> Dict[int, float]:
    samples: Dict[int, float] = {}
    for point in row.get("values") or []:
        if len(point) < 2:
            continue
        timestamp, value = _number(point[0]), _number(point[1])
        if timestamp is not None and value is not None:
            samples[int(timestamp)] = value
    return samples


def _aligned_ratio_row(numerator: Dict[str, Any], denominator: Dict[str, Any]) -> Dict[str, Any]:
    numerator_samples, denominator_samples = _samples_by_timestamp(numerator), _samples_by_timestamp(denominator)
    return {"values": [[timestamp, numerator_samples[timestamp] / denominator_samples[timestamp] * 100] for timestamp in sorted(numerator_samples.keys() & denominator_samples.keys()) if denominator_samples[timestamp] > 0]}


def _aligned_ratio(numerator: Dict[str, Any], denominator: Dict[str, Any]) -> list[float]:
    return _values(_aligned_ratio_row(numerator, denominator))


def _aligned_difference(left: Dict[str, Any], right: Dict[str, Any]) -> list[float]:
    left_samples, right_samples = _samples_by_timestamp(left), _samples_by_timestamp(right)
    return [left_samples[timestamp] - right_samples[timestamp] for timestamp in sorted(left_samples.keys() & right_samples.keys())]


def _aligned_difference_row(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    left_samples, right_samples = _samples_by_timestamp(left), _samples_by_timestamp(right)
    return {"values": [[timestamp, left_samples[timestamp] - right_samples[timestamp]] for timestamp in sorted(left_samples.keys() & right_samples.keys())]}


def _trend(values: list[float]) -> str:
    if len(values) < 6:
        return "insufficient_data"
    width = max(1, len(values) // 5)
    first, last = mean(values[:width]), mean(values[-width:])
    if first == 0:
        return "rising" if last > 0 else "stable"
    change = (last - first) / first * 100
    return "rising" if change > 10 else "falling" if change < -10 else "stable"


def _time_label(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Shanghai")).isoformat()


def _time_series_summary(row: Dict[str, Any], unit: str) -> Dict[str, Any]:
    """Summarize every sample without returning redundant steady-state points."""
    samples = sorted(_samples_by_timestamp(row).items())
    if not samples:
        return {"sample_count": 0, "trend": "insufficient_data", "key_points": []}

    first_timestamp, first_value = samples[0]
    last_timestamp, last_value = samples[-1]
    values = [value for _, value in samples]
    minimum_timestamp, minimum_value = min(samples, key=lambda sample: sample[1])
    maximum_timestamp, maximum_value = max(samples, key=lambda sample: sample[1])
    key_points = []
    seen_timestamps = set()
    for timestamp, value in ((first_timestamp, first_value), (minimum_timestamp, minimum_value), (maximum_timestamp, maximum_value), (last_timestamp, last_value)):
        if timestamp not in seen_timestamps:
            key_points.append((timestamp, value))
            seen_timestamps.add(timestamp)
    first_displayed, last_displayed = _resource(first_value, unit), _resource(last_value, unit)
    change = last_value - first_value
    if first_displayed == last_displayed or math.isclose(change, 0, rel_tol=1e-9, abs_tol=1e-9):
        change = 0.0
    change_percent = change / first_value * 100 if first_value else None
    return {
        "sample_count": len(samples),
        "first_sample_at": _time_label(first_timestamp),
        "last_sample_at": _time_label(last_timestamp),
        "start": first_displayed,
        "end": last_displayed,
        "minimum": _resource(min(values), unit),
        "maximum": _resource(max(values), unit),
        "average": _resource(mean(values), unit),
        "change": _resource(change, unit),
        "change_percent": round(change_percent, 2) if change_percent is not None else None,
        "trend": _trend(values),
        "key_points": [{"at": _time_label(timestamp), "value": _resource(value, unit)} for timestamp, value in key_points],
    }


def _chart_samples(row: Dict[str, Any], unit: str) -> list[list[float]]:
    samples = []
    for timestamp, value in sorted(_samples_by_timestamp(row).items()):
        displayed = _resource(value, unit)
        if displayed is not None:
            samples.append([timestamp, displayed])
    return samples


def _rows(result: Dict[str, Any]) -> list[Dict[str, Any]]:
    return (((result.get("result") or {}).get("data") or {}).get("result") or []) if result.get("success") else []


def _analysis_window(analysis_date: Optional[str], analysis_days: int) -> tuple[str, str, int, int]:
    timezone = ZoneInfo("Asia/Shanghai")
    try:
        if analysis_days < 1 or analysis_days > 7:
            raise ValueError("analysis_days must be between 1 and 7")
        if analysis_date and analysis_days != 1:
            raise ValueError("analysis_date can only be used with analysis_days=1")
        end_day = date.fromisoformat(analysis_date) + timedelta(days=1) if analysis_date else datetime.now(timezone).date()
    except ValueError as exc:
        message = str(exc)
        raise ValueError(message if message.startswith("analysis_") else "analysis_date must use YYYY-MM-DD") from exc
    start_day = end_day - timedelta(days=analysis_days)
    start = datetime.combine(start_day, time.min, tzinfo=timezone)
    end = datetime.combine(end_day, time.min, tzinfo=timezone)
    return start_day.isoformat(), end_day.isoformat(), int(start.timestamp()), int(end.timestamp())


def _query(region: str, instance_id: str, query: str, start: int, end: int, ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str]) -> Dict[str, Any]:
    return aom.get_aom_prom_metrics_http(region, instance_id, query, start=start, end=end, step=300, ak=ak, sk=sk, project_id=project_id, security_token=security_token)


def _resolve_prom_instance(region: str, cluster_id: str, start: int, end: int, ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str]) -> Dict[str, Any]:
    configured = cce.get_prom_instance_id(region, cluster_id, ak, sk, project_id, security_token=security_token)
    if configured.get("success"):
        return configured
    listed = cce.list_aom_prom_instances(region, ak, sk, project_id, security_token=security_token)
    if not listed.get("success"):
        return {"success": False, "error": f"{configured.get('error')}; AOM fallback failed: {listed.get('error')}"}
    probe = f'count(kube_node_info{{cluster="{cluster_id}"}})'
    candidates = listed.get("instances") or []
    if not candidates:
        return {"success": False, "error": f"{configured.get('error')}; no CCE AOM Prometheus instances were found"}
    def _matches_cluster(candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        result = _query(region, candidate["id"], probe, start, end, ak, sk, project_id, security_token)
        return candidate if _rows(result) else None
    with ThreadPoolExecutor(max_workers=min(8, len(candidates))) as executor:
        matches = [candidate for candidate in executor.map(_matches_cluster, candidates) if candidate]
    if len(matches) == 1:
        return {"success": True, "aom_instance_id": matches[0]["id"], "source": "hcloud AOM ListPromInstance verified by cluster metrics"}
    if not matches:
        return {"success": False, "error": f"{configured.get('error')}; no AOM Prometheus instance exposed metrics for cluster {cluster_id}"}
    return {"success": False, "error": f"{configured.get('error')}; multiple AOM Prometheus instances exposed metrics for cluster {cluster_id}"}


def _resource(value: Optional[float], unit: str) -> Optional[float]:
    return round(value / _GIB, 2) if value is not None and unit == "GiB" else round(value, 3) if value is not None else None


def analyze_cce_cost_optimization(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, analysis_date: Optional[str] = None, analysis_days: int = 1, top_n: int = 20, security_token: Optional[str] = None, exclude_namespaces: Optional[str] = None, include_chart_series: bool = False, **_: Any) -> Dict[str, Any]:
    """Analyze capacity, requests, actual use, elasticity, and cost opportunities.

    Prometheus is the primary source so the analysis does not enumerate Pods or
    workloads from the Kubernetes API.  Missing metric families are reported as
    data gaps rather than silently replaced with a broader cluster read.
    """
    try:
        start_day, end_day, start, end = _analysis_window(analysis_date, int(analysis_days))
    except ValueError as exc:
        return {"success": False, "action": "analyze_cce_cost_optimization", "error": str(exc)}
    excluded = {item.strip() for item in (exclude_namespaces or "").split(",") if item.strip()}
    selector = f'cluster="{cluster_id}"'
    instance = _resolve_prom_instance(region, cluster_id, start, end, ak, sk, project_id, security_token)
    nodepools = cce.list_cce_node_pools(region, cluster_id, ak, sk, project_id, security_token=security_token)
    gaps: list[str] = []
    if not instance.get("success"):
        return {"success": False, "action": "analyze_cce_cost_optimization", "error": instance.get("error"), "data_gaps": ["AOM Prometheus instance is required for capacity and usage analysis."]}
    if not nodepools.get("success"):
        gaps.append(f"nodepools: {nodepools.get('error')}")

    queries = {
        "cpu_total_capacity": f'sum(kube_node_status_capacity{{{selector},resource="cpu",unit="core"}})',
        "memory_total_capacity": f'sum(kube_node_status_capacity{{{selector},resource="memory",unit="byte"}})',
        "cluster_node_count": f'count(kube_node_info{{{selector}}})',
        "cpu_capacity": f'sum(kube_node_status_allocatable{{{selector},resource="cpu",unit="core"}})',
        "memory_capacity": f'sum(kube_node_status_allocatable{{{selector},resource="memory",unit="byte"}})',
        "declared_cpu_requests": f'sum(kube_pod_container_resource_requests{{{selector},resource="cpu",unit="core"}})',
        "declared_memory_requests": f'sum(kube_pod_container_resource_requests{{{selector},resource="memory",unit="byte"}})',
        "node_bound_cpu_requests": f'sum(kube_pod_container_resource_requests{{{selector},resource="cpu",unit="core"}} * on (namespace,pod) group_left(node) kube_pod_info{{{selector},node!=""}})',
        "node_bound_memory_requests": f'sum(kube_pod_container_resource_requests{{{selector},resource="memory",unit="byte"}} * on (namespace,pod) group_left(node) kube_pod_info{{{selector},node!=""}})',
        "pending_cpu_requests": f'sum(kube_pod_container_resource_requests{{{selector},resource="cpu",unit="core"}} * on (namespace,pod) group_left() (kube_pod_status_phase{{{selector},phase="Pending"}} == 1))',
        "pending_memory_requests": f'sum(kube_pod_container_resource_requests{{{selector},resource="memory",unit="byte"}} * on (namespace,pod) group_left() (kube_pod_status_phase{{{selector},phase="Pending"}} == 1))',
        "namespace_declared_cpu_requests": f'sum by (namespace) (kube_pod_container_resource_requests{{{selector},resource="cpu",unit="core"}})',
        "namespace_declared_memory_requests": f'sum by (namespace) (kube_pod_container_resource_requests{{{selector},resource="memory",unit="byte"}})',
        "namespace_node_bound_cpu_requests": f'sum by (namespace) (kube_pod_container_resource_requests{{{selector},resource="cpu",unit="core"}} * on (namespace,pod) group_left(node) kube_pod_info{{{selector},node!=""}})',
        "namespace_node_bound_memory_requests": f'sum by (namespace) (kube_pod_container_resource_requests{{{selector},resource="memory",unit="byte"}} * on (namespace,pod) group_left(node) kube_pod_info{{{selector},node!=""}})',
        "namespace_pending_cpu_requests": f'sum by (namespace) (kube_pod_container_resource_requests{{{selector},resource="cpu",unit="core"}} * on (namespace,pod) group_left() (kube_pod_status_phase{{{selector},phase="Pending"}} == 1))',
        "namespace_pending_memory_requests": f'sum by (namespace) (kube_pod_container_resource_requests{{{selector},resource="memory",unit="byte"}} * on (namespace,pod) group_left() (kube_pod_status_phase{{{selector},phase="Pending"}} == 1))',
        "namespace_cpu_usage": f'sum by (namespace) (rate(container_cpu_usage_seconds_total{{{selector},image!="",container!="POD"}}[5m]))',
        "namespace_memory_usage": f'sum by (namespace) (container_memory_working_set_bytes{{{selector},image!="",container!="POD"}})',
        "cluster_cpu_usage": f'sum(rate(container_cpu_usage_seconds_total{{{selector},image!="",container!="POD"}}[5m]))',
        "cluster_memory_usage": f'sum(container_memory_working_set_bytes{{{selector},image!="",container!="POD"}})',
        "gpu_capacity": f'sum by (resource, unit) (kube_node_status_allocatable{{{selector},resource=~".*gpu.*"}})',
        "gpu_bound_requests": f'sum by (resource, unit) (kube_pod_container_resource_requests{{{selector},resource=~".*gpu.*"}} * on (namespace,pod) group_left(node) kube_pod_info{{{selector},node!=""}})',
        "gpu_pending_requests": f'sum by (resource, unit) (kube_pod_container_resource_requests{{{selector},resource=~".*gpu.*"}} * on (namespace,pod) group_left() (kube_pod_status_phase{{{selector},phase="Pending"}} == 1))',
        "gpu_utilization": f'avg(cce_gpu_utilization{{{selector}}})',
        "gpu_memory_utilization": f'avg(cce_gpu_memory_utilization{{{selector}}})',
        "xgpu_memory_used": f'sum(xgpu_memory_used{{{selector}}})',
        "xgpu_memory_total": f'sum(xgpu_memory_total{{{selector}}})',
        "xgpu_core_used": f'sum(xgpu_core_percentage_used{{{selector}}})',
        "xgpu_core_total": f'sum(xgpu_core_percentage_total{{{selector}}})',
        "pool_cpu_total_capacity": f'sum by (label_cce_cloud_com_cce_nodepool) (kube_node_status_capacity{{{selector},resource="cpu",unit="core"}} * on (node) group_left(label_cce_cloud_com_cce_nodepool) kube_node_labels{{{selector}}})',
        "pool_node_count": f'count by (label_cce_cloud_com_cce_nodepool) (kube_node_labels{{{selector},label_cce_cloud_com_cce_nodepool!=""}})',
        "pool_memory_total_capacity": f'sum by (label_cce_cloud_com_cce_nodepool) (kube_node_status_capacity{{{selector},resource="memory",unit="byte"}} * on (node) group_left(label_cce_cloud_com_cce_nodepool) kube_node_labels{{{selector}}})',
        "pool_cpu_capacity": f'sum by (label_cce_cloud_com_cce_nodepool) (kube_node_status_allocatable{{{selector},resource="cpu",unit="core"}} * on (node) group_left(label_cce_cloud_com_cce_nodepool) kube_node_labels{{{selector}}})',
        "pool_memory_capacity": f'sum by (label_cce_cloud_com_cce_nodepool) (kube_node_status_allocatable{{{selector},resource="memory",unit="byte"}} * on (node) group_left(label_cce_cloud_com_cce_nodepool) kube_node_labels{{{selector}}})',
        "pool_cpu_requests": f'sum by (label_cce_cloud_com_cce_nodepool) (kube_pod_container_resource_requests{{{selector},resource="cpu",unit="core"}} * on (namespace,pod) group_left(node) kube_pod_info{{{selector}}} * on (node) group_left(label_cce_cloud_com_cce_nodepool) kube_node_labels{{{selector}}})',
        "pool_memory_requests": f'sum by (label_cce_cloud_com_cce_nodepool) (kube_pod_container_resource_requests{{{selector},resource="memory",unit="byte"}} * on (namespace,pod) group_left(node) kube_pod_info{{{selector}}} * on (node) group_left(label_cce_cloud_com_cce_nodepool) kube_node_labels{{{selector}}})',
        "hpa_max_replicas": f'max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_max_replicas{{{selector}}})',
    }
    def _run_query(item: tuple[str, str]) -> tuple[str, Dict[str, Any]]:
        name, query = item
        return name, _query(region, instance["aom_instance_id"], query, start, end, ak, sk, project_id, security_token)

    with ThreadPoolExecutor(max_workers=min(8, len(queries))) as executor:
        results = dict(executor.map(_run_query, queries.items()))
    for name, result in results.items():
        if not result.get("success"):
            gaps.append(f"{name}: {result.get('error')}")
        elif not _rows(result) and "pending_" not in name and not (name.startswith("gpu_") or name.startswith("xgpu_")):
            gaps.append(f"{name}: AOM returned no matching time series")

    total_capacity_cpu_row = _rows(results["cpu_total_capacity"])[0] if _rows(results["cpu_total_capacity"]) else {}
    total_capacity_memory_row = _rows(results["memory_total_capacity"])[0] if _rows(results["memory_total_capacity"]) else {}
    capacity_cpu_row = _rows(results["cpu_capacity"])[0] if _rows(results["cpu_capacity"]) else {}
    capacity_memory_row = _rows(results["memory_capacity"])[0] if _rows(results["memory_capacity"]) else {}
    declared_cpu_row = _rows(results["declared_cpu_requests"])[0] if _rows(results["declared_cpu_requests"]) else {}
    declared_memory_row = _rows(results["declared_memory_requests"])[0] if _rows(results["declared_memory_requests"]) else {}
    bound_cpu_row = _rows(results["node_bound_cpu_requests"])[0] if _rows(results["node_bound_cpu_requests"]) else {}
    bound_memory_row = _rows(results["node_bound_memory_requests"])[0] if _rows(results["node_bound_memory_requests"]) else {}
    pending_cpu_row = _rows(results["pending_cpu_requests"])[0] if _rows(results["pending_cpu_requests"]) else {}
    pending_memory_row = _rows(results["pending_memory_requests"])[0] if _rows(results["pending_memory_requests"]) else {}
    total_capacity_cpu_samples, total_capacity_memory_samples = _values(total_capacity_cpu_row), _values(total_capacity_memory_row)
    capacity_cpu_samples, capacity_memory_samples = _values(capacity_cpu_row), _values(capacity_memory_row)
    declared_cpu_samples, declared_memory_samples = _values(declared_cpu_row), _values(declared_memory_row)
    bound_cpu_samples, bound_memory_samples = _values(bound_cpu_row), _values(bound_memory_row)
    pending_cpu_samples, pending_memory_samples = _values(pending_cpu_row), _values(pending_memory_row)
    capacity_cpu = _minimum(capacity_cpu_samples)
    capacity_memory = _minimum(capacity_memory_samples)
    cpu_allocation_row = _aligned_ratio_row(bound_cpu_row, capacity_cpu_row)
    memory_allocation_row = _aligned_ratio_row(bound_memory_row, capacity_memory_row)
    unallocated_cpu_row = _aligned_difference_row(capacity_cpu_row, bound_cpu_row)
    unallocated_memory_row = _aligned_difference_row(capacity_memory_row, bound_memory_row)
    reserve_cpu = _minimum(_values(unallocated_cpu_row))
    reserve_memory = _minimum(_values(unallocated_memory_row))

    def _row_for_gpu_resource(result_name: str, resource: str) -> Dict[str, Any]:
        return next((row for row in _rows(results[result_name]) if (row.get("metric") or {}).get("resource") == resource), {})

    gpu_resources = []
    for capacity_metric in _rows(results["gpu_capacity"]):
        labels = capacity_metric.get("metric") or {}
        resource, unit = labels.get("resource"), labels.get("unit") or "integer"
        if not resource:
            continue
        bound_metric = _row_for_gpu_resource("gpu_bound_requests", resource)
        pending_metric = _row_for_gpu_resource("gpu_pending_requests", resource)
        allocation_metric = _aligned_ratio_row(bound_metric, capacity_metric)
        reserve_values = _aligned_difference(capacity_metric, bound_metric)
        minimum_reserve = _minimum(reserve_values)
        gpu_resources.append({
            "resource": resource,
            "unit": unit,
            "allocatable_trend": _time_series_summary(capacity_metric, unit),
            "node_bound_request_trend": _time_series_summary(bound_metric, unit),
            "pending_request_trend": _time_series_summary(pending_metric, unit),
            "allocation_trend": _time_series_summary(allocation_metric, "percent"),
            "minimum_unallocated": _resource(minimum_reserve, unit),
        })

    gpu_actual = {
        "gpu_utilization_percent_trend": _time_series_summary(_rows(results["gpu_utilization"])[0] if _rows(results["gpu_utilization"]) else {}, "percent"),
        "gpu_memory_utilization_percent_trend": _time_series_summary(_rows(results["gpu_memory_utilization"])[0] if _rows(results["gpu_memory_utilization"]) else {}, "percent"),
        "xgpu_memory_utilization_percent_trend": _time_series_summary(_aligned_ratio_row(_rows(results["xgpu_memory_used"])[0] if _rows(results["xgpu_memory_used"]) else {}, _rows(results["xgpu_memory_total"])[0] if _rows(results["xgpu_memory_total"]) else {}), "percent"),
        "xgpu_core_utilization_percent_trend": _time_series_summary(_aligned_ratio_row(_rows(results["xgpu_core_used"])[0] if _rows(results["xgpu_core_used"]) else {}, _rows(results["xgpu_core_total"])[0] if _rows(results["xgpu_core_total"]) else {}), "percent"),
    }
    gpu_detected = bool(gpu_resources) or any(trend.get("sample_count") for trend in gpu_actual.values())
    if gpu_resources and not any(trend.get("sample_count") for trend in gpu_actual.values()):
        gaps.append("GPU allocatable resources were found, but cce_gpu/xgpu utilization metrics were not collected by AOM.")

    namespace_rows: Dict[str, Dict[str, Any]] = {}
    for result, field in ((results["namespace_declared_cpu_requests"], "declared_cpu_request_metric"), (results["namespace_declared_memory_requests"], "declared_memory_request_metric"), (results["namespace_node_bound_cpu_requests"], "bound_cpu_request_metric"), (results["namespace_node_bound_memory_requests"], "bound_memory_request_metric"), (results["namespace_pending_cpu_requests"], "pending_cpu_request_metric"), (results["namespace_pending_memory_requests"], "pending_memory_request_metric"), (results["namespace_cpu_usage"], "cpu_usage_metric"), (results["namespace_memory_usage"], "memory_usage_metric")):
        for metric_row in _rows(result):
            namespace = (metric_row.get("metric") or {}).get("namespace")
            if namespace and namespace not in excluded:
                namespace_rows.setdefault(namespace, {"namespace": namespace})[field] = metric_row

    namespaces = []
    namespace_chart_series: Dict[str, Dict[str, Dict[str, list[list[float]]]]] = {}
    namespace_allocation_share_series: Dict[str, Dict[str, list[list[float]]]] = {"cpu": {}, "memory": {}}
    for row in namespace_rows.values():
        is_system_namespace = row["namespace"] in _SYSTEM_NAMESPACES
        declared_cpu_request_metric = row.pop("declared_cpu_request_metric", {})
        declared_memory_request_metric = row.pop("declared_memory_request_metric", {})
        cpu_request_metric, memory_request_metric = row.pop("bound_cpu_request_metric", {}), row.pop("bound_memory_request_metric", {})
        pending_cpu_request_metric = row.pop("pending_cpu_request_metric", {})
        pending_memory_request_metric = row.pop("pending_memory_request_metric", {})
        cpu_usage_metric, memory_usage_metric = row.pop("cpu_usage_metric", {}), row.pop("memory_usage_metric", {})
        cpu_samples, memory_samples = _values(cpu_usage_metric), _values(memory_usage_metric)
        declared_cpu_request, declared_memory_request = mean(_values(declared_cpu_request_metric)) if _values(declared_cpu_request_metric) else None, mean(_values(declared_memory_request_metric)) if _values(declared_memory_request_metric) else None
        cpu_request, memory_request = mean(_values(cpu_request_metric)) if _values(cpu_request_metric) else None, mean(_values(memory_request_metric)) if _values(memory_request_metric) else None
        cpu_ratio_samples = _aligned_ratio(cpu_usage_metric, cpu_request_metric)
        memory_ratio_samples = _aligned_ratio(memory_usage_metric, memory_request_metric)
        cpu_usage_trend = _time_series_summary(cpu_usage_metric, "core")
        memory_usage_trend = _time_series_summary(memory_usage_metric, "GiB")
        cpu_ratio_trend = _time_series_summary(_aligned_ratio_row(cpu_usage_metric, cpu_request_metric), "percent")
        memory_ratio_trend = _time_series_summary(_aligned_ratio_row(memory_usage_metric, memory_request_metric), "percent")
        cpu_allocatable_share_metric = _aligned_ratio_row(cpu_request_metric, capacity_cpu_row)
        memory_allocatable_share_metric = _aligned_ratio_row(memory_request_metric, capacity_memory_row)
        cpu_allocated_share_metric = _aligned_ratio_row(cpu_request_metric, bound_cpu_row)
        memory_allocated_share_metric = _aligned_ratio_row(memory_request_metric, bound_memory_row)
        cpu_usage_allocatable_share_metric = _aligned_ratio_row(cpu_usage_metric, capacity_cpu_row)
        memory_usage_allocatable_share_metric = _aligned_ratio_row(memory_usage_metric, capacity_memory_row)
        cpu_ratio_max, memory_ratio_max = max(cpu_ratio_samples, default=None), max(memory_ratio_samples, default=None)
        stable_oversized = not is_system_namespace and all(value is not None and value < 50 for value in (cpu_ratio_max, memory_ratio_max))
        cpu_rightsized = max(cpu_samples, default=None) * 1.3 if stable_oversized and cpu_samples else None
        memory_rightsized = max(memory_samples, default=None) * 1.3 if stable_oversized and memory_samples else None
        row.update({
            "declared_cpu_request_trend": _time_series_summary(declared_cpu_request_metric, "core"),
            "declared_memory_request_trend": _time_series_summary(declared_memory_request_metric, "GiB"),
            "node_bound_cpu_request_trend": _time_series_summary(cpu_request_metric, "core"),
            "node_bound_memory_request_trend": _time_series_summary(memory_request_metric, "GiB"),
            "pending_cpu_request_trend": _time_series_summary(pending_cpu_request_metric, "core"),
            "pending_memory_request_trend": _time_series_summary(pending_memory_request_metric, "GiB"),
            "cpu_allocatable_share_trend": _time_series_summary(cpu_allocatable_share_metric, "percent"),
            "memory_allocatable_share_trend": _time_series_summary(memory_allocatable_share_metric, "percent"),
            "cpu_allocated_cost_share_trend": _time_series_summary(cpu_allocated_share_metric, "percent"),
            "memory_allocated_cost_share_trend": _time_series_summary(memory_allocated_share_metric, "percent"),
            "cpu_usage_trend": cpu_usage_trend,
            "memory_usage_trend": memory_usage_trend,
            "cpu_usage_of_allocatable_trend": _time_series_summary(cpu_usage_allocatable_share_metric, "percent"),
            "memory_usage_of_allocatable_trend": _time_series_summary(memory_usage_allocatable_share_metric, "percent"),
            "cpu_usage_to_request_trend": cpu_ratio_trend,
            "memory_usage_to_request_trend": memory_ratio_trend,
            "estimated_rightsized_cpu_request_cores": _resource(cpu_rightsized, "core"),
            "estimated_rightsized_memory_request_gib": _resource(memory_rightsized, "GiB"),
            "estimated_reducible_cpu_request_cores": _resource(max(0, cpu_request - cpu_rightsized), "core") if cpu_request is not None and cpu_rightsized is not None else None,
            "estimated_reducible_memory_request_gib": _resource(max(0, memory_request - memory_rightsized), "GiB") if memory_request is not None and memory_rightsized is not None else None,
            "cpu_trend": _trend(cpu_samples),
            "memory_trend": _trend(memory_samples),
        })
        row["request_risk"] = "adjustment_not_recommended_system_namespace" if is_system_namespace else "under_requested" if any((value or 0) > 100 for value in (cpu_ratio_max, memory_ratio_max)) else "over_requested" if stable_oversized else "balanced"
        namespace_chart_series[row["namespace"]] = {
            "cpu": {
                "Requests": _chart_samples(cpu_request_metric, "core"),
                "Actual usage": _chart_samples(cpu_usage_metric, "core"),
            },
            "memory": {
                "Requests": _chart_samples(memory_request_metric, "GiB"),
                "Actual usage": _chart_samples(memory_usage_metric, "GiB"),
            },
        }
        namespace_allocation_share_series["cpu"][row["namespace"]] = _chart_samples(cpu_allocatable_share_metric, "percent")
        namespace_allocation_share_series["memory"][row["namespace"]] = _chart_samples(memory_allocatable_share_metric, "percent")
        namespaces.append(row)
    namespaces.sort(key=lambda item: max((item.get("cpu_allocatable_share_trend") or {}).get("average") or 0, (item.get("memory_allocatable_share_trend") or {}).get("average") or 0), reverse=True)

    pool_metrics: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for result_name, field in (("pool_node_count", "node_count"), ("pool_cpu_total_capacity", "cpu_total_capacity"), ("pool_memory_total_capacity", "memory_total_capacity"), ("pool_cpu_capacity", "cpu_capacity"), ("pool_memory_capacity", "memory_capacity"), ("pool_cpu_requests", "cpu_requests"), ("pool_memory_requests", "memory_requests")):
        for row in _rows(results[result_name]):
            pool_name = (row.get("metric") or {}).get("label_cce_cloud_com_cce_nodepool")
            if pool_name:
                pool_metrics.setdefault(pool_name, {})[field] = row

    def _pool_allocation(metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Optional[float]]:
        node_count_metric = metrics.get("node_count", {})
        total_cpu_capacity_metric, total_memory_capacity_metric = metrics.get("cpu_total_capacity", {}), metrics.get("memory_total_capacity", {})
        cpu_capacity_metric, memory_capacity_metric = metrics.get("cpu_capacity", {}), metrics.get("memory_capacity", {})
        cpu_request_metric, memory_request_metric = metrics.get("cpu_requests", {}), metrics.get("memory_requests", {})
        total_cpu_capacity, total_memory_capacity = _minimum(_values(total_cpu_capacity_metric)), _minimum(_values(total_memory_capacity_metric))
        cpu_capacity, memory_capacity = _minimum(_values(cpu_capacity_metric)), _minimum(_values(memory_capacity_metric))
        return {
            "node_count_trend": _time_series_summary(node_count_metric, "nodes"),
            "minimum_total_cpu_cores": _resource(total_cpu_capacity, "core"),
            "minimum_total_memory_gib": _resource(total_memory_capacity, "GiB"),
            "minimum_allocatable_cpu_cores": _resource(cpu_capacity, "core"),
            "minimum_allocatable_memory_gib": _resource(memory_capacity, "GiB"),
            "total_cpu_capacity_trend": _time_series_summary(total_cpu_capacity_metric, "core"),
            "total_memory_capacity_trend": _time_series_summary(total_memory_capacity_metric, "GiB"),
            "allocatable_cpu_capacity_trend": _time_series_summary(cpu_capacity_metric, "core"),
            "allocatable_memory_capacity_trend": _time_series_summary(memory_capacity_metric, "GiB"),
            "cpu_request_trend": _time_series_summary(cpu_request_metric, "core"),
            "memory_request_trend": _time_series_summary(memory_request_metric, "GiB"),
            "minimum_unallocated_cpu_cores": _resource(_minimum(_values(_aligned_difference_row(cpu_capacity_metric, cpu_request_metric))), "core"),
            "minimum_unallocated_memory_gib": _resource(_minimum(_values(_aligned_difference_row(memory_capacity_metric, memory_request_metric))), "GiB"),
            "cpu_unallocated_trend": _time_series_summary(_aligned_difference_row(cpu_capacity_metric, cpu_request_metric), "core"),
            "memory_unallocated_trend": _time_series_summary(_aligned_difference_row(memory_capacity_metric, memory_request_metric), "GiB"),
            "cpu_request_allocation_trend": _time_series_summary(_aligned_ratio_row(cpu_request_metric, cpu_capacity_metric), "percent"),
            "memory_request_allocation_trend": _time_series_summary(_aligned_ratio_row(memory_request_metric, memory_capacity_metric), "percent"),
        }

    def _pool_chart_series(metrics: Dict[str, Dict[str, Any]]) -> Dict[str, list[list[float]]]:
        return {
            "node_count": _chart_samples(metrics.get("node_count", {}), "nodes"),
            "allocatable_cpu": _chart_samples(metrics.get("cpu_capacity", {}), "core"),
            "allocated_cpu": _chart_samples(metrics.get("cpu_requests", {}), "core"),
            "allocatable_memory": _chart_samples(metrics.get("memory_capacity", {}), "GiB"),
            "allocated_memory": _chart_samples(metrics.get("memory_requests", {}), "GiB"),
        }

    pools = []
    node_chart_pools: Dict[str, Dict[str, list[list[float]]]] = {}
    for pool in nodepools.get("nodepools") or []:
        item = dict(pool)
        metrics = pool_metrics.pop(item.get("name"), {})
        item["allocation"] = _pool_allocation(metrics)
        if item.get("name"):
            node_chart_pools[item["name"]] = _pool_chart_series(metrics)
        pools.append(item)
    for name, metrics in pool_metrics.items():
        pools.append({"name": name, "allocation": _pool_allocation(metrics)})
        node_chart_pools[name] = _pool_chart_series(metrics)

    hpas = [{"namespace": (row.get("metric") or {}).get("namespace"), "name": (row.get("metric") or {}).get("horizontalpodautoscaler"), "max_replicas": _latest([row])} for row in _rows(results["hpa_max_replicas"])]
    stable_oversized = [row for row in namespaces if row.get("request_risk") == "over_requested"]
    under_requested = [row for row in namespaces if row.get("request_risk") == "under_requested"]
    estimated_reduction = {
        "cpu_request_cores": round(sum(row.get("estimated_reducible_cpu_request_cores") or 0 for row in stable_oversized), 3),
        "memory_request_gib": round(sum(row.get("estimated_reducible_memory_request_gib") or 0 for row in stable_oversized), 2),
        "method": "Per namespace, observed peak usage plus a 30% safety margin; valid only for stable oversized-request review candidates.",
    }
    recommendations = []
    if stable_oversized:
        names = ", ".join(row["namespace"] for row in stable_oversized[:5])
        recommendations.append({"priority": "medium", "category": "request_rightsizing", "message": f"{len(stable_oversized)} namespaces remain below 50% usage-to-Request throughout the observed window ({names}).", "action": "Reduce Requests only after validating peak usage and keeping an application-specific safety margin."})
    if under_requested:
        names = ", ".join(row["namespace"] for row in under_requested[:5])
        recommendations.append({"priority": "high", "category": "request_underallocation", "message": f"{len(under_requested)} non-system namespaces exceeded their CPU or memory Requests during the observed window ({names}).", "action": "Increase the affected workload Requests after verifying peak usage, throttling, OOM signals, and HPA behavior."})
    volatile_namespaces = [
        row for row in namespaces
        if row["namespace"] not in _SYSTEM_NAMESPACES and any(
            (trend.get("average") or 0) > 0 and ((trend.get("maximum") or 0) - (trend.get("minimum") or 0)) / trend["average"] >= 0.5
            for trend in (row.get("cpu_usage_trend") or {}, row.get("memory_usage_trend") or {})
        )
    ]
    if volatile_namespaces:
        names = ", ".join(row["namespace"] for row in volatile_namespaces[:5])
        recommendations.append({"priority": "medium", "category": "autoscaling", "message": f"Material CPU or memory usage variation was observed in {len(volatile_namespaces)} non-system namespaces ({names}).", "action": "Evaluate HPA for workload-level demand changes after Requests are calibrated."})
    if not hpas:
        recommendations.append({"priority": "info", "category": "hpa", "message": "No HPA metrics were discovered for the cluster.", "action": "For bursty workloads, add calibrated requests first, then evaluate HPA with a conservative min/max replica range."})

    cluster_usage = {
        "cpu_usage_trend": _time_series_summary(_rows(results["cluster_cpu_usage"])[0] if _rows(results["cluster_cpu_usage"]) else {}, "core"),
        "memory_usage_trend": _time_series_summary(_rows(results["cluster_memory_usage"])[0] if _rows(results["cluster_memory_usage"]) else {}, "GiB"),
    }
    total_cpu_trend = _time_series_summary(total_capacity_cpu_row, "core")
    total_memory_trend = _time_series_summary(total_capacity_memory_row, "GiB")
    cluster_node_count_trend = _time_series_summary(_rows(results["cluster_node_count"])[0] if _rows(results["cluster_node_count"]) else {}, "nodes")
    allocatable_cpu_trend = _time_series_summary(capacity_cpu_row, "core")
    allocatable_memory_trend = _time_series_summary(capacity_memory_row, "GiB")
    declared_cpu_trend = _time_series_summary(declared_cpu_row, "core")
    declared_memory_trend = _time_series_summary(declared_memory_row, "GiB")
    bound_cpu_trend = _time_series_summary(bound_cpu_row, "core")
    bound_memory_trend = _time_series_summary(bound_memory_row, "GiB")
    pending_cpu_trend = _time_series_summary(pending_cpu_row, "core")
    pending_memory_trend = _time_series_summary(pending_memory_row, "GiB")
    cpu_allocation_trend = _time_series_summary(cpu_allocation_row, "percent")
    memory_allocation_trend = _time_series_summary(memory_allocation_row, "percent")
    resource_cost_view = {
        "meaning": "Total capacity is Kubernetes node capacity. Allocatable capacity is the Pod-schedulable subset after system reservations. Allocated node-bound Pod Requests plus unallocated redundancy equals allocatable capacity at the same timestamp. Values are resource capacity, not monetary billing.",
        "total_capacity": {"cpu_cores_trend": total_cpu_trend, "memory_gib_trend": total_memory_trend},
        "total_allocatable": {"cpu_cores_trend": allocatable_cpu_trend, "memory_gib_trend": allocatable_memory_trend},
        "allocated": {"cpu_request_cores_trend": bound_cpu_trend, "memory_request_gib_trend": bound_memory_trend},
        "redundant_reserve": {"cpu_cores_trend": _time_series_summary(unallocated_cpu_row, "core"), "memory_gib_trend": _time_series_summary(unallocated_memory_row, "GiB")},
        "allocation_rate": {"cpu_percent_trend": cpu_allocation_trend, "memory_percent_trend": memory_allocation_trend},
    }
    resource_data_coverage = {
        "first_sample_at": total_cpu_trend.get("first_sample_at"),
        "last_sample_at": total_cpu_trend.get("last_sample_at"),
        "sample_count": total_cpu_trend.get("sample_count", 0),
        "step_seconds": 300,
    }
    response = {
        "success": True,
        "action": "analyze_cce_cost_optimization",
        "scope": {"region": region, "cluster_id": cluster_id, "analysis_start_date": start_day, "analysis_end_date_exclusive": end_day, "analysis_days": analysis_days, "time_zone": "Asia/Shanghai", "start": start, "end": end, "excluded_namespaces": sorted(excluded), "data_source": "AOM Prometheus"},
        "capacity": {"minimum_total_cpu_cores": _resource(_minimum(total_capacity_cpu_samples), "core"), "minimum_total_memory_gib": _resource(_minimum(total_capacity_memory_samples), "GiB"), "minimum_allocatable_cpu_cores": _resource(capacity_cpu, "core"), "minimum_allocatable_memory_gib": _resource(capacity_memory, "GiB"), "average_allocatable_cpu_cores": _resource(mean(capacity_cpu_samples), "core") if capacity_cpu_samples else None, "average_allocatable_memory_gib": _resource(mean(capacity_memory_samples), "GiB") if capacity_memory_samples else None, "total_cpu_trend": total_cpu_trend, "total_memory_trend": total_memory_trend, "allocatable_cpu_trend": allocatable_cpu_trend, "allocatable_memory_trend": allocatable_memory_trend, "declared_cpu_request_trend": declared_cpu_trend, "declared_memory_request_trend": declared_memory_trend, "node_bound_cpu_request_trend": bound_cpu_trend, "node_bound_memory_request_trend": bound_memory_trend, "pending_cpu_request_trend": pending_cpu_trend, "pending_memory_request_trend": pending_memory_trend, "cpu_request_allocation_trend": cpu_allocation_trend, "memory_request_allocation_trend": memory_allocation_trend, "minimum_unallocated_cpu_cores": _resource(reserve_cpu, "core"), "minimum_unallocated_memory_gib": _resource(reserve_memory, "GiB"), "calculation": "Node-bound Requests determine allocation and unallocated redundancy; Pending Requests are reported separately."},
        "resource_cost_view": resource_cost_view,
        "node_change": {"cluster_node_count_trend": cluster_node_count_trend},
        "resource_data_coverage": resource_data_coverage,
        "cluster_usage": cluster_usage,
        "gpu": {"detected": gpu_detected, "resources": gpu_resources, "actual_utilization": gpu_actual},
        "namespace_allocation_and_usage": namespaces[:max(1, top_n)],
        "namespace_count": len(namespaces),
        "node_pool_elasticity": pools,
        "hpa": {"count": len(hpas), "items": hpas, "discovery": "kube-state-metrics via AOM Prometheus", "optimization_note": "HPA can reduce replica-related waste only after Requests are calibrated. This report does not estimate billing savings from HPA."},
        "estimated_rightsizing_potential": estimated_reduction,
        "recommendations": recommendations,
        "promql": queries,
        "data_gaps": gaps,
        "disclaimer": "Potential savings are resource-capacity estimates, not billing estimates. Do not reduce requests or node count until workload SLOs, scheduling headroom, and autoscaler behavior are validated.",
    }
    if include_chart_series:
        response["_resource_chart_series"] = {
            "cpu": {
                "Total capacity": _chart_samples(total_capacity_cpu_row, "core"),
                "Allocatable": _chart_samples(capacity_cpu_row, "core"),
                "Allocated Requests": _chart_samples(bound_cpu_row, "core"),
                "Unallocated redundancy": _chart_samples(unallocated_cpu_row, "core"),
            },
            "memory": {
                "Total capacity": _chart_samples(total_capacity_memory_row, "GiB"),
                "Allocatable": _chart_samples(capacity_memory_row, "GiB"),
                "Allocated Requests": _chart_samples(bound_memory_row, "GiB"),
                "Unallocated redundancy": _chart_samples(unallocated_memory_row, "GiB"),
            },
            "allocation_rate": {
                "CPU": _chart_samples(cpu_allocation_row, "percent"),
                "Memory": _chart_samples(memory_allocation_row, "percent"),
            },
            "namespaces": {
                item["namespace"]: namespace_chart_series.get(item["namespace"], {})
                for item in namespaces[:max(1, top_n)]
            },
            "namespace_allocation_share": {
                resource: {
                    item["namespace"]: namespace_allocation_share_series[resource].get(item["namespace"], [])
                    for item in namespaces[:max(1, top_n)]
                }
                for resource in ("cpu", "memory")
            },
            "nodes": {
                "cluster_node_count": _chart_samples(_rows(results["cluster_node_count"])[0] if _rows(results["cluster_node_count"]) else {}, "nodes"),
                "pools": node_chart_pools,
            },
        }
    return response


def _trend_line(label: str, trend: Dict[str, Any], unit: str) -> str:
    if not trend or not trend.get("sample_count"):
        return f"- {label}: no matching data"
    return (
        f"- {label}: {trend.get('trend')}; "
        f"start {trend.get('start')} {unit}, end {trend.get('end')} {unit}, "
        f"min/max/average {trend.get('minimum')}/{trend.get('maximum')}/{trend.get('average')} {unit}, "
        f"change {trend.get('change')} {unit} ({trend.get('change_percent')}%)."
    )


def _write_resource_cost_chart(chart_series: Dict[str, Any], output_path: Path) -> Optional[str]:
    """Render a standalone HTML/SVG chart from internal five-minute AOM samples."""
    series = ()
    if chart_series.get("cpu") or chart_series.get("memory") or chart_series.get("allocation_rate"):
        series = (
            ("CPU Resource Trend", "cores", (
                ("Allocatable", (chart_series.get("cpu") or {}).get("Allocatable") or [], "#0891b2"),
                ("Allocated Requests", (chart_series.get("cpu") or {}).get("Allocated Requests") or [], "#d97706"),
            )),
            ("Memory Resource Trend", "GiB", (
                ("Allocatable", (chart_series.get("memory") or {}).get("Allocatable") or [], "#0891b2"),
                ("Allocated Requests", (chart_series.get("memory") or {}).get("Allocated Requests") or [], "#d97706"),
            )),
            ("Allocation Rate", "%", (
                ("CPU", (chart_series.get("allocation_rate") or {}).get("CPU") or [], "#7c3aed"),
                ("Memory", (chart_series.get("allocation_rate") or {}).get("Memory") or [], "#dc2626"),
            )),
        )

    namespace_colors = ("#2563eb", "#dc2626", "#0891b2", "#d97706", "#16a34a", "#7c3aed", "#be123c", "#0f766e")
    for namespace, resources in (chart_series.get("namespaces") or {}).items():
        series += (
            (f"Namespace {namespace}: CPU Request And Usage", "cores", (
                ("Requests", (resources.get("cpu") or {}).get("Requests") or [], "#7c3aed"),
                ("Actual usage", (resources.get("cpu") or {}).get("Actual usage") or [], "#dc2626"),
            )),
            (f"Namespace {namespace}: Memory Request And Usage", "GiB", (
                ("Requests", (resources.get("memory") or {}).get("Requests") or [], "#7c3aed"),
                ("Actual usage", (resources.get("memory") or {}).get("Actual usage") or [], "#dc2626"),
            )),
        )
    for resource, title in (("cpu", "Namespace CPU Allocation Share"), ("memory", "Namespace Memory Allocation Share")):
        shares = (chart_series.get("namespace_allocation_share") or {}).get(resource) or {}
        entries = tuple(
            (namespace, samples, namespace_colors[index % len(namespace_colors)])
            for index, (namespace, samples) in enumerate(shares.items())
            if samples
        )
        if entries:
            series += ((title, "%", entries),)

    nodes = chart_series.get("nodes") or {}
    if nodes.get("cluster_node_count"):
        node_entries = [("Cluster", nodes["cluster_node_count"], "#172554")]
        node_entries.extend(
            (pool_name, resources.get("node_count") or [], namespace_colors[index % len(namespace_colors)])
            for index, (pool_name, resources) in enumerate((nodes.get("pools") or {}).items())
            if resources.get("node_count")
        )
        series += (("Cluster And Node Pool Node Count", "nodes", tuple(node_entries)),)

    payload = {title: {label: samples for label, samples, _ in entries} for title, _, entries in series}
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    colors = {label: color for _, _, entries in series for label, _, color in entries}
    colors_json = json.dumps(colors).replace("</", "<\\/")
    document = f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>CCE Resource Cost Trend</title><style>
body {{ margin: 0; background: #f7f9fc; color: #172033; font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; }}
main {{ max-width: 1240px; margin: 0 auto; padding: 28px 20px 40px; }} h1 {{ margin: 0; font-size: 24px; }} p {{ color: #52627a; }}
.chart {{ background: #fff; border: 1px solid #dce3ed; border-radius: 6px; margin-top: 18px; padding: 16px; overflow-x: auto; }}
svg {{ display: block; min-width: 900px; width: 100%; height: auto; }} .grid {{ stroke: #e7edf5; stroke-width: 1; }} .axis {{ stroke: #8b98aa; stroke-width: 1; }}
.label {{ fill: #52627a; font-size: 12px; }} .title {{ fill: #172033; font-size: 16px; font-weight: 700; }} .legend {{ fill: #34435a; font-size: 12px; }}
.line {{ fill: none; stroke-width: 2.25; }} .point {{ stroke: #fff; stroke-width: 1; }}
</style></head><body><main><h1>CCE Resource Cost Trend</h1><p>Five-minute AOM samples. Hover a point to view its timestamp and value.</p><div id=\"charts\"></div></main>
<script>
const data = JSON.parse('{payload_json}'); const colors = JSON.parse('{colors_json}');
const charts = document.getElementById('charts'); const width=1160, height=300, left=76, right=32, chartTop=52, bottom=54;
for (const [title, groups] of Object.entries(data)) {{
  const entries = Object.entries(groups).filter(([, values]) => values.length);
  const panel = document.createElement('section'); panel.className='chart';
  if (!entries.length) {{ panel.textContent = title + ': no matching data'; charts.append(panel); continue; }}
  const samples = entries.flatMap(([, values]) => values); const xs=samples.map(p=>p[0]), ys=samples.map(p=>p[1]);
  const x0=Math.min(...xs), x1=Math.max(...xs), y0=Math.min(...ys), y1=Math.max(...ys); const xSpan=Math.max(1,x1-x0), padding=Math.max(0.5,(y1-y0)*0.08), low=y0-padding, high=y1+padding;
  const sx=x=>left+(x-x0)/xSpan*(width-left-right), sy=y=>chartTop+(high-y)/(high-low)*(height-chartTop-bottom);
  const esc=t=>String(t).replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));
  let svg=`<svg viewBox=\"0 0 ${{width}} ${{height}}\" role=\"img\" aria-label=\"${{esc(title)}}\"><text class=\"title\" x=\"${{left}}\" y=\"25\">${{esc(title)}}</text>`;
  for(let i=0;i<5;i++) {{ const y=chartTop+i*(height-chartTop-bottom)/4, value=high-i*(high-low)/4; svg+=`<line class=\"grid\" x1=\"${{left}}\" y1=\"${{y}}\" x2=\"${{width-right}}\" y2=\"${{y}}\"/><text class=\"label\" x=\"${{left-10}}\" y=\"${{y+4}}\" text-anchor=\"end\">${{value.toFixed(2)}}</text>`; }}
  svg+=`<line class=\"axis\" x1=\"${{left}}\" y1=\"${{height-bottom}}\" x2=\"${{width-right}}\" y2=\"${{height-bottom}}\"/>`;
  for(let i=0;i<5;i++) {{ const timestamp=x0+i*xSpan/4, x=sx(timestamp), label=new Date(timestamp*1000).toLocaleString(); svg+=`<text class=\"label\" x=\"${{x}}\" y=\"${{height-22}}\" text-anchor=\"middle\">${{label}}</text>`; }}
  entries.forEach(([label, values], index) => {{ const color=colors[label]||'#2563eb', points=values.map(p=>`${{sx(p[0]).toFixed(2)}},${{sy(p[1]).toFixed(2)}}`).join(' '); const lx=width-right-((entries.length-index)*170); svg+=`<polyline class=\"line\" stroke=\"${{color}}\" points=\"${{points}}\"/><line x1=\"${{lx}}\" y1=\"42\" x2=\"${{lx+20}}\" y2=\"42\" stroke=\"${{color}}\" stroke-width=\"3\"/><text class=\"legend\" x=\"${{lx+26}}\" y=\"46\">${{esc(label)}}</text>`; values.forEach(p=>{{const dt=new Date(p[0]*1000).toLocaleString(); svg+=`<circle class=\"point\" cx=\"${{sx(p[0]).toFixed(2)}}\" cy=\"${{sy(p[1]).toFixed(2)}}\" r=\"2.3\" fill=\"${{color}}\"><title>${{esc(label)}}: ${{p[1]}} at ${{esc(dt)}}</title></circle>`;}}); }});
  svg+='</svg>'; panel.innerHTML=svg; charts.append(panel);
}}
</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return str(output_path)


def _inline_report_html(value: str) -> str:
    escaped = html.escape(str(value), quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: f'<a href="{html.escape(match.group(2), quote=True)}">{match.group(1)}</a>',
        escaped,
    )


def _markdown_report_body(markdown: str, embedded_charts: Optional[Dict[str, str]] = None) -> str:
    """Render the report's constrained Markdown subset without external packages."""
    lines = markdown.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if embedded_charts and line in embedded_charts:
            blocks.append(embedded_charts[line])
            index += 1
            continue
        heading = re.fullmatch(r"(#{1,3})\s+(.+)", line)
        if heading:
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{_inline_report_html(heading.group(2))}</h{level}>")
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and re.match(r"^\|\s*[-:| ]+\|\s*$", lines[index + 1]):
            headers = [item.strip() for item in line.strip("|").split("|")]
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([item.strip() for item in lines[index].strip("|").split("|")])
                index += 1
            header_html = "".join(f"<th>{_inline_report_html(item)}</th>" for item in headers)
            row_html = "".join(
                "<tr>" + "".join(f"<td>{_inline_report_html(item)}</td>" for item in row) + "</tr>"
                for row in rows
            )
            blocks.append(f"<div class=\"table-wrap\"><table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table></div>")
            continue
        if line.startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append(f"<li>{_inline_report_html(lines[index][2:])}</li>")
                index += 1
            blocks.append("<ul>" + "".join(items) + "</ul>")
            continue
        blocks.append(f"<p>{_inline_report_html(line)}</p>")
        index += 1
    return "\n".join(blocks)


def _write_html_cost_report(report_markdown: str, cluster_chart_path: Optional[str], node_chart_path: Optional[str], namespace_chart_path: Optional[str], output_path: Path) -> str:
    def embedded_chart(title: str, chart_path: Optional[str]) -> str:
        if not chart_path:
            return ""
        chart_name = html.escape(Path(chart_path).name, quote=True)
        return f'<section class="trend"><iframe title="{title}" src="{chart_name}" loading="lazy"></iframe></section>'

    embedded_charts = {
        "{{CLUSTER_RESOURCE_TREND_CHART}}": embedded_chart("CCE cluster resource trends", cluster_chart_path),
        "{{NODE_CHANGE_TREND_CHART}}": embedded_chart("CCE node change trends", node_chart_path),
        "{{NAMESPACE_RESOURCE_TREND_CHART}}": embedded_chart("CCE namespace resource trends", namespace_chart_path),
    }
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CCE Cost Optimization Report</title><style>
:root {{ color: #172033; background: #f5f7fb; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
body {{ margin: 0; }} main {{ max-width: 1320px; margin: 0 auto; padding: 32px 24px 56px; }}
h1 {{ font-size: 30px; margin: 0 0 24px; }} h2 {{ font-size: 21px; margin: 32px 0 12px; }} h3 {{ font-size: 17px; margin: 24px 0 8px; }}
p, li {{ line-height: 1.55; }} code {{ background: #edf2f7; border-radius: 3px; padding: 2px 5px; }} a {{ color: #1769aa; }}
.trend, .table-wrap {{ background: #fff; border: 1px solid #dce3ed; border-radius: 6px; }} .trend {{ margin: 24px 0; padding: 16px; }} .trend h2 {{ margin-top: 0; }}
iframe {{ width: 100%; height: 1060px; border: 0; }} .table-wrap {{ overflow-x: auto; margin: 12px 0 20px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }} th, td {{ padding: 10px 12px; border-bottom: 1px solid #e4eaf2; text-align: left; vertical-align: top; white-space: nowrap; }} th {{ background: #f0f4f8; color: #334155; }}
</style></head><body><main>{_markdown_report_body(report_markdown, embedded_charts)}</main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return str(output_path)


def generate_cce_cost_optimization_report(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, analysis_date: Optional[str] = None, analysis_days: int = 1, top_n: int = 20, security_token: Optional[str] = None, exclude_namespaces: Optional[str] = None, output_file: Optional[str] = None, output_format: str = "html") -> Dict[str, Any]:
    """Run the cost analysis and render HTML and/or Markdown reports without cloud changes."""
    output_format = (output_format or "html").strip().lower()
    if output_format not in {"html", "markdown", "both"}:
        return {"success": False, "error": "output_format must be one of: html, markdown, both"}
    analysis = analyze_cce_cost_optimization(
        region=region,
        cluster_id=cluster_id,
        ak=ak,
        sk=sk,
        project_id=project_id,
        analysis_date=analysis_date,
        analysis_days=analysis_days,
        top_n=top_n,
        security_token=security_token,
        exclude_namespaces=exclude_namespaces,
        include_chart_series=True,
    )
    if not analysis.get("success"):
        return analysis

    scope = analysis["scope"]
    coverage = analysis.get("resource_data_coverage") or {}
    requested_path = Path(output_file) if output_file else Path("/tmp") / f"cce-resource-cost-{scope['cluster_id']}.html"
    report_path = requested_path if requested_path.suffix.lower() == ".html" else requested_path.with_suffix(".html")
    markdown_path = requested_path.with_suffix(".md") if requested_path.suffix.lower() != ".md" else requested_path
    chart_series = analysis.pop("_resource_chart_series", {})
    cluster_chart_path = _write_resource_cost_chart(
        {key: chart_series.get(key, {}) for key in ("cpu", "memory", "allocation_rate")},
        report_path.with_name(f"{report_path.stem}-cluster-trend.html"),
    )
    node_chart_path = _write_resource_cost_chart(
        {"nodes": chart_series.get("nodes", {})},
        report_path.with_name(f"{report_path.stem}-node-trend.html"),
    )
    namespace_chart_path = _write_resource_cost_chart(
        {key: chart_series.get(key, {}) for key in ("namespaces", "namespace_allocation_share")},
        report_path.with_name(f"{report_path.stem}-namespace-trend.html"),
    )
    resource_cost = analysis.get("resource_cost_view") or {}
    node_change = analysis.get("node_change") or {}

    def trend_value(trend: Dict[str, Any], key: str, unit: str) -> str:
        value = trend.get(key)
        return f"{value} {unit}" if value is not None else "N/A"

    def trend_span(trend: Dict[str, Any], unit: str) -> str:
        minimum, maximum = _number(trend.get("minimum")), _number(trend.get("maximum"))
        return f"{round(maximum - minimum, 3)} {unit}" if minimum is not None and maximum is not None else "N/A"

    def peak_share(pool_trend: Dict[str, Any], cluster_trend: Dict[str, Any]) -> str:
        pool_peak = _number(pool_trend.get("maximum"))
        cluster_peak = _number(cluster_trend.get("maximum"))
        if pool_peak is None or cluster_peak is None or cluster_peak <= 0:
            return "N/A"
        return f"{round(pool_peak * 100 / cluster_peak, 2)}%"

    def six_hour_windows() -> list[tuple[int, int, str]]:
        start_at = datetime.fromtimestamp(scope["start"], ZoneInfo(scope["time_zone"]))
        end_at = datetime.fromtimestamp(scope["end"], ZoneInfo(scope["time_zone"]))
        windows = []
        current = start_at
        while current < end_at:
            next_window = min(current + timedelta(hours=6), end_at)
            windows.append((int(current.timestamp()), int(next_window.timestamp()), f"{current:%m-%d %H:%M}-{next_window:%H:%M}"))
            current = next_window
        return windows

    def window_average(samples: list[list[float]], start_at: int, end_at: int, unit: str = "") -> str:
        valid_values = []
        for point in samples:
            if len(point) < 2:
                continue
            timestamp, value = _number(point[0]), _number(point[1])
            if timestamp is not None and value is not None and start_at <= timestamp < end_at:
                valid_values.append(value)
        if not valid_values:
            return "N/A"
        value = round(mean(valid_values), 3)
        return f"{value} {unit}" if unit else str(value)

    cluster_allocatable = resource_cost.get("total_allocatable") or {}
    cluster_allocatable_cpu = cluster_allocatable.get("cpu_cores_trend") or {}
    cluster_allocatable_memory = cluster_allocatable.get("memory_gib_trend") or {}
    trend_windows = six_hour_windows()

    lines = [
        "# CCE Cost Optimization Report",
        "",
        "## Scope",
        f"- Region: `{scope['region']}`",
        f"- Cluster ID: `{scope['cluster_id']}`",
        f"- Analysis window: {scope['analysis_start_date']} to {scope['analysis_end_date_exclusive']} ({scope['time_zone']})",
        f"- Data source: {scope['data_source']}",
        f"- AOM resource data coverage: {coverage.get('first_sample_at') or 'N/A'} to {coverage.get('last_sample_at') or 'N/A'} ({coverage.get('sample_count', 0)} samples at {coverage.get('step_seconds', 300)}-second intervals)",
        "",
        "## 1. Node Trends And Elasticity",
        "| Scope | Minimum nodes | Maximum nodes | Peak CPU capacity | Peak memory capacity | Observed elasticity |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        f"| Cluster | {trend_value(node_change.get('cluster_node_count_trend') or {}, 'minimum', '')} | {trend_value(node_change.get('cluster_node_count_trend') or {}, 'maximum', '')} | {trend_value((resource_cost.get('total_capacity') or {}).get('cpu_cores_trend') or {}, 'maximum', 'cores')} | {trend_value((resource_cost.get('total_capacity') or {}).get('memory_gib_trend') or {}, 'maximum', 'GiB')} | {trend_span((resource_cost.get('total_capacity') or {}).get('cpu_cores_trend') or {}, 'CPU cores')} CPU / {trend_span((resource_cost.get('total_capacity') or {}).get('memory_gib_trend') or {}, 'GiB')} memory |",
        "",
    ]
    lines.extend(["| Node pool | Minimum nodes | Maximum nodes | Autoscaling | Configured range | Peak allocatable CPU (cluster share) | Peak allocatable memory (cluster share) |", "| --- | ---: | ---: | --- | --- | ---: | ---: |"])
    for pool in analysis.get("node_pool_elasticity") or []:
        allocation = pool.get("allocation") or {}
        node_trend = allocation.get("node_count_trend") or {}
        cpu_trend = allocation.get("allocatable_cpu_capacity_trend") or {}
        memory_trend = allocation.get("allocatable_memory_capacity_trend") or {}
        lines.append(
            f"| `{pool.get('name')}` | {trend_value(node_trend, 'minimum', '')} | {trend_value(node_trend, 'maximum', '')} | `{pool.get('autoscaling_enabled')}` | {pool.get('min_node_count')} to {pool.get('max_node_count')} | {trend_value(cpu_trend, 'maximum', '')} ({peak_share(cpu_trend, cluster_allocatable_cpu)}) | {trend_value(memory_trend, 'maximum', 'GiB')} ({peak_share(memory_trend, cluster_allocatable_memory)}) |"
        )
    lines.extend([
        "", "## 2. Cluster Resource Allocation",
        "| Resource | Allocatable average | Allocated Request average | Redundant reserve average | Allocation rate average | Trend |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        f"| CPU cores | {trend_value((resource_cost.get('total_allocatable') or {}).get('cpu_cores_trend') or {}, 'average', '')} | {trend_value((resource_cost.get('allocated') or {}).get('cpu_request_cores_trend') or {}, 'average', '')} | {trend_value((resource_cost.get('redundant_reserve') or {}).get('cpu_cores_trend') or {}, 'average', '')} | {trend_value((resource_cost.get('allocation_rate') or {}).get('cpu_percent_trend') or {}, 'average', '%')} | {((resource_cost.get('allocation_rate') or {}).get('cpu_percent_trend') or {}).get('trend', 'N/A')} |",
        f"| Memory GiB | {trend_value((resource_cost.get('total_allocatable') or {}).get('memory_gib_trend') or {}, 'average', '')} | {trend_value((resource_cost.get('allocated') or {}).get('memory_request_gib_trend') or {}, 'average', '')} | {trend_value((resource_cost.get('redundant_reserve') or {}).get('memory_gib_trend') or {}, 'average', '')} | {trend_value((resource_cost.get('allocation_rate') or {}).get('memory_percent_trend') or {}, 'average', '%')} | {((resource_cost.get('allocation_rate') or {}).get('memory_percent_trend') or {}).get('trend', 'N/A')} |",
    ])
    cluster_cpu_series = chart_series.get("cpu") or {}
    cluster_memory_series = chart_series.get("memory") or {}
    allocation_rate_series = chart_series.get("allocation_rate") or {}
    if any(cluster_cpu_series.values()) or any(cluster_memory_series.values()):
        lines.extend([
            "", "### Six-Hour Resource Trend",
            "| Time window | Allocatable CPU | Allocated CPU Request | CPU allocation rate | Allocatable memory | Allocated memory Request | Memory allocation rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for window_start, window_end, label in trend_windows:
            lines.append(
                f"| {label} | {window_average(cluster_cpu_series.get('Allocatable') or [], window_start, window_end, 'cores')} | {window_average(cluster_cpu_series.get('Allocated Requests') or [], window_start, window_end, 'cores')} | {window_average(allocation_rate_series.get('CPU') or [], window_start, window_end, '%')} | {window_average(cluster_memory_series.get('Allocatable') or [], window_start, window_end, 'GiB')} | {window_average(cluster_memory_series.get('Allocated Requests') or [], window_start, window_end, 'GiB')} | {window_average(allocation_rate_series.get('Memory') or [], window_start, window_end, '%')} |"
            )
    gpu = analysis.get("gpu") or {}
    if gpu.get("detected"):
        lines.extend(["", "### GPU Capacity And Usage"])
        for resource in gpu.get("resources") or []:
            lines.extend([
                f"### {resource.get('resource')}",
                _trend_line("Allocatable", resource.get("allocatable_trend") or {}, resource.get("unit") or "units"),
                _trend_line("Node-bound Requests", resource.get("node_bound_request_trend") or {}, resource.get("unit") or "units"),
                _trend_line("Pending Requests", resource.get("pending_request_trend") or {}, resource.get("unit") or "units"),
                _trend_line("Allocation", resource.get("allocation_trend") or {}, "%"),
                f"- Minimum unallocated: {resource.get('minimum_unallocated')} {resource.get('unit')}.",
            ])
        actual_gpu = gpu.get("actual_utilization") or {}
        lines.extend([
            _trend_line("GPU utilization", actual_gpu.get("gpu_utilization_percent_trend") or {}, "%"),
            _trend_line("GPU memory utilization", actual_gpu.get("gpu_memory_utilization_percent_trend") or {}, "%"),
            _trend_line("xGPU memory utilization", actual_gpu.get("xgpu_memory_utilization_percent_trend") or {}, "%"),
            _trend_line("xGPU core utilization", actual_gpu.get("xgpu_core_utilization_percent_trend") or {}, "%"),
        ])
    lines.extend(["", "## 3. Namespace Cost Allocation", "| Namespace | CPU Request avg | CPU share | Memory Request avg | Memory share | CPU usage/Request | Memory usage/Request |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for namespace in analysis.get("namespace_allocation_and_usage") or []:
        cpu_request = namespace.get("node_bound_cpu_request_trend") or {}
        memory_request = namespace.get("node_bound_memory_request_trend") or {}
        cpu_share = namespace.get("cpu_allocatable_share_trend") or {}
        memory_share = namespace.get("memory_allocatable_share_trend") or {}
        cpu_usage = namespace.get("cpu_usage_trend") or {}
        memory_usage = namespace.get("memory_usage_trend") or {}
        cpu_ratio = namespace.get("cpu_usage_to_request_trend") or {}
        memory_ratio = namespace.get("memory_usage_to_request_trend") or {}
        lines.append(
            f"| `{namespace.get('namespace')}` | {trend_value(cpu_request, 'average', '')} | {trend_value(cpu_share, 'average', '%')} | {trend_value(memory_request, 'average', 'GiB')} | {trend_value(memory_share, 'average', '%')} | {trend_value(cpu_ratio, 'average', '%')} | {trend_value(memory_ratio, 'average', '%')} |"
        )
    namespace_series = chart_series.get("namespaces") or {}
    namespace_shares = chart_series.get("namespace_allocation_share") or {}
    if namespace_series:
        lines.append("\n### Six-Hour Namespace Trends")
    for namespace, resources in namespace_series.items():
        cpu_resources = resources.get("cpu") or {}
        memory_resources = resources.get("memory") or {}
        cpu_shares = (namespace_shares.get("cpu") or {}).get(namespace) or []
        memory_shares = (namespace_shares.get("memory") or {}).get(namespace) or []
        lines.extend([
            "", f"#### `{namespace}`",
            "| Time window | CPU Request | CPU share | CPU usage | Memory Request | Memory share | Memory usage |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for window_start, window_end, label in trend_windows:
            lines.append(
                f"| {label} | {window_average(cpu_resources.get('Requests') or [], window_start, window_end, 'cores')} | {window_average(cpu_shares, window_start, window_end, '%')} | {window_average(cpu_resources.get('Actual usage') or [], window_start, window_end, 'cores')} | {window_average(memory_resources.get('Requests') or [], window_start, window_end, 'GiB')} | {window_average(memory_shares, window_start, window_end, '%')} | {window_average(memory_resources.get('Actual usage') or [], window_start, window_end, 'GiB')} |"
            )
    lines.extend(["", "## 4. Optimization Recommendations"])
    for recommendation in analysis.get("recommendations") or []:
        lines.append(f"- **{recommendation.get('priority')} / {recommendation.get('category')}**: {recommendation.get('message')} {recommendation.get('action')}")
    gaps = analysis.get("data_gaps") or []
    if gaps:
        lines.extend(["", "## Data Gaps"])
        lines.extend(f"- {gap}" for gap in gaps)
    lines.extend(["", "## Disclaimer", analysis.get("disclaimer", "")])
    report_template = "\n".join(lines) + "\n"
    markdown_path.write_text(report_template, encoding="utf-8")
    html_template = report_template
    for heading, placeholder in (
        ("## 1. Node Trends And Elasticity\n", "{{NODE_CHANGE_TREND_CHART}}\n"),
        ("## 2. Cluster Resource Allocation\n", "{{CLUSTER_RESOURCE_TREND_CHART}}\n"),
        ("## 3. Namespace Cost Allocation\n", "{{NAMESPACE_RESOURCE_TREND_CHART}}\n"),
    ):
        html_template = html_template.replace(heading, f"{heading}{placeholder}", 1)
    html_report_path = _write_html_cost_report(html_template, cluster_chart_path, node_chart_path, namespace_chart_path, report_path)
    primary_output = markdown_path if output_format == "markdown" else html_report_path
    return {
        "success": True,
        "action": "generate_cce_cost_optimization_report",
        "output_format": output_format,
        "scope": scope,
        "report_markdown": report_template,
        "output_file": str(primary_output),
        "html_file": html_report_path,
        "markdown_file": str(markdown_path),
        "chart_file": cluster_chart_path,
        "node_chart_file": node_chart_path,
        "namespace_chart_file": namespace_chart_path,
        "analysis": analysis,
    }
