"""Independent read-only checks for the CCE daily cluster inspector."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from . import aom, cce, cce_metrics


def _scope(region: str, cluster_id: str, namespace: Optional[str] = None) -> Dict[str, str]:
    value = {"region": region, "cluster_id": cluster_id}
    if namespace:
        value["namespace"] = namespace
    return value


def _finding(severity: str, category: str, message: str, **extra: Any) -> Dict[str, Any]:
    return {"severity": severity, "category": category, "message": message, **extra}


def _mark_current_state_fallback(result: Dict[str, Any], fallback_reason: Optional[str], observation_scope: str, observation_note: str) -> Dict[str, Any]:
    """Make reduced historical coverage explicit after a successful kubectl fallback."""
    if not result.get("success"):
        return result
    result.setdefault("source", "kubectl_cce")
    result.setdefault("observation_scope", observation_scope)
    result["fallback_used"] = True
    result["fallback_reason"] = fallback_reason
    result["historical_coverage"] = False
    result["observation_note"] = observation_note
    gap = f"Historical coverage unavailable; {observation_note}"
    gaps = result.setdefault("data_gaps", [])
    if gap not in gaps:
        gaps.append(gap)
    return result


def _cluster_name(cluster: Dict[str, Any]) -> Optional[str]:
    metadata = cluster.get("metadata") or {}
    return metadata.get("name") or cluster.get("name")


def _alarm_matches_cluster(value: Any, cluster_id: str, cluster_name: Optional[str] = None, field: str = "", in_monitor_object: bool = False) -> bool:
    """Match exact cluster fields and PromQL labels without broad substring matching."""
    normalized_field = field.lower().replace("_", "").replace("-", "")
    identifiers = {cluster_id}
    if cluster_name:
        identifiers.add(cluster_name)
    if isinstance(value, dict):
        monitor_object = in_monitor_object or normalized_field in {"monitorobject", "monitorobjects"}
        return any(_alarm_matches_cluster(item, cluster_id, cluster_name, key, monitor_object) for key, item in value.items())
    if isinstance(value, list):
        monitor_object = in_monitor_object or normalized_field in {"monitorobject", "monitorobjects"}
        return any(_alarm_matches_cluster(item, cluster_id, cluster_name, field, monitor_object) for item in value)
    if not isinstance(value, str):
        return False
    if normalized_field in {"cluster", "clusterid", "clustername"}:
        return value in identifiers
    if in_monitor_object and normalized_field in {"id", "name", "value", "resource"}:
        return value in identifiers
    if normalized_field in {"promql", "query", "expression"}:
        return any(
            f'{label}="{identifier}"' in value or f"{label}='{identifier}'" in value
            for identifier in identifiers
            for label in ("cluster", "cluster_id", "cluster_name")
        )
    return False


def inspect_nodes(region: str, cluster_id: str, include_events: bool = True, hours: int = 1, **auth: Any) -> Dict[str, Any]:
    prometheus_result = inspect_node_health_from_prometheus(region, cluster_id, hours=hours, **auth)
    if prometheus_result.get("success"):
        prometheus_result["action"] = "node_status_inspection"
        prometheus_result["scope"] = _scope(region, cluster_id)
        prometheus_result["fallback_used"] = False
        return prometheus_result

    result = cce.get_kubernetes_nodes(region, cluster_id, **auth)
    if not result.get("success"):
        return result
    findings = []
    for node in result.get("nodes") or []:
        conditions = {item.get("type"): item.get("status") for item in node.get("conditions") or []}
        if conditions.get("Ready") != "True":
            findings.append(_finding("high", "node_ready", f"Node {node.get('name')} is not Ready."))
        for condition in ("DiskPressure", "MemoryPressure", "PIDPressure", "NetworkUnavailable"):
            if conditions.get(condition) == "True":
                findings.append(_finding("high", "node_condition", f"Node {node.get('name')} reports {condition}."))
        if node.get("unschedulable"):
            findings.append(_finding("medium", "node_unschedulable", f"Node {node.get('name')} is cordoned."))
        for taint in node.get("taints") or []:
            effect = taint.get("effect")
            if effect in {"NoSchedule", "NoExecute"}:
                findings.append(_finding("medium", "node_taint", f"Node {node.get('name')} has {effect} taint {taint.get('key')}={taint.get('value', '')}.", taint=taint))

    if not include_events:
        return {"success": True, "action": "node_status_inspection", "scope": _scope(region, cluster_id), "source": "kubectl_cce", "observation_scope": "current_state", "collection_scope": "cluster_wide_current_state", "fallback_used": True, "fallback_reason": prometheus_result.get("error"), "nodes": result.get("nodes", []), "findings": findings}
    events_result = cce._kubectl(region, cluster_id, ["get", "events", "-A", "--field-selector=involvedObject.kind=Node,type=Warning", "--chunk-size=200", "--request-timeout=45s", "-o", "json"], **auth)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    node_events = [event for event in ((events_result.get("data") or {}).get("items", []) if events_result.get("success") else []) if _event_time(event) >= cutoff]
    for event in node_events[:200]:
        involved = event.get("involvedObject") or {}
        findings.append(_finding("medium", "node_warning_event", f"Node {involved.get('name')}: {event.get('reason') or 'Warning'} - {event.get('message') or ''}", node=involved.get("name"), reason=event.get("reason"), count=event.get("count")))
    gaps = [] if events_result.get("success") else [f"node_events: {events_result.get('error')}"]
    return {"success": True, "action": "node_status_inspection", "scope": _scope(region, cluster_id), "source": "kubectl_cce", "observation_scope": "current_state", "collection_scope": "cluster_wide_current_state", "fallback_used": True, "fallback_reason": prometheus_result.get("error"), "nodes": result.get("nodes", []), "node_warning_events": node_events[:200], "findings": findings, "data_gaps": gaps, "node_event_summary": {"time_window_hours": hours, "server_filtered": True, "returned": len(node_events[:200]), "truncated": len(node_events) > 200, "chunk_size": 200, "request_timeout_seconds": 45}}


def inspect_cluster_availability(region: str, cluster_id: str, **auth: Any) -> Dict[str, Any]:
    result = cce.show_cce_cluster(region, cluster_id, **auth)
    if not result.get("success"):
        return result
    cluster = result.get("cluster") or {}
    status = str(cluster.get("status") or "Unknown")
    healthy = status.lower() in {"available", "running", "normal"}
    findings = [] if healthy else [_finding("high", "cluster_status", f"CCE cluster status is {status}.")]
    return {"success": True, "action": "cluster_availability", "scope": _scope(region, cluster_id), "cluster": cluster, "findings": findings}


def inspect_pods(region: str, cluster_id: str, namespace: str, hours: int = 1, pod_limit: int = 200, **auth: Any) -> Dict[str, Any]:
    prometheus_result = inspect_pod_health_from_prometheus(region, cluster_id, pod_limit=pod_limit, namespace=namespace, hours=hours, **auth)
    if prometheus_result.get("success"):
        prometheus_result["action"] = "pod_status_inspection"
        prometheus_result["scope"] = _scope(region, cluster_id, namespace)
        prometheus_result["fallback_used"] = False
        return prometheus_result

    result = cce.get_kubernetes_pods(region, cluster_id, namespace=namespace, **auth)
    if not result.get("success"):
        return result
    findings = []
    unhealthy = {"Failed", "Unknown", "Pending"}
    for pod in result.get("pods") or []:
        if pod.get("phase") in unhealthy:
            findings.append(_finding("high", "pod_phase", f"Pod {pod.get('name')} is {pod.get('phase')}."))
        elif any(not container.get("ready") for container in pod.get("containers") or []):
            findings.append(_finding("medium", "pod_readiness", f"Pod {pod.get('name')} has an unready container."))
    return {"success": True, "action": "pod_status_inspection", "scope": _scope(region, cluster_id, namespace), "source": "kubectl_cce", "observation_scope": "current_state", "fallback_used": True, "fallback_reason": prometheus_result.get("error"), "pods": result.get("pods", []), "findings": findings}


def inspect_events(region: str, cluster_id: str, namespace: str, limit: int = 200, hours: int = 1, **auth: Any) -> Dict[str, Any]:
    lts_result = inspect_recent_warning_events_from_lts(region, cluster_id, event_hours=hours, event_limit=limit, namespace=namespace, **auth)
    if lts_result.get("success"):
        lts_result["action"] = "event_inspection"
        lts_result["scope"] = _scope(region, cluster_id, namespace)
        lts_result["fallback_used"] = False
        return lts_result

    result = cce.get_kubernetes_events(region, cluster_id, namespace=namespace, limit=limit, warning_only=True, **auth)
    if not result.get("success"):
        return result
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    warnings = [event for event in result.get("events") or [] if event.get("type") == "Warning" and _event_time(event) >= cutoff]
    grouped: Dict[str, int] = {}
    for event in warnings:
        key = event.get("reason") or "Unknown"
        grouped[key] = grouped.get(key, 0) + int(event.get("count") or 1)
    findings = [_finding("medium", "warning_event", f"{count} Warning event occurrence(s) for {reason}.", reason=reason, count=count) for reason, count in sorted(grouped.items(), key=lambda item: item[1], reverse=True)]
    return {"success": True, "action": "event_inspection", "scope": _scope(region, cluster_id, namespace), "source": "kubectl_cce", "observation_scope": "current_event_records", "fallback_used": True, "fallback_reason": lts_result.get("error"), "warning_events": warnings, "findings": findings, "time_window_hours": hours}


def inspect_node_resources(region: str, cluster_id: str, hours: int = 1, top_n: int = 10, **auth: Any) -> Dict[str, Any]:
    metrics = cce_metrics.get_cce_node_metrics_topN(region, cluster_id, auth.get("ak"), auth.get("sk"), auth.get("project_id"), top_n=top_n, hours=hours)
    if not metrics.get("success"):
        return {"success": False, "action": "node_resource_inspection", "scope": _scope(region, cluster_id), "error": metrics.get("error")}
    findings = []
    for category, rows in (metrics.get("metrics") or {}).items():
        for row in rows or []:
            values = [float(item[1]) for item in row.get("time_series") or [] if isinstance(item, list) and len(item) > 1]
            if values and max(values) >= 85:
                findings.append(_finding("high", "node_pressure", f"{category} peak is {max(values):.1f}% for {row.get('node_name') or row.get('node_ip') or row.get('instance')}.", metric=category))
    return {"success": True, "action": "node_resource_inspection", "scope": _scope(region, cluster_id), "metrics": metrics.get("metrics", {}), "findings": findings}


def inspect_aom_alarms(region: str, cluster_id: str, **auth: Any) -> Dict[str, Any]:
    from .common import _run_hcloud_json

    cluster_result = cce.show_cce_cluster(region, cluster_id, **auth)
    if not cluster_result.get("success"):
        return {"success": False, "action": "aom_alarm_inspection", "scope": _scope(region, cluster_id), "error": cluster_result.get("error")}
    cluster_name = _cluster_name(cluster_result.get("cluster") or {})
    page_limit, max_pages, offset = 200, 100, 0
    rules, pages, truncated = [], 0, False
    while pages < max_pages:
        command = [
            "hcloud", "AOM", "ListMetricOrEventAlarmRule",
            f"--cli-region={region}", "--cli-output=json",
            f"--limit={page_limit}", f"--offset={offset}",
        ]
        for key, flag in (("project_id", "--cli-project-id"), ("ak", "--cli-access-key"), ("sk", "--cli-secret-key"), ("security_token", "--cli-security-token")):
            if auth.get(key):
                command.append(f"{flag}={auth[key]}")
        result = _run_hcloud_json(command)
        if not result.get("success"):
            return {"success": False, "action": "aom_alarm_inspection", "scope": _scope(region, cluster_id), "error": result.get("error")}
        payload = result.get("data") or {}
        page = payload if isinstance(payload, list) else payload.get("alarm_rules", payload.get("rules", []))
        if not isinstance(page, list):
            return {"success": False, "action": "aom_alarm_inspection", "scope": _scope(region, cluster_id), "error": "hcloud returned an invalid AOM alarm-rule page"}
        rules.extend(rule for rule in page if isinstance(rule, dict) and _alarm_matches_cluster(rule, cluster_id, cluster_name))
        pages += 1
        if len(page) < page_limit:
            break
        offset += page_limit
    else:
        truncated = True
    return {
        "success": True,
        "action": "aom_alarm_inspection",
        "scope": _scope(region, cluster_id),
        "cluster_name": cluster_name,
        "alarm_rules": rules,
        "findings": [],
        "alarm_rule_summary": {"matched": len(rules), "pages": pages, "page_limit": page_limit, "truncated": truncated},
    }


def inspect_aom_alarm_configuration_and_events(region: str, cluster_id: str, hours: int = 1, alarm_limit: int = 200, **auth: Any) -> Dict[str, Any]:
    """Inspect configured cluster alarm rules and AOM alarm events in one response."""
    rules_result = inspect_aom_alarms(region, cluster_id, **auth)
    if not rules_result.get("success"):
        return rules_result

    events_result = inspect_recent_aom_alarms(
        region,
        cluster_id,
        alarm_limit=alarm_limit,
        cluster_name=rules_result.get("cluster_name"),
        hours=hours,
        **auth,
    )
    if not events_result.get("success"):
        return {
            "success": False,
            "action": "aom_alarm_inspection",
            "scope": _scope(region, cluster_id),
            "alarm_rules": rules_result.get("alarm_rules", []),
            "alarm_rule_summary": rules_result.get("alarm_rule_summary", {}),
            "error": events_result.get("error"),
        }

    event_groups: Dict[str, Dict[str, Any]] = {}
    for alarm in events_result.get("alarms") or []:
        metadata = alarm.get("metadata") or {}
        name = str(metadata.get("event_name") or alarm.get("event_name") or "AOM alarm")
        group = event_groups.setdefault(name, {"event_name": name, "active": 0, "history": 0, "total": 0})
        state = alarm.get("state")
        if state in {"active", "history"}:
            group[state] += 1
        group["total"] += 1

    return {
        "success": True,
        "action": "aom_alarm_inspection",
        "scope": _scope(region, cluster_id),
        "cluster_name": rules_result.get("cluster_name"),
        "alarm_rules": rules_result.get("alarm_rules", []),
        "alarm_rule_summary": rules_result.get("alarm_rule_summary", {}),
        "alarms": events_result.get("alarms", []),
        "findings": events_result.get("findings", []),
        "alarm_event_analysis": {
            "time_window_hours": hours,
            **events_result.get("alarm_summary", {}),
            "by_event_name": sorted(event_groups.values(), key=lambda item: (-item["active"], -item["total"], item["event_name"])),
        },
    }


def inspect_recent_aom_alarms(region: str, cluster_id: str, alarm_limit: int = 200, cluster_name: Optional[str] = None, hours: int = 1, **auth: Any) -> Dict[str, Any]:
    """Inspect active and recovered AOM alarms in the requested time window."""
    from .common import _run_hcloud_json

    time_range_minutes = max(hours, 1) * 60

    def list_events(alert_type: str, limit: int) -> tuple[list[Dict[str, Any]], bool, Optional[str]]:
        events, marker, truncated, pages = [], "0", False, 0
        while marker and len(events) < limit and pages < 20:
            command = ["hcloud", "AOM", "ListEvents", f"--cli-region={region}", "--cli-output=json", f"--type={alert_type}", f"--time_range=-1.-1.{time_range_minutes}", f"--limit={min(200, limit - len(events))}", f"--marker={marker}"]
            for key, flag in (("project_id", "--cli-project-id"), ("ak", "--cli-access-key"), ("sk", "--cli-secret-key"), ("security_token", "--cli-security-token")):
                if auth.get(key):
                    command.append(f"{flag}={auth[key]}")
            result = _run_hcloud_json(command)
            if not result.get("success"):
                return [], False, result.get("error")
            payload = result.get("data") or {}
            page = payload if isinstance(payload, list) else payload.get("events", payload.get("event_info", []))
            events.extend(
                item for item in page
                if isinstance(item, dict) and _alarm_matches_cluster(item, cluster_id, cluster_name)
            )
            marker = None if isinstance(payload, list) else payload.get("next_marker")
            pages += 1
            truncated = bool(marker) and (len(events) >= limit or pages >= 20)
            if not page:
                break
        return events[:limit], truncated, None

    total_limit = max(alarm_limit, 1)
    active_events, active_truncated, active_error = list_events("active_alert", total_limit)
    history_limit = max(total_limit - len(active_events), 0)
    history_events, history_truncated, history_error = list_events("history_alert", history_limit)
    if active_error or history_error:
        errors = "; ".join(error for error in (active_error, history_error) if error)
        return {"success": False, "action": "recent_aom_alarms", "scope": _scope(region, cluster_id), "error": errors}

    alarms, seen = [], set()
    for alert_type, events in (("active", active_events), ("history", history_events)):
        for item in events:
            identity = item.get("id") or item.get("event_sn") or json.dumps(item, sort_keys=True, ensure_ascii=False)
            if identity in seen:
                continue
            seen.add(identity)
            alarms.append({"state": alert_type, **item})

    findings = []
    for alarm in alarms:
        metadata = alarm.get("metadata") or {}
        name = metadata.get("event_name") or alarm.get("event_name") or "AOM alarm"
        category = "aom_active_alarm" if alarm["state"] == "active" else "aom_history_alarm"
        severity = "high" if alarm["state"] == "active" else "medium"
        findings.append(_finding(severity, category, f"{name} observed during the last {hours} hour(s).", state=alarm["state"], event_id=alarm.get("id") or alarm.get("event_sn")))
    return {"success": True, "action": "recent_aom_alarms", "scope": _scope(region, cluster_id), "source": "aom", "time_window_hours": hours, "alarms": alarms, "findings": findings, "alarm_summary": {"active_returned": sum(1 for alarm in alarms if alarm["state"] == "active"), "history_returned": sum(1 for alarm in alarms if alarm["state"] == "history"), "truncated": active_truncated or history_truncated, "limit": alarm_limit}}


def _event_time(event: Dict[str, Any]) -> datetime:
    value = event.get("eventTime") or event.get("lastTimestamp") or ((event.get("metadata") or {}).get("creationTimestamp"))
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _latest_prom_samples(result: Dict[str, Any]) -> list[tuple[Dict[str, str], float]]:
    samples = []
    for item in ((result.get("result") or {}).get("data") or {}).get("result") or []:
        values = item.get("values") or ([item["value"]] if item.get("value") else [])
        if not values:
            continue
        try:
            samples.append((item.get("metric") or {}, float(values[-1][1])))
        except (IndexError, TypeError, ValueError):
            continue
    return samples


def inspect_pod_health_from_prometheus(region: str, cluster_id: str, pod_limit: int = 200, namespace: Optional[str] = None, hours: int = 1, **auth: Any) -> Dict[str, Any]:
    instance_result = cce.get_prom_instance_id(region, cluster_id, auth.get("ak"), auth.get("sk"), auth.get("project_id"), auth.get("security_token"))
    if not instance_result.get("success"):
        return {"success": False, "action": "pod_health_prometheus", "scope": _scope(region, cluster_id), "error": instance_result.get("error")}

    cluster_filter = f"cluster={json.dumps(cluster_id)}"
    pod_filter = ",".join(part for part in (cluster_filter, f"namespace={json.dumps(namespace)}" if namespace else "") if part)
    queries = {
        "cluster_metric_available": f"count(kube_pod_status_phase{{{cluster_filter}}})",
        "scope_pod_count": f"count(kube_pod_status_phase{{{pod_filter}}})",
        "not_ready": f'max_over_time(kube_pod_status_ready{{{pod_filter},condition=~"false|unknown"}}[{hours}h]) == 1',
        "phase": f'max_over_time(kube_pod_status_phase{{{pod_filter},phase=~"Pending|Failed|Unknown"}}[{hours}h]) == 1',
        "waiting": f'max_over_time(kube_pod_container_status_waiting_reason{{{pod_filter},reason=~"CrashLoopBackOff|ImagePullBackOff|ErrImagePull|CreateContainerConfigError"}}[{hours}h]) == 1',
        "oom": f'max_over_time(kube_pod_container_status_last_terminated_reason{{{pod_filter},reason="OOMKilled"}}[{hours}h]) == 1',
    }
    results = {
        name: aom.get_aom_prom_instant_query_http(
            region,
            instance_result["aom_instance_id"],
            query,
            ak=auth.get("ak"),
            sk=auth.get("sk"),
            project_id=auth.get("project_id"),
            security_token=auth.get("security_token"),
            # Limit each abnormal-series response before it reaches the inspector.
            limit=pod_limit if name in {"not_ready", "phase", "waiting", "oom"} else None,
        )
        for name, query in queries.items()
    }
    failed = [f"{name}: {result.get('error')}" for name, result in results.items() if not result.get("success")]
    if failed:
        return {"success": False, "action": "pod_health_prometheus", "scope": _scope(region, cluster_id), "error": "; ".join(failed)}
    if not any(value > 0 for _, value in _latest_prom_samples(results["cluster_metric_available"])):
        return {"success": False, "action": "pod_health_prometheus", "scope": _scope(region, cluster_id), "error": "kube-state-metrics Pod status metrics are unavailable for this cluster"}
    scope_pod_count = sum(value for _, value in _latest_prom_samples(results["scope_pod_count"]))
    if scope_pod_count <= 0:
        return {
            "success": True,
            "action": "pod_health_prometheus",
            "scope": _scope(region, cluster_id, namespace),
            "source": "aom_prometheus",
            "aom_instance_id": instance_result["aom_instance_id"],
            "findings": [],
            "promql": queries,
            "inspection_window_hours": hours,
            "pod_count": 0,
            "scope_empty": True,
        }

    categories = {
        "not_ready": ("medium", "pod_not_ready", "is not Ready"),
        "phase": ("high", "pod_phase", "has abnormal phase"),
        "waiting": ("high", "pod_waiting", "is waiting"),
        "oom": ("high", "pod_oom", "was OOMKilled"),
    }
    pod_findings: Dict[tuple[str, str], Dict[str, Any]] = {}
    namespace_categories: Dict[str, Dict[str, set[str]]] = {}
    truncated = False
    for name, (severity, category, description) in categories.items():
        for labels, value in _latest_prom_samples(results[name]):
            if value <= 0:
                continue
            namespace = labels.get("namespace", "unknown")
            pod = labels.get("pod", "unknown")
            key = (namespace, pod)
            if key not in pod_findings and len(pod_findings) >= pod_limit:
                truncated = True
                continue
            reason = labels.get("reason") or labels.get("phase")
            namespace_categories.setdefault(namespace, {}).setdefault(category, set()).add(pod)
            record = pod_findings.setdefault(key, {"severity": severity, "categories": [], "reasons": []})
            if severity == "high":
                record["severity"] = "high"
            if category not in record["categories"]:
                record["categories"].append(category)
            if reason and reason not in record["reasons"]:
                record["reasons"].append(reason)
    findings = []
    for (namespace, pod), record in pod_findings.items():
        categories_text = ", ".join(record["categories"])
        reasons_text = f" (reasons: {', '.join(record['reasons'])})" if record["reasons"] else ""
        findings.append(_finding(record["severity"], "pod_health", f"Pod {namespace}/{pod} had {categories_text} during the last {hours} hour(s).{reasons_text}", namespace=namespace, pod=pod, categories=record["categories"], reasons=record["reasons"]))
    namespace_summary = {
        namespace: {category: len(pods) for category, pods in categories.items()}
        for namespace, categories in namespace_categories.items()
    }
    return {
        "success": True,
        "action": "pod_health_prometheus",
        "scope": _scope(region, cluster_id, namespace),
        "source": "aom_prometheus",
        "aom_instance_id": instance_result["aom_instance_id"],
        "namespace_summary": namespace_summary,
        "findings": findings,
        "promql": queries,
        "inspection_window_hours": hours,
        "pod_count": scope_pod_count,
        "scope_empty": False,
        "detail_limit": pod_limit,
        "query_series_limit": pod_limit,
        "truncated": truncated,
    }


def inspect_node_health_from_prometheus(region: str, cluster_id: str, node_limit: int = 200, hours: int = 1, **auth: Any) -> Dict[str, Any]:
    instance_result = cce.get_prom_instance_id(region, cluster_id, auth.get("ak"), auth.get("sk"), auth.get("project_id"), auth.get("security_token"))
    if not instance_result.get("success"):
        return {"success": False, "action": "node_health_prometheus", "scope": _scope(region, cluster_id), "error": instance_result.get("error")}

    cluster_filter = f"cluster={json.dumps(cluster_id)}"
    queries = {
        "metric_available": f'count(kube_node_status_condition{{{cluster_filter},condition="Ready"}})',
        "not_ready": f'max_over_time(kube_node_status_condition{{{cluster_filter},condition="Ready",status=~"false|unknown"}}[{hours}h]) == 1',
        "pressure": f'max_over_time(kube_node_status_condition{{{cluster_filter},condition=~"DiskPressure|MemoryPressure|PIDPressure|NetworkUnavailable",status="true"}}[{hours}h]) == 1',
        "npd_condition": f'max_over_time(kube_node_status_condition{{{cluster_filter},condition!~"Ready|DiskPressure|MemoryPressure|PIDPressure|NetworkUnavailable",status="true"}}[{hours}h]) == 1',
        "unschedulable": f"max_over_time(kube_node_spec_unschedulable{{{cluster_filter}}}[{hours}h]) == 1",
        "taint": f'max_over_time(kube_node_spec_taint{{{cluster_filter},effect=~"NoSchedule|NoExecute"}}[{hours}h]) == 1',
    }
    results = {
        name: aom.get_aom_prom_instant_query_http(
            region,
            instance_result["aom_instance_id"],
            query,
            ak=auth.get("ak"),
            sk=auth.get("sk"),
            project_id=auth.get("project_id"),
            security_token=auth.get("security_token"),
        )
        for name, query in queries.items()
    }
    failed = [f"{name}: {result.get('error')}" for name, result in results.items() if not result.get("success")]
    if failed:
        return {"success": False, "action": "node_health_prometheus", "scope": _scope(region, cluster_id), "error": "; ".join(failed)}
    if not any(value > 0 for _, value in _latest_prom_samples(results["metric_available"])):
        return {"success": False, "action": "node_health_prometheus", "scope": _scope(region, cluster_id), "error": "kube-state-metrics node status metrics are unavailable for this cluster"}

    categories = {
        "not_ready": ("high", "node_ready", "is not Ready"),
        "pressure": ("high", "node_condition", "reports an abnormal condition"),
        "npd_condition": ("high", "node_npd_condition", "reports an NPD or custom NodeCondition"),
        "unschedulable": ("medium", "node_unschedulable", "is cordoned"),
        "taint": ("medium", "node_taint", "has a scheduling taint"),
    }
    findings = []
    for name, (severity, category, description) in categories.items():
        for labels, value in _latest_prom_samples(results[name]):
            if value <= 0 or len(findings) >= node_limit:
                continue
            node = labels.get("node", "unknown")
            detail = labels.get("condition") or labels.get("effect") or labels.get("key")
            suffix = f" ({detail})" if detail else ""
            findings.append(_finding(severity, category, f"Node {node} {description}{suffix} during the last {hours} hour(s).", node=node, detail=detail))
    return {"success": True, "action": "node_health_prometheus", "scope": _scope(region, cluster_id), "source": "aom_prometheus", "aom_instance_id": instance_result["aom_instance_id"], "findings": findings, "promql": queries, "inspection_window_hours": hours, "detail_limit": node_limit, "truncated": len(findings) >= node_limit}


def inspect_cluster_pods(region: str, cluster_id: str, pod_limit: int = 200, **auth: Any) -> Dict[str, Any]:
    states_result = cce._kubectl(region, cluster_id, ["get", "pods", "-A", "--chunk-size=200", "--request-timeout=45s", "-o", "custom-columns=NS:.metadata.namespace,NAME:.metadata.name,PHASE:.status.phase,READY:.status.containerStatuses[*].ready,WAITING:.status.containerStatuses[*].state.waiting.reason,LAST:.status.containerStatuses[*].lastState.terminated.reason", "--no-headers"], **auth, expect_json=False)
    if not states_result.get("success"):
        return {"success": False, "action": "cluster_pod_check", "scope": _scope(region, cluster_id), "error": states_result.get("error")}
    findings = []

    def classify_pod(namespace: str, name: str, phase: str, ready_values: str = "<none>", waiting: str = "<none>", last_reason: str = "<none>") -> Optional[Dict[str, str]]:
        pod_key = f"{namespace}/{name}"
        if phase == "Pending":
            return _finding("high", "pod_pending", f"Pod {pod_key} is Pending.")
        ready = ready_values != "<none>" and all(value == "true" for value in ready_values.split(","))
        if ready or phase == "Succeeded":
            return None
        reason = waiting if waiting != "<none>" else last_reason
        category = {
            "CrashLoopBackOff": "pod_crashloop",
            "ImagePullBackOff": "pod_image_pull",
            "ErrImagePull": "pod_image_pull",
            "CreateContainerConfigError": "pod_config",
            "OOMKilled": "pod_oom",
        }.get(reason, "pod_not_ready")
        severity = "high" if category != "pod_not_ready" else "medium"
        if category == "pod_not_ready":
            message = f"Pod {pod_key} is not Ready (phase={phase}, waiting={waiting}, last_terminated={last_reason})."
        else:
            message = f"Pod {pod_key} reports {reason}."
        return _finding(severity, category, message)

    for line in (states_result.get("output") or "").splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        namespace, name, phase, ready_values, waiting, last_reason = parts[:6]
        if sum(1 for finding in findings if finding["category"].startswith("pod_")) >= pod_limit:
            continue
        finding = classify_pod(namespace, name, phase, ready_values, waiting, last_reason)
        if finding:
            findings.append(finding)
    pod_findings = [finding for finding in findings if finding["category"].startswith("pod_")]
    return {"success": True, "action": "cluster_pod_check", "scope": _scope(region, cluster_id), "source": "kubectl_cce", "observation_scope": "current_state", "collection_scope": "cluster_wide_current_state", "findings": findings, "pod_summary": {"state_columns_only": True, "detail_limit": pod_limit, "returned": len(pod_findings), "truncated": len(pod_findings) >= pod_limit, "chunk_size": 200, "request_timeout_seconds": 45}}


def inspect_recent_warning_events(region: str, cluster_id: str, event_hours: int = 1, event_limit: int = 200, **auth: Any) -> Dict[str, Any]:
    events_result = cce._kubectl(region, cluster_id, ["get", "events", "-A", "--field-selector=type=Warning", "--chunk-size=200", "--request-timeout=45s", "-o", "json"], **auth)
    if not events_result.get("success"):
        return {"success": False, "action": "warning_event_check", "scope": _scope(region, cluster_id), "error": events_result.get("error")}
    all_events = (events_result.get("data") or {}).get("items", [])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(event_hours, 1))
    recent_events = [event for event in all_events if _event_time(event) >= cutoff]
    recent_events.sort(key=_event_time, reverse=True)
    events = recent_events[:max(event_limit, 1)]
    findings = [_finding("medium", "warning_event", f"{event.get('reason') or 'Warning'}: {event.get('message') or ''}") for event in events]
    return {"success": True, "action": "warning_event_check", "scope": _scope(region, cluster_id), "source": "kubectl_cce", "observation_scope": "current_event_records", "collection_scope": "cluster_wide_current_state", "findings": findings, "warning_event_summary": {"time_window_hours": event_hours, "server_filtered": True, "total_warning_events": len(all_events), "within_window": len(recent_events), "returned": len(events), "truncated": len(recent_events) > len(events), "chunk_size": 200, "request_timeout_seconds": 45}}


def _lts_command(operation: str, region: str, **auth: Any) -> list[str]:
    command = ["hcloud", "LTS", operation, f"--cli-region={region}", "--cli-output=json"]
    for key, flag in (("project_id", "--cli-project-id"), ("ak", "--cli-access-key"), ("sk", "--cli-secret-key"), ("security_token", "--cli-security-token")):
        if auth.get(key):
            command.append(f"{flag}={auth[key]}")
    return command


def _aggregate_lts_warning_events(logs: Iterable[Dict[str, Any]], event_limit: int, namespace: Optional[str] = None) -> tuple[list[Dict[str, Any]], int, int]:
    """Collapse repeated LTS snapshots of the same Kubernetes Warning event."""
    groups: Dict[tuple[str, str, str, str], Dict[str, Any]] = {}
    discarded_non_warning = 0
    for log in logs:
        content = log.get("content")
        try:
            event = json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError:
            event = None
        if not isinstance(event, dict):
            discarded_non_warning += 1
            continue

        event_type = re.sub(r"<[^>]+>", "", str(event.get("type") or "")).strip()
        if event_type.lower() != "warning":
            discarded_non_warning += 1
            continue

        event_namespace = str(event.get("namespace") or "unknown")
        if namespace and event_namespace != namespace:
            continue
        resource_kind = str(event.get("resource_kind") or "unknown")
        resource_name = str(event.get("resource_name") or event.get("pod") or "unknown")
        event_name = str(event.get("name") or event.get("reason") or "Warning")
        key = (event_namespace, resource_kind, resource_name, event_name)
        observed_at = str(event.get("start_time") or log.get("timestamp") or "")
        reason = str(event.get("reason") or "")
        try:
            count = int(event.get("count") or 0)
        except (TypeError, ValueError):
            count = 0

        aggregate = groups.setdefault(key, {
            "namespace": event_namespace,
            "app_name": event.get("app_name"),
            "resource_kind": resource_kind,
            "resource_name": resource_name,
            "pod": event.get("pod"),
            "node": event.get("node"),
            "event_name": event_name,
            "reasons": [],
            "first_seen": observed_at,
            "last_seen": observed_at,
            "max_count": count,
            "raw_record_count": 0,
        })
        aggregate["raw_record_count"] += 1
        aggregate["max_count"] = max(aggregate["max_count"], count)
        if reason and reason not in aggregate["reasons"]:
            aggregate["reasons"].append(reason)
        if observed_at:
            if not aggregate["first_seen"] or observed_at < aggregate["first_seen"]:
                aggregate["first_seen"] = observed_at
            if not aggregate["last_seen"] or observed_at > aggregate["last_seen"]:
                aggregate["last_seen"] = observed_at

    events = sorted(groups.values(), key=lambda item: (item["last_seen"], item["max_count"]), reverse=True)
    return events[:max(event_limit, 1)], len(events), discarded_non_warning


def inspect_recent_warning_events_from_lts(region: str, cluster_id: str, event_hours: int = 1, event_limit: int = 200, namespace: Optional[str] = None, **auth: Any) -> Dict[str, Any]:
    from .common import _run_hcloud_json

    groups_result = _run_hcloud_json(_lts_command("ListLogGroups", region, **auth))
    if not groups_result.get("success"):
        return {"success": False, "action": "warning_event_lts_check", "scope": _scope(region, cluster_id), "error": groups_result.get("error")}
    expected_group = f"k8s-log-{cluster_id}"
    groups = (groups_result.get("data") or {}).get("log_groups") or []
    group = next((item for item in groups if item.get("log_group_name") == expected_group), None)
    if not group:
        return {"success": False, "action": "warning_event_lts_check", "scope": _scope(region, cluster_id), "error": f"LTS log group {expected_group!r} was not found"}

    streams_command = _lts_command("ListLogStreams", region, **auth)
    streams_command.append(f"--log_group_name={expected_group}")
    streams_result = _run_hcloud_json(streams_command)
    if not streams_result.get("success"):
        return {"success": False, "action": "warning_event_lts_check", "scope": _scope(region, cluster_id), "error": streams_result.get("error")}
    streams = (streams_result.get("data") or {}).get("log_streams") or []
    event_streams = [item for item in streams if "event" in str(item.get("log_stream_name", "")).lower()]
    if len(event_streams) != 1:
        description = "no" if not event_streams else "multiple"
        return {"success": False, "action": "warning_event_lts_check", "scope": _scope(region, cluster_id), "error": f"{description} event log stream was found in {expected_group!r}; cannot select one automatically"}

    now = datetime.now(timezone.utc)
    stream = event_streams[0]
    page_limit, max_pages = min(max(max(event_limit, 1) * 5, 100), 1000), 10
    start_time = int((now - timedelta(hours=max(event_hours, 1))).timestamp() * 1000)
    end_time = int(now.timestamp() * 1000)
    logs, pages, scroll_id, stopped_reason = [], 0, None, "completed"
    seen_scroll_ids = set()
    for _ in range(max_pages):
        logs_command = _lts_command("ListLogs", region, **auth)
        logs_command.extend([
            f"--log_group_id={group.get('log_group_id')}",
            f"--log_stream_id={stream.get('log_stream_id')}",
            f"--start_time={start_time}",
            f"--end_time={end_time}",
            f"--limit={page_limit}",
            "--keywords=Warning",
            "--is_desc=true",
            "--is_iterative=true",
            "--highlight=false",
        ])
        if scroll_id:
            logs_command.extend(["--search_type=backwards", f"--scroll_id={scroll_id}"])
        logs_result = _run_hcloud_json(logs_command)
        if not logs_result.get("success"):
            return {"success": False, "action": "warning_event_lts_check", "scope": _scope(region, cluster_id), "error": logs_result.get("error")}
        payload = logs_result.get("data") or {}
        page = payload.get("logs") or []
        logs.extend(item for item in page if isinstance(item, dict))
        pages += 1
        next_scroll_id = payload.get("scroll_id") or payload.get("scrollId")
        if payload.get("is_query_complete") is True or payload.get("isQueryComplete") is True or not next_scroll_id:
            break
        if next_scroll_id in seen_scroll_ids:
            stopped_reason = "repeated_scroll_id"
            scroll_id = next_scroll_id
            break
        seen_scroll_ids.add(next_scroll_id)
        scroll_id = next_scroll_id
    else:
        stopped_reason = "max_pages_reached"

    events, aggregated_total, discarded_non_warning = _aggregate_lts_warning_events(
        logs,
        max(event_limit, 1),
        namespace=namespace,
    )
    findings = []
    for event in events:
        target = f"{event['resource_kind']} {event['namespace']}/{event['resource_name']}"
        reasons = "; ".join(event["reasons"]) or "Warning event"
        findings.append(_finding(
            "medium",
            "warning_event",
            f"{target}: {event['event_name']} ({reasons}).",
            **event,
        ))
    raw_truncated = bool(scroll_id) and stopped_reason != "completed"
    aggregated_truncated = aggregated_total > len(events)
    return {"success": True, "action": "warning_event_lts_check", "scope": _scope(region, cluster_id, namespace), "source": "lts", "log_group_id": group.get("log_group_id"), "log_stream_id": stream.get("log_stream_id"), "warning_events": events, "findings": findings, "warning_event_summary": {"time_window_hours": event_hours, "server_keyword_filtered": True, "warning_type_verified": True, "raw_returned": len(logs), "discarded_non_warning": discarded_non_warning, "aggregated_total": aggregated_total, "aggregated_returned": len(events), "event_limit": event_limit, "page_limit": page_limit, "pages_fetched": pages, "max_pages": max_pages, "stopped_reason": stopped_reason, "truncated": raw_truncated or aggregated_truncated, "raw_truncated": raw_truncated, "aggregated_truncated": aggregated_truncated}}


def _elb_command(operation: str, region: str, project_id: Optional[str], access_key: Optional[str], secret_key: Optional[str], security_token: Optional[str], *arguments: str) -> list[str]:
    command = ["hcloud", "ELB", operation, f"--cli-region={region}", "--cli-output=json"]
    if project_id:
        command.extend([f"--project_id={project_id}", f"--cli-project-id={project_id}"])
    for value, flag in ((access_key, "--cli-access-key"), (secret_key, "--cli-secret-key"), (security_token, "--cli-security-token")):
        if value:
            command.append(f"{flag}={value}")
    command.extend(arguments)
    return command


def _listener_description_matches_cluster(listener: Dict[str, Any], cluster_id: str) -> bool:
    """Match only a cluster_id key in the CCE-managed listener description."""
    description = listener.get("description")
    if not isinstance(description, str):
        return False
    try:
        parsed = json.loads(description)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and str(parsed.get("cluster_id") or parsed.get("clusterId") or "") == cluster_id:
        return True
    escaped_cluster_id = re.escape(cluster_id)
    return bool(re.search(rf'(?i)(?:"cluster_id"|"clusterId"|cluster_id|clusterId)\s*[:=]\s*["\']?{escaped_cluster_id}(?:["\']|\b)', description))


def _list_elb_listeners(region: str, project_id: Optional[str], access_key: Optional[str], secret_key: Optional[str], security_token: Optional[str]) -> Dict[str, Any]:
    from .common import _run_hcloud_json

    page_limit, max_pages, marker = 200, 100, None
    listeners, seen_markers = [], set()
    for _ in range(max_pages):
        arguments = [f"--limit={page_limit}"]
        if marker:
            arguments.append(f"--marker={marker}")
        result = _run_hcloud_json(_elb_command("ListListeners", region, project_id, access_key, secret_key, security_token, *arguments))
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        payload = result.get("data") or {}
        page = payload.get("listeners", []) if isinstance(payload, dict) else []
        if not isinstance(page, list):
            return {"success": False, "error": "hcloud returned an invalid ELB listener page"}
        listeners.extend(item for item in page if isinstance(item, dict))
        marker = ((payload.get("page_info") or {}).get("next_marker")) if isinstance(payload, dict) else None
        if not marker:
            return {"success": True, "listeners": listeners, "pages": len(seen_markers) + 1, "truncated": False}
        if marker in seen_markers:
            return {"success": False, "error": "ELB listener listing returned a repeated pagination marker"}
        seen_markers.add(marker)
    return {"success": True, "listeners": listeners, "pages": max_pages, "truncated": True}


def _get_elb_ces_metric(region: str, project_id: Optional[str], access_key: Optional[str], secret_key: Optional[str], security_token: Optional[str], loadbalancer_id: str, metric_name: str, hours: int) -> Dict[str, Any]:
    """Read one CES ELB metric and retain a compact latest/peak summary."""
    from .common import _run_hcloud_json

    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp() * 1000)
    command = [
        "hcloud", "CES", "ShowMetricData", f"--cli-region={region}", "--cli-output=json",
        f"--namespace=SYS.ELB", f"--metric_name={metric_name}",
        f"--dim.0=lbaas_instance_id,{loadbalancer_id}",
        f"--from={start_time}", f"--to={end_time}", "--period=300", "--filter=average",
    ]
    if project_id:
        command.extend([f"--project_id={project_id}", f"--cli-project-id={project_id}"])
    for value, flag in ((access_key, "--cli-access-key"), (secret_key, "--cli-secret-key"), (security_token, "--cli-security-token")):
        if value:
            command.append(f"{flag}={value}")
    result = _run_hcloud_json(command)
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}
    payload = result.get("data") or {}
    datapoints = payload.get("datapoints") or payload.get("datapoint") or []
    values = []
    for point in datapoints:
        try:
            value = float(point.get("average"))
            timestamp = int(point.get("timestamp") or 0)
        except (AttributeError, TypeError, ValueError):
            continue
        values.append((timestamp, value))
    if not values:
        return {"success": True, "observed": False}
    values.sort()
    return {"success": True, "observed": True, "latest": values[-1][1], "peak": max(value for _, value in values)}


def _inspect_elb_metrics(region: str, loadbalancer_id: str, loadbalancer_name: Optional[str], hours: int, project_id: Optional[str], access_key: Optional[str], secret_key: Optional[str], security_token: Optional[str]) -> tuple[Dict[str, Any], list[Dict[str, Any]], list[str]]:
    metric_names = ("m9_abnormal_servers", "l4_con_usage", "l7_con_usage", "dropped_connections", "mf_l7_http_5xx", "m14_l7_rt")
    metrics, findings, gaps = {}, [], []
    for metric_name in metric_names:
        result = _get_elb_ces_metric(region, project_id, access_key, secret_key, security_token, loadbalancer_id, metric_name, hours)
        if not result.get("success"):
            gaps.append(f"ELB {loadbalancer_id} {metric_name}: {result.get('error')}")
            continue
        if result.get("observed"):
            metrics[metric_name] = {"latest": result["latest"], "peak": result["peak"]}

    display_name = loadbalancer_name or loadbalancer_id
    abnormal_servers = metrics.get("m9_abnormal_servers", {}).get("peak")
    if abnormal_servers and abnormal_servers > 0:
        findings.append(_finding("high", "elb_abnormal_backends", f"ELB {display_name} had {abnormal_servers:.0f} abnormal backend server(s) during the last {hours} hour(s).", elb_id=loadbalancer_id, metric="m9_abnormal_servers", value=abnormal_servers))
    for metric_name in ("l4_con_usage", "l7_con_usage"):
        usage = metrics.get(metric_name, {}).get("peak")
        if usage is not None and usage >= 80:
            severity = "high" if usage >= 90 else "medium"
            findings.append(_finding(severity, "elb_capacity_usage", f"ELB {display_name} {metric_name} peak usage was {usage:.1f}% during the last {hours} hour(s).", elb_id=loadbalancer_id, metric=metric_name, value=usage))
    dropped_connections = metrics.get("dropped_connections", {}).get("peak")
    if dropped_connections and dropped_connections > 0:
        findings.append(_finding("medium", "elb_dropped_connections", f"ELB {display_name} dropped connections at a peak rate of {dropped_connections:.2f}/s during the last {hours} hour(s).", elb_id=loadbalancer_id, metric="dropped_connections", value=dropped_connections))
    http_5xx = metrics.get("mf_l7_http_5xx", {}).get("peak")
    if http_5xx and http_5xx > 0:
        findings.append(_finding("medium", "elb_http_5xx", f"ELB {display_name} 5xx response rate peaked at {http_5xx:.2f}/s during the last {hours} hour(s).", elb_id=loadbalancer_id, metric="mf_l7_http_5xx", value=http_5xx))
    response_time = metrics.get("m14_l7_rt", {}).get("peak")
    if response_time is not None and response_time >= 1000:
        severity = "high" if response_time >= 3000 else "medium"
        findings.append(_finding(severity, "elb_response_time", f"ELB {display_name} average response time peaked at {response_time:.1f} ms during the last {hours} hour(s).", elb_id=loadbalancer_id, metric="m14_l7_rt", value=response_time))
    return metrics, findings, gaps


def inspect_elb(region: str, cluster_id: str, hours: int = 1, **auth: Any) -> Dict[str, Any]:
    from .common import _run_hcloud_json, get_credentials_with_region

    access_key, secret_key, project_id = get_credentials_with_region(
        region,
        auth.get("ak"),
        auth.get("sk"),
        auth.get("project_id"),
        auth.get("security_token"),
    )
    listeners_result = _list_elb_listeners(region, project_id, access_key, secret_key, auth.get("security_token"))
    if not listeners_result.get("success"):
        return {"success": False, "action": "elb_monitoring_inspection", "scope": _scope(region, cluster_id), "error": listeners_result.get("error")}

    listeners = [item for item in listeners_result.get("listeners", []) if _listener_description_matches_cluster(item, cluster_id)]
    listener_by_loadbalancer: Dict[str, list[Dict[str, Any]]] = {}
    for listener in listeners:
        loadbalancer_id = listener.get("loadbalancer_id")
        if loadbalancer_id:
            listener_by_loadbalancer.setdefault(str(loadbalancer_id), []).append(listener)

    loadbalancers, findings, data_gaps = [], [], []
    for loadbalancer_id, matched_listeners in listener_by_loadbalancer.items():
        result = _run_hcloud_json(_elb_command("ShowLoadBalancer", region, project_id, access_key, secret_key, auth.get("security_token"), f"--loadbalancer_id={loadbalancer_id}"))
        if not result.get("success"):
            data_gaps.append(f"ELB {loadbalancer_id}: {result.get('error')}")
            continue
        payload = result.get("data") or {}
        loadbalancer = payload.get("loadbalancer", payload) if isinstance(payload, dict) else {}
        if not isinstance(loadbalancer, dict):
            data_gaps.append(f"ELB {loadbalancer_id}: hcloud returned an invalid load balancer detail")
            continue
        listener_summaries = [
            {
                "id": listener.get("id"),
                "name": listener.get("name"),
                "protocol": listener.get("protocol"),
                "protocol_port": listener.get("protocol_port"),
                "admin_state_up": listener.get("admin_state_up"),
                "default_pool_id": listener.get("default_pool_id"),
                "association": "listener_description.cluster_id",
            }
            for listener in matched_listeners
        ]
        item = {
            "id": loadbalancer.get("id", loadbalancer_id),
            "name": loadbalancer.get("name"),
            "provisioning_status": loadbalancer.get("provisioning_status"),
            "operating_status": loadbalancer.get("operating_status"),
            "admin_state_up": loadbalancer.get("admin_state_up"),
            "matched_listeners": listener_summaries,
        }
        metrics, metric_findings, metric_gaps = _inspect_elb_metrics(
            region,
            str(item["id"]),
            item["name"],
            hours,
            project_id,
            access_key,
            secret_key,
            auth.get("security_token"),
        )
        item["metrics"] = metrics
        loadbalancers.append(item)
        data_gaps.extend(metric_gaps)
        findings.extend(metric_findings)
        if loadbalancer.get("admin_state_up") is False:
            findings.append(_finding("high", "elb_disabled", f"ELB {item['name'] or item['id']} is administratively disabled.", elb_id=item["id"]))
        if str(loadbalancer.get("provisioning_status") or "").lower() in {"error", "failed", "degraded"}:
            findings.append(_finding("high", "elb_provisioning", f"ELB {item['name'] or item['id']} provisioning status is {loadbalancer.get('provisioning_status')}.", elb_id=item["id"]))
        for listener in listener_summaries:
            if listener.get("admin_state_up") is False:
                findings.append(_finding("medium", "elb_listener_disabled", f"Listener {listener['name'] or listener['id']} on ELB {item['name'] or item['id']} is disabled.", elb_id=item["id"], listener_id=listener["id"]))

    return {
        "success": True,
        "action": "elb_monitoring_inspection",
        "scope": _scope(region, cluster_id),
        "loadbalancers": loadbalancers,
        "findings": findings,
        "data_gaps": data_gaps,
        "association_summary": {
            "method": "listener_description.cluster_id",
            "matched_listeners": len(listeners),
            "matched_loadbalancers": len(loadbalancers),
            "listener_pages": listeners_result.get("pages"),
            "listener_listing_truncated": listeners_result.get("truncated", False),
        },
        "metric_window_hours": hours,
    }


def _prometheus_queries(region: str, cluster_id: str, queries: Dict[str, str], **auth: Any) -> tuple[Optional[str], Dict[str, Dict[str, Any]], Optional[str]]:
    """Run related instant Prometheus queries through the cluster's AOM instance."""
    instance_result = cce.get_prom_instance_id(
        region,
        cluster_id,
        auth.get("ak"),
        auth.get("sk"),
        auth.get("project_id"),
        auth.get("security_token"),
    )
    if not instance_result.get("success"):
        return None, {}, instance_result.get("error", "AOM Prometheus is unavailable")
    instance_id = instance_result["aom_instance_id"]
    results = {
        name: aom.get_aom_prom_instant_query_http(
            region,
            instance_id,
            query,
            ak=auth.get("ak"),
            sk=auth.get("sk"),
            project_id=auth.get("project_id"),
            security_token=auth.get("security_token"),
        )
        for name, query in queries.items()
    }
    failed = [f"{name}: {result.get('error')}" for name, result in results.items() if not result.get("success")]
    return instance_id, results, "; ".join(failed) if failed else None


