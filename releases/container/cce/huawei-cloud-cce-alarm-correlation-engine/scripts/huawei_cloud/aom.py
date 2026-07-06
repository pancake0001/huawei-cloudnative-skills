"""AOM alarm actions implemented through hcloud CLI."""

from __future__ import annotations

import json
import re
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import extract_items, get_project_id_for_region, redact_command, run_hcloud, run_hcloud_json_input


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

DEFAULT_EVENT_ALARM_NAMES = {
    "PodOOMKilling",
    "FailedStart",
    "FailedPullImage",
    "BackOffStart",
    "FailedScheduling",
    "BackOffPullImage",
    "FailedCreate",
    "Rebooted",
    "NodeNotSchedulable",
    "NodeNotReady",
    "NodeCreateFailed",
    "FailedToAttachDetach",
    "ScaleUpTimedOut",
    "NotTriggerScaleUp",
    "ScaleDownFailed",
    "FailedToScaleUpGroup",
    "ScaleUpFailed",
    "NodePoolSoldOut",
}


def _reference_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "references"


def _parse_markdown_table(path: Path, expected_columns: int) -> List[List[str]]:
    if not path.exists():
        return []

    rows: List[List[str]] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip().strip("`").replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line.strip("|"))]
        if len(cells) < expected_columns:
            continue
        if cells[0].lower() in {"告警项", "alarm item (cn)", "category", "event description (cn)"}:
            continue
        rows.append(cells)
    return rows


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return slug or fallback


def _display_name(value: str) -> str:
    match = re.search(r"\(([^)]+)\)\s*$", value)
    return match.group(1) if match else value


def _parse_promql_threshold(promql: str) -> tuple[str, str]:
    match = re.search(r"\s(>=|<=|>|<|==)\s*([0-9.]+)\s*$", promql)
    if match:
        return match.group(1), match.group(2)
    return ">", "0"


def _scope_promql_to_cluster(promql: str, cluster_id: str) -> str:
    def add_cluster(match: re.Match[str]) -> str:
        labels = match.group(1).strip()
        if re.search(r'(^|,)\s*cluster\s*=~?\s*"', labels):
            return "{" + labels + "}"
        return "{" + (labels + "," if labels else "") + f'cluster="{cluster_id}"' + "}"

    scoped = re.sub(r"\{([^{}]*)\}", add_cluster, promql)
    if scoped == promql:
        return f"{promql} and on() kube_node_info{{cluster=\"{cluster_id}\"}} >= 0"
    return scoped


def _load_metric_alarm_templates() -> List[Dict[str, Any]]:
    rows = _parse_markdown_table(_reference_dir() / "cce-prometheus-metric-alarms.md", 3)
    templates: List[Dict[str, Any]] = []
    for index, cells in enumerate(rows, start=1):
        name, description, promql = cells[:3]
        operator, threshold = _parse_promql_threshold(promql)
        templates.append({
            "kind": "metric",
            "name": name,
            "description": description,
            "promql": promql,
            "metric_name": f"cce_promql_rule_{index}_{_slug(name, str(index))}",
            "namespace": "CCE.PROMETHEUS",
            "comparison_operator": operator,
            "threshold": threshold,
            "period": 60,
            "evaluation_periods": 3,
            "statistic": "average",
            "alarm_level": 2,
        })
    return templates


def _load_event_alarm_templates() -> List[Dict[str, Any]]:
    rows = _parse_markdown_table(_reference_dir() / "cce-event-list.md", 4)
    templates: List[Dict[str, Any]] = []
    for cells in rows:
        category, description, event_name, event_level = cells[:4]
        if event_name not in DEFAULT_EVENT_ALARM_NAMES:
            continue
        zh_match = re.search(r"\(([^)]+)\)", description)
        cn_description = zh_match.group(1) if zh_match else description
        templates.append({
            "kind": "event",
            "name": event_name,
            "category": category,
            "description": description,
            "event_name": f"{cn_description}##{event_name}",
            "alarm_level": "Major" if event_level.lower() == "important" else "Minor",
        })
    return templates


