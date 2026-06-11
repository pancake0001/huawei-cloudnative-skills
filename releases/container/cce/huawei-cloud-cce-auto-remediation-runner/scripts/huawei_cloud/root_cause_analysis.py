"""Cross-signal root cause synthesis for Huawei Cloud CCE incidents."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import aom, cce, cce_diagnosis, cce_metrics, change_impact_analysis, dependency_impact_analysis, workload_rollout_diagnosis


REMEDIATION_SKILL = "huawei-cloud-cce-auto-remediation-runner"


def _to_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _confidence_value(value: Any, default: float = 0.5) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    text = str(value or "").lower()
    mapping = {"critical": 0.92, "high": 0.86, "medium": 0.62, "low": 0.35}
    return mapping.get(text, default)


def _md_cell(value: Any, max_len: int = 180) -> str:
    if value is None or value == "":
        return "-"
    text = str(value).replace("\n", " ").replace("|", "\\|").strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _safe_capture(label: str, collector: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    try:
        result = collector()
        if isinstance(result, dict):
            return result
        return {"success": True, "result": result}
    except Exception as exc:  # pragma: no cover - defensive cloud/API boundary
        return {"success": False, "stage": label, "error": str(exc), "error_type": type(exc).__name__}


def _workload_name(params: Dict[str, str]) -> Optional[str]:
    return params.get("workload_name") or params.get("target_name") or params.get("app_name") or params.get("name")


def _json_param(params: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    value = params.get(key)
    if not value:
        return None
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except (TypeError, json.JSONDecodeError):
        return None


def _extract_abnormal_object_analysis(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    direct = _json_param(params, "abnormal_object_analysis")
    if direct:
        return direct
    for key in ("root_cause_handoff", "inspection_handoff", "diagnosis", "inspection_result", "evidence"):
        payload = _json_param(params, key)
        if not payload:
            continue
        if payload.get("abnormal_object_analysis"):
            return payload["abnormal_object_analysis"]
        diagnosis = payload.get("diagnosis") if isinstance(payload.get("diagnosis"), dict) else None
        if diagnosis and diagnosis.get("abnormal_object_analysis"):
            return diagnosis["abnormal_object_analysis"]
        evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else payload
        if isinstance(evidence, dict) and evidence.get("abnormal_object_analysis"):
            return evidence["abnormal_object_analysis"]
        nested_diagnosis = evidence.get("diagnosis") if isinstance(evidence.get("diagnosis"), dict) else None
        if nested_diagnosis and nested_diagnosis.get("abnormal_object_analysis"):
            return nested_diagnosis["abnormal_object_analysis"]
    return None


def _scope_hints_from_abnormal_objects(abnormal_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Use inspector output only to narrow RCA scope, never as root-cause proof."""
    objects = (abnormal_analysis or {}).get("abnormal_objects") or []
    hints = {
        "source": "daily_inspector.abnormal_object_analysis" if abnormal_analysis else None,
        "namespaces": sorted({obj.get("namespace") for obj in objects if obj.get("namespace")}),
        "target_objects": [],
        "workloads": [],
        "pods": [],
        "nodes": [],
        "node_ips": [],
        "services": [],
        "ingresses": [],
        "time_window": (abnormal_analysis or {}).get("timeline") if abnormal_analysis else None,
        "note": "Inspector data is a scope hint only. RCA must collect fresh Events, metrics, changes, topology, and domain evidence before ranking causes.",
    }
    for obj in objects:
        kind = obj.get("kind") or "Unknown"
        ref = {"kind": kind, "namespace": obj.get("namespace"), "name": obj.get("name"), "key": obj.get("key")}
        hints["target_objects"].append(ref)
        if kind in {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Workload"} and obj.get("name"):
            hints["workloads"].append(ref)
        elif kind == "Pod" and obj.get("name"):
            hints["pods"].append(ref)
            workload = (obj.get("relationships") or {}).get("workload")
            if isinstance(workload, dict) and workload.get("name"):
                hints["workloads"].append(workload)
            node = (obj.get("relationships") or {}).get("node")
            if node:
                hints["nodes"].append(str(node))
        elif kind == "Node" and obj.get("name"):
            hints["nodes"].append(obj.get("name"))
        elif kind == "Service" and obj.get("name"):
            hints["services"].append(ref)
        elif kind == "Ingress" and obj.get("name"):
            hints["ingresses"].append(ref)
    for key in ("workloads", "pods", "services", "ingresses"):
        seen = set()
        unique = []
        for item in hints[key]:
            marker = (item.get("kind"), item.get("namespace"), item.get("name"))
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(item)
        hints[key] = unique
    hints["nodes"] = sorted({node for node in hints["nodes"] if node})
    return hints


def _apply_scope_hints(params: Dict[str, Any], scope_hints: Dict[str, Any]) -> Dict[str, Any]:
    scoped = dict(params)
    if not scoped.get("namespace") and len(scope_hints.get("namespaces") or []) == 1:
        scoped["namespace"] = scope_hints["namespaces"][0]
    if not _workload_name(scoped) and scope_hints.get("workloads"):
        workload = scope_hints["workloads"][0]
        scoped["target_name"] = workload.get("name")
        scoped["workload_name"] = workload.get("name")
        scoped["kind"] = workload.get("kind") if workload.get("kind") != "Workload" else scoped.get("kind", "deployment")
        if workload.get("namespace"):
            scoped["namespace"] = workload.get("namespace")
    return scoped


def _cause_key(cause: Dict[str, Any]) -> str:
    return str(cause.get("type") or cause.get("title") or "Unknown")


def _add_or_merge(causes: List[Dict[str, Any]], new_cause: Dict[str, Any]) -> None:
    key = _cause_key(new_cause)
    for cause in causes:
        if _cause_key(cause) != key:
            continue
        cause["confidence"] = max(_confidence_value(cause.get("confidence")), _confidence_value(new_cause.get("confidence")))
        cause.setdefault("evidence", []).extend(new_cause.get("evidence") or [])
        cause["evidence"] = cause["evidence"][:12]
        for recommendation in new_cause.get("recommendation") or []:
            if recommendation not in cause.setdefault("recommendation", []):
                cause["recommendation"].append(recommendation)
        return
    causes.append(new_cause)


def _causes_from_rollout(rollout: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not rollout.get("success"):
        return []
    result = []
    target = rollout.get("target") or {}
    target_key = f"{target.get('namespace')}/{target.get('name')}"
    for cause in rollout.get("top_causes") or []:
        cause_type = cause.get("type")
        if cause_type == "HealthyOrConverging":
            continue
        evidence = list(cause.get("evidence") or [])
        evidence.append({"source": "workload_rollout", "summary": rollout.get("summary", {}).get("headline"), "target": target_key})
        confidence = _confidence_value(cause.get("confidence"), 0.72)
        if cause_type == "ContainerCommandNotFound":
            confidence = max(confidence, 0.94)
        result.append({
            "type": cause_type,
            "title": cause.get("title") or "工作负载发布异常",
            "domain": "workload",
            "confidence": confidence,
            "evidence": evidence[:10],
            "counter_evidence": [],
            "recommendation": cause.get("recommendation") or [],
            "remediation_hint": _remediation_hint_for_rollout(cause_type),
        })
    return result


def _remediation_hint_for_rollout(cause_type: Optional[str]) -> Dict[str, Any]:
    if cause_type in {"ContainerCommandNotFound", "CrashLoopOrAppExit", "ProbeFailure", "ImagePullBlocked", "RolloutTimeout"}:
        return {
            "skill": REMEDIATION_SKILL,
            "action": "huawei_auto_remediation_run",
            "strategy": "rollback_previous_revision",
            "requires_confirmation": True,
        }
    return {"skill": REMEDIATION_SKILL, "requires_confirmation": True}


def _causes_from_change_impact(change_impact: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not change_impact.get("success"):
        return []
    result = []
    for change in change_impact.get("top_changes") or []:
        confidence = _confidence_value(change.get("confidence"), 0.55)
        score = _to_int(change.get("risk_score"), 0)
        if score >= 85:
            confidence = max(confidence, 0.82)
        result.append({
            "type": f"Change:{change.get('category')}",
            "title": change.get("title") or "近期变更可能触发故障",
            "domain": "change",
            "confidence": confidence,
            "evidence": change.get("evidence") or [],
            "counter_evidence": [],
            "recommendation": [f"复核该变更的 before/after 差异；如需回滚，先由 {REMEDIATION_SKILL} 生成预览。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "requires_confirmation": True},
        })
    return result


def _supporting_findings_from_dependency(dependency: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not dependency.get("success"):
        return []
    summary = dependency.get("summary") or {}
    health = summary.get("pod_health") or {}
    if summary.get("risk_level") not in {"High", "Medium"}:
        return []
    return [{
        "type": "DependencyImpactScope",
        "title": "目标服务异常的依赖传播与影响面",
        "domain": "dependency",
        "confidence": 0.72 if summary.get("risk_level") == "High" else 0.55,
        "evidence": [
            {
                "source": "dependency_topology",
                "summary": summary.get("risk_reason"),
                "pod_health": health,
                "paths": dependency.get("propagation_paths", [])[:3],
            }
        ],
        "counter_evidence": ["这是影响面/传播路径，不是直接根因；静态 Kubernetes 拓扑不能证明真实调用链，需要 APM/访问日志补强下游消费者证据。"],
        "recommendation": ["用于恢复优先级和验证范围：先恢复直接根因对象，再复查入口、Service endpoint 和上游访问错误率。"],
    }]


def _supporting_findings_from_alarms(alarms: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not alarms.get("success"):
        return []
    alarm_items = []
    for key in ("sudden_alarms", "focus_alarms", "alarms", "items"):
        value = alarms.get(key)
        if isinstance(value, list):
            alarm_items.extend(value)
    if not alarm_items:
        return []
    return [{
        "type": "AlarmEvidence",
        "title": "AOM 告警与故障窗口存在关联信号",
        "domain": "alarm",
        "confidence": 0.5,
        "evidence": [{"source": "aom", "summary": f"关联告警 {len(alarm_items)} 条", "sample": alarm_items[:5]}],
        "counter_evidence": ["告警本身通常是症状或旁证，不是独立根因；必须与工作负载、事件、变更和监控窗口交叉验证。"],
        "recommendation": ["用于增强或削弱其它根因候选的时间相关性：按突发告警时间回看对应 Pod/Node/Service 指标。"],
    }]


def _capture_pod_traffic_metrics(params: Dict[str, Any], common: Dict[str, Any]) -> Dict[str, Any]:
    region = params["region"]
    cluster_id = params["cluster_id"]
    namespace = params.get("namespace")
    top_n = _to_int(params.get("top_n"), 10)
    hours = _to_int(params.get("hours"), 1)
    access_key = common.get("ak")
    secret_key = common.get("sk")
    project_id = common.get("project_id")
    cluster_name = params.get("cluster_name") or cce_diagnosis.get_cluster_name(
        region,
        cluster_id,
        access_key,
        secret_key,
        project_id,
    )
    aom_result = cce_diagnosis.get_aom_instance(region, cluster_id, access_key, secret_key, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance unavailable"),
            "error_type": aom_result.get("error_type"),
        }
    filters = ['pod!=""']
    if namespace:
        filters.append(f'namespace="{namespace}"')
    filter_expr = ",".join(filters)
    query = (
        f'topk({top_n}, sum by (pod, namespace) ('
        f'rate(container_network_receive_bytes_total{{{filter_expr}}}[5m]) + '
        f'rate(container_network_transmit_bytes_total{{{filter_expr}}}[5m])'
        f'))'
    )
    raw = aom.get_aom_prom_metrics_http(
        region,
        aom_result["aom_instance_id"],
        query,
        hours=hours,
        ak=access_key,
        sk=secret_key,
        project_id=project_id,
    )
    if not raw.get("success"):
        return {"success": False, "error": raw.get("error", "pod traffic query failed"), "query": query}
    items = []
    for item in raw.get("result", {}).get("data", {}).get("result", []) or []:
        metric = item.get("metric") or {}
        values = item.get("values") or []
        if not values:
            continue
        latest = _to_float(values[-1][1])
        items.append({
            "pod": metric.get("pod") or metric.get("pod_name") or "unknown",
            "namespace": metric.get("namespace") or namespace,
            "latest_bytes_per_second": round(latest, 2) if latest is not None else None,
            "time_series": values,
        })
    items.sort(key=lambda item: item.get("latest_bytes_per_second") or 0, reverse=True)
    return {
        "success": True,
        "aom_instance_id": aom_result["aom_instance_id"],
        "query": query,
        "metrics": {
            "traffic_top_n": items[:top_n],
        },
        "summary": {
            "traffic_pod_count": len(items),
        },
    }


def _capture_coredns_metrics(params: Dict[str, Any], common: Dict[str, Any]) -> Dict[str, Any]:
    region = params["region"]
    cluster_id = params["cluster_id"]
    hours = _to_int(params.get("hours"), 1)
    access_key = common.get("ak")
    secret_key = common.get("sk")
    project_id = common.get("project_id")
    cluster_name = params.get("cluster_name") or cce_diagnosis.get_cluster_name(
        region,
        cluster_id,
        access_key,
        secret_key,
        project_id,
    )
    aom_result = cce_diagnosis.get_aom_instance(region, cluster_id, access_key, secret_key, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance unavailable"),
            "error_type": aom_result.get("error_type"),
        }

    coredns_filter = f'cluster_name="{cluster_name}",namespace="kube-system",pod=~".*coredns.*"'
    queries = {
        "cpu_usage_percent": (
            "max("
            f'sum by (pod, namespace) (rate(container_cpu_usage_seconds_total{{image!="",{coredns_filter}}}[5m])) '
            "/ on (pod, namespace) group_left "
            f'sum by (pod, namespace) (kube_pod_container_resource_limits{{resource="cpu",{coredns_filter}}}) * 100'
            ")"
        ),
        "success_rate_percent": (
            "sum(rate(coredns_dns_responses_total{rcode!~\"SERVFAIL|REFUSED\"}[5m])) "
            "/ sum(rate(coredns_dns_responses_total[5m])) * 100"
        ),
        "p99_latency_ms": (
            "histogram_quantile(0.99, sum(rate(coredns_dns_request_duration_seconds_bucket[5m])) by (le)) * 1000"
        ),
    }
    thresholds = {
        "cpu_usage_percent": 80,
        "success_rate_percent": 99,
        "p99_latency_ms": 100,
    }
    comparisons = {
        "cpu_usage_percent": "lte",
        "success_rate_percent": "gte",
        "p99_latency_ms": "lte",
    }

    metrics: Dict[str, Any] = {}
    anomalies = []
    unavailable_metrics = []
    for metric_name, query in queries.items():
        raw = aom.get_aom_prom_metrics_http(
            region,
            aom_result["aom_instance_id"],
            query,
            hours=hours,
            ak=access_key,
            sk=secret_key,
            project_id=project_id,
        )
        summary = _summarize_prom_series(raw)
        if summary is None:
            unavailable_metrics.append(metric_name)
            metrics[metric_name] = {
                "value": None,
                "threshold": thresholds[metric_name],
                "comparison": comparisons[metric_name],
                "status": "unavailable",
                "query": query,
                "error": raw.get("error") if isinstance(raw, dict) else None,
                "note": "metric not found or has no samples; not reported as an anomaly",
            }
            continue
        value = summary["latest"]
        threshold = thresholds[metric_name]
        comparison = comparisons[metric_name]
        is_anomaly = value < threshold if comparison == "gte" else value > threshold
        metrics[metric_name] = {
            **summary,
            "threshold": threshold,
            "comparison": comparison,
            "status": "abnormal" if is_anomaly else "normal",
            "query": query,
        }
        if is_anomaly:
            anomalies.append({
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "comparison": comparison,
                "latest_time": summary.get("latest_time"),
            })

    return {
        "success": True,
        "aom_instance_id": aom_result["aom_instance_id"],
        "metrics": metrics,
        "anomalies": anomalies,
        "data_gaps": [],
        "unavailable_metrics": unavailable_metrics,
        "summary": {
            "anomaly_count": len(anomalies),
            "unavailable_metric_count": len(unavailable_metrics),
        },
    }


def _capture_runtime_evidence(params: Dict[str, Any], scope_hints: Dict[str, Any]) -> Dict[str, Any]:
    namespace = params.get("namespace")
    region = params["region"]
    cluster_id = params["cluster_id"]
    common = {
        "ak": params.get("ak"),
        "sk": params.get("sk"),
        "project_id": params.get("project_id"),
    }
    captures = {
        "success": True,
        "scope_hints_used": {
            "namespaces": scope_hints.get("namespaces", []),
            "target_objects": scope_hints.get("target_objects", [])[:20],
            "nodes": scope_hints.get("nodes", []),
            "time_window": scope_hints.get("time_window"),
        },
        "data_gaps": [],
        "note": "Collected by root-cause-analyzer independently; inspector input is not treated as root-cause evidence.",
    }

    collectors = {
        "events": lambda: cce.get_kubernetes_events(region, cluster_id, namespace=namespace, limit=_to_int(params.get("event_limit"), 500), **common),
        "pods": lambda: cce.get_kubernetes_pods(region, cluster_id, namespace=namespace, **common),
        "nodes": lambda: cce.get_kubernetes_nodes(region, cluster_id, **common),
        "pod_metrics_topn": lambda: cce_metrics.get_cce_pod_metrics_topN(
            region=region,
            cluster_id=cluster_id,
            top_n=_to_int(params.get("top_n"), 10),
            hours=_to_int(params.get("hours"), 1),
            **common,
        ),
        "node_metrics_topn": lambda: cce_metrics.get_cce_node_metrics_topN(
            region=region,
            cluster_id=cluster_id,
            top_n=_to_int(params.get("top_n"), 10),
            hours=_to_int(params.get("hours"), 1),
            **common,
        ),
        "pod_traffic": lambda: _capture_pod_traffic_metrics(params, common),
        "coredns": lambda: _capture_coredns_metrics(params, common),
    }
    for key, collector in collectors.items():
        captures[key] = _safe_capture(key, collector)
        if not captures[key].get("success"):
            captures["success"] = False
            captures["data_gaps"].append({"source": key, "reason": captures[key].get("error")})
    captures["summary"] = {
        "headline": "RCA runtime evidence collected independently",
        "events": len(captures.get("events", {}).get("events", []) or []),
        "pods": len(captures.get("pods", {}).get("pods", []) or []),
        "nodes": len(captures.get("nodes", {}).get("nodes", []) or []),
    }
    return captures


def _causes_from_runtime_evidence(runtime: Dict[str, Any], scope_hints: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not runtime:
        return []
    causes: List[Dict[str, Any]] = []
    events = runtime.get("events", {}).get("events", []) if isinstance(runtime.get("events"), dict) else []
    pods = runtime.get("pods", {}).get("pods", []) if isinstance(runtime.get("pods"), dict) else []
    nodes = runtime.get("nodes", {}).get("nodes", []) if isinstance(runtime.get("nodes"), dict) else []
    pod_topn = runtime.get("pod_metrics_topn", {})
    node_topn = runtime.get("node_metrics_topn", {})
    pod_traffic = runtime.get("pod_traffic", {})
    coredns = runtime.get("coredns", {})

    event_text = json.dumps(events[:200], ensure_ascii=False).lower()
    if any(token in event_text for token in ("imagepullbackoff", "errimagepull", "pull image", "failed to pull image")):
        causes.append({
            "type": "ImagePullBlocked",
            "title": "镜像拉取链路异常导致 Pod 无法启动",
            "domain": "workload",
            "confidence": 0.78,
            "evidence": [{"source": "rca.kubernetes_events", "sample": _filter_events(events, ("ImagePull", "ErrImagePull", "Failed"))[:8]}],
            "counter_evidence": ["需要进一步确认镜像仓权限、镜像地址、节点到镜像仓网络和 pull secret。"],
            "recommendation": [f"校验镜像地址、SWR/第三方仓权限和 pull secret；恢复动作交给 {REMEDIATION_SKILL} 预览。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "strategy": "fix_image_or_pull_secret", "requires_confirmation": True},
        })
    if any(token in event_text for token in ("crashloopbackoff", "oomkilled", "back-off restarting failed container")):
        causes.append({
            "type": "PodRuntimeFailure",
            "title": "容器运行时异常或 OOM 导致应用实例不可用",
            "domain": "workload",
            "confidence": 0.76,
            "evidence": [
                {"source": "rca.kubernetes_events", "sample": _filter_events(events, ("CrashLoopBackOff", "OOMKilled", "BackOff"))[:8]},
                {"source": "rca.pod_metrics_topn", "summary": _metric_summary(pod_topn)},
            ],
            "counter_evidence": ["Pod 异常也可能由节点压力或发布变更触发，需要结合 node metrics 与 change impact 排序。"],
            "recommendation": ["查看容器退出码、日志、探针、资源限制和近期镜像/配置变更。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "strategy": "rollback_or_resize_workload", "requires_confirmation": True},
        })
    if any(token in event_text for token in ("failedscheduling", "insufficient", "nodepressure", "notready")):
        causes.append({
            "type": "SchedulingOrNodeConstraint",
            "title": "调度失败或节点约束导致 Pod 无法获得可用运行环境",
            "domain": "node",
            "confidence": 0.72,
            "evidence": [{"source": "rca.kubernetes_events", "sample": _filter_events(events, ("FailedScheduling", "Insufficient", "NotReady"))[:8]}],
            "counter_evidence": ["调度失败可能由资源请求、亲和性、污点或配额触发，需要结合 Pod spec 和节点状态确认。"],
            "recommendation": ["核对 requests/limits、nodeSelector/affinity、taints/tolerations、配额和节点可用资源。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "strategy": "scale_nodepool_or_adjust_scheduling_preview", "requires_confirmation": True},
        })

    pressured_nodes = _find_pressured_nodes(nodes, node_topn, scope_hints)
    node_bottlenecks = _node_resource_bottlenecks(nodes, node_topn, scope_hints)
    if node_bottlenecks:
        causes.append({
            "type": "NodeCapacityOrSystemBottleneck",
            "title": "节点性能瓶颈或系统层面异常已达到阈值",
            "domain": "node",
            "confidence": 0.84,
            "evidence": [
                {"source": "rca.node_bottleneck", "bottleneck_nodes": node_bottlenecks[:10]},
                {"source": "rca.node_metrics_topn", "summary": _metric_summary(node_topn)},
            ],
            "counter_evidence": ["需要继续区分是业务 Pod 消耗打满节点，还是 kubelet/runtime/ECS/磁盘/网络等系统层问题触发。"],
            "recommendation": ["优先确认高水位节点上的 Top Pod、节点 conditions、kubelet/runtime 事件和底层 ECS 指标，再选择扩容、迁移或节点修复。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "strategy": "cordon_drain_or_scale_nodepool_preview", "requires_confirmation": True},
        })
    elif pressured_nodes:
        causes.append({
            "type": "NodeConditionAbnormal",
            "title": "节点 condition 存在异常，需要排除系统层问题",
            "domain": "node",
            "confidence": 0.68,
            "evidence": [{"source": "rca.kubernetes_nodes", "pressured_nodes": pressured_nodes[:10]}],
            "counter_evidence": ["未看到节点资源监控达到瓶颈阈值，可能是短暂 condition、系统组件上报或非资源类节点问题。"],
            "recommendation": ["复核 Node condition 的 True 项、节点事件、NPD 上报和 kubelet/runtime 状态。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "strategy": "node_repair_or_observation_preview", "requires_confirmation": True},
        })

    hot_pods = _pod_topn_high(pod_topn)
    if hot_pods and not node_bottlenecks:
        traffic_analysis = _traffic_spike_analysis(pod_traffic, hot_pods)
        traffic_confirmed = traffic_analysis.get("spike_detected")
        causes.append({
            "type": "ApplicationPerformanceOrQuotaBottleneck",
            "title": "Pod 流量陡增导致应用性能瓶颈或资源配额打满" if traffic_confirmed else "应用自身性能瓶颈或 Pod 资源配额已打满",
            "domain": "workload",
            "confidence": _resource_bottleneck_confidence(hot_pods, traffic_confirmed),
            "evidence": [
                {"source": "rca.pod_metrics_topn", "hot_pods": hot_pods[:10]},
                {"source": "rca.pod_traffic", "traffic_analysis": traffic_analysis},
                {"source": "rca.node_metrics_topn", "node_status": "未发现 Node 资源瓶颈阈值被触发", "summary": _metric_summary(node_topn)},
            ],
            "counter_evidence": _application_bottleneck_counter_evidence(traffic_analysis),
            "recommendation": ["优先检查应用性能指标、Pod 网络流量、资源 limit/request；恢复预案优先考虑扩 Pod 副本、提高资源规格或配置 HPA，而不是节点类恢复。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "strategy": "resize_or_hpa_preview", "requires_confirmation": True},
        })
    coredns_bottleneck = _coredns_performance_bottleneck(coredns)
    if coredns_bottleneck:
        causes.append({
            "type": "DnsPerformanceBottleneck",
            "title": "CoreDNS 性能瓶颈导致集群 DNS 解析能力不足",
            "domain": "dns",
            "confidence": coredns_bottleneck["confidence"],
            "evidence": [
                {"source": "rca.coredns_metrics", **coredns_bottleneck},
            ],
            "counter_evidence": [
                "仍需结合业务侧 DNS 错误率、CoreDNS 日志和上游 DNS/网络状态，确认不是外部 DNS 或网络抖动引起。",
            ],
            "recommendation": ["优先扩容 kube-system/coredns 副本数，恢复后复查 CoreDNS CPU、解析成功率和 P99 解析时延。"],
            "remediation_hint": {"skill": REMEDIATION_SKILL, "strategy": "scale_coredns_out", "requires_confirmation": False},
        })
    return causes


def _target_params(params: Dict[str, str]) -> Dict[str, Any]:
    target = _workload_name(params)
    return {
        "region": params.get("region"),
        "cluster_id": params.get("cluster_id"),
        "namespace": params.get("namespace"),
        "workload_type": params.get("workload_type") or params.get("kind") or "deployment",
        "name": target,
        "workload_name": target,
    }


def _current_pod_count(captures: Dict[str, Dict[str, Any]], causes: List[Dict[str, Any]]) -> Optional[int]:
    dep_summary = (captures.get("dependency") or {}).get("summary") or {}
    pod_health = dep_summary.get("pod_health") or {}
    for key in ("total", "ready"):
        value = pod_health.get(key)
        if isinstance(value, int) and value > 0:
            return value
    for cause in causes:
        if cause.get("type") != "ApplicationPerformanceOrQuotaBottleneck":
            continue
        for evidence in cause.get("evidence") or []:
            hot_pods = evidence.get("hot_pods") or []
            if hot_pods:
                return len({f"{item.get('namespace')}/{item.get('pod')}" for item in hot_pods})
    return None


def _current_coredns_pod_count(captures: Dict[str, Dict[str, Any]]) -> Optional[int]:
    pods = ((captures.get("runtime_evidence") or {}).get("pods") or {}).get("pods", [])
    names = {
        pod.get("name")
        for pod in pods or []
        if pod.get("namespace") == "kube-system" and "coredns" in str(pod.get("name") or "").lower()
    }
    return len(names) if names else None


def _node_names_from_causes(causes: List[Dict[str, Any]]) -> List[str]:
    names: List[str] = []
    for cause in causes:
        if cause.get("type") not in {"NodeCapacityOrSystemBottleneck", "NodeConditionAbnormal", "SchedulingOrNodeConstraint"}:
            continue
        for evidence in cause.get("evidence") or []:
            for key in ("bottleneck_nodes", "pressured_nodes", "nodes"):
                for item in evidence.get(key) or []:
                    if isinstance(item, str):
                        name = item
                    elif isinstance(item, dict):
                        name = item.get("name") or item.get("node_name") or item.get("internal_ip") or item.get("node_ip")
                    else:
                        name = None
                    if name and name not in names:
                        names.append(str(name))
    return names


def _candidate(
    *,
    strategy: str,
    action: str,
    risk_level: str,
    target: Dict[str, Any],
    params: Dict[str, Any],
    reason: str,
    verification: List[str],
    requires_confirmation: bool = True,
) -> Dict[str, Any]:
    return {
        "skill": REMEDIATION_SKILL,
        "strategy": strategy,
        "action": action,
        "risk_level": risk_level,
        "target": {key: value for key, value in target.items() if value},
        "params": {key: value for key, value in params.items() if value is not None and value != ""},
        "reason": reason,
        "verification": verification,
        "requires_confirmation": requires_confirmation,
    }


def _build_remediation_candidates(
    params: Dict[str, str],
    captures: Dict[str, Dict[str, Any]],
    ranked_causes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    target = _target_params(params)
    candidates: List[Dict[str, Any]] = []
    seen = set()

    def add(item: Dict[str, Any]) -> None:
        key = (
            item.get("strategy"),
            item.get("action"),
            json.dumps(item.get("params") or {}, ensure_ascii=False, sort_keys=True),
        )
        if key in seen:
            return
        seen.add(key)
        candidates.append(item)

    cause_types = {cause.get("type") for cause in ranked_causes}
    rollback_types = {"RolloutTimeout", "ImagePullBlocked", "ContainerCommandNotFound", "CrashLoopOrAppExit", "ProbeFailure", "PodRuntimeFailure"}
    if rollback_types & cause_types and target.get("namespace") and target.get("name"):
        rollback_params = {
            "region": target.get("region"),
            "cluster_id": target.get("cluster_id"),
            "namespace": target.get("namespace"),
            "workload_type": target.get("workload_type"),
            "name": target.get("name"),
        }
        add(_candidate(
            strategy="rollback_previous_revision",
            action="huawei_rollback_cce_workload",
            risk_level="R1",
            target=target,
            params=rollback_params,
            reason="新版本不可用、镜像/启动/探针/运行时异常或 rollout 超时，可预览回滚到上一 revision。",
            verification=["huawei_workload_rollout_diagnose", "huawei_get_cce_events", "huawei_get_cce_pods"],
        ))

    if "ImagePullBlocked" in cause_types and target.get("namespace") and target.get("name"):
        add(_candidate(
            strategy="fix_image_or_pull_secret_preview",
            action="manual_review_image_pull_secret",
            risk_level="R3",
            target=target,
            params={
                "region": target.get("region"),
                "cluster_id": target.get("cluster_id"),
                "namespace": target.get("namespace"),
                "workload_type": target.get("workload_type"),
                "name": target.get("name"),
            },
            reason="先只读核验镜像名、tag、imagePullSecret、ServiceAccount 绑定和节点到仓库连通性；不要猜测或创建凭证。",
            verification=["huawei_workload_rollout_diagnose", "huawei_get_cce_events"],
            requires_confirmation=False,
        ))

    if "ApplicationPerformanceOrQuotaBottleneck" in cause_types and target.get("namespace") and target.get("name"):
        current_pods = _current_pod_count(captures, ranked_causes)
        min_replicas = current_pods or 1
        max_replicas = max(min_replicas + 1, min_replicas * 2)
        target_replicas = max_replicas
        risk = "R2" if current_pods else "R1"
        add(_candidate(
            strategy="scale_workload_out",
            action="huawei_scale_cce_workload",
            risk_level=risk,
            target=target,
            params={
                "region": target.get("region"),
                "cluster_id": target.get("cluster_id"),
                "namespace": target.get("namespace"),
                "workload_type": target.get("workload_type"),
                "name": target.get("name"),
                "replicas": target_replicas,
            },
            reason="Pod 资源持续高位且 Node 正常，优先通过扩 Pod 副本分摊负载；当目标副本数大于当前副本数且不涉及新增云资源费用时属于 R2。",
            verification=["huawei_workload_rollout_diagnose", "huawei_get_cce_pod_metrics_topN", "huawei_get_cce_events"],
        ))
        add(_candidate(
            strategy="configure_hpa",
            action="huawei_configure_cce_hpa",
            risk_level=risk,
            target=target,
            params={
                "region": target.get("region"),
                "cluster_id": target.get("cluster_id"),
                "namespace": target.get("namespace"),
                "workload_name": target.get("name"),
                "workload_type": target.get("workload_type"),
                "min_replicas": min_replicas,
                "max_replicas": max_replicas,
            },
            reason="扩副本后建议配置 HPA 固化弹性能力；当 minReplicas 不低于当前 Pod 数、maxReplicas 更大且不涉及新增云资源费用时属于 R2。",
            verification=["huawei_workload_rollout_diagnose", "huawei_get_cce_pod_metrics_topN"],
        ))
        add(_candidate(
            strategy="resize_workload",
            action="huawei_resize_cce_workload",
            risk_level="R1",
            target=target,
            params={
                "region": target.get("region"),
                "cluster_id": target.get("cluster_id"),
                "namespace": target.get("namespace"),
                "workload_type": target.get("workload_type"),
                "name": target.get("name"),
            },
            reason="如果 HPA 不适合或资源 limit/request 明显偏小，再预览工作负载资源规格调整。",
            verification=["huawei_workload_rollout_diagnose", "huawei_get_cce_pod_metrics_topN"],
        ))

    if "DnsPerformanceBottleneck" in cause_types:
        current_coredns_pods = _current_coredns_pod_count(captures)
        target_replicas = max((current_coredns_pods or 1) + 1, (current_coredns_pods or 1) * 2)
        coredns_risk = "R2" if current_coredns_pods else "R1"
        coredns_target = {
            "region": target.get("region"),
            "cluster_id": target.get("cluster_id"),
            "namespace": "kube-system",
            "workload_type": "deployment",
            "name": "coredns",
            "workload_name": "coredns",
        }
        add(_candidate(
            strategy="scale_coredns_out",
            action="huawei_scale_cce_workload",
            risk_level=coredns_risk,
            target=coredns_target,
            params={
                "region": target.get("region"),
                "cluster_id": target.get("cluster_id"),
                "namespace": "kube-system",
                "workload_type": "deployment",
                "name": "coredns",
                "replicas": target_replicas,
            },
            reason="CoreDNS CPU 高或 P99 解析时延升高，判断为 DNS 性能瓶颈；优先扩容 CoreDNS 副本分摊解析压力。能确认当前副本且不涉及新增云资源费用时属于 R2，否则按 R1 预览。",
            verification=["huawei_get_cce_pods", "huawei_get_aom_metrics", "huawei_workload_rollout_diagnose"],
        ))

    if {"NodeCapacityOrSystemBottleneck", "NodeConditionAbnormal", "SchedulingOrNodeConstraint"} & cause_types:
        node_names = _node_names_from_causes(ranked_causes)
        for node_name in node_names[:3]:
            node_target = {"region": target.get("region"), "cluster_id": target.get("cluster_id"), "node_name": node_name}
            add(_candidate(
                strategy="cordon_node",
                action="huawei_cce_node_cordon",
                risk_level="R2",
                target=node_target,
                params={
                    "region": target.get("region"),
                    "cluster_id": target.get("cluster_id"),
                    "node_name": node_name,
                },
                reason="节点资源或系统层面异常已达到阈值，优先 cordon 隔离对应节点，阻止新 Pod 继续调度到该节点。",
                verification=["huawei_get_kubernetes_nodes", "huawei_node_diagnose", "huawei_get_cce_events"],
            ))
            add(_candidate(
                strategy="drain_node_after_cordon",
                action="huawei_cce_node_drain",
                risk_level="R1",
                target=node_target,
                params={
                    "region": target.get("region"),
                    "cluster_id": target.get("cluster_id"),
                    "node_name": node_name,
                },
                reason="如果 cordon 后节点仍影响存量 Pod 或需要迁移负载，再预览 drain；drain 会驱逐存量 Pod，属于 R1。",
                verification=["huawei_get_kubernetes_nodes", "huawei_node_diagnose", "huawei_workload_rollout_diagnose"],
            ))
        add(_candidate(
            strategy="node_cordon_drain_or_scale_nodepool_preview",
            action="manual_select_node_or_nodepool_action",
            risk_level="R1",
            target={key: target.get(key) for key in ("region", "cluster_id")},
            params={"region": target.get("region"), "cluster_id": target.get("cluster_id")},
            reason="如果 RCA 未能唯一确定节点或需要补容量，先明确 node_name 或 nodepool_id，再按 R0/R1/R2/R3 风险规则生成预览。",
            verification=["huawei_get_kubernetes_nodes", "huawei_node_diagnose", "huawei_workload_rollout_diagnose"],
        ))

    return candidates


def _filter_events(events: List[Dict[str, Any]], keywords: Tuple[str, ...]) -> List[Dict[str, Any]]:
    result = []
    lowered = tuple(item.lower() for item in keywords)
    for event in events or []:
        text = json.dumps(event, ensure_ascii=False).lower()
        if any(keyword in text for keyword in lowered):
            result.append({
                "namespace": event.get("namespace"),
                "reason": event.get("reason"),
                "message": event.get("message"),
                "first_timestamp": event.get("first_timestamp"),
                "last_timestamp": event.get("last_timestamp"),
                "object": event.get("involved_object") or event.get("object"),
            })
    return result


def _metric_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
    payload = metrics.get("metrics", {}) if isinstance(metrics, dict) else {}
    return {
        "cpu_top_n": (payload.get("cpu_top_n") or [])[:5],
        "memory_top_n": (payload.get("memory_top_n") or [])[:5],
        "disk_top_n": (payload.get("disk_top_n") or [])[:5],
    }


def _find_pressured_nodes(nodes: List[Dict[str, Any]], node_topn: Dict[str, Any], scope_hints: Dict[str, Any]) -> List[Dict[str, Any]]:
    pressured = []
    for node in nodes or []:
        name = node.get("name") or node.get("node_name") or node.get("internal_ip")
        conditions = node.get("conditions") or []
        abnormal_conditions = _abnormal_node_conditions(conditions)
        if abnormal_conditions:
            pressured.append({
                "name": name,
                "status": node.get("status"),
                "conditions": abnormal_conditions,
                "taints": node.get("taints", []),
                "internal_ip": node.get("internal_ip"),
            })
    metrics = (node_topn.get("metrics", {}) if isinstance(node_topn, dict) else {})
    hot_names = set()
    for key in ("cpu_top_n", "memory_top_n", "disk_top_n"):
        for item in metrics.get(key, []) or []:
            value = item.get("cpu_usage_percent") or item.get("memory_usage_percent") or item.get("disk_usage_percent")
            if _to_float(value) is not None and float(value) >= 80:
                hot_names.add(item.get("node_name") or item.get("node_ip") or item.get("instance"))
    for name in hot_names:
        if name and not any(item.get("name") == name for item in pressured):
            pressured.append({"name": name, "status": "metric_high", "conditions": [], "taints": []})
    return pressured


def _abnormal_node_conditions(conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    abnormal = []
    for condition in conditions or []:
        ctype = condition.get("type")
        status = str(condition.get("status")).lower()
        if ctype == "Ready" and status != "true":
            abnormal.append(condition)
        elif ctype in {"MemoryPressure", "DiskPressure", "PIDPressure", "NetworkUnavailable"} and status == "true":
            abnormal.append(condition)
        elif ctype and ctype.endswith("Problem") and status == "true":
            abnormal.append(condition)
    return abnormal


def _node_resource_bottlenecks(
    nodes: List[Dict[str, Any]],
    node_topn: Dict[str, Any],
    scope_hints: Dict[str, Any],
) -> List[Dict[str, Any]]:
    bottlenecks = []
    node_index = {
        node.get("name") or node.get("node_name") or node.get("internal_ip"): node
        for node in nodes or []
    }
    metrics = node_topn.get("metrics", {}) if isinstance(node_topn, dict) else {}
    specs = (
        ("cpu_top_n", "cpu_usage_percent", 80),
        ("memory_top_n", "memory_usage_percent", 80),
        ("disk_top_n", "disk_usage_percent", 85),
    )
    for list_key, field, threshold in specs:
        for item in metrics.get(list_key, []) or []:
            value = _to_float(item.get(field))
            if value is None or value < threshold:
                continue
            name = item.get("node_name") or item.get("node_ip") or item.get("instance")
            node = node_index.get(name) or {}
            bottlenecks.append({
                "name": name,
                "metric": field,
                "value": round(value, 2),
                "threshold": threshold,
                "status": item.get("status"),
                "conditions": _abnormal_node_conditions(node.get("conditions") or []),
                "internal_ip": node.get("internal_ip") or item.get("node_ip"),
            })
    for node in nodes or []:
        abnormal_conditions = _abnormal_node_conditions(node.get("conditions") or [])
        if not abnormal_conditions:
            continue
        name = node.get("name") or node.get("node_name") or node.get("internal_ip")
        if not any(item.get("name") == name for item in bottlenecks):
            bottlenecks.append({
                "name": name,
                "metric": "node_condition",
                "value": "abnormal",
                "threshold": "condition_true_or_ready_false",
                "conditions": abnormal_conditions,
                "internal_ip": node.get("internal_ip"),
            })
    return bottlenecks


def _pod_topn_high(pod_topn: Dict[str, Any]) -> List[Dict[str, Any]]:
    metrics = pod_topn.get("metrics", {}) if isinstance(pod_topn, dict) else {}
    hot = []
    for key, field, threshold in (
        ("cpu_top_n", "cpu_usage_percent", 70),
        ("memory_top_n", "memory_usage_percent", 80),
    ):
        for item in metrics.get(key, []) or []:
            value = item.get(field)
            if _to_float(value) is not None and float(value) >= threshold:
                hot.append({
                    "metric": field,
                    "namespace": item.get("namespace"),
                    "pod": item.get("pod"),
                    "value": round(float(value), 2),
                    "threshold": threshold,
                    "status": item.get("status"),
                    "sustained_points": _count_sustained_points(item.get("time_series", []), threshold),
                    "peak": _series_peak(item.get("time_series", [])),
                })
    return hot


def _traffic_spike_analysis(pod_traffic: Dict[str, Any], hot_pods: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(pod_traffic, dict) or not pod_traffic.get("success"):
        return {
            "checked": False,
            "spike_detected": False,
            "reason": pod_traffic.get("error", "pod traffic metrics unavailable") if isinstance(pod_traffic, dict) else "pod traffic metrics unavailable",
        }
    hot_names = {item.get("pod") for item in hot_pods if item.get("pod")}
    traffic_items = (pod_traffic.get("metrics") or {}).get("traffic_top_n", []) or []
    matched = []
    for item in traffic_items:
        if hot_names and item.get("pod") not in hot_names:
            continue
        analysis = _series_spike(item.get("time_series", []))
        matched.append({
            "namespace": item.get("namespace"),
            "pod": item.get("pod"),
            "latest_bytes_per_second": item.get("latest_bytes_per_second"),
            **analysis,
        })
    spike_items = [item for item in matched if item.get("spike_detected")]
    return {
        "checked": True,
        "spike_detected": bool(spike_items),
        "matched_pods": matched[:10],
        "spike_pods": spike_items[:10],
        "note": "Traffic spike is inferred from pod receive+transmit bytes/s baseline vs recent/peak values.",
    }


def _series_spike(time_series: List[Any]) -> Dict[str, Any]:
    values = []
    for point in time_series or []:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            value = _to_float(point[1])
            if value is not None:
                values.append(value)
    if len(values) < 6:
        return {"spike_detected": False, "reason": "insufficient traffic datapoints"}
    midpoint = max(1, len(values) // 2)
    baseline_values = values[:midpoint]
    recent_values = values[midpoint:]
    baseline = sum(baseline_values) / len(baseline_values)
    recent = sum(recent_values) / len(recent_values)
    peak = max(values)
    ratio_recent = (recent / baseline) if baseline > 0 else None
    ratio_peak = (peak / baseline) if baseline > 0 else None
    spike = (
        (ratio_recent is not None and ratio_recent >= 1.8 and recent - baseline >= 1024)
        or (ratio_peak is not None and ratio_peak >= 2.5 and peak - baseline >= 2048)
    )
    return {
        "spike_detected": spike,
        "baseline_bytes_per_second": round(baseline, 2),
        "recent_bytes_per_second": round(recent, 2),
        "peak_bytes_per_second": round(peak, 2),
        "recent_to_baseline_ratio": round(ratio_recent, 2) if ratio_recent is not None else None,
        "peak_to_baseline_ratio": round(ratio_peak, 2) if ratio_peak is not None else None,
    }


def _count_sustained_points(time_series: List[Any], threshold: float) -> int:
    count = 0
    for point in time_series or []:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            value = _to_float(point[1])
            if value is not None and value >= threshold:
                count += 1
    return count


def _series_peak(time_series: List[Any]) -> Optional[float]:
    values = []
    for point in time_series or []:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            value = _to_float(point[1])
            if value is not None:
                values.append(value)
    return round(max(values), 2) if values else None


def _resource_bottleneck_confidence(hot_pods: List[Dict[str, Any]], traffic_confirmed: bool = False) -> float:
    if not hot_pods:
        return 0.5
    peak = max((_to_float(item.get("peak")) or _to_float(item.get("value")) or 0) for item in hot_pods)
    sustained = max((item.get("sustained_points") or 0) for item in hot_pods)
    bonus = 0.05 if traffic_confirmed else 0
    if peak >= 95 and sustained >= 5:
        return min(0.92, 0.86 + bonus)
    if peak >= 90:
        return min(0.88, 0.8 + bonus)
    return min(0.8, 0.72 + bonus)


def _application_bottleneck_counter_evidence(traffic_analysis: Dict[str, Any]) -> List[str]:
    if traffic_analysis.get("spike_detected"):
        return ["仍需业务 QPS、请求耗时、线程池/连接池、GC、慢查询等应用指标来区分正常流量增长与代码性能瓶颈。"]
    if traffic_analysis.get("checked"):
        return ["Pod 流量监控未发现明确陡增，更偏向应用代码性能瓶颈、资源 limit/request 偏小、后台任务或内部热点。"]
    return ["未获取到 Pod 流量监控，仍需业务 QPS、ELB/Ingress 指标或应用监控补强流量增长证据。"]


def _parse_ts(ts: Any) -> Optional[float]:
    try:
        value = float(ts)
        return value / 1000 if value > 10_000_000_000 else value
    except (TypeError, ValueError):
        return None


def _format_ts(ts: Any) -> Any:
    value = _parse_ts(ts)
    if value is None:
        return ts
    try:
        return datetime.fromtimestamp(value, timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")
    except (OSError, ValueError):
        return ts


def _summarize_prom_series(query_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    series = (
        query_result.get("result", {})
        .get("data", {})
        .get("result", [])
        if isinstance(query_result, dict)
        else []
    )
    points = []
    for item in series or []:
        for point in item.get("values", []) or []:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                value = _to_float(point[1])
                if value is not None:
                    points.append((point[0], value))
    if not points:
        return None
    points.sort(key=lambda item: _parse_ts(item[0]) or 0)
    latest_ts, latest_value = points[-1]
    values = [value for _, value in points]
    return {
        "latest": round(latest_value, 2),
        "latest_time": _format_ts(latest_ts),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(sum(values) / len(values), 2),
        "sample_count": len(points),
    }


def _coredns_performance_bottleneck(coredns: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(coredns, dict) or not coredns.get("success"):
        return None
    metrics = coredns.get("metrics") or {}
    anomalies = coredns.get("anomalies") or []
    cpu_high = any(item.get("metric") == "cpu_usage_percent" for item in anomalies)
    latency_high = any(item.get("metric") == "p99_latency_ms" for item in anomalies)
    success_low = any(item.get("metric") == "success_rate_percent" for item in anomalies)
    if not (cpu_high or latency_high):
        return None
    confidence = 0.84
    if cpu_high and latency_high:
        confidence = 0.9
    elif latency_high and success_low:
        confidence = 0.88
    return {
        "summary": "CoreDNS CPU 高或 P99 解析时延升高，符合 DNS 性能瓶颈特征。",
        "cpu_high": cpu_high,
        "latency_high": latency_high,
        "success_rate_low": success_low,
        "metrics": metrics,
        "anomalies": anomalies,
        "unavailable_metrics": coredns.get("unavailable_metrics", []),
        "confidence": confidence,
    }


def _to_float(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
        if parsed != parsed or parsed in (float("inf"), float("-inf")):
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _rank_causes(causes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def score(cause: Dict[str, Any]) -> float:
        confidence = _confidence_value(cause.get("confidence"))
        evidence_bonus = min(len(cause.get("evidence") or []) * 0.025, 0.08)
        domain_bonus = 0.05 if cause.get("domain") == "workload" else 0
        return confidence + evidence_bonus + domain_bonus

    ranked = sorted(causes, key=score, reverse=True)
    for index, cause in enumerate(ranked, start=1):
        cause["rank"] = index
        cause["confidence"] = round(_confidence_value(cause.get("confidence")), 2)
    return ranked


def _capture_status_rows(captures: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    labels = {
        "scope_hints": "巡检入口线索",
        "runtime_evidence": "RCA 独立事件/监控/状态取证",
        "rollout": "Workload 发布诊断",
        "dependency": "依赖影响面分析",
        "change": "变更影响分析",
        "alarms": "AOM 告警关联",
    }
    rows = []
    for key, label in labels.items():
        item = captures.get(key)
        if not item:
            rows.append((label, "跳过", "未启用或缺少必要范围"))
            continue
        rows.append((label, "成功" if item.get("success") else "失败", item.get("error") or item.get("summary", {}).get("headline") or "已采集"))
    return rows


def _timeline_rows(captures: Dict[str, Dict[str, Any]]) -> str:
    rows = ["| 来源 | 时间/阶段 | 事件 |", "| --- | --- | --- |"]
    scope_hints = captures.get("scope_hints") or {}
    if scope_hints.get("success"):
        timeline = scope_hints.get("scope_hints", {}).get("time_window") or {}
        if timeline.get("first_seen"):
            rows.append(f"| Inspector Hint | {_md_cell(timeline.get('first_seen'))} | 巡检提示的首次异常时间，用作 RCA 查询窗口线索 |")
        if timeline.get("last_seen"):
            rows.append(f"| Inspector Hint | {_md_cell(timeline.get('last_seen'))} | 巡检提示的最近异常时间，用作 RCA 查询窗口线索 |")
    runtime = captures.get("runtime_evidence") or {}
    for event in (runtime.get("events") or {}).get("events", [])[:20]:
        event_time = event.get("last_timestamp") or event.get("event_time") or event.get("first_timestamp")
        if event_time:
            rows.append(f"| RCA K8s Event | {_md_cell(event_time)} | {_md_cell(event.get('reason'))}: {_md_cell(event.get('message'), 260)} |")
    rollout = captures.get("rollout") or {}
    if rollout.get("success"):
        for event in (rollout.get("events") or {}).get("timeline") or []:
            rows.append(f"| K8s Event | {_md_cell(event.get('event_time') or event.get('last_timestamp'))} | {_md_cell(event.get('reason'))}: {_md_cell(event.get('message'), 260)} |")
    change = captures.get("change") or {}
    if change.get("success"):
        for item in change.get("top_changes") or []:
            rows.append(f"| Audit Change | {_md_cell(item.get('time'))} | {_md_cell(item.get('verb'))} {_md_cell(item.get('object_key'))}: {_md_cell(item.get('title'))} |")
    if len(rows) == 2:
        rows.append("| - | - | 未收集到可展示时间线 |")
    return "\n".join(rows)


def build_markdown_report(
    trace_id: str,
    params: Dict[str, str],
    captures: Dict[str, Dict[str, Any]],
    causes: List[Dict[str, Any]],
    supporting_findings: Optional[List[Dict[str, Any]]] = None,
) -> str:
    target = _workload_name(params) or "未指定"
    top = causes[0] if causes else None
    conclusion = (
        f"最高置信根因是 `{top.get('title')}`，类型 `{top.get('type')}`，置信度 `{top.get('confidence')}`。"
        if top
        else "当前证据不足以给出明确根因，需要补齐事件、日志、审计或指标数据。"
    )
    status_rows = [
        "| 数据源 | 状态 | 说明 |",
        "| --- | --- | --- |",
        *[f"| {_md_cell(source)} | {_md_cell(status)} | {_md_cell(note, 260)} |" for source, status, note in _capture_status_rows(captures)],
    ]
    cause_rows = ["| 排名 | 根因候选 | 域 | 置信度 | 关键证据 |", "| --- | --- | --- | --- | --- |"]
    for cause in causes[:3]:
        evidence = cause.get("evidence") or []
        cause_rows.append(
            f"| {cause.get('rank')} | {_md_cell(cause.get('title'))} | {_md_cell(cause.get('domain'))} | "
            f"{_md_cell(cause.get('confidence'))} | {_md_cell(evidence[0] if evidence else '-', 300)} |"
        )
    if len(cause_rows) == 2:
        cause_rows.append("| - | - | - | - | - |")

    evidence_lines = []
    for cause in causes[:3]:
        evidence_lines.append(f"### Top {cause.get('rank')}: {cause.get('title')}")
        for item in cause.get("evidence") or []:
            evidence_lines.append(f"- `{item.get('source', cause.get('domain')) if isinstance(item, dict) else cause.get('domain')}`: {_md_cell(item, 360)}")
        for item in cause.get("counter_evidence") or []:
            evidence_lines.append(f"- 反证/限制: {_md_cell(item, 260)}")
    if not evidence_lines:
        evidence_lines.append("证据不足：没有形成可排序根因候选。")

    supporting_lines = []
    for finding in supporting_findings or []:
        supporting_lines.append(
            f"- **{finding.get('title')}** (`{finding.get('type')}`): "
            f"{_md_cell((finding.get('evidence') or [{}])[0], 360)}"
        )
        for item in finding.get("counter_evidence") or []:
            supporting_lines.append(f"  - 限制: {_md_cell(item, 260)}")
    if not supporting_lines:
        supporting_lines.append("- 未形成单独的支撑发现。")

    remediation_lines = []
    for cause in causes[:3]:
        hint = cause.get("remediation_hint") or {}
        recommendation = "；".join(cause.get("recommendation") or [])
        remediation_lines.append(
            f"- **{cause.get('title')}**: {recommendation or '先补充验证。'} "
            f"恢复交接: `{hint.get('skill', REMEDIATION_SKILL)}`"
            + (f" / `{hint.get('action')}`" if hint.get("action") else "")
        )
    if not remediation_lines:
        remediation_lines.append("- 暂不建议执行恢复动作；先补齐缺失证据。")

    return "\n".join(
        [
            "# CCE 综合根因分析报告",
            "",
            "## 1. 分析摘要",
            "",
            f"- Analysis-Trace-ID: `{trace_id}`",
            f"- 集群: `{params.get('cluster_id')}`",
            f"- 区域: `{params.get('region')}`",
            f"- 命名空间: `{params.get('namespace') or '全集群'}`",
            f"- 目标对象: `{target}`",
            f"- 初步结论: {conclusion}",
            "",
            "## 2. 排查过程",
            "",
            "1. 明确故障对象和时间窗口，建立跨信号 Trace ID。",
            "2. 独立采集 Kubernetes Events、Pod/Node 状态、Pod/Node 监控 TopN，并汇聚发布、依赖、变更和 AOM 告警。",
            "3. 将可解释故障起点的信号转换为根因候选；依赖传播和告警相关性只作为支撑发现。",
            "4. 按证据强度、时间吻合度、影响面和可恢复性排序，输出 Top3 根因。",
            f"5. 恢复动作只给交接建议，实际执行由 {REMEDIATION_SKILL} 预览并确认。",
            "",
            "## 3. 数据源与采集状态",
            "",
            "\n".join(status_rows),
            "",
            "## 4. 时间线",
            "",
            _timeline_rows(captures),
            "",
            "## 5. Top3 根因结论",
            "",
            "\n".join(cause_rows),
            "",
            "## 6. 证据链与反证",
            "",
            "\n".join(evidence_lines),
            "",
            "## 7. 影响面",
            "",
            (captures.get("dependency") or {}).get("summary", {}).get("risk_reason", "影响面需要结合 dependency-impact-analyzer 输出继续确认。"),
            "",
            "## 7.1 支撑发现",
            "",
            "\n".join(supporting_lines),
            "",
            "## 8. 恢复建议与交接",
            "",
            "\n".join(remediation_lines),
            "",
            "## 9. 能力复用与缺口",
            "",
            "- 已复用 runtime evidence、workload rollout、dependency impact、change impact、AOM alarm 等组合能力。",
            "- 巡检输入只作为范围线索；根因候选来自 RCA 自采集证据和域诊断器。",
            "- 建议继续补充 EndpointSlice、APM 调用边、CTS 云审计、业务流量指标和 before/after YAML diff，提升影响面和变更归因置信度。",
            "",
        ]
    )


def analyze_root_cause(params: Dict[str, str]) -> Dict[str, Any]:
    missing = [key for key in ("region", "cluster_id") if not params.get(key)]
    if missing:
        return {"success": False, "error": f"{', '.join(missing)} is required"}

    trace_id = params.get("analysis_trace_id") or f"RCA-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    abnormal_object_analysis = _extract_abnormal_object_analysis(params)
    scope_hints = _scope_hints_from_abnormal_objects(abnormal_object_analysis)
    params = _apply_scope_hints(params, scope_hints)
    target = _workload_name(params)
    namespace = params.get("namespace")
    captures: Dict[str, Dict[str, Any]] = {}
    if abnormal_object_analysis:
        captures["scope_hints"] = {
            "success": True,
            "summary": {
                "headline": "已使用 daily inspector abnormal_object_analysis 作为 RCA 范围线索",
                "object_count": abnormal_object_analysis.get("object_count") or len(abnormal_object_analysis.get("abnormal_objects", []) or []),
                "timeline": scope_hints.get("time_window"),
            },
            "scope_hints": scope_hints,
        }

    captures["runtime_evidence"] = _capture_runtime_evidence(params, scope_hints)

    if target and namespace and _to_bool(params.get("include_rollout"), True):
        kind = params.get("kind") or params.get("workload_type") or "deployment"
        captures["rollout"] = _safe_capture(
            "rollout",
            lambda: workload_rollout_diagnosis.workload_rollout_diagnose(
                region=params["region"],
                cluster_id=params["cluster_id"],
                namespace=namespace,
                kind=kind,
                name=target,
                include_pod_diagnosis=True,
                include_logs=_to_bool(params.get("include_logs"), True),
                include_metrics=_to_bool(params.get("include_metrics"), False),
                tail_lines=_to_int(params.get("tail_lines"), 80),
                hours=_to_int(params.get("hours"), 1),
                max_pods=_to_int(params.get("max_pods"), 20),
                event_limit=_to_int(params.get("event_limit"), 500),
                label_selector=params.get("label_selector"),
                ak=params.get("ak"),
                sk=params.get("sk"),
                project_id=params.get("project_id"),
            ),
        )

    if _to_bool(params.get("include_dependency"), True):
        dep_params = dict(params)
        dep_params["analysis_trace_id"] = trace_id
        captures["dependency"] = _safe_capture("dependency", lambda: dependency_impact_analysis.analyze_dependency_impact(dep_params))

    if _to_bool(params.get("include_change"), True):
        change_params = dict(params)
        change_params["analysis_trace_id"] = trace_id
        if target and not change_params.get("target_name"):
            change_params["target_name"] = target
        captures["change"] = _safe_capture("change", lambda: change_impact_analysis.analyze_change_impact(change_params))

    if _to_bool(params.get("include_alarms"), True):
        captures["alarms"] = _safe_capture(
            "alarms",
            lambda: aom.analyze_aom_alarms(
                region=params["region"],
                ak=params.get("ak"),
                sk=params.get("sk"),
                project_id=params.get("project_id"),
                cluster_id=params.get("cluster_id"),
                cluster_name=params.get("cluster_name"),
                hours=_to_int(params.get("hours"), 1),
            ),
        )

    causes: List[Dict[str, Any]] = []
    for cause in _causes_from_runtime_evidence(captures.get("runtime_evidence") or {}, scope_hints):
        _add_or_merge(causes, cause)
    for cause in _causes_from_rollout(captures.get("rollout") or {}):
        _add_or_merge(causes, cause)
    for cause in _causes_from_change_impact(captures.get("change") or {}):
        _add_or_merge(causes, cause)
    supporting_findings = (
        _supporting_findings_from_dependency(captures.get("dependency") or {})
        + _supporting_findings_from_alarms(captures.get("alarms") or {})
    )

    ranked = _rank_causes(causes)
    remediation_candidates = _build_remediation_candidates(params, captures, ranked)
    report_markdown = build_markdown_report(trace_id, params, captures, ranked, supporting_findings)
    output_file = params.get("output_file")
    if output_file:
        Path(output_file).write_text(report_markdown, encoding="utf-8")

    return {
        "success": True,
        "analysis_trace_id": trace_id,
        "scope": {
            "region": params.get("region"),
            "cluster_id": params.get("cluster_id"),
            "namespace": namespace,
            "target_name": target,
        },
        "summary": {
            "top_cause": ranked[0] if ranked else None,
            "cause_count": len(ranked),
            "data_sources": {source: bool(result.get("success")) for source, result in captures.items()},
            "scope_hint_input": "abnormal_object_analysis" if abnormal_object_analysis else None,
            "root_cause_evidence_policy": "Root cause is ranked from RCA-collected evidence and domain analyzers, not from inspector output alone.",
            "remediation_candidate_count": len(remediation_candidates),
            "supporting_finding_count": len(supporting_findings),
        },
        "top_causes": ranked[:3],
        "causes": ranked,
        "supporting_findings": supporting_findings,
        "remediation_candidates": remediation_candidates,
        "remediation_handoff": {
            "skill": REMEDIATION_SKILL,
            "input_field": "remediation_candidates",
            "mode": "advice | preview | authorized_execution",
            "policy": "Runner must preview first unless the candidate is R3 read-only or an R2 low-risk action covered by explicit customer authorization.",
        },
        "report_markdown": report_markdown,
        "report_file": output_file,
        "capture_metadata": {
            source: {
                "success": result.get("success"),
                "error": result.get("error"),
                "summary": result.get("summary"),
            }
            for source, result in captures.items()
        },
    }


def analyze_root_cause_action(params: Dict[str, str]) -> Dict[str, Any]:
    return analyze_root_cause(params)