def _prom_scalar(result: Dict[str, Any]) -> Optional[float]:
    samples = _latest_prom_samples(result)
    return samples[0][1] if samples else None


def inspect_control_plane_health(region: str, cluster_id: str, **auth: Any) -> Dict[str, Any]:
    """Assess API server availability pressure using cluster-scoped Prometheus metrics."""
    selector = f"cluster={json.dumps(cluster_id)},component=\"apiserver\""
    queries = {
        "qps": f"sum(rate(apiserver_request_total{{{selector}}}[5m]))",
        "error_rate_percent": f"sum(rate(apiserver_request_total{{{selector},code=~\"5..\"}}[5m])) / sum(rate(apiserver_request_total{{{selector}}}[5m])) * 100",
        "latency_p95_ms": f"histogram_quantile(0.95, sum by (le) (rate(apiserver_request_duration_seconds_bucket{{{selector},verb!~\"WATCH|CONNECT\"}}[5m]))) * 1000",
        "inflight_requests": f"sum(apiserver_current_inflight_requests{{{selector}}})",
    }
    instance_id, results, error = _prometheus_queries(region, cluster_id, queries, **auth)
    if error:
        return {"success": False, "action": "control_plane_health", "scope": _scope(region, cluster_id), "error": error, "promql": queries}
    values = {name: _prom_scalar(result) for name, result in results.items()}
    findings = []
    if values["error_rate_percent"] is not None and values["error_rate_percent"] >= 1:
        severity = "high" if values["error_rate_percent"] >= 5 else "medium"
        findings.append(_finding(severity, "apiserver_5xx", f"API server 5xx rate is {values['error_rate_percent']:.2f}% over the latest five-minute rate window."))
    if values["latency_p95_ms"] is not None and values["latency_p95_ms"] >= 500:
        severity = "high" if values["latency_p95_ms"] >= 1000 else "medium"
        findings.append(_finding(severity, "apiserver_latency", f"API server P95 latency is {values['latency_p95_ms']:.1f} ms over the latest five-minute rate window."))
    return {"success": True, "action": "control_plane_health", "scope": _scope(region, cluster_id), "source": "aom_prometheus", "aom_instance_id": instance_id, "metrics": values, "promql": queries, "findings": findings}


