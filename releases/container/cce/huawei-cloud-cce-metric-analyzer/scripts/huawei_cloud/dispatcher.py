"""CLI dispatch helpers for the CCE metric analyzer."""

from __future__ import annotations

from typing import Any, Callable, Dict

from . import cce_cluster_monitoring, cce_metrics, ecs, elb, network


Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    if missing:
        return f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required"
    return None


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _metric_action(handler: Callable[..., Dict[str, Any]], *args: Any) -> Dict[str, Any]:
    result = handler(*args)
    if isinstance(result, dict) and result.get("success") is False:
        result.setdefault("hint", "Check hcloud configuration, IAM permissions, region, and resource identifiers.")
    return result


def _get_ecs_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return ecs.get_ecs_metrics(
        params["region"],
        params["instance_id"],
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _get_elb_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return elb.get_elb_metrics(
        params["region"],
        params["elb_id"],
        _to_int(params.get("hours"), 1),
        _to_int(params.get("period"), 300),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _get_eip_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return network.get_eip_metrics(
        params["region"],
        params["eip_id"],
        _to_int(params.get("hours"), 1),
        _to_int(params.get("period"), 300),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _get_nat_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return network.get_nat_gateway_metrics(
        params["region"],
        params["nat_gateway_id"],
        _to_int(params.get("hours"), 1),
        _to_int(params.get("period"), 300),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _cce_cluster_monitoring_aggregation(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_cluster_monitoring.cce_cluster_monitoring_aggregation_action(params)


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_get_cce_pod_metrics_topN": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_pod_metrics_topN,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace"),
            params.get("label_selector"),
            _to_int(params.get("top_n"), 10),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
            params.get("node_ip"),
        ),
    ),
    "huawei_get_cce_pod_metrics": (
        ("region", "cluster_id", "pod_name"),
        lambda params: _metric_action(
            cce_metrics.get_cce_pod_metrics,
            params["region"],
            params["cluster_id"],
            params["pod_name"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace"),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
        ),
    ),
    "huawei_get_cce_node_metrics_topN": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_node_metrics_topN,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            _to_int(params.get("top_n"), 10),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
        ),
    ),
    "huawei_get_cce_node_metrics": (
        ("region", "cluster_id", "node_ip"),
        lambda params: _metric_action(
            cce_metrics.get_cce_node_metrics,
            params["region"],
            params["cluster_id"],
            params["node_ip"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
        ),
    ),
    "huawei_get_ecs_metrics": (("region", "instance_id"), _get_ecs_metrics),
    "huawei_get_elb_metrics": (("region", "elb_id"), _get_elb_metrics),
    "huawei_get_eip_metrics": (("region", "eip_id"), _get_eip_metrics),
    "huawei_get_nat_gateway_metrics": (("region", "nat_gateway_id"), _get_nat_metrics),
    "huawei_cce_cluster_monitoring_aggregation": (
        ("region", "cluster_id", "start_time", "end_time"),
        _cce_cluster_monitoring_aggregation,
    ),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    if error:
        return {"success": False, "error": error}
    return handler(params)