def _load_aom_rule_body_templates() -> List[Dict[str, Any]]:
    path = _reference_dir() / "cce-aom-alarm-rule-templates.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    templates = data.get("templates") if isinstance(data, dict) else data
    if not isinstance(templates, list):
        return []
    return [{"raw": item} for item in templates if isinstance(item, dict)]


def _cluster_id_in_rule(rule: Dict[str, Any]) -> Optional[str]:
    match = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        json.dumps(rule, ensure_ascii=False),
    )
    return match.group(0) if match else None


def _candidate_from_rule_template(
    template_rule: Dict[str, Any],
    cluster_id: str,
    prefix: str,
    explicit_prefix: bool,
) -> Dict[str, Any]:
    alias = template_rule.get("alias") or template_rule.get("alarm_rule_name") or "CCE alarm rule"
    old_cluster_id = _cluster_id_in_rule(template_rule)
    if explicit_prefix:
        rule_name = f"{prefix}-{_slug(str(alias), str(alias))}"
    else:
        rule_name = _replace_cluster_id(
            template_rule.get("alarm_rule_name") or f"CCE_{alias}_{cluster_id}",
            old_cluster_id,
            cluster_id,
        )
    return {
        "kind": template_rule.get("alarm_rule_type"),
        "name": str(alias),
        "description": template_rule.get("alarm_rule_description") or str(alias),
        "rule_name": rule_name,
        "display_name": str(alias),
        "_template_rule": template_rule,
    }