def inspect_workload_resources(region: str, cluster_id: str, hours: int = 1, top_n: int = 10, **auth: Any) -> Dict[str, Any]:
    """Identify node and Pod CPU or memory utilisation above 85 percent of limits."""
    cluster_filter = f"cluster={json.dumps(cluster_id)}"
    queries = {
        "node_cpu_percent": f"topk({top_n}, 100 - (avg by (instance) (rate(node_cpu_seconds_total{{{cluster_filter},mode=\"idle\"}}[5m])) * 100))",
        "node_memory_percent": f"topk({top_n}, (1 - node_memory_MemAvailable_bytes{{{cluster_filter}}} / node_memory_MemTotal_bytes{{{cluster_filter}}}) * 100)",
        "pod_cpu_percent": f"topk({top_n}, sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{{{cluster_filter},image!=\"\"}}[5m])) / on (namespace, pod) group_left sum by (namespace, pod) (kube_pod_container_resource_limits{{{cluster_filter},resource=\"cpu\"}}) * 100)",
        "pod_memory_percent": f"topk({top_n}, sum by (namespace, pod) (container_memory_working_set_bytes{{{cluster_filter},image!=\"\"}}) / on (namespace, pod) group_left sum by (namespace, pod) (kube_pod_container_resource_limits{{{cluster_filter},resource=\"memory\"}}) * 100)",
    }
    instance_id, results, error = _prometheus_queries(region, cluster_id, queries, **auth)
    if error:
        return {"success": False, "action": "resource_utilization", "scope": _scope(region, cluster_id), "error": error, "promql": queries}
    findings, metrics = [], {}
    for metric_name, result in results.items():
        rows = []
        for labels, value in _latest_prom_samples(result):
            rows.append({"labels": labels, "value_percent": value})
            if value >= 85:
                target = labels.get("pod") or labels.get("instance") or "unknown"
                namespace = labels.get("namespace")
                qualified_target = f"{namespace}/{target}" if namespace else target
                findings.append(_finding("high", "resource_utilization", f"{metric_name} is {value:.1f}% for {qualified_target}.", metric=metric_name, target=qualified_target, value_percent=value))
        metrics[metric_name] = rows
    return {"success": True, "action": "resource_utilization", "scope": _scope(region, cluster_id), "source": "aom_prometheus", "aom_instance_id": instance_id, "inspection_window_hours": max(hours, 1), "threshold_percent": 85, "metrics": metrics, "promql": queries, "findings": findings}


