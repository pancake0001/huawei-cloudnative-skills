"""AOM alarm actions implemented through hcloud CLI."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .common import extract_items, redact_command, run_hcloud, run_hcloud_json_input


EVENT_NAME_ALIASES = {
    "FailedScheduling": "调度失败##FailedScheduling",
    "FailedCreate": "创建失败##FailedCreate",
    "FailedDelete": "删除失败##FailedDelete",
    "FailedUpdate": "更新失败##FailedUpdate",
    "NodeNotReady": "节点未就绪##NodeNotReady",
    "NodeReady": "节点就绪##NodeReady",
    "Unhealthy": "不健康##Unhealthy",
    "BackOff": "容器启动退避##BackOff",
    "OOMKilling": "OOM 击杀##OOMKilling",
    "Killing": "容器终止##Killing",
    "Pulling": "拉取镜像##Pulling",
    "Pulled": "镜像拉取完成##Pulled",
}


def _normalize_alarm_rule_name(rule_name: str) -> str:
    return "_".join(str(rule_name).split())


def _period_to_window(period: int) -> str:
    if period <= 30:
        return "30s"
    if period <= 60:
        return "1m"
    if period <= 300:
        return "5m"
    if period <= 900:
        return "15m"
    return "1h"


def _severity_key(alarm_level: Any) -> str:
    mapping = {
        "critical": "1",
        "major": "2",
        "minor": "3",
        "info": "4",
        "warning": "4",
    }
    return mapping.get(str(alarm_level).strip().lower(), str(alarm_level))


def _normalize_event_name(event_name: str) -> str:
    if "##" in event_name:
        return event_name
    return EVENT_NAME_ALIASES.get(event_name, event_name)


def _first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def _get_nested(source: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        cur: Any = source
        for part in path.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                cur = None
            if cur is None:
                break
        if cur is not None:
            return cur
    return None


def _normalize_event(raw: Dict[str, Any], default_status: str) -> Dict[str, Any]:
    metadata = _first_dict(raw.get("metadata"), raw.get("annotations"), raw.get("resource_provider"))
    starts_at = _get_nested(raw, "starts_at", "start_time", "create_time", "occur_time", "arrives_at", "metadata.starts_at")
    try:
        starts_at = int(starts_at) if starts_at is not None else None
    except (TypeError, ValueError):
        starts_at = None

    status = _get_nested(raw, "status", "event_status", "metadata.status") or default_status
    if default_status == "active_alert" and status == default_status:
        status = "firing"
    elif default_status == "history_alert" and status == default_status:
        status = "resolved"

    normalized = {
        "event_sn": _get_nested(raw, "event_sn", "id", "event_id", "metadata.event_sn"),
        "event_name": _get_nested(raw, "event_name", "name", "metadata.event_name") or "Unknown",
        "event_severity": _get_nested(raw, "event_severity", "severity", "level", "metadata.event_severity") or "Unknown",
        "status": status,
        "starts_at": starts_at,
        "resource_id": _get_nested(raw, "resource_id", "resource", "metadata.resource_id") or "",
        "cluster_id": _get_nested(raw, "cluster_id", "metadata.clusterId", "metadata.cluster_id") or "",
        "cluster_name": _get_nested(raw, "cluster_name", "metadata.clusterName", "metadata.cluster_name") or "",
        "cluster_alias_name": _get_nested(raw, "cluster_alias_name", "metadata.clusterAliasName") or "",
        "namespace": _get_nested(raw, "namespace", "metadata.namespace") or "",
        "pod_name": _get_nested(raw, "pod_name", "metadata.podName", "metadata.pod_name") or "",
        "message": _get_nested(raw, "message", "description", "metadata.message") or "",
        "raw": raw,
    }
    if isinstance(metadata, dict):
        normalized["metadata"] = metadata
    return normalized


def _filter_events_by_cluster(events: list, cluster_id: Optional[str] = None, cluster_name: Optional[str] = None) -> list:
    if not cluster_id and not cluster_name:
        return events

    filtered = []
    for event in events:
        resource_id = event.get("resource_id", "")
        if cluster_id and (event.get("cluster_id") == cluster_id or cluster_id in resource_id or cluster_id in str(event.get("raw", ""))):
            filtered.append(event)
            continue
        if cluster_name and (
            event.get("cluster_name") == cluster_name
            or cluster_name in event.get("cluster_alias_name", "")
            or cluster_name in str(event.get("raw", ""))
        ):
            filtered.append(event)
    return filtered


def _build_metric_alarm_params(
    rule_name: str,
    metric_name: str,
    namespace: str,
    comparison_operator: str,
    threshold: str,
    period: int,
    evaluation_periods: int,
    statistic: str,
    alarm_level: int,
    create_fields: Optional[Dict[str, Any]] = None,
    action_id: str = "add-alarm-action",
) -> List[tuple[str, Any]]:
    fields = create_fields or {}
    level_key = _severity_key(fields.get("alarm_level", alarm_level))
    params: List[tuple[str, Any]] = [
        ("action_id", action_id),
        ("alarm_rule_name", _normalize_alarm_rule_name(rule_name)),
        ("alarm_rule_type", "metric"),
        ("alarm_rule_enable", fields.get("is_turn_on", fields.get("alarm_rule_enable", True))),
        ("alarm_rule_description", fields.get("alarm_rule_description") or fields.get("alarm_description") or "Created by Codex hcloud skill."),
        ("metric_alarm_spec.monitor_type", fields.get("monitor_type", "all_metric")),
        ("metric_alarm_spec.trigger_conditions.1.metric_name", metric_name),
        ("metric_alarm_spec.trigger_conditions.1.metric_namespace", namespace),
        ("metric_alarm_spec.trigger_conditions.1.operator", comparison_operator),
        (f"metric_alarm_spec.trigger_conditions.1.thresholds.{level_key}", threshold),
        ("metric_alarm_spec.trigger_conditions.1.aggregation_window", _period_to_window(period)),
        ("metric_alarm_spec.trigger_conditions.1.trigger_times", evaluation_periods),
        ("metric_alarm_spec.trigger_conditions.1.aggregation_type", statistic),
    ]
    if fields.get("unit"):
        params.append(("metric_alarm_spec.trigger_conditions.1.metric_unit", fields["unit"]))
    if fields.get("prom_instance_id"):
        params.append(("prom_instance_id", fields["prom_instance_id"]))
    if fields.get("promql"):
        params.extend([
            ("metric_alarm_spec.monitor_type", "promql"),
            ("metric_alarm_spec.trigger_conditions.1.promql", fields["promql"]),
        ])
    return params


def _preview(action: str, region: str, params: List[tuple[str, Any]], risk: str, message: str) -> Dict[str, Any]:
    command = ["hcloud", "AOM", action, f"--cli-region={region}", "--cli-output=json"]
    for key, value in params:
        if value is not None:
            if isinstance(value, bool):
                value = "true" if value else "false"
            command.append(f"--{key}={value}")
    return {
        "success": True,
        "action": action,
        "region": region,
        "risk": risk,
        "confirm_required": True,
        "will_execute": False,
        "executed": False,
        "hcloud_command": redact_command(command),
        "message": message,
    }


def list_aom_alarm_rules(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    enterprise_project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params: List[tuple[str, Any]] = [
        ("limit", str(limit)),
        ("offset", str(offset)),
        ("Enterprise-Project-Id", enterprise_project_id or "all_granted_eps"),
    ]
    result = run_hcloud("AOM", "ListMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    if not result["success"]:
        return result

    rules = extract_items(result.get("data"), "alarm_rules", "rules")
    formatted = []
    for rule in rules:
        metric_spec = rule.get("metric_alarm_spec") or {}
        event_spec = rule.get("event_alarm_spec") or {}
        formatted.append({
            "rule_name": rule.get("alarm_rule_name") or rule.get("name"),
            "rule_id": rule.get("alarm_rule_id") or rule.get("id"),
            "rule_type": rule.get("alarm_rule_type"),
            "enabled": rule.get("alarm_rule_enable"),
            "status": rule.get("alarm_rule_status"),
            "severity": rule.get("event_severity"),
            "metric_alarm_spec": metric_spec,
            "event_alarm_spec": event_spec,
            "raw": rule,
        })

    return {
        "success": True,
        "region": region,
        "action": "list_aom_alarm_rules",
        "count": len(formatted),
        "rules": formatted,
        "raw": result.get("data"),
        "hcloud_command": result["command"],
    }


def create_aom_alarm_rule(
    region: str,
    rule_name: str,
    metric_name: str,
    namespace: str,
    comparison_operator: str,
    threshold: str,
    period: int,
    evaluation_periods: int,
    statistic: str,
    alarm_level: int,
    create_fields: Optional[Dict[str, Any]] = None,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params = _build_metric_alarm_params(
        rule_name, metric_name, namespace, comparison_operator, threshold,
        period, evaluation_periods, statistic, alarm_level, create_fields,
    )
    if not confirm:
        preview = _preview("AddOrUpdateMetricOrEventAlarmRule", region, params, "MEDIUM", "Preview only. Add confirm=true to create the AOM metric alarm rule through hcloud.")
        preview["rule_payload"] = dict(params)
        return preview

    result = run_hcloud("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    result.update({"action": "create_aom_alarm_rule", "executed": result["success"]})
    return result


def create_aom_event_alarm_rule(
    region: str,
    cluster_id: str,
    rule_name: str,
    event_name: str,
    bind_notification_rule_id: Optional[str] = None,
    event_label: Optional[str] = None,
    alarm_level: str = "Major",
    description: Optional[str] = None,
    alias: Optional[str] = None,
    trigger_type: str = "immediately",
    frequency: str = "-1",
    prom_instance_id: Optional[str] = None,
    enterprise_project_id: Optional[str] = None,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_event_name = _normalize_event_name(event_name)
    level_key = _severity_key(alarm_level)
    params: List[tuple[str, Any]] = [
        ("action_id", "add-alarm-action"),
        ("Enterprise-Project-Id", enterprise_project_id or "0"),
        ("alarm_rule_name", _normalize_alarm_rule_name(rule_name)),
        ("alarm_rule_type", "event"),
        ("alarm_rule_enable", True),
        ("alarm_rule_description", description or "Created by Codex hcloud skill."),
        ("alias", alias or _normalize_alarm_rule_name(rule_name)),
        ("event_alarm_spec.alarm_source", "systemEvent"),
        ("event_alarm_spec.event_source", "CCE"),
        ("event_alarm_spec.monitor_objects.1.clusterId", cluster_id),
        ("event_alarm_spec.trigger_conditions.1.event_name", normalized_event_name),
        ("event_alarm_spec.trigger_conditions.1.trigger_type", trigger_type),
        ("event_alarm_spec.trigger_conditions.1.frequency", frequency),
        (f"event_alarm_spec.trigger_conditions.1.thresholds.{level_key}", 1),
    ]
    if event_label:
        params.append(("event_alarm_spec.monitor_objects.1.event_label", event_label))
    if prom_instance_id:
        params.append(("prom_instance_id", prom_instance_id))
    if bind_notification_rule_id:
        params.extend([
            ("alarm_notifications.notification_type", "direct"),
            ("alarm_notifications.notification_enable", True),
            ("alarm_notifications.route_group_enable", False),
            ("alarm_notifications.bind_notification_rule_id", bind_notification_rule_id),
            ("alarm_notifications.notify_frequency", 0),
            ("alarm_notifications.notify_resolved", False),
            ("alarm_notifications.notify_triggered", True),
        ])
    else:
        params.extend([
            ("alarm_notifications.notification_type", "alarm_policy"),
            ("alarm_notifications.notification_enable", False),
            ("alarm_notifications.route_group_enable", True),
            ("alarm_notifications.notify_frequency", -1),
            ("alarm_notifications.notify_resolved", False),
            ("alarm_notifications.notify_triggered", False),
        ])

    if not confirm:
        preview = _preview("AddOrUpdateMetricOrEventAlarmRule", region, params, "MEDIUM", "Preview only. Add confirm=true to create the AOM event alarm rule through hcloud.")
        preview["rule_payload"] = dict(params)
        return preview

    result = run_hcloud("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    result.update({"action": "create_aom_event_alarm_rule", "executed": result["success"]})
    return result


def update_aom_alarm_rule(
    region: str,
    rule_name: str,
    updates: Dict[str, Any],
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params = _build_metric_alarm_params(
        rule_name=rule_name,
        metric_name=updates.get("metric_name", ""),
        namespace=updates.get("namespace", ""),
        comparison_operator=updates.get("comparison_operator", ">"),
        threshold=str(updates.get("threshold", "")),
        period=int(updates.get("period", 60) or 60),
        evaluation_periods=int(updates.get("evaluation_periods", 1) or 1),
        statistic=updates.get("statistic", "average"),
        alarm_level=int(updates.get("alarm_level", 2) or 2),
        create_fields=updates,
        action_id="update-alarm-action",
    )
    if not confirm:
        preview = _preview("AddOrUpdateMetricOrEventAlarmRule", region, params, "HIGH", "Preview only. Add confirm=true to update the AOM alarm rule through hcloud.")
        preview["rule_payload"] = dict(params)
        return preview

    result = run_hcloud("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    result.update({"action": "update_aom_alarm_rule", "executed": result["success"]})
    return result


def delete_aom_alarm_rule(
    region: str,
    rule_name: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params = [("alarm_rules.1", rule_name)]
    if not confirm:
        return _preview("DeleteMetricOrEventAlarmRule", region, params, "HIGH", "Preview only. Add confirm=true to delete the AOM alarm rule through hcloud.")
    result = run_hcloud("AOM", "DeleteMetricOrEventAlarmRule", region, params, ak, sk, project_id)
    result.update({"action": "delete_aom_alarm_rule", "executed": result["success"]})
    return result


def _find_rule_by_id(region: str, rule_id: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Optional[Dict[str, Any]]:
    result = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0)
    for item in result.get("rules", []):
        raw = item.get("raw", {})
        if str(item.get("rule_id")) == str(rule_id):
            return raw
    return None


def _set_alarm_rule_enabled(region: str, rule_id: str, enabled: bool, confirm: bool, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    if not confirm:
        action = "enable" if enabled else "disable"
        return {
            "success": True,
            "action": f"{action}_aom_alarm_rule",
            "region": region,
            "rule_id": rule_id,
            "risk": "HIGH" if not enabled else "MEDIUM",
            "confirm_required": True,
            "will_execute": False,
            "executed": False,
            "message": f"Preview only. Add confirm=true to {action} the AOM alarm rule through hcloud.",
        }

    rule = _find_rule_by_id(region, rule_id, ak, sk, project_id)
    if not rule:
        return {"success": False, "error": f"Alarm rule not found by rule_id={rule_id}"}

    body = {
        "alarm_rule_name": rule.get("alarm_rule_name"),
        "alarm_rule_type": rule.get("alarm_rule_type"),
        "alarm_rule_enable": enabled,
        "alarm_rule_description": rule.get("alarm_rule_description"),
        "prom_instance_id": rule.get("prom_instance_id"),
        "event_alarm_spec": rule.get("event_alarm_spec"),
        "metric_alarm_spec": rule.get("metric_alarm_spec"),
        "alarm_notifications": rule.get("alarm_notifications"),
    }
    body = {k: v for k, v in body.items() if v is not None}
    payload = {
        "query": {"action_id": "update-alarm-action"},
        "body": body,
    }
    if project_id:
        payload["path"] = {"project_id": project_id}
    ep_id = rule.get("enterprise_project_id")
    if ep_id:
        payload["header"] = {"Enterprise-Project-Id": ep_id}

    result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, project_id)
    result.update({"action": "enable_aom_alarm_rule" if enabled else "disable_aom_alarm_rule", "executed": result["success"]})
    return result


def disable_aom_alarm_rule(region: str, rule_id: str, confirm: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    return _set_alarm_rule_enabled(region, rule_id, False, confirm, ak, sk, project_id)


def enable_aom_alarm_rule(region: str, rule_id: str, confirm: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    return _set_alarm_rule_enabled(region, rule_id, True, confirm, ak, sk, project_id)


def list_aom_action_rules(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, enterprise_project_id: Optional[str] = None) -> Dict[str, Any]:
    del enterprise_project_id
    result = run_hcloud("AOM", "ListActionRule", region, [], ak, sk, project_id)
    if not result["success"]:
        return result
    rules = extract_items(result.get("data"), "action_rules", "rules")
    return {"success": True, "region": region, "action": "list_aom_action_rules", "count": len(rules), "rules": rules, "raw": result.get("data"), "hcloud_command": result["command"]}


def delete_aom_action_rule(region: str, rule_name: str, confirm: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    params = [("1", rule_name)]
    if not confirm:
        return _preview("DeleteActionRule", region, params, "HIGH", "Preview only. Add confirm=true to delete the AOM action rule through hcloud.")
    result = run_hcloud("AOM", "DeleteActionRule", region, params, ak, sk, project_id)
    result.update({"action": "delete_aom_action_rule", "executed": result["success"]})
    return result


def list_aom_mute_rules(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    result = run_hcloud("AOM", "ListMuteRule", region, [], ak, sk, project_id)
    if not result["success"]:
        return result
    rules = extract_items(result.get("data"), "mute_rules", "rules")
    return {"success": True, "region": region, "action": "list_aom_mute_rules", "count": len(rules), "rules": rules, "raw": result.get("data"), "hcloud_command": result["command"]}


def list_aom_current_alarms(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    event_type: str = "active_alert",
    event_severity: str = None,
    time_range: str = None,
    limit: int = 100,
    cluster_id: Optional[str] = None,
) -> Dict[str, Any]:
    params: List[tuple[str, Any]] = [
        ("time_range", time_range or "-1.-1.1440"),
        ("type", event_type),
        ("limit", limit),
    ]
    result = run_hcloud("AOM", "ListEvents", region, params, ak, sk, project_id)
    if not result["success"]:
        return result

    raw_events = extract_items(result.get("data"), "events", "event_info", "alarms")
    events = [_normalize_event(item, event_type) for item in raw_events]
    events = _filter_events_by_cluster(events, cluster_id=cluster_id)
    if event_severity:
        events = [event for event in events if str(event.get("event_severity")).lower() == event_severity.lower()]

    firing_count = sum(1 for event in events if event.get("status") == "firing")
    resolved_count = sum(1 for event in events if event.get("status") == "resolved")
    severity_stats: Dict[str, int] = {}
    for event in events:
        sev = event.get("event_severity", "Unknown")
        severity_stats[sev] = severity_stats.get(sev, 0) + 1

    return {
        "success": True,
        "region": region,
        "api": "hcloud AOM ListEvents",
        "query_type": event_type,
        "cluster_id": cluster_id,
        "time_range": time_range or "-1.-1.1440",
        "total_count": len(events),
        "firing_count": firing_count,
        "resolved_count": resolved_count,
        "severity_stats": severity_stats,
        "events": events,
        "raw": result.get("data"),
        "hcloud_command": result["command"],
    }


def list_aom_alarms(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    hours: int = 1,
    event_severity: Optional[str] = None,
    cluster_id: Optional[str] = None,
    cluster_name: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    time_range_str = f"-1.-1.{hours * 60}"
    tz8 = timezone(timedelta(hours=8))

    active_result = list_aom_current_alarms(region, ak, sk, project_id, "active_alert", event_severity, time_range_str, limit, cluster_id)
    if not active_result.get("success"):
        return active_result
    history_result = list_aom_current_alarms(region, ak, sk, project_id, "history_alert", event_severity, time_range_str, limit, cluster_id)
    if not history_result.get("success"):
        return history_result

    seen_sns = set()
    all_events = []
    for event in active_result.get("events", []) + history_result.get("events", []):
        sn = event.get("event_sn") or json.dumps(event.get("raw", {}), sort_keys=True, ensure_ascii=False)
        if sn in seen_sns:
            continue
        seen_sns.add(sn)
        all_events.append(event)

    all_events = _filter_events_by_cluster(all_events, cluster_id=cluster_id, cluster_name=cluster_name)
    firing_count = sum(1 for event in all_events if event.get("status") == "firing")
    resolved_count = sum(1 for event in all_events if event.get("status") == "resolved")

    type_stats: Dict[str, Dict[str, int]] = {}
    severity_stats: Dict[str, int] = {}
    for event in all_events:
        name = event.get("event_name", "Unknown")
        type_stats.setdefault(name, {"count": 0, "firing": 0, "resolved": 0})
        type_stats[name]["count"] += 1
        if event.get("status") == "firing":
            type_stats[name]["firing"] += 1
        else:
            type_stats[name]["resolved"] += 1
        sev = event.get("event_severity", "Unknown")
        severity_stats[sev] = severity_stats.get(sev, 0) + 1

    lines = [
        f"告警查询报告 (近 {hours} 小时, active + history via hcloud)",
        f"活跃告警: {firing_count} 条 | 已恢复: {resolved_count} 条 | 合并去重后: {len(all_events)} 条",
        "",
    ]
    if type_stats:
        lines.append("按类型统计:")
        for name, stats in sorted(type_stats.items(), key=lambda item: item[1]["count"], reverse=True):
            lines.append(f"  {name}: {stats['count']}条 (触发中{stats['firing']} / 已恢复{stats['resolved']})")

    resource_alarms = [event for event in all_events if any(
        kw in (event.get("event_name", "") + " " + event.get("message", ""))
        for kw in ["CPU", "cpu", "Memory", "memory", "内存", "磁盘", "Disk", "OOM", "oom", "Pressure", "pressure"]
    )]
    if resource_alarms:
        lines.append("")
        lines.append(f"资源相关告警 ({len(resource_alarms)} 条):")
        for event in sorted(resource_alarms, key=lambda item: item.get("starts_at") or 0, reverse=True)[:10]:
            ts = datetime.fromtimestamp(event["starts_at"] / 1000, tz=tz8).strftime("%H:%M:%S") if event.get("starts_at") else "?"
            lines.append(f"  [{ts}] {event.get('event_name', '')} {event.get('status', '')}")

    return {
        "success": True,
        "region": region,
        "action": "list_aom_alarms",
        "hours": hours,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "total_count": len(all_events),
        "firing_count": firing_count,
        "resolved_count": resolved_count,
        "active_count": len(active_result.get("events", [])),
        "history_count": len(history_result.get("events", [])),
        "type_stats": type_stats,
        "severity_stats": severity_stats,
        "events": all_events,
        "report": "\n".join(lines),
        "message": f"查询完成: {len(all_events)}条告警(活跃{firing_count}+已恢复{resolved_count}), {len(type_stats)}种类型",
    }


def analyze_aom_alarms(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
    cluster_name: Optional[str] = None,
    hours: int = 1,
    chronic_threshold: int = 5,
    sudden_window_minutes: int = 10,
) -> Dict[str, Any]:
    result = list_aom_alarms(region, ak, sk, project_id, hours, None, cluster_id, cluster_name)
    if not result.get("success"):
        return {"success": False, "error": f"获取告警失败: {result.get('error', '')}", "raw": result}

    all_alarms = result.get("events", [])
    if not all_alarms:
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "total_alarms": 0,
            "sudden_alarms": [],
            "attention_alarms": [],
            "chronic_alarms": [],
            "summary": {"total": 0, "sudden": 0, "attention": 0, "chronic": 0},
            "message": f"近{hours}小时无告警（active + history 均无）",
        }

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    sudden_window_ms = sudden_window_minutes * 60 * 1000
    chronic_patterns = ["NotTriggerScaleUp", "未触发节点扩容", "FailedScheduling", "调度失败", "Unhealthy", "不健康", "NodeNotReady", "节点未就绪"]
    resource_keywords = ["CPU", "cpu", "Memory", "memory", "内存", "磁盘", "Disk", "disk", "OOM", "oom", "Evicted", "evicted", "CrashLoopBackOff", "Pressure", "pressure"]

    groups: Dict[str, Dict[str, Any]] = {}
    for alarm in all_alarms:
        event_name = alarm.get("event_name", "Unknown")
        namespace = alarm.get("namespace", "")
        pod_name = alarm.get("pod_name", "")
        resource_id = alarm.get("resource_id", "")
        if pod_name:
            base_pod = re.sub(r"-[a-z0-9]{5,10}$", "", pod_name)
            resource_key = f"{namespace}/{base_pod}"
        else:
            resource_key = resource_id[:80]
        group_key = f"{event_name}||{resource_key}"
        group = groups.setdefault(group_key, {
            "event_name": event_name,
            "resource_key": resource_key,
            "namespace": namespace,
            "pods": set(),
            "count": 0,
            "first_seen_ms": now_ms,
            "last_seen_ms": 0,
            "severity": alarm.get("event_severity", "Major"),
            "messages": set(),
        })
        group["count"] += 1
        if pod_name:
            group["pods"].add(pod_name)
        starts = alarm.get("starts_at") or 0
        if starts and starts < group["first_seen_ms"]:
            group["first_seen_ms"] = starts
        if starts and starts > group["last_seen_ms"]:
            group["last_seen_ms"] = starts
        if alarm.get("message"):
            group["messages"].add(alarm["message"][:200])

    sudden_alarms: List[Dict[str, Any]] = []
    attention_alarms: List[Dict[str, Any]] = []
    chronic_alarms: List[Dict[str, Any]] = []

    for group in groups.values():
        event_name = group["event_name"]
        count = group["count"]
        is_recent = (now_ms - group["first_seen_ms"]) < sudden_window_ms if group["first_seen_ms"] else False
        is_chronic_pattern = any(pattern in event_name for pattern in chronic_patterns)
        has_resource_keyword = any(kw in event_name or any(kw in msg for msg in group["messages"]) for kw in resource_keywords)

        if is_chronic_pattern and count >= chronic_threshold and not has_resource_keyword:
            priority, label, reason = "chronic", "常态", f"已知常态模式在{hours}h内重复{count}次"
        elif is_recent and count <= 3:
            priority, label, reason = "sudden", "突发", f"近{sudden_window_minutes}分钟内首次出现，当前{count}次"
        elif has_resource_keyword and count <= chronic_threshold:
            priority, label, reason = "sudden", "突发", f"涉及资源指标且出现次数较少({count}次)"
        elif has_resource_keyword:
            priority, label, reason = "attention", "关注", f"涉及资源指标，重复{count}次需关注"
        elif count >= chronic_threshold or is_chronic_pattern:
            priority, label, reason = "chronic", "常态", f"重复{count}次或命中常态模式"
        else:
            priority, label, reason = "attention", "关注", f"出现{count}次，需要关注"

        entry = {
            "priority": priority,
            "priority_label": label,
            "event_name": event_name,
            "namespace": group["namespace"],
            "pods": sorted(group["pods"]),
            "pod_count": len(group["pods"]),
            "alarm_count": count,
            "severity": group["severity"],
            "first_seen": datetime.fromtimestamp(group["first_seen_ms"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if group["first_seen_ms"] else "-",
            "last_seen": datetime.fromtimestamp(group["last_seen_ms"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if group["last_seen_ms"] else "-",
            "sample_message": next(iter(group["messages"]), "-"),
            "reason": reason,
        }
        if priority == "sudden":
            sudden_alarms.append(entry)
        elif priority == "attention":
            attention_alarms.append(entry)
        else:
            chronic_alarms.append(entry)

    sudden_alarms.sort(key=lambda item: item["alarm_count"], reverse=True)
    attention_alarms.sort(key=lambda item: item["alarm_count"], reverse=True)
    chronic_alarms.sort(key=lambda item: item["alarm_count"], reverse=True)
    total = len(all_alarms)
    summary = {
        "total_raw_alarms": total,
        "unique_alarm_groups": len(groups),
        "sudden_count": len(sudden_alarms),
        "attention_count": len(attention_alarms),
        "chronic_count": len(chronic_alarms),
        "noise_reduction_pct": round(sum(item["alarm_count"] for item in chronic_alarms) / total * 100, 1) if total else 0,
    }

    report = "\n".join([
        f"告警过滤分析报告 (近 {hours} 小时, via hcloud)",
        f"原始告警: {total} 条 -> 去重后: {len(groups)} 组",
        f"突发: {len(sudden_alarms)} | 关注: {len(attention_alarms)} | 常态: {len(chronic_alarms)}",
        f"噪音削减: {summary['noise_reduction_pct']}%",
    ])
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "hours": hours,
        "chronic_threshold": chronic_threshold,
        "sudden_window_minutes": sudden_window_minutes,
        "summary": summary,
        "sudden_alarms": sudden_alarms,
        "attention_alarms": attention_alarms,
        "chronic_alarms": chronic_alarms,
        "report": report,
        "message": f"告警过滤完成: {total}条原始告警 -> {summary['sudden_count']}突发 + {summary['attention_count']}关注 + {summary['chronic_count']}常态",
    }