def _split_csv(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def _matches_any(value: str, candidates: set[str]) -> bool:
    return any(item == value or item in value or value in item for item in candidates)


def _name_key(value: str) -> str:
    value = str(value or "").lower()
    replacements = {
        "百分之八十": "80",
        "百分之十": "10",
        "百分之九十": "90",
        "%": "",
        ">": "",
        "<": "",
        "大于": "",
        "超过": "",
        "不足": "",
        "小于": "",
        " ": "",
        "_": "",
        "-": "",
        "(": "",
        ")": "",
        "（": "",
        "）": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def _promql_metric_names(promql: str) -> set[str]:
    names = set(re.findall(r"\b([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(?:\{|\[)", promql or ""))
    return {name for name in names if not name.endswith("_over_time")}


def _to_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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


def _seconds_to_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _severity_key(alarm_level: Any) -> str:
    mapping = {
        "critical": "1",
        "major": "2",
        "minor": "3",
        "info": "4",
        "warning": "4",
    }
    return mapping.get(str(alarm_level).strip().lower(), str(alarm_level))


def _severity_name(alarm_level: Any) -> str:
    mapping = {
        "1": "Critical",
        "2": "Major",
        "3": "Minor",
        "4": "Info",
        "critical": "Critical",
        "major": "Major",
        "minor": "Minor",
        "info": "Info",
        "warning": "Info",
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


def _rule_matches_scope(rule: Dict[str, Any], cluster_id: Optional[str] = None, cluster_name: Optional[str] = None) -> bool:
    if not cluster_id and not cluster_name:
        return True
    raw_text = json.dumps(rule, ensure_ascii=False)
    if cluster_id and cluster_id in raw_text:
        return True
    if cluster_name and cluster_name in raw_text:
        return True
    return False


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
    if fields.get("promql"):
        level_key = fields.get("severity") or fields.get("alarm_level_name") or _severity_name(fields.get("alarm_level", alarm_level))
        threshold = str(fields.get("threshold_value", 0))
    monitor_type = "promql" if fields.get("promql") else fields.get("monitor_type", "all_metric")
    params: List[tuple[str, Any]] = [
        ("action_id", action_id),
        ("alarm_rule_name", _normalize_alarm_rule_name(rule_name)),
        ("alarm_rule_type", "metric"),
        ("alarm_rule_enable", fields.get("is_turn_on", fields.get("alarm_rule_enable", True))),
        ("alarm_rule_description", fields.get("alarm_rule_description") or fields.get("alarm_description") or "Created by Codex hcloud skill."),
        ("metric_alarm_spec.monitor_type", monitor_type),
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
        params = [
            item for item in params
            if item[0] not in {
                "metric_alarm_spec.trigger_conditions.1.aggregation_window",
                "metric_alarm_spec.trigger_conditions.1.aggregation_type",
            }
        ]
        params.extend([
            ("alias", fields.get("alias") or _normalize_alarm_rule_name(rule_name)),
            ("metric_alarm_spec.alarm_rule_template_bind_enable", False),
            ("metric_alarm_spec.alarm_rule_template_id", fields.get("alarm_rule_template_id", "at0000000000000000cce001")),
            ("metric_alarm_spec.alarm_tags.1.custom_tags.1", "resource_type=node"),
            ("metric_alarm_spec.monitor_objects.1.cluster", fields.get("cluster_id")),
            ("metric_alarm_spec.trigger_conditions.1.metric_query_mode", fields.get("metric_query_mode", "NATIVE_PROM")),
            ("metric_alarm_spec.trigger_conditions.1.trigger_type", fields.get("trigger_type", "FIXED_RATE")),
            ("metric_alarm_spec.trigger_conditions.1.trigger_interval", fields.get("trigger_interval", _period_to_window(period))),
            ("metric_alarm_spec.trigger_conditions.1.promql_for", fields.get("promql_for", _seconds_to_duration(period * evaluation_periods))),
            ("metric_alarm_spec.trigger_conditions.1.metric_labels.1", "cluster"),
            ("metric_alarm_spec.trigger_conditions.1.metric_labels.2", "cluster_name"),
            ("metric_alarm_spec.trigger_conditions.1.metric_labels.3", "namespace"),
            ("metric_alarm_spec.trigger_conditions.1.metric_labels.4", "pod"),
            ("metric_alarm_spec.trigger_conditions.1.metric_labels.5", "node"),
            ("metric_alarm_spec.trigger_conditions.1.promql", fields["promql"]),
            ("metric_alarm_spec.recovery_conditions.recovery_timeframe", fields.get("recovery_timeframe", min(max(evaluation_periods, 1), 3))),
        ])
    if fields.get("bind_notification_rule_id"):
        params.extend([
            ("alarm_notifications.notification_type", "direct"),
            ("alarm_notifications.notification_enable", True),
            ("alarm_notifications.route_group_enable", False),
            ("alarm_notifications.route_group_rule", ""),
            ("alarm_notifications.bind_notification_rule_id", fields["bind_notification_rule_id"]),
            ("alarm_notifications.notify_frequency", 0),
            ("alarm_notifications.notify_resolved", False),
            ("alarm_notifications.notify_triggered", False),
        ])
    elif not fields.get("promql"):
        params.extend([
            ("alarm_notifications.notification_type", "alarm_policy"),
            ("alarm_notifications.notification_enable", False),
            ("alarm_notifications.route_group_enable", False),
            ("alarm_notifications.notify_frequency", -1),
            ("alarm_notifications.notify_resolved", False),
            ("alarm_notifications.notify_triggered", False),
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


def _insert_payload_value(target: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    current: Any = target
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        next_part = parts[index + 1] if not is_last else None
        if isinstance(current, list) and part.isdigit():
            item_index = int(part) - 1
            while len(current) <= item_index:
                current.append({})
            if is_last:
                current[item_index] = value
                return
            current = current[item_index]
            continue

        if is_last:
            current[part] = value
            return

        if next_part and next_part.isdigit() and part != "thresholds":
            current = current.setdefault(part, [])
            continue

        current = current.setdefault(part, {})


def _metric_alarm_payload(params: List[tuple[str, Any]], project_id: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"query": {}, "body": {}}
    if project_id:
        payload["path"] = {"project_id": project_id}
    for key, value in params:
        if key == "action_id":
            payload["query"][key] = value
        elif key == "Enterprise-Project-Id":
            payload.setdefault("header", {})[key] = value
        else:
            _insert_payload_value(payload["body"], key, value)
    return payload


def _replace_cluster_id(value: Any, old_cluster_id: Optional[str], new_cluster_id: str) -> Any:
    if isinstance(value, str):
        return value.replace(old_cluster_id, new_cluster_id) if old_cluster_id else value
    if isinstance(value, list):
        return [_replace_cluster_id(item, old_cluster_id, new_cluster_id) for item in value]
    if isinstance(value, dict):
        return {key: _replace_cluster_id(item, old_cluster_id, new_cluster_id) for key, item in value.items()}
    return value


def _find_template_rule(candidate: Dict[str, Any], template_rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    wanted_kind = candidate.get("kind")
    display_key = _name_key(candidate.get("display_name") or candidate.get("name") or candidate.get("event_name") or "")
    candidate_metric_names = _promql_metric_names(candidate.get("promql", ""))

    for item in template_rules:
        raw = item.get("raw") or {}
        if raw.get("alarm_rule_type") != wanted_kind:
            continue
        alias_key = _name_key(raw.get("alias") or raw.get("alarm_rule_name") or "")

        if wanted_kind == "event":
            raw_event_spec = raw.get("event_alarm_spec") or {}
            raw_conditions = raw_event_spec.get("trigger_conditions") or []
            raw_event_names = {condition.get("event_name") for condition in raw_conditions if isinstance(condition, dict)}
            if candidate.get("event_name") in raw_event_names or display_key and display_key in alias_key:
                return raw
            continue

        raw_metric_spec = raw.get("metric_alarm_spec") or {}
        raw_conditions = raw_metric_spec.get("trigger_conditions") or []
        raw_metric_names = {condition.get("metric_name") for condition in raw_conditions if isinstance(condition, dict)}
        if candidate_metric_names and raw_metric_names and candidate_metric_names & raw_metric_names:
            return raw
        if display_key and (display_key in alias_key or alias_key in display_key):
            return raw
    return None


def _build_rule_from_template(
    template_rule: Dict[str, Any],
    candidate: Dict[str, Any],
    cluster_id: str,
    rule_name: str,
    bind_notification_rule_id: Optional[str],
    prom_instance_id: Optional[str],
    enterprise_project_id: Optional[str],
    project_id: Optional[str],
) -> Dict[str, Any]:
    old_cluster_id = None
    raw_text = json.dumps(template_rule, ensure_ascii=False)
    match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", raw_text)
    if match:
        old_cluster_id = match.group(0)

    body: Dict[str, Any] = copy.deepcopy(template_rule)
    body.pop("alarm_rule_id", None)
    body.pop("id", None)
    body.update({
        "alarm_rule_description": template_rule.get("alarm_rule_description") or candidate.get("description") or "Created by Codex hcloud skill.",
        "alarm_rule_enable": True,
        "alarm_rule_name": _normalize_alarm_rule_name(rule_name),
        "alarm_rule_type": template_rule.get("alarm_rule_type"),
        "prom_instance_id": prom_instance_id or template_rule.get("prom_instance_id"),
        "alias": template_rule.get("alias") or candidate.get("display_name") or _normalize_alarm_rule_name(rule_name),
    })

    if bind_notification_rule_id:
        notifications = body.setdefault("alarm_notifications", {})
        notifications.update({
            "notification_type": "direct",
            "notification_enable": True,
            "route_group_enable": False,
            "bind_notification_rule_id": bind_notification_rule_id,
        })

    body = _replace_cluster_id(body, old_cluster_id, cluster_id)
    header_ep = enterprise_project_id or template_rule.get("enterprise_project_id")
    payload: Dict[str, Any] = {
        "query": {"action_id": "add-alarm-action"},
        "body": body,
    }
    if project_id:
        payload["path"] = {"project_id": project_id}
    if header_ep:
        payload["header"] = {"Enterprise-Project-Id": header_ep}
    return payload


def list_aom_alarm_rules(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    enterprise_project_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
    cluster_name: Optional[str] = None,
) -> Dict[str, Any]:
    filtered = bool(cluster_id or cluster_name)
    page_limit = max(1, min(limit, 200))
    scan_offset = offset
    all_rules: List[Dict[str, Any]] = []
    hcloud_commands = []
    raw_pages = []

    while True:
        params: List[tuple[str, Any]] = [
            ("limit", str(page_limit)),
            ("offset", str(scan_offset)),
            ("Enterprise-Project-Id", enterprise_project_id or "all_granted_eps"),
        ]
        result = run_hcloud("AOM", "ListMetricOrEventAlarmRule", region, params, ak, sk, project_id)
        if not result["success"]:
            return result

        hcloud_commands.append(result["command"])
        raw_pages.append(result.get("data"))
        page_rules = extract_items(result.get("data"), "alarm_rules", "rules")
        all_rules.extend(page_rules)
        if not filtered or len(page_rules) < page_limit:
            break
        scan_offset += page_limit

    total_count = len(all_rules)
    rules = [
        rule for rule in all_rules
        if _rule_matches_scope(rule, cluster_id, cluster_name)
    ] if filtered else all_rules

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
        "filtered": filtered,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "total_count": total_count,
        "count": len(formatted),
        "rules": formatted,
        "raw": raw_pages[-1] if len(raw_pages) == 1 else raw_pages,
        "hcloud_command": hcloud_commands[-1] if len(hcloud_commands) == 1 else hcloud_commands,
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

    if create_fields and create_fields.get("promql"):
        if not create_fields.get("bind_notification_rule_id"):
            return {
                "success": False,
                "action": "create_aom_alarm_rule",
                "executed": False,
                "error": "bind_notification_rule_id is required for confirmed PromQL AOM alarm rule creation. Query existing action rules with huawei_list_aom_action_rules and pass an existing rule ID.",
            }
        resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
        if not resolved_project_id:
            return {"success": False, "error": "Project ID not found for JSON input. Please provide project_id parameter."}
        payload = _metric_alarm_payload(params, resolved_project_id)
        result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
    else:
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
        ("event_alarm_spec.monitor_objects.1.event_name", normalized_event_name),
        ("event_alarm_spec.monitor_objects.1.event_severity", alarm_level),
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
            ("alarm_notifications.route_group_enable", False),
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


def configure_cce_aom_alarm_rules(
    region: str,
    cluster_id: str,
    bind_notification_rule_id: Optional[str] = None,
    rule_name_prefix: Optional[str] = None,
    include_metric_alarms: bool = True,
    include_event_alarms: bool = True,
    alarm_items: Optional[str] = None,
    skip_existing: bool = True,
    prom_instance_id: Optional[str] = None,
    enterprise_project_id: Optional[str] = None,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    explicit_rule_name_prefix = bool(rule_name_prefix)
    prefix = rule_name_prefix or cluster_id
    wanted_items = _split_csv(alarm_items)
    candidates: List[Dict[str, Any]] = []
    embedded_template_rules = _load_aom_rule_body_templates()

    if embedded_template_rules:
        for item in embedded_template_rules:
            template_rule = item.get("raw") or {}
            kind = template_rule.get("alarm_rule_type")
            if kind == "metric" and not include_metric_alarms:
                continue
            if kind == "event" and not include_event_alarms:
                continue
            candidate = _candidate_from_rule_template(template_rule, cluster_id, prefix, explicit_rule_name_prefix)
            if wanted_items and not _matches_any(candidate["name"], wanted_items):
                continue
            candidates.append(candidate)

    if not embedded_template_rules and include_metric_alarms:
        for template in _load_metric_alarm_templates():
            if wanted_items and not (_matches_any(template["name"], wanted_items) or template["metric_name"] in wanted_items):
                continue
            candidates.append({
                **template,
                "rule_name": f"{prefix}-{_slug(template['name'], template['metric_name'])}",
                "display_name": _display_name(template["name"]),
                "promql": _scope_promql_to_cluster(template["promql"], cluster_id),
            })

    if not embedded_template_rules and include_event_alarms:
        for template in _load_event_alarm_templates():
            if wanted_items and not (_matches_any(template["name"], wanted_items) or _matches_any(template["event_name"], wanted_items)):
                continue
            candidates.append({**template, "rule_name": f"{prefix}-{template['name']}"})

    if not candidates:
        return {
            "success": False,
            "action": "configure_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "error": "No alarm templates matched the requested filters.",
        }

    if not confirm:
        preview_commands = []
        for candidate in candidates[:10]:
            if candidate.get("_template_rule"):
                preview_commands.append([
                    "hcloud",
                    "AOM",
                    "AddOrUpdateMetricOrEventAlarmRule",
                    f"--cli-region={region}",
                    "--cli-output=json",
                    "--cli-jsonInput=<generated-cce-aom-template-payload>",
                ])
            elif candidate["kind"] == "metric":
                fields = {
                    "promql": candidate["promql"],
                    "cluster_id": cluster_id,
                    "prom_instance_id": prom_instance_id,
                    "bind_notification_rule_id": bind_notification_rule_id,
                    "alarm_rule_description": candidate["description"],
                    "severity": "Major",
                }
                params = _build_metric_alarm_params(
                    candidate["rule_name"],
                    candidate["metric_name"],
                    candidate["namespace"],
                    candidate["comparison_operator"],
                    candidate["threshold"],
                    candidate["period"],
                    candidate["evaluation_periods"],
                    candidate["statistic"],
                    candidate["alarm_level"],
                    fields,
                )
                preview_commands.append(_preview("AddOrUpdateMetricOrEventAlarmRule", region, params, "R2", "Preview only.")["hcloud_command"])
            else:
                preview_commands.append(
                    create_aom_event_alarm_rule(
                        region=region,
                        cluster_id=cluster_id,
                        rule_name=candidate["rule_name"],
                        event_name=candidate["event_name"],
                        bind_notification_rule_id=bind_notification_rule_id,
                        alarm_level=candidate["alarm_level"],
                        description=candidate["description"],
                        prom_instance_id=prom_instance_id,
                        enterprise_project_id=enterprise_project_id,
                        confirm=False,
                    )["hcloud_command"]
                )
        return {
            "success": True,
            "action": "configure_cce_aom_alarm_rules",
            "region": region,
            "cluster_id": cluster_id,
            "risk": "R2",
            "confirm_required": True,
            "will_execute": False,
            "executed": False,
            "template_count": len(candidates),
            "metric_template_count": sum(1 for item in candidates if item["kind"] == "metric"),
            "event_template_count": sum(1 for item in candidates if item["kind"] == "event"),
            "rules": [{"kind": item["kind"], "rule_name": item["rule_name"], "source_name": item["name"], "display_name": item.get("display_name")} for item in candidates],
            "hcloud_command_samples": preview_commands,
            "notes": [
                "Add confirm=true to create these AOM alarm rules through hcloud.",
                "Notification action rules are not created automatically; pass bind_notification_rule_id to bind an existing notification rule.",
                "skip_existing is evaluated only during confirmed execution.",
            ],
        }

    existing_names: set[str] = set()
    template_rules: List[Dict[str, Any]] = []
    if skip_existing:
        existing = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0, cluster_id=cluster_id)
        if not existing.get("success"):
            return existing
        template_rules = existing.get("rules", [])
        existing_names = {
            _normalize_alarm_rule_name(str(rule.get("rule_name")))
            for rule in existing.get("rules", [])
            if rule.get("rule_name")
        }
    else:
        existing = list_aom_alarm_rules(region, ak, sk, project_id, limit=200, offset=0, cluster_id=cluster_id)
        if existing.get("success"):
            template_rules = existing.get("rules", [])

    created = []
    skipped = []
    failed = []
    for candidate in candidates:
        normalized_name = _normalize_alarm_rule_name(candidate["rule_name"])
        if skip_existing and normalized_name in existing_names:
            skipped.append({"rule_name": candidate["rule_name"], "reason": "already exists"})
            continue

        template_rule = _find_template_rule(candidate, template_rules)
        if template_rule and skip_existing and not explicit_rule_name_prefix:
            skipped.append({
                "rule_name": template_rule.get("alarm_rule_name") or candidate["rule_name"],
                "reason": "matching template rule already exists",
            })
            continue
        if not template_rule and skip_existing and not explicit_rule_name_prefix and template_rules:
            skipped.append({
                "rule_name": candidate["rule_name"],
                "reason": "existing cluster templates present but no matching source template was found",
            })
            continue
        if not template_rule:
            template_rule = candidate.get("_template_rule") or _find_template_rule(candidate, embedded_template_rules)
        if template_rule:
            effective_rule_name = candidate["rule_name"]
            resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
            if not resolved_project_id:
                result = {"success": False, "error": "Project ID not found. Please provide project_id parameter."}
            else:
                payload = _build_rule_from_template(
                    template_rule,
                    candidate,
                    cluster_id,
                    effective_rule_name,
                    bind_notification_rule_id,
                    prom_instance_id,
                    enterprise_project_id,
                    resolved_project_id,
                )
                result = run_hcloud_json_input("AOM", "AddOrUpdateMetricOrEventAlarmRule", region, payload, ak, sk, resolved_project_id)
                result.update({"action": "configure_cce_aom_alarm_rules.template_create", "executed": result["success"]})
        elif candidate["kind"] == "metric":
            fields = {
                "promql": candidate["promql"],
                "cluster_id": cluster_id,
                "prom_instance_id": prom_instance_id,
                "bind_notification_rule_id": bind_notification_rule_id,
                "alarm_rule_description": candidate["description"],
                "severity": "Major",
            }
            result = create_aom_alarm_rule(
                region=region,
                rule_name=candidate["rule_name"],
                metric_name=candidate["metric_name"],
                namespace=candidate["namespace"],
                comparison_operator=candidate["comparison_operator"],
                threshold=candidate["threshold"],
                period=candidate["period"],
                evaluation_periods=candidate["evaluation_periods"],
                statistic=candidate["statistic"],
                alarm_level=candidate["alarm_level"],
                create_fields=fields,
                confirm=True,
                ak=ak,
                sk=sk,
                project_id=project_id,
            )
        else:
            result = create_aom_event_alarm_rule(
                region=region,
                cluster_id=cluster_id,
                rule_name=candidate["rule_name"],
                event_name=candidate["event_name"],
                bind_notification_rule_id=bind_notification_rule_id,
                alarm_level=candidate["alarm_level"],
                description=candidate["description"],
                prom_instance_id=prom_instance_id,
                enterprise_project_id=enterprise_project_id,
                confirm=True,
                ak=ak,
                sk=sk,
                project_id=project_id,
            )

        entry = {
            "kind": candidate["kind"],
            "rule_name": candidate["rule_name"],
            "source_name": candidate["name"],
            "result": result,
        }
        if result.get("success"):
            created.append(entry)
        elif (result.get("data") or {}).get("error_code") == "AOM.02021062":
            skipped.append({"rule_name": candidate["rule_name"], "reason": "already exists"})
        else:
            failed.append(entry)

    return {
        "success": not failed,
        "action": "configure_cce_aom_alarm_rules",
        "region": region,
        "cluster_id": cluster_id,
        "executed": True,
        "template_count": len(candidates),
        "created_count": len(created),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "created": created,
        "skipped": skipped,
        "failed": failed,
    }


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