def inspect_addon_metrics(region: str, cluster_id: str, **auth: Any) -> Dict[str, Any]:
    """Inspect installed CoreDNS, ingress, Everest, and autoscaler add-ons."""
    cluster_filter = f"cluster={json.dumps(cluster_id)}"
    everest_pod_regex = "everest-csi-controller.*|everest-csi-driver.*"
    autoscaler_pod_regex = ".*cluster.*autoscaler.*|.*autoscaler.*"
    queries = {
        "coredns_replicas": f'count(kube_pod_info{{{cluster_filter},namespace="kube-system",pod=~".*coredns.*"}})',
        "nginx_replicas": f'count(kube_pod_info{{{cluster_filter},namespace="kube-system",pod=~".*nginx.*ingress.*|.*ingress.*nginx.*"}})',
        "everest_replicas": f'count(kube_pod_info{{{cluster_filter},namespace="kube-system",pod=~"{everest_pod_regex}"}})',
        "autoscaler_replicas": f'count(kube_pod_info{{{cluster_filter},namespace="kube-system",pod=~"{autoscaler_pod_regex}"}})',
        "coredns_error_rate_percent": f'sum(rate(coredns_dns_responses_total{{{cluster_filter},namespace="kube-system",rcode!~"NOERROR|NXDOMAIN"}}[5m])) / sum(rate(coredns_dns_responses_total{{{cluster_filter},namespace="kube-system"}}[5m])) * 100',
        "coredns_latency_p95_ms": f'histogram_quantile(0.95, sum by (le) (rate(coredns_dns_request_duration_seconds_bucket{{{cluster_filter},namespace="kube-system"}}[5m]))) * 1000',
        "nginx_5xx_qps": f'sum(rate(nginx_ingress_controller_requests{{{cluster_filter},status=~"5.."}}[5m]))',
        "nginx_latency_p95_ms": f'histogram_quantile(0.95, sum by (le) (rate(nginx_ingress_controller_request_duration_seconds_bucket{{{cluster_filter}}}[5m]))) * 1000',
        "everest_ready_pods": f'sum(kube_pod_status_ready{{{cluster_filter},namespace="kube-system",pod=~"{everest_pod_regex}",condition="true"}})',
        "everest_not_ready": f'max_over_time(kube_pod_status_ready{{{cluster_filter},namespace="kube-system",pod=~"{everest_pod_regex}",condition=~"false|unknown"}}[1h]) == 1',
        "everest_pvc_metric_series": f'count(kube_persistentvolumeclaim_status_phase{{{cluster_filter}}})',
        "everest_pending_pvc": f'sum(kube_persistentvolumeclaim_status_phase{{{cluster_filter},phase="Pending"}})',
        "everest_csi_operation_metric_series": f'count(csi_operations_seconds_count{{{cluster_filter}}})',
        "everest_csi_errors_1h": f'sum(increase(csi_operations_seconds_count{{{cluster_filter},grpc_status_code!~"OK|Unknown"}}[1h]))',
        "autoscaler_unschedulable_pods": f'sum(cluster_autoscaler_unschedulable_pods_count{{{cluster_filter},namespace="kube-system",pod=~"{autoscaler_pod_regex}"}})',
        "autoscaler_errors_1h": f'sum(increase(cluster_autoscaler_errors_total{{{cluster_filter},namespace="kube-system",pod=~"{autoscaler_pod_regex}"}}[1h]))',
        "autoscaler_scaled_up_nodes_1h": f'sum(increase(cluster_autoscaler_scaled_up_nodes_total{{{cluster_filter},namespace="kube-system",pod=~"{autoscaler_pod_regex}"}}[1h]))',
        "autoscaler_scaled_down_nodes_1h": f'sum(increase(cluster_autoscaler_scaled_down_nodes_total{{{cluster_filter},namespace="kube-system",pod=~"{autoscaler_pod_regex}"}}[1h]))',
    }
    instance_id, results, error = _prometheus_queries(region, cluster_id, queries, **auth)
    if error:
        return {"success": False, "action": "addon_metrics", "scope": _scope(region, cluster_id), "error": error, "promql": queries}
    values = {name: _prom_scalar(result) for name, result in results.items()}
    findings, components = [], {}
    for component, presence_key, signals in (
        ("coredns", "coredns_replicas", (("coredns_error_rate_percent", 1), ("coredns_latency_p95_ms", 200))),
        ("nginx_ingress", "nginx_replicas", (("nginx_5xx_qps", 0), ("nginx_latency_p95_ms", 500))),
    ):
        present = bool(values[presence_key] and values[presence_key] > 0)
        components[component] = {"present": present, "metrics": {name: values[name] for name, _ in signals}}
        if not present:
            components[component]["status"] = "not_installed_or_not_observed"
            continue
        observed = [name for name, _ in signals if values[name] is not None]
        components[component]["observed_metrics"] = observed
        components[component]["status"] = "healthy" if observed else "metrics_not_observed"
        for name, threshold in signals:
            value = values[name]
            if value is not None and value > threshold:
                components[component]["status"] = "degraded"
                findings.append(_finding("medium", "addon_metric", f"{component} {name} is {value:.2f}.", component=component, metric=name, value=value))

    everest_signals = (
        ("everest_not_ready", 0, "Everest CSI Pods were not Ready during the last hour."),
        ("everest_pending_pvc", 0, "PersistentVolumeClaims are Pending."),
        ("everest_csi_errors_1h", 0, "Everest CSI operations reported errors during the last hour."),
    )
    everest_coverage = {
        "everest_not_ready": values["everest_ready_pods"] is not None,
        "everest_pending_pvc": values["everest_pvc_metric_series"] is not None,
        "everest_csi_errors_1h": values["everest_csi_operation_metric_series"] is not None,
    }
    for signal, covered in everest_coverage.items():
        if covered and values[signal] is None:
            values[signal] = 0.0
    everest_present = bool(values["everest_replicas"] and values["everest_replicas"] > 0)
    components["everest"] = {
        "present": everest_present,
        "metrics": {
            "replicas": values["everest_replicas"],
            "ready_pods": values["everest_ready_pods"],
            **{name: values[name] for name, _, _ in everest_signals},
        },
    }
    if not everest_present:
        components["everest"]["status"] = "not_installed_or_not_observed"
    else:
        observed = [name for name, _, _ in everest_signals if everest_coverage[name]]
        components["everest"]["observed_metrics"] = observed
        components["everest"]["status"] = "healthy" if observed else "metrics_not_observed"
        for name, threshold, message in everest_signals:
            value = values[name]
            if value is not None and value > threshold:
                components["everest"]["status"] = "degraded"
                findings.append(_finding("medium", "addon_metric", f"{message} Observed value: {value:.2f}.", component="everest", metric=name, value=value))

    autoscaler_signals = (
        ("autoscaler_unschedulable_pods", 0, "Cluster Autoscaler reports unschedulable Pods."),
        ("autoscaler_errors_1h", 0, "Cluster Autoscaler reported errors during the last hour."),
    )
    autoscaler_present = bool(values["autoscaler_replicas"] and values["autoscaler_replicas"] > 0)
    components["cluster_autoscaler"] = {
        "present": autoscaler_present,
        "metrics": {
            "replicas": values["autoscaler_replicas"],
            **{name: values[name] for name, _, _ in autoscaler_signals},
            "autoscaler_scaled_up_nodes_1h": values["autoscaler_scaled_up_nodes_1h"],
            "autoscaler_scaled_down_nodes_1h": values["autoscaler_scaled_down_nodes_1h"],
        },
    }
    if not autoscaler_present:
        components["cluster_autoscaler"]["status"] = "not_installed_or_not_observed"
    else:
        observed = [name for name, _, _ in autoscaler_signals if values[name] is not None]
        components["cluster_autoscaler"]["observed_metrics"] = observed
        components["cluster_autoscaler"]["status"] = "healthy" if observed else "metrics_not_observed"
        for name, threshold, message in autoscaler_signals:
            value = values[name]
            if value is not None and value > threshold:
                components["cluster_autoscaler"]["status"] = "degraded"
                findings.append(_finding("high", "addon_metric", f"{message} Observed value: {value:.2f}.", component="cluster_autoscaler", metric=name, value=value))
    return {"success": True, "action": "addon_metrics", "scope": _scope(region, cluster_id), "source": "aom_prometheus", "aom_instance_id": instance_id, "components": components, "promql": queries, "findings": findings}


def inspect_active_aom_alarms(region: str, cluster_id: str, cluster_name: Optional[str] = None, alarm_limit: int = 200, **auth: Any) -> Dict[str, Any]:
    """Return current active AOM alarms only; recovered history is intentionally excluded."""
    from .common import _run_hcloud_json

    alarms, marker, pages, truncated, seen = [], "0", 0, False, set()
    while marker and len(alarms) < max(alarm_limit, 1) and pages < 20:
        command = ["hcloud", "AOM", "ListEvents", f"--cli-region={region}", "--cli-output=json", "--type=active_alert", "--time_range=-1.-1.60", f"--limit={min(200, max(alarm_limit, 1) - len(alarms))}", f"--marker={marker}"]
        for key, flag in (("project_id", "--cli-project-id"), ("ak", "--cli-access-key"), ("sk", "--cli-secret-key"), ("security_token", "--cli-security-token")):
            if auth.get(key):
                command.append(f"{flag}={auth[key]}")
        result = _run_hcloud_json(command)
        if not result.get("success"):
            return {"success": False, "action": "active_aom_alarms", "scope": _scope(region, cluster_id), "error": result.get("error")}
        payload = result.get("data") or {}
        source = payload if isinstance(payload, list) else payload.get("events", payload.get("event_info", []))
        for item in source:
            if not isinstance(item, dict) or not _alarm_matches_cluster(item, cluster_id, cluster_name):
                continue
            identity = item.get("id") or item.get("event_sn") or json.dumps(item, sort_keys=True, ensure_ascii=False)
            if identity not in seen:
                seen.add(identity)
                alarms.append(item)
        marker = None if isinstance(payload, list) else payload.get("next_marker")
        pages += 1
        truncated = bool(marker) and (len(alarms) >= alarm_limit or pages >= 20)
        if not source:
            break
    alarms = alarms[:max(alarm_limit, 1)]
    findings = [_finding("high", "aom_active_alarm", f"{((alarm.get('metadata') or {}).get('event_name') or alarm.get('event_name') or 'AOM alarm')} is active.", event_id=alarm.get("id") or alarm.get("event_sn")) for alarm in alarms]
    return {"success": True, "action": "active_aom_alarms", "scope": _scope(region, cluster_id), "source": "aom", "active_alarms": alarms, "findings": findings, "alarm_summary": {"active_returned": len(alarms), "limit": alarm_limit, "truncated": truncated, "pages": pages}}


def aggregate(results: Iterable[Dict[str, Any]], action: str = "cce_auto_inspection") -> Dict[str, Any]:
    checks = list(results)
    for check in checks:
        if not check.get("success"):
            check.setdefault("status", "unavailable")
        elif any(finding.get("severity") in {"high", "medium"} for finding in check.get("findings") or []):
            check.setdefault("status", "degraded")
        else:
            check.setdefault("status", "healthy")
    findings = [finding for check in checks if check.get("success") for finding in check.get("findings") or []]
    gaps = [f"{check.get('action', 'check')}: {check.get('error')}" for check in checks if not check.get("success")]
    gaps.extend(gap for check in checks if check.get("success") for gap in check.get("data_gaps") or [])
    statuses = {status: sum(check.get("status") == status for check in checks) for status in ("healthy", "degraded", "unavailable")}
    overall_status = "unavailable" if statuses["unavailable"] else "degraded" if statuses["degraded"] else "healthy"
    return {"success": True, "action": action, "checks": checks, "findings": findings, "data_gaps": gaps, "summary": {"checks": len(checks), "findings": len(findings), "failed_checks": sum(not check.get("success") for check in checks), "status_counts": statuses, "overall_status": overall_status}}


def inspect_cluster(region: str, cluster_id: str, namespace: Optional[str] = None, hours: int = 1, top_n: int = 10, mode: str = "auto", **auth: Any) -> Dict[str, Any]:
    availability = inspect_cluster_availability(region, cluster_id, **auth)
    if not availability.get("success"):
        return {"success": False, "action": "cce_deep_diagnosis", "scope": _scope(region, cluster_id, namespace), "checks": [availability], "findings": [], "data_gaps": [f"cluster_availability: {availability.get('error')}"]}
    if availability.get("findings"):
        result = aggregate([availability], "cce_deep_diagnosis")
        result["execution_stopped"] = True
        result["stop_reason"] = "The cluster is not available; dependent diagnostics were not queried."
        result["scope"] = _scope(region, cluster_id, namespace)
        return result

    cluster_name = _cluster_name(availability.get("cluster") or {})
    node_check = inspect_node_health_from_prometheus(region, cluster_id, hours=hours, **auth)
    if not node_check.get("success"):
        fallback_error = node_check.get("error")
        node_check = inspect_nodes(region, cluster_id, include_events=False, hours=hours, **auth)
        node_check = _mark_current_state_fallback(
            node_check,
            fallback_error,
            "current_state",
            "Prometheus history is unavailable; kubectl cce was used to inspect current node state only.",
        )
    resource_check = inspect_workload_resources(region, cluster_id, hours, top_n, **auth)
    pod_check = inspect_pod_health_from_prometheus(region, cluster_id, hours=hours, **auth)
    if not pod_check.get("success"):
        fallback_error = pod_check.get("error")
        pod_check = inspect_cluster_pods(region, cluster_id, **auth)
        pod_check = _mark_current_state_fallback(
            pod_check,
            fallback_error,
            "current_state",
            "Prometheus history is unavailable; kubectl cce was used to inspect current Pod state only.",
        )
    event_check = inspect_recent_warning_events_from_lts(region, cluster_id, hours, **auth)
    if not event_check.get("success"):
        fallback_error = event_check.get("error")
        event_check = inspect_recent_warning_events(region, cluster_id, hours, **auth)
        event_check = _mark_current_state_fallback(
            event_check,
            fallback_error,
            "current_event_records",
            f"LTS history is unavailable; kubectl cce was used to read current Event records filtered to the preceding {hours} hour(s).",
        )
    checks = [
        availability,
        inspect_control_plane_health(region, cluster_id, **auth),
        node_check,
        resource_check,
        pod_check,
        event_check,
        inspect_addon_metrics(region, cluster_id, **auth),
        inspect_active_aom_alarms(region, cluster_id, cluster_name, **auth),
        inspect_elb(region, cluster_id, hours=hours, **auth),
    ]
    result = aggregate(checks, "cce_deep_diagnosis")
    result["scope"] = _scope(region, cluster_id, namespace)
    return result


def quick_check(region: str, cluster_id: str, event_limit: int = 200, pod_limit: int = 200, alarm_limit: int = 200, hours: int = 1, **auth: Any) -> Dict[str, Any]:
    availability = inspect_cluster_availability(region, cluster_id, **auth)
    if not availability.get("success"):
        return {"success": False, "action": "cce_quick_check", "checks": [availability], "findings": [], "data_gaps": [f"cluster_availability: {availability.get('error')}"], "summary": {"checks": 1, "findings": 0, "failed_checks": 1, "status_counts": {"healthy": 0, "degraded": 0, "unavailable": 1}, "overall_status": "unavailable"}}
    if availability.get("findings"):
        result = aggregate([availability], "cce_quick_check")
        result["execution_stopped"] = True
        result["stop_reason"] = "The cluster is not in an available state; dependent evidence was not queried."
        return result

    node_health = inspect_node_health_from_prometheus(region, cluster_id, hours=hours, **auth)
    if not node_health.get("success"):
        fallback_error = node_health.get("error")
        node_health = inspect_nodes(region, cluster_id, include_events=False, hours=hours, **auth)
        node_health.setdefault("action", "node_status_inspection")
        node_health.setdefault("scope", _scope(region, cluster_id))
        node_health.setdefault("source", "kubectl_cce")
        node_health.setdefault("observation_scope", "current_state")
        node_health["fallback_reason"] = fallback_error
        node_health["historical_coverage"] = False
        node_health["observation_note"] = "Prometheus history is unavailable; kubectl cce was used to inspect current node state only."
    pod_health = inspect_pod_health_from_prometheus(region, cluster_id, pod_limit, hours=hours, **auth)
    if not pod_health.get("success"):
        fallback_error = pod_health.get("error")
        pod_health = inspect_cluster_pods(region, cluster_id, pod_limit, **auth)
        pod_health.setdefault("action", "cluster_pod_check")
        pod_health.setdefault("scope", _scope(region, cluster_id))
        pod_health.setdefault("source", "kubectl_cce")
        pod_health.setdefault("observation_scope", "current_state")
        pod_health["fallback_reason"] = fallback_error
        pod_health["historical_coverage"] = False
        pod_health["observation_note"] = "Prometheus history is unavailable; kubectl cce was used to inspect current Pod state only."
    event_check = inspect_recent_warning_events_from_lts(region, cluster_id, hours, event_limit, **auth)
    if not event_check.get("success"):
        fallback_error = event_check.get("error")
        event_check = inspect_recent_warning_events(region, cluster_id, hours, event_limit, **auth)
        event_check.setdefault("action", "warning_event_check")
        event_check.setdefault("scope", _scope(region, cluster_id))
        event_check.setdefault("source", "kubectl_cce")
        event_check.setdefault("observation_scope", "current_event_records")
        event_check["fallback_reason"] = fallback_error
        event_check["historical_coverage"] = False
        event_check["observation_note"] = f"LTS history is unavailable; kubectl cce was used to read current Event records and filter their timestamps to the preceding {hours} hour(s)."
    return aggregate([availability, node_health, pod_health, event_check, inspect_recent_aom_alarms(region, cluster_id, alarm_limit, cluster_name=_cluster_name(availability.get("cluster") or {}), hours=hours, **auth)], "cce_quick_check")


def _markdown_cell(value: Any) -> str:
    return str(value if value is not None else "N/A").replace("|", "\\|").replace("\n", " ")


def _inspection_markdown(result: Dict[str, Any]) -> str:
    """Render the compact, human-readable view of an inspection result."""
    scope = result.get("scope") or {}
    summary = result.get("summary") or {}
    checks = result.get("checks") or []
    findings = result.get("findings") or []
    lines = [
        "# CCE Inspection Report",
        "",
        "## Scope",
        f"- Region: `{_markdown_cell(scope.get('region'))}`",
        f"- Cluster ID: `{_markdown_cell(scope.get('cluster_id'))}`",
        f"- Overall status: **{_markdown_cell(summary.get('overall_status', 'unknown'))}**",
        "",
        "## Summary",
        "| Checks | Healthy | Degraded | Unavailable | Findings |",
        "| ---: | ---: | ---: | ---: | ---: |",
        f"| {_markdown_cell(summary.get('checks', len(checks)))} | {_markdown_cell((summary.get('status_counts') or {}).get('healthy', 0))} | {_markdown_cell((summary.get('status_counts') or {}).get('degraded', 0))} | {_markdown_cell((summary.get('status_counts') or {}).get('unavailable', 0))} | {_markdown_cell(summary.get('findings', len(findings)))} |",
        "",
        "## Check Results",
        "| Check | Status | Source | Findings |",
        "| --- | --- | --- | ---: |",
    ]
    for check in checks:
        check_findings = check.get("findings") or []
        lines.append(
            f"| `{_markdown_cell(check.get('action'))}` | {_markdown_cell(check.get('status'))} | {_markdown_cell(check.get('source', 'N/A'))} | {len(check_findings)} |"
        )
    if findings:
        lines.extend([
            "",
            "## Findings",
            "| Severity | Category | Detail |",
            "| --- | --- | --- |",
        ])
        for finding in findings:
            lines.append(
                f"| {_markdown_cell(finding.get('severity'))} | {_markdown_cell(finding.get('category'))} | {_markdown_cell(finding.get('message'))} |"
            )
    gaps = result.get("data_gaps") or []
    if gaps:
        lines.extend(["", "## Data Gaps"])
        lines.extend(f"- {_markdown_cell(gap)}" for gap in gaps)
    return "\n".join(lines) + "\n"


def export_report(result: Dict[str, Any], output_file: str) -> Dict[str, Any]:
    target = Path(output_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    output_format = "markdown" if target.suffix.lower() in {".md", ".markdown"} else "json"
    content = _inspection_markdown(result) if output_format == "markdown" else json.dumps(result, ensure_ascii=False, indent=2)
    target.write_text(content, encoding="utf-8")
    return {"success": True, "action": "export_inspection_report", "output_file": str(target), "output_format": output_format}
