"""Application log discovery and query helpers."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from . import cce, common, kubectl_client, lts


DEFAULT_ERROR_PATTERNS = [
    r"\berror\b", r"\bexception\b", r"\btraceback\b", r"\bpanic\b", r"\bfatal\b",
    r"\bfailed?\b", r"\bfailure\b", r"\btimeout\b", r"\btimed out\b",
    r"\bconnection refused\b", r"\bunavailable\b", r"\boom\b", r"out of memory",
    r"segmentation fault", r"stacktrace",
]
DEFAULT_WARNING_PATTERNS = [r"\bwarn(?:ing)?\b", r"\bdeprecated\b", r"\bretry(?:ing)?\b", r"\bslow\b"]
_KUBERNETES_NAMESPACE_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


def _get_policy_name(params: Dict[str, str]) -> Optional[str]:
    return params.get("logconfig_name") or params.get("policy_name")


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "y", "on"}


def _to_int(value: Optional[str], default: int) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_text_list(value: Optional[str], default: List[str]) -> List[str]:
    if not value:
        return default
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return default
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in text.split(",") if item.strip()]


def _parse_logconfig_namespaces(value: Optional[str]) -> List[str]:
    """Parse and validate namespace scope for all-container stdout collection."""
    namespaces = _parse_text_list(value, [])
    invalid = [namespace for namespace in namespaces if not _KUBERNETES_NAMESPACE_RE.fullmatch(namespace)]
    if invalid:
        raise ValueError(
            "namespaces must be a JSON array such as '[\"default\"]' or a comma-separated list such as 'default,kube-system'; "
            f"invalid namespace value(s): {', '.join(invalid)}"
        )
    return namespaces


def _parse_json_value(value: Optional[str], default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


def _format_ts(timestamp_ms: Optional[int]) -> Optional[str]:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def _recent_lts_window(hours: int) -> Tuple[str, str]:
    """Return a UTC time range compatible with the LTS timestamp parser."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    return (
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        end_time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _content_of(log: Dict[str, Any]) -> str:
    content = log.get("content")
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    if content is None:
        return ""
    return str(content)


def _json_content_of(log: Dict[str, Any]) -> Dict[str, Any]:
    content = log.get("content")
    if isinstance(content, dict):
        return content
    if not content:
        return {}
    text = str(content).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for nested_key in ("log", "message", "content"):
                nested = parsed.get(nested_key)
                if isinstance(nested, str) and nested.strip().startswith("{"):
                    try:
                        nested_parsed = json.loads(nested)
                        if isinstance(nested_parsed, dict):
                            merged = dict(parsed)
                            merged.update(nested_parsed)
                            return merged
                    except json.JSONDecodeError:
                        pass
            return parsed
        return {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\})", text)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _deep_get(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _extract_log_time_ms(log: Dict[str, Any]) -> Optional[int]:
    timestamp = log.get("timestamp")
    if timestamp not in (None, ""):
        try:
            value = int(timestamp)
            if value < 10_000_000_000:
                value *= 1000
            return value
        except (TypeError, ValueError):
            pass

    content = _content_of(log)
    nginx_match = re.search(r"\[(\d{1,2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})\]", content)
    if nginx_match:
        try:
            parsed = datetime.strptime(nginx_match.group(1), "%d/%b/%Y:%H:%M:%S %z")
            return int(parsed.timestamp() * 1000)
        except ValueError:
            pass

    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b", content)
    if iso_match:
        try:
            parsed = datetime.strptime(iso_match.group(1).replace("T", " "), "%Y-%m-%d %H:%M:%S")
            return int(parsed.timestamp() * 1000)
        except ValueError:
            pass

    epoch_match = re.search(r"\b(1[6-9]\d{8}(?:\d{3})?)\b", content)
    if epoch_match:
        value = int(epoch_match.group(1))
        if value < 10_000_000_000:
            value *= 1000
        return value
    return None


def _extract_audit_time_ms(log: Dict[str, Any], audit: Dict[str, Any]) -> Optional[int]:
    for path in ("stageTimestamp", "requestReceivedTimestamp", "timestamp", "time"):
        value = _deep_get(audit, path)
        if not value:
            continue
        if isinstance(value, (int, float)):
            numeric = int(value)
            return numeric * 1000 if numeric < 10_000_000_000 else numeric
        text = str(value).replace("T", " ").replace("Z", "").split(".")[0]
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S%z"):
            try:
                return int(datetime.strptime(text, fmt).timestamp() * 1000)
            except ValueError:
                continue
    return _extract_log_time_ms(log)


def _extract_http_status(content: str) -> Optional[int]:
    match = re.search(r'"\S+\s+\S+\s+HTTP/[^"]+"\s+(\d{3})\b', content)
    if not match:
        match = re.search(r"\bstatus(?:=|:|\s)(\d{3})\b", content, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _classify_log(
    content: str,
    error_patterns: List[str],
    warning_patterns: List[str],
    http_error_status_threshold: int,
    include_http_4xx: bool,
) -> Tuple[bool, str, List[str], Optional[int]]:
    reasons = []
    lower_content = content.lower()
    severity = "normal"

    for pattern in error_patterns:
        try:
            if re.search(pattern, content, flags=re.IGNORECASE):
                reasons.append(pattern)
        except re.error:
            if pattern.lower() in lower_content:
                reasons.append(pattern)

    warning_reasons = []
    for pattern in warning_patterns:
        try:
            if re.search(pattern, content, flags=re.IGNORECASE):
                warning_reasons.append(pattern)
        except re.error:
            if pattern.lower() in lower_content:
                warning_reasons.append(pattern)

    status_code = _extract_http_status(content)
    if status_code is not None:
        if status_code >= http_error_status_threshold:
            reasons.append(f"http_{status_code}")
        elif include_http_4xx and status_code >= 400:
            warning_reasons.append(f"http_{status_code}")

    if reasons:
        if re.search(r"\b(fatal|panic|oom|out of memory|segmentation fault|traceback)\b", content, flags=re.IGNORECASE):
            severity = "critical"
        else:
            severity = "error"
        return True, severity, reasons, status_code
    if warning_reasons:
        return True, "warning", warning_reasons, status_code
    return False, severity, [], status_code


def _analysis_options(params: Dict[str, str]) -> Tuple[List[str], List[str], int, bool, int, int]:
    return (
        _parse_text_list(params.get("error_patterns"), DEFAULT_ERROR_PATTERNS),
        _parse_text_list(params.get("warning_patterns"), DEFAULT_WARNING_PATTERNS),
        _to_int(params.get("http_error_status_threshold"), 500),
        _to_bool(params.get("include_http_4xx"), False),
        _to_int(params.get("incident_gap_minutes"), 5),
        _to_int(params.get("sample_limit"), 20),
    )


def _new_log_lines(initial_logs: str, followup_logs: str) -> Tuple[List[str], int]:
    """Return follow-up lines that do not overlap with the initial tail sample."""
    initial_lines = initial_logs.splitlines()
    followup_lines = followup_logs.splitlines()
    for overlap in range(min(len(initial_lines), len(followup_lines)), -1, -1):
        if not overlap or initial_lines[-overlap:] == followup_lines[:overlap]:
            return followup_lines[overlap:], overlap
    return followup_lines, 0


def _build_incident_windows(anomalies: List[Dict[str, Any]], gap_minutes: int) -> List[Dict[str, Any]]:
    if not anomalies:
        return []
    gap_ms = max(gap_minutes, 1) * 60 * 1000
    sorted_items = sorted(anomalies, key=lambda item: (item.get("timestamp_ms") is None, item.get("timestamp_ms") or 0, item["index"]))
    windows = []
    current = None
    for item in sorted_items:
        item_ts = item.get("timestamp_ms")
        if current is None:
            current = {
                "start_time": item.get("time"),
                "end_time": item.get("time"),
                "start_timestamp": item_ts,
                "end_timestamp": item_ts,
                "count": 1,
                "severities": {item["severity"]: 1},
                "reasons": {},
            }
        elif item_ts is not None and current.get("end_timestamp") is not None and item_ts - current["end_timestamp"] <= gap_ms:
            current["end_time"] = item.get("time")
            current["end_timestamp"] = item_ts
            current["count"] += 1
            current["severities"][item["severity"]] = current["severities"].get(item["severity"], 0) + 1
        elif item_ts is None and current.get("end_timestamp") is None:
            current["count"] += 1
            current["severities"][item["severity"]] = current["severities"].get(item["severity"], 0) + 1
        else:
            windows.append(current)
            current = {
                "start_time": item.get("time"),
                "end_time": item.get("time"),
                "start_timestamp": item_ts,
                "end_timestamp": item_ts,
                "count": 1,
                "severities": {item["severity"]: 1},
                "reasons": {},
            }
        for reason in item.get("reasons", []):
            current["reasons"][reason] = current["reasons"].get(reason, 0) + 1
    if current:
        windows.append(current)
    for window in windows:
        if window.get("start_timestamp") is not None and window.get("end_timestamp") is not None:
            window["duration_seconds"] = max(0, int((window["end_timestamp"] - window["start_timestamp"]) / 1000))
        else:
            window["duration_seconds"] = None
        window["top_reasons"] = sorted(window.pop("reasons").items(), key=lambda item: item[1], reverse=True)[:10]
    return windows


LOGCONFIG_API_GROUP = "logging.openvessel.io"
LOGCONFIG_API_VERSION = "v1"
LOGCONFIG_PLURAL = "logconfigs"


def _get_cce_custom_objects_api(params: Dict[str, str]) -> Any:
    return kubectl_client.KubectlCustomObjectsApi(params)


def _query_logs_with_pagination(
    params: Dict[str, str],
    log_group_id: str,
    log_stream_id: str,
    start_time: Optional[str],
    end_time: Optional[str],
    labels: Dict[str, str],
) -> Dict[str, Any]:
    auto_paginate = _to_bool(params.get("auto_paginate"), False)
    page_limit = _to_int(params.get("limit"), 1000)
    max_pages = _to_int(params.get("max_pages"), 10 if auto_paginate else 1)
    max_pages = max(max_pages, 1)
    is_desc = _to_bool(params.get("is_desc"), True)
    is_iterative = _to_bool(params.get("is_iterative"), auto_paginate)

    all_logs = []
    page_results = []
    scroll_id = params.get("scroll_id")
    seen_scroll_ids = set()
    last_result: Dict[str, Any] = {}
    stopped_reason = "completed"

    for page_index in range(max_pages):
        page = lts.query_logs(
            region=params["region"],
            log_group_id=log_group_id,
            log_stream_id=log_stream_id,
            start_time=start_time,
            end_time=end_time,
            keywords=params.get("keywords"),
            limit=page_limit,
            scroll_id=scroll_id,
            is_desc=is_desc,
            is_iterative=is_iterative,
            labels=labels,
            ak=params.get("ak"),
            sk=params.get("sk"),
            project_id=params.get("project_id"),
            security_token=params.get("security_token"),
        )
        if not page.get("success"):
            if not all_logs:
                return page
            page["partial_logs"] = all_logs
            page["partial_total"] = len(all_logs)
            page["pages_fetched"] = len(page_results)
            return page

        page_logs = page.get("logs", [])
        all_logs.extend(page_logs)
        next_scroll_id = page.get("scroll_id")
        page_results.append(
            {
                "page": page_index + 1,
                "count": len(page_logs),
                "scroll_id": next_scroll_id,
            }
        )
        last_result = page

        if not auto_paginate:
            stopped_reason = "auto_paginate_disabled"
            break
        if not next_scroll_id:
            stopped_reason = "no_more_pages"
            break
        if next_scroll_id in seen_scroll_ids:
            stopped_reason = "repeated_scroll_id"
            break

        seen_scroll_ids.add(next_scroll_id)
        scroll_id = next_scroll_id
    else:
        stopped_reason = "max_pages_reached"

    result = dict(last_result)
    result["logs"] = all_logs
    result["total"] = len(all_logs)
    result["auto_paginate"] = auto_paginate
    result["page_limit"] = page_limit
    result["max_pages"] = max_pages
    result["pages_fetched"] = len(page_results)
    result["page_results"] = page_results
    result["stopped_reason"] = stopped_reason
    result["has_more"] = stopped_reason == "max_pages_reached" and bool(result.get("scroll_id"))
    return result


def get_cce_logconfigs_action(params: Dict[str, str]) -> Dict[str, Any]:
    cluster_id = params["cluster_id"]
    namespace = params.get("namespace") or "kube-system"

    try:
        custom_api = _get_cce_custom_objects_api(params)

        api_version = f"{LOGCONFIG_API_GROUP}/{LOGCONFIG_API_VERSION}/{LOGCONFIG_PLURAL}"
        probe_errors = []
        try:
            api_result = custom_api.list_namespaced_custom_object(
                group=LOGCONFIG_API_GROUP,
                version=LOGCONFIG_API_VERSION,
                namespace=namespace,
                plural=LOGCONFIG_PLURAL,
            )
        except Exception as exc:
            probe_errors.append(
                {
                    "api_version": api_version,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                }
            )
            return {
                "success": False,
                "error": f"unable to query CCE LogConfig resources through {api_version}",
                "cluster_id": cluster_id,
                "namespace": namespace,
                "tried_api_combinations": [api_version],
                "probe_errors": probe_errors,
            }

        logconfigs = []
        for item in api_result.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            input_detail = spec.get("inputDetail", {})
            output_detail = spec.get("outputDetail", {})
            logconfigs.append(
                {
                    "name": metadata.get("name"),
                    "logconfig_name": metadata.get("name"),
                    "policy_name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "creation_time": str(metadata.get("creationTimestamp")),
                    "input_type": input_detail.get("type"),
                    "output_type": output_detail.get("type"),
                    "spec": spec,
                    "status": item.get("status", {}),
                    "api_version": f"{LOGCONFIG_API_GROUP}/{LOGCONFIG_API_VERSION}",
                }
            )

        return {
            "success": True,
            "cluster_id": cluster_id,
            "namespace": namespace,
            "count": len(logconfigs),
            "tried_api_combinations": [api_version],
            "probe_errors": probe_errors,
            "logconfigs": logconfigs,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}


def _build_file_spec(params: Dict[str, str]) -> Dict[str, str]:
    log_path = params.get("log_path")
    if not log_path:
        raise ValueError("log_path is required for file LogConfig")
    file_pattern = params.get("file_pattern")
    if not file_pattern:
        is_directory_path = log_path.endswith("/")
        normalized_path = log_path.rstrip("/")
        parent, separator, basename = normalized_path.rpartition("/")
        if not is_directory_path and separator and basename:
            log_path = parent or "/"
            file_pattern = basename
        else:
            file_pattern = "*.log"
    return {"logPath": log_path, "filePattern": file_pattern}


def _build_logconfig_workloads(params: Dict[str, str], source_type: str) -> List[Dict[str, Any]]:
    workloads = _parse_json_value(params.get("workloads"), None)
    if workloads is not None:
        if not isinstance(workloads, list):
            raise ValueError("workloads must be a JSON array")
        return workloads

    workload_namespace = params.get("workload_namespace") or params.get("namespace") or "default"
    workload_name = params.get("workload_name") or params.get("app_name")
    if not workload_name:
        raise ValueError("workload_name or app_name is required when workloads is not provided")
    workload = {
        "namespace": workload_namespace,
        "kind": params.get("workload_kind", "Deployment"),
        "name": workload_name,
    }
    container_name = params.get("container")
    if container_name:
        workload["container"] = container_name

    if source_type == "container_file":
        workload["files"] = _parse_json_value(
            params.get("files"),
            [_build_file_spec(params)],
        )
    return [workload]


def _build_logconfig_body(params: Dict[str, str]) -> Dict[str, Any]:
    name = params.get("logconfig_name") or params.get("name")
    if not name:
        raise ValueError("logconfig_name or name is required")
    source_type = params.get("source_type") or params.get("input_type") or "container_stdout"
    if source_type not in {"container_stdout", "container_file", "host_file"}:
        raise ValueError("source_type must be container_stdout, container_file, or host_file")

    log_group_id = params.get("log_group_id")
    log_stream_id = params.get("log_stream_id")
    if not log_group_id or not log_stream_id:
        raise ValueError("log_group_id and log_stream_id are required")

    all_containers = _to_bool(params.get("all_containers"), source_type == "container_stdout" and not params.get("workload_name") and not params.get("app_name") and not params.get("workloads"))
    input_detail: Dict[str, Any] = {
        "containerFile": {"discoveredForwardSize": params.get("discovered_forward_size", "1MB" if source_type == "container_file" else "")},
        "containerStdout": {},
        "event": {
            "normalEvents": {"enable": False},
            "warningEvents": {"enable": False},
        },
        "hostFile": {"file": {}},
        "processors": _parse_json_value(params.get("processors"), {"fluentBitConfig": {}, "type": params.get("processor_type", "singleline")}),
        "type": source_type,
    }

    if source_type == "container_stdout":
        if all_containers:
            input_detail["containerStdout"] = {"allContainers": True}
            namespaces = _parse_logconfig_namespaces(params.get("namespaces"))
            if namespaces:
                input_detail["containerStdout"]["namespaces"] = namespaces
        else:
            input_detail["containerStdout"] = {"allContainers": False, "workloads": _build_logconfig_workloads(params, source_type)}
    else:
        if source_type == "container_file":
            input_detail["containerFile"]["workloads"] = _build_logconfig_workloads(params, source_type)
        else:
            input_detail["hostFile"] = {"file": _build_file_spec(params)}

    return {
        "apiVersion": f"{params.get('api_group', 'logging.openvessel.io')}/{params.get('api_version', 'v1')}",
        "kind": "LogConfig",
        "metadata": {
            "name": name,
            "namespace": params.get("logconfig_namespace", "kube-system"),
        },
        "spec": {
            "inputDetail": input_detail,
            "logConfigStatus": {
                "LTS": {},
                "conditions": [],
            },
            "outputDetail": {
                "AOM": {},
                "LTS": {
                    "isCustomised": _to_bool(params.get("is_customised"), False),
                    "ltsGroupCreateParam": _parse_json_value(params.get("lts_group_create_param"), {}),
                    "ltsGroupID": log_group_id,
                    "ltsStreamCreateParam": _parse_json_value(params.get("lts_stream_create_param"), {}),
                    "ltsStreamID": log_stream_id,
                },
                "kafka": {},
                "type": "LTS",
            },
        },
    }


def _is_not_found_error(error: Exception) -> bool:
    text = str(error).lower()
    return "notfound" in text or "not found" in text or "(404)" in text


def _logconfig_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    input_detail = spec.get("inputDetail", {})
    lts_detail = (spec.get("outputDetail", {}) or {}).get("LTS", {})
    return {
        "name": metadata.get("name"),
        "namespace": metadata.get("namespace"),
        "creation_time": metadata.get("creationTimestamp"),
        "source_type": input_detail.get("type"),
        "log_group_id": lts_detail.get("ltsGroupID"),
        "log_stream_id": lts_detail.get("ltsStreamID"),
        "spec": spec,
    }


def _logconfig_change_summary(existing: Dict[str, Any], requested: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    old = _logconfig_summary(existing)
    new = _logconfig_summary(requested)
    return {
        key: {"current": old.get(key), "requested": new.get(key)}
        for key in ("source_type", "log_group_id", "log_stream_id", "spec")
        if old.get(key) != new.get(key)
    }


def create_cce_logconfig_action(params: Dict[str, str]) -> Dict[str, Any]:
    destination_check = lts.require_explicit_cluster_log_destination(params)
    if destination_check:
        return destination_check
    try:
        body = _build_logconfig_body(params)
        group = params.get("api_group", "logging.openvessel.io")
        version = params.get("api_version", "v1")
        plural = params.get("plural", "logconfigs")
        namespace = body["metadata"]["namespace"]
        custom_api = _get_cce_custom_objects_api(params)
        existing = None
        try:
            existing = custom_api.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=body["metadata"]["name"],
            )
        except Exception as exc:
            if not _is_not_found_error(exc):
                raise

        if existing:
            changes = _logconfig_change_summary(existing, body)
            if not _to_bool(params.get("update_existing"), False):
                return {
                    "success": False,
                    "error": "CCE LogConfig with the same name already exists; creation will not overwrite it",
                    "requires_update_existing": True,
                    "cluster_id": params["cluster_id"],
                    "logconfig_name": body["metadata"]["name"],
                    "logconfig_namespace": namespace,
                    "existing": _logconfig_summary(existing),
                    "requested_changes": changes,
                    "request_body": body,
                }
            if not _to_bool(params.get("confirm"), False):
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "message": "Updating an existing CCE LogConfig changes log collection. Re-run with update_existing=true and confirm=true after review.",
                    "cluster_id": params["cluster_id"],
                    "logconfig_name": body["metadata"]["name"],
                    "logconfig_namespace": namespace,
                    "existing": _logconfig_summary(existing),
                    "requested_changes": changes,
                    "request_body": body,
                }

        if not _to_bool(params.get("confirm"), False):
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "创建CCE LogConfig会修改集群日志采集配置。如确认创建，请带 confirm=true 重新调用。",
                "cluster_id": params["cluster_id"],
                "logconfig_name": body["metadata"]["name"],
                "logconfig_namespace": namespace,
                "api_version": body["apiVersion"],
                "request_body": body,
            }

        response = custom_api.create_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            body=body,
        )
        metadata = response.get("metadata", {}) if isinstance(response, dict) else {}
        return {
            "success": True,
            "cluster_id": params["cluster_id"],
            "logconfig_name": metadata.get("name", body["metadata"]["name"]),
            "logconfig_namespace": metadata.get("namespace", namespace),
            "api_version": body["apiVersion"],
            "source_type": body["spec"]["inputDetail"]["type"],
            "log_group_id": body["spec"]["outputDetail"]["LTS"]["ltsGroupID"],
            "log_stream_id": body["spec"]["outputDetail"]["LTS"]["ltsStreamID"],
            "updated_existing": bool(existing),
            "response": response,
        }
    except Exception as exc:
        status = getattr(exc, "status", None)
        reason = getattr(exc, "reason", None)
        body_text = getattr(exc, "body", None)
        return {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "status": status,
            "reason": reason,
            "response_body": body_text,
        }


def delete_cce_logconfig_action(params: Dict[str, str]) -> Dict[str, Any]:
    try:
        name = params.get("logconfig_name") or params.get("name")
        if not name:
            raise ValueError("logconfig_name or name is required")
        namespace = params.get("logconfig_namespace") or params.get("namespace") or "kube-system"
        group = params.get("api_group", "logging.openvessel.io")
        version = params.get("api_version", "v1")
        plural = params.get("plural", "logconfigs")

        custom_api = _get_cce_custom_objects_api(params)
        existing = custom_api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )
        metadata = existing.get("metadata", {}) if isinstance(existing, dict) else {}
        spec = existing.get("spec", {}) if isinstance(existing, dict) else {}
        input_detail = spec.get("inputDetail", {})
        output_detail = spec.get("outputDetail", {})

        if not _to_bool(params.get("confirm"), False):
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "删除CCE LogConfig会停止对应日志采集。如确认删除，请带 confirm=true 重新调用。",
                "cluster_id": params["cluster_id"],
                "logconfig_name": metadata.get("name", name),
                "logconfig_namespace": metadata.get("namespace", namespace),
                "api_version": f"{group}/{version}",
                "source_type": input_detail.get("type"),
                "output_type": output_detail.get("type"),
                "target": {
                    "group": group,
                    "version": version,
                    "namespace": namespace,
                    "plural": plural,
                    "name": name,
                },
                "existing": {
                    "name": metadata.get("name", name),
                    "namespace": metadata.get("namespace", namespace),
                    "creation_time": metadata.get("creationTimestamp"),
                    "input_type": input_detail.get("type"),
                    "output_type": output_detail.get("type"),
                    "log_group_id": output_detail.get("LTS", {}).get("ltsGroupID"),
                    "log_stream_id": output_detail.get("LTS", {}).get("ltsStreamID"),
                },
            }

        response = custom_api.delete_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )
        return {
            "success": True,
            "cluster_id": params["cluster_id"],
            "logconfig_name": name,
            "logconfig_namespace": namespace,
            "api_version": f"{group}/{version}",
            "response": response,
        }
    except Exception as exc:
        status = getattr(exc, "status", None)
        reason = getattr(exc, "reason", None)
        body_text = getattr(exc, "body", None)
        return {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "status": status,
            "reason": reason,
            "response_body": body_text,
        }


def _discover_audit_log_stream(params: Dict[str, str]) -> Dict[str, Any]:
    cluster_id = params["cluster_id"]
    config_command = common.hcloud_command(
        "CCE", "ShowClusterConfig", params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
    )
    config_command.append(f"--cluster_id={cluster_id}")
    if params.get("project_id"):
        config_command.append(f"--project_id={params['project_id']}")
    config_result = common.run_hcloud(config_command)
    if not config_result.get("success"):
        return config_result
    audit_config = next(
        (item for item in config_result.get("data", {}).get("log_configs", []) if item.get("name") == "audit"),
        None,
    )
    if not audit_config or not audit_config.get("enable"):
        return {
            "success": False,
            "error": "CCE audit log collection is not enabled",
            "note": "Enable the audit log configuration before querying or analyzing Kubernetes audit logs.",
        }

    if params.get("log_group_id") and params.get("log_stream_id"):
        return {
            "success": True,
            "log_group_id": params["log_group_id"],
            "log_stream_id": params["log_stream_id"],
            "match_type": "explicit_ids",
            "cluster_audit_enabled": True,
        }

    expected_group_name = f"k8s-log-{cluster_id}"
    expected_stream_name = f"audit-{cluster_id}"

    groups_result = lts.list_log_groups(
        params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not groups_result.get("success"):
        return groups_result
    group = next(
        (item for item in groups_result.get("log_groups", []) if item.get("log_group_name") == expected_group_name),
        None,
    )
    if not group:
        return {
            "success": False,
            "error": f"CCE audit log group {expected_group_name} was not found",
            "note": "Audit is enabled, but the expected LTS log group is unavailable or has not been created yet.",
        }
    streams_result = lts.list_log_streams(
        params["region"],
        group["log_group_id"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not streams_result.get("success"):
        return streams_result
    stream = next(
        (item for item in streams_result.get("log_streams", []) if item.get("log_stream_name") == expected_stream_name),
        None,
    )
    if not stream:
        return {
            "success": False,
            "error": f"CCE audit log stream {expected_stream_name} was not found",
            "note": "Audit is enabled, but the expected LTS log stream is unavailable or has not been created yet.",
        }
    return {
        "success": True,
        "log_group_id": group.get("log_group_id"),
        "log_stream_id": stream.get("log_stream_id"),
        "log_group_name": expected_group_name,
        "log_stream_name": expected_stream_name,
        "match_type": "cluster_config_name",
        "cluster_audit_enabled": True,
    }


def _audit_filters(params: Dict[str, str]) -> Dict[str, Any]:
    audit_type = params.get("audit_type") or params.get("scenario")
    resource_name = params.get("resource_name") or params.get("pod_name") or params.get("workload_name") or params.get("app_name")
    content_keywords = _parse_text_list(params.get("content_keywords"), [])
    for keyword in (
        resource_name,
        params.get("namespace"),
        params.get("user"),
        params.get("status_code"),
        params.get("verb"),
        params.get("resource"),
        *(_parse_text_list(params.get("verbs"), [])),
        *(_parse_text_list(params.get("resources"), [])),
    ):
        if keyword and keyword not in content_keywords:
            content_keywords.append(keyword)
    if audit_type == "pod_delete":
        for keyword in ("delete", "pods"):
            if keyword not in content_keywords:
                content_keywords.append(keyword)
    elif audit_type in {"workload_change", "application_change", "app_change"}:
        for keyword in ("create", "update", "patch", "delete"):
            if keyword not in content_keywords:
                content_keywords.append(keyword)
    filters: Dict[str, Any] = {
        "audit_type": audit_type,
        "resource_name": resource_name,
        "content_keywords": content_keywords,
    }
    return filters


def _extract_audit_event(log: Dict[str, Any]) -> Dict[str, Any]:
    content = _content_of(log)
    audit = _json_content_of(log)
    object_ref = audit.get("objectRef", {}) if isinstance(audit.get("objectRef"), dict) else {}
    user_info = audit.get("user", {}) if isinstance(audit.get("user"), dict) else {}
    response_status = audit.get("responseStatus", {}) if isinstance(audit.get("responseStatus"), dict) else {}
    timestamp_ms = _extract_audit_time_ms(log, audit)
    return {
        "timestamp_ms": timestamp_ms,
        "time": _format_ts(timestamp_ms),
        "verb": audit.get("verb"),
        "user": user_info.get("username") or audit.get("username"),
        "resource": object_ref.get("resource"),
        "subresource": object_ref.get("subresource"),
        "namespace": object_ref.get("namespace"),
        "name": object_ref.get("name"),
        "api_group": object_ref.get("apiGroup"),
        "api_version": object_ref.get("apiVersion"),
        "request_uri": audit.get("requestURI"),
        "source_ips": audit.get("sourceIPs"),
        "user_agent": audit.get("userAgent"),
        "stage": audit.get("stage"),
        "status_code": response_status.get("code"),
        "status_reason": response_status.get("reason"),
        "content": content[:1000],
        "raw": audit,
    }


def _audit_event_matches(event: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    content_lower = re.sub(r"</?highlighttag>", "", str(event.get("content") or ""), flags=re.IGNORECASE).lower()
    keywords = [item.lower() for item in filters.get("content_keywords", [])]
    if keywords and not all(keyword in content_lower for keyword in keywords):
        return False
    return True


def query_cce_audit_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    stream_result = _discover_audit_log_stream(params)
    if not stream_result.get("success"):
        return stream_result

    filters = _audit_filters(params)
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "5")
    query_params.setdefault("limit", "500")
    if not query_params.get("keywords") and filters.get("content_keywords"):
        query_params["keywords"] = " ".join(filters["content_keywords"])
    if not query_params.get("start_time") and not query_params.get("end_time"):
        hours = _to_int(query_params.get("hours"), 1)
        query_params["start_time"], query_params["end_time"] = _recent_lts_window(hours)

    labels = _parse_labels(query_params.get("labels")) or {}
    if query_params.get("cluster_id") and _to_bool(query_params.get("add_cluster_label"), False):
        labels.setdefault("clusterId", query_params["cluster_id"])

    query_result = _query_logs_with_pagination(
        params=query_params,
        log_group_id=stream_result["log_group_id"],
        log_stream_id=stream_result["log_stream_id"],
        start_time=query_params.get("start_time"),
        end_time=query_params.get("end_time"),
        labels=labels,
    )
    if not query_result.get("success"):
        return query_result

    events = [_extract_audit_event(log) for log in query_result.get("logs", [])]
    matched_events = [event for event in events if _audit_event_matches(event, filters)]
    sample_limit = _to_int(params.get("sample_limit"), 50)

    def _count_by(key: str) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for event in matched_events:
            value = event.get(key)
            if value is None or value == "":
                value = "unknown"
            value = str(value)
            counts[value] = counts.get(value, 0) + 1
        return [{"value": value, "count": count} for value, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:20]]

    return {
        "success": True,
        "cluster_id": params["cluster_id"],
        "log_group_id": stream_result["log_group_id"],
        "log_stream_id": stream_result["log_stream_id"],
        "log_group_name": stream_result.get("log_group_name"),
        "log_stream_name": stream_result.get("log_stream_name"),
        "stream_match_type": stream_result.get("match_type"),
        "analysis_window": {
            "start_time": query_result.get("start_time"),
            "end_time": query_result.get("end_time"),
        },
        "filters": filters,
        "summary": {
            "queried_logs": len(query_result.get("logs", [])),
            "parsed_audit_events": len(events),
            "matched_events": len(matched_events),
            "matched_ratio": round(len(matched_events) / len(events), 6) if events else 0.0,
        },
        "top_users": _count_by("user"),
        "top_verbs": _count_by("verb"),
        "top_resources": _count_by("resource"),
        "top_namespaces": _count_by("namespace"),
        "top_status_codes": _count_by("status_code"),
        "events": matched_events[:sample_limit],
        "query_summary": {
            "auto_paginate": query_result.get("auto_paginate"),
            "page_limit": query_result.get("page_limit"),
            "max_pages": query_result.get("max_pages"),
            "pages_fetched": query_result.get("pages_fetched"),
            "stopped_reason": query_result.get("stopped_reason"),
            "labels": labels,
            "lts_keywords": query_params.get("keywords"),
        },
        "discovery_candidates": stream_result.get("candidates"),
    }


def _discover_control_plane_log_stream(
    params: Dict[str, str], component: str, config_names: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Verify a control-plane log switch and resolve its standard LTS stream."""
    cluster_id = params["cluster_id"]
    command = common.hcloud_command(
        "CCE", "ShowClusterConfig", params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
    )
    command.append(f"--cluster_id={cluster_id}")
    config_result = common.run_hcloud(command)
    if not config_result.get("success"):
        return config_result
    config = next(
        (item for item in config_result.get("data", {}).get("log_configs", [])
         if item.get("name") in (config_names or {component})),
        None,
    )
    if not config or not config.get("enable"):
        return {
            "success": False,
            "error": f"CCE {component} log collection is not enabled",
            "note": f"Enable {component} control-plane logs in the CCE Log Center before querying or analyzing them.",
            "requires_control_plane_log": component,
        }
    group_name = f"k8s-log-{cluster_id}"
    stream_name = f"{component}-{cluster_id}"
    groups = lts.list_log_groups(params["region"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token"))
    if not groups.get("success"):
        return groups
    group = next((item for item in groups.get("log_groups", []) if item.get("log_group_name") == group_name), None)
    if not group:
        return {"success": False, "error": f"CCE {component} log group {group_name} was not found"}
    streams = lts.list_log_streams(params["region"], group["log_group_id"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token"))
    if not streams.get("success"):
        return streams
    stream = next((item for item in streams.get("log_streams", []) if item.get("log_stream_name") == stream_name), None)
    if not stream:
        return {
            "success": False,
            "error": f"CCE {component} log stream {stream_name} was not found",
            "note": f"{component} logging is enabled, but its expected LTS stream is unavailable or has not been created yet.",
        }
    return {"success": True, "log_group_id": group["log_group_id"], "log_stream_id": stream["log_stream_id"], "log_group_name": group_name, "log_stream_name": stream_name}


def _discover_kube_apiserver_log_stream(params: Dict[str, str]) -> Dict[str, Any]:
    return _discover_control_plane_log_stream(
        params, "kube-apiserver", {"kube-apiserver", "kube_apiserver", "apiserver"},
    )


def _discover_kube_scheduler_log_stream(params: Dict[str, str]) -> Dict[str, Any]:
    return _discover_control_plane_log_stream(
        params, "kube-scheduler", {"kube-scheduler", "kube_scheduler", "scheduler"},
    )


def query_kube_apiserver_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    source = _discover_kube_apiserver_log_stream(params)
    if not source.get("success"):
        return source
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "5")
    query_params.setdefault("limit", "500")
    if not query_params.get("start_time") and not query_params.get("end_time"):
        query_params["start_time"], query_params["end_time"] = _recent_lts_window(_to_int(query_params.get("hours"), 1))
    labels = _parse_labels(query_params.get("labels")) or {}
    result = _query_logs_with_pagination(query_params, source["log_group_id"], source["log_stream_id"], query_params.get("start_time"), query_params.get("end_time"), labels)
    if result.get("success"):
        result.update({"cluster_id": params["cluster_id"], "component": "kube-apiserver", "log_group_name": source["log_group_name"], "log_stream_name": source["log_stream_name"], "labels": labels})
    return result


def query_kube_scheduler_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    source = _discover_kube_scheduler_log_stream(params)
    if not source.get("success"):
        return source
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "5")
    query_params.setdefault("limit", "500")
    if not query_params.get("start_time") and not query_params.get("end_time"):
        query_params["start_time"], query_params["end_time"] = _recent_lts_window(_to_int(query_params.get("hours"), 1))
    labels = _parse_labels(query_params.get("labels")) or {}
    result = _query_logs_with_pagination(query_params, source["log_group_id"], source["log_stream_id"], query_params.get("start_time"), query_params.get("end_time"), labels)
    if result.get("success"):
        result.update({"cluster_id": params["cluster_id"], "component": "kube-scheduler", "log_group_name": source["log_group_name"], "log_stream_name": source["log_stream_name"], "labels": labels})
    return result


def _extract_apiserver_status(content: str) -> Optional[int]:
    match = re.search(r"\b(?:resp|status(?:_code)?)[=:]?(\d{3})\b", content, flags=re.IGNORECASE)
    return int(match.group(1)) if match else _extract_http_status(content)


def _extract_apiserver_latency_ms(content: str) -> Optional[float]:
    match = re.search(r"\b(?:latency|duration|elapsed|took)[=:]?\"?([0-9][0-9A-Za-zµ.]*)", content, flags=re.IGNORECASE)
    if not match:
        return None
    units = re.findall(r"([0-9]+(?:\.[0-9]+)?)(ms|us|µs|h|m|s)", match.group(1).lower())
    if not units:
        return None
    multipliers = {"us": 0.001, "µs": 0.001, "ms": 1, "s": 1000, "m": 60000, "h": 3600000}
    return sum(float(value) * multipliers[unit] for value, unit in units)


def _extract_apiserver_verb(content: str) -> Optional[str]:
    match = re.search(r'\bverb="([^"]+)"', content, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def _latency_statistics(latencies: List[float]) -> Dict[str, Any]:
    if not latencies:
        return {"samples": 0, "avg_ms": None, "p95_ms": None, "max_ms": None}
    values = sorted(latencies)
    return {
        "samples": len(values),
        "avg_ms": round(sum(values) / len(values), 3),
        "p95_ms": values[max(0, int((len(values) - 1) * 0.95))],
        "max_ms": values[-1],
    }


def _without_http_timeout_query_parameter(content: str) -> str:
    """Exclude timeout-duration metadata while preserving actual timeout failures."""
    without_query_parameter = re.sub(
        r"([?&])timeout=[^&\"\s]*", r"\1", content, flags=re.IGNORECASE
    )
    return re.sub(
        r'\btimeout="?[0-9]+(?:\.[0-9]+)?(?:h|m|s|ms|us|µs)+"?',
        "request_deadline_metadata",
        without_query_parameter,
        flags=re.IGNORECASE,
    )


def analyze_kube_apiserver_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    query_params = dict(params)
    query_params.setdefault("hours", "1")
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "1000")
    result = query_kube_apiserver_logs_action(query_params)
    if not result.get("success"):
        return result
    threshold, sample_limit = float(params.get("slow_latency_ms") or 1000), _to_int(params.get("sample_limit"), 20)
    statuses: Dict[str, int] = {}
    latencies: List[float] = []
    watch_latencies: List[float] = []
    non_watch_latencies: List[float] = []
    anomalies = []
    slow_watch_count = 0
    for index, log in enumerate(result.get("logs", [])):
        content = _content_of(log)
        status = _extract_apiserver_status(content)
        latency = _extract_apiserver_latency_ms(content)
        verb = _extract_apiserver_verb(content)
        reasons = []
        if status is not None:
            statuses[str(status)] = statuses.get(str(status), 0) + 1
            if not 200 <= status < 300:
                reasons.append(f"http_{status}")
        if latency is not None:
            latencies.append(latency)
            (watch_latencies if verb == "WATCH" else non_watch_latencies).append(latency)
            if latency >= threshold:
                reasons.append("slow_request")
                if verb == "WATCH":
                    slow_watch_count += 1
        classification_content = _without_http_timeout_query_parameter(content)
        generic, _, generic_reasons, _ = _classify_log(classification_content, *_analysis_options(params)[:4])
        if generic:
            reasons.extend(reason for reason in generic_reasons if reason not in reasons)
        if reasons:
            anomalies.append({"index": index, "time": _format_ts(_extract_log_time_ms(log)), "verb": verb, "status_code": status, "latency_ms": latency, "reasons": reasons, "content": content[:500]})
    all_latency = _latency_statistics(latencies)
    watch_latency = _latency_statistics(watch_latencies)
    non_watch_latency = _latency_statistics(non_watch_latencies)
    non_200 = sum(count for code, count in statuses.items() if code != "200")
    successful_non_200 = sum(count for code, count in statuses.items() if code != "200" and 200 <= int(code) < 300)
    non_success = sum(count for code, count in statuses.items() if not 200 <= int(code) < 300)
    return {
        "success": True, "cluster_id": result["cluster_id"], "component": "kube-apiserver",
        "log_group_name": result["log_group_name"], "log_stream_name": result["log_stream_name"],
        "analysis_window": {"start_time": result.get("start_time"), "end_time": result.get("end_time")},
        "summary": {
            "total_logs": len(result.get("logs", [])),
            "non_200_count": non_200,
            "successful_non_200_count": successful_non_200,
            "non_success_status_count": non_success,
            "slow_request_count": sum("slow_request" in item["reasons"] for item in anomalies),
            "slow_watch_count": slow_watch_count,
            "other_abnormal_count": sum(any(reason != "slow_request" and not reason.startswith("http_") for reason in item["reasons"]) for item in anomalies),
            "slow_latency_ms": threshold,
            "latency_samples": all_latency["samples"],
            "latency_avg_ms": all_latency["avg_ms"],
            "latency_p95_ms": all_latency["p95_ms"],
            "latency_max_ms": all_latency["max_ms"],
            "watch_latency": watch_latency,
            "non_watch_latency": non_watch_latency,
        },
        "status_codes": [{"status_code": code, "count": count} for code, count in sorted(statuses.items(), key=lambda item: item[1], reverse=True)],
        "anomaly_samples": anomalies[:sample_limit], "query_summary": {"pages_fetched": result.get("pages_fetched"), "stopped_reason": result.get("stopped_reason")},
    }


_SCHEDULER_ANOMALY_PATTERNS = {
    "scheduling_failure": r"\bfailed to schedule\b|\bfailedscheduling\b|\b0/\d+ nodes are available\b",
    "binding_failure": r"\bfailed to bind\b|\berror binding\b|\bfailed binding\b",
    "preemption_issue": r"\bpreemption is not helpful\b|\bno preemption victims found\b|\bpreemption.*failed\b",
    "leader_election_issue": r"\bfailed to renew lease\b|\blost lease\b|\bfailed to acquire lease\b|\bleaderelection.*error\b",
}


def analyze_kube_scheduler_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    query_params = dict(params)
    query_params.setdefault("hours", "1")
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "1000")
    result = query_kube_scheduler_logs_action(query_params)
    if not result.get("success"):
        return result

    sample_limit = _to_int(params.get("sample_limit"), 20)
    counts = {name: 0 for name in _SCHEDULER_ANOMALY_PATTERNS}
    successful_assignment_count = 0
    leader_renewal_count = 0
    generic_abnormal_count = 0
    anomalies = []
    for index, log in enumerate(result.get("logs", [])):
        content = _content_of(log)
        reasons = [
            name for name, pattern in _SCHEDULER_ANOMALY_PATTERNS.items()
            if re.search(pattern, content, flags=re.IGNORECASE)
        ]
        for reason in reasons:
            counts[reason] += 1
        if re.search(r"\bsuccessfully assigned\b", content, flags=re.IGNORECASE):
            successful_assignment_count += 1
        if re.search(r"\bsuccessfully renewed lease\b", content, flags=re.IGNORECASE):
            leader_renewal_count += 1
        generic, _, generic_reasons, _ = _classify_log(content, *_analysis_options(params)[:4])
        if generic and not reasons:
            generic_abnormal_count += 1
            reasons.extend(generic_reasons)
        if reasons:
            anomalies.append({
                "index": index,
                "time": _format_ts(_extract_log_time_ms(log)),
                "reasons": reasons,
                "content": content[:500],
            })
    return {
        "success": True,
        "cluster_id": result["cluster_id"],
        "component": "kube-scheduler",
        "log_group_name": result["log_group_name"],
        "log_stream_name": result["log_stream_name"],
        "analysis_window": {"start_time": result.get("start_time"), "end_time": result.get("end_time")},
        "summary": {
            "total_logs": len(result.get("logs", [])),
            "successful_assignment_count": successful_assignment_count,
            "leader_renewal_count": leader_renewal_count,
            **counts,
            "generic_abnormal_count": generic_abnormal_count,
            "abnormal_log_count": len(anomalies),
        },
        "anomaly_samples": anomalies[:sample_limit],
        "query_summary": {"pages_fetched": result.get("pages_fetched"), "stopped_reason": result.get("stopped_reason")},
    }


def _audit_timeline_event_matches(
    event: Dict[str, Any],
    resource_names: List[str],
    namespaces: List[str],
    resources: List[str],
    verbs: List[str],
) -> bool:
    if resource_names and str(event.get("name") or "") not in resource_names:
        return False
    if namespaces and str(event.get("namespace") or "") not in namespaces:
        return False
    if resources and str(event.get("resource") or "").lower() not in {item.lower() for item in resources}:
        return False
    if verbs and str(event.get("verb") or "").lower() not in {item.lower() for item in verbs}:
        return False
    return True


def analyze_cce_audit_timeline_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Group CCE audit events into resource change timelines and lifecycle summaries."""
    resource_names = _parse_text_list(
        params.get("resource_names") or params.get("resource_name") or params.get("pod_name") or params.get("workload_name") or params.get("app_name"),
        [],
    )
    namespaces = _parse_text_list(params.get("namespaces") or params.get("namespace"), [])
    resources = _parse_text_list(params.get("resources") or params.get("resource"), [])
    requested_verbs = _parse_text_list(params.get("verbs") or params.get("verb"), [])
    include_read_events = _to_bool(params.get("include_read_events"), False)
    mutation_verbs = {"create", "update", "patch", "delete", "deletecollection"}
    effective_verbs = requested_verbs or ([] if include_read_events else sorted(mutation_verbs))
    query_params = dict(params)
    # LTS keywords combine terms conjunctively. Apply multi-value resource and verb
    # filters after retrieval so a timeline can include either Pods or Deployments.
    if len(resources) > 1:
        query_params.pop("resources", None)
        query_params.pop("resource", None)
    if len(requested_verbs) > 1:
        query_params.pop("verbs", None)
        query_params.pop("verb", None)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "500")
    query_params.setdefault("sample_limit", str(_to_int(params.get("timeline_limit"), 500)))
    query_results = []
    events = []
    seen_events = set()
    for verb in effective_verbs or [None]:
        verb_query_params = dict(query_params)
        if verb:
            verb_query_params["verb"] = verb
        query_result = query_cce_audit_logs_action(verb_query_params)
        if not query_result.get("success"):
            return query_result
        query_results.append(query_result)
        for event in query_result.get("events", []):
            key = (
                event.get("timestamp_ms"), event.get("verb"), event.get("resource"),
                event.get("namespace"), event.get("name"), event.get("request_uri"),
            )
            if key not in seen_events:
                seen_events.add(key)
                events.append(event)

    source_result = query_results[0]

    filtered_events = [
        event
        for event in events
        if _audit_timeline_event_matches(event, resource_names, namespaces, resources, effective_verbs)
    ]
    filtered_events.sort(key=lambda item: (item.get("timestamp_ms") is None, item.get("timestamp_ms") or 0))

    lifecycles: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for event in filtered_events:
        key = (
            str(event.get("resource") or "unknown"),
            str(event.get("namespace") or ""),
            str(event.get("name") or ""),
            str(event.get("api_group") or ""),
        )
        lifecycle = lifecycles.setdefault(
            key,
            {
                "resource": key[0],
                "namespace": key[1] or None,
                "name": key[2] or None,
                "api_group": key[3] or None,
                "event_count": 0,
                "observed_create_time": None,
                "observed_delete_time": None,
                "last_change_time": None,
                "last_verb": None,
                "actors": {},
                "status_codes": {},
            },
        )
        lifecycle["event_count"] += 1
        verb = str(event.get("verb") or "").lower()
        event_time = event.get("time")
        if verb == "create" and lifecycle["observed_create_time"] is None:
            lifecycle["observed_create_time"] = event_time
        if verb in {"delete", "deletecollection"}:
            lifecycle["observed_delete_time"] = event_time
        lifecycle["last_change_time"] = event_time
        lifecycle["last_verb"] = event.get("verb")
        actor = str(event.get("user") or "unknown")
        lifecycle["actors"][actor] = lifecycle["actors"].get(actor, 0) + 1
        status_code = str(event.get("status_code") or "unknown")
        lifecycle["status_codes"][status_code] = lifecycle["status_codes"].get(status_code, 0) + 1

    lifecycle_items = []
    for lifecycle in lifecycles.values():
        lifecycle["actors"] = [
            {"user": user, "count": count}
            for user, count in sorted(lifecycle["actors"].items(), key=lambda item: item[1], reverse=True)
        ]
        lifecycle["status_codes"] = [
            {"status_code": code, "count": count}
            for code, count in sorted(lifecycle["status_codes"].items(), key=lambda item: item[1], reverse=True)
        ]
        lifecycle_items.append(lifecycle)
    lifecycle_items.sort(key=lambda item: (item.get("last_change_time") is None, item.get("last_change_time") or ""))

    timeline = [
        {
            "time": event.get("time"),
            "verb": event.get("verb"),
            "resource": event.get("resource"),
            "namespace": event.get("namespace"),
            "name": event.get("name"),
            "user": event.get("user"),
            "status_code": event.get("status_code"),
            "status_reason": event.get("status_reason"),
            "request_uri": event.get("request_uri"),
        }
        for event in filtered_events
    ]
    return {
        "success": True,
        "action": "analyze_cce_audit_timeline",
        "cluster_id": params["cluster_id"],
        "analysis_window": source_result.get("analysis_window"),
        "audit_source": {
            "log_group_id": source_result.get("log_group_id"),
            "log_stream_id": source_result.get("log_stream_id"),
            "log_group_name": source_result.get("log_group_name"),
            "log_stream_name": source_result.get("log_stream_name"),
        },
        "filters": {
            "resource_names": resource_names,
            "namespaces": namespaces,
            "resources": resources,
            "verbs": effective_verbs,
            "include_read_events": include_read_events,
        },
        "summary": {
            "queried_audit_events": sum(result.get("summary", {}).get("matched_events", 0) for result in query_results),
            "timeline_events": len(timeline),
            "resources_observed": len(lifecycle_items),
        },
        "resource_lifecycles": lifecycle_items,
        "timeline": timeline,
        "note": "Creation and deletion times are inferred only from retained audit records; they do not establish the resource's current existence.",
        "query_summary": {
            "query_count": len(query_results),
            "per_verb": [
                {"verb": verb, "matched_events": result.get("summary", {}).get("matched_events", 0)}
                for verb, result in zip(effective_verbs or [None], query_results)
            ],
        },
    }


def _extract_logconfig_lts_destination(logconfig: Dict[str, Any]) -> Dict[str, Optional[str]]:
    lts_config = logconfig.get("spec", {}).get("outputDetail", {}).get("LTS", {})
    log_stream_id = lts_config.get("ltsStreamID", lts_config.get("streamID"))
    if not log_stream_id:
        log_stream_id = logconfig.get("spec", {}).get("logConfigStatus", {}).get("LTS", {}).get("streamID")
    return {"log_group_id": lts_config.get("ltsGroupID"), "log_stream_id": log_stream_id}


def _resolve_application_log_source(params: Dict[str, str]) -> Dict[str, Any]:
    """Resolve one user-selected collection rule to its LTS destination."""
    logconfig_name = _get_policy_name(params)
    access_config_name = params.get("access_config_name")
    access_config_id = params.get("access_config_id")
    selected = [value for value in (logconfig_name, access_config_name, access_config_id) if value]
    if len(selected) != 1:
        return {
            "success": False,
            "error": "exactly one collection rule is required: logconfig_name, access_config_name, or access_config_id",
            "note": "First list CCE LogConfigs and LTS Access Configs for the target cluster, then provide the rule selected by the user. The tool never selects a rule automatically.",
        }

    if logconfig_name:
        lookup_params = dict(params)
        if params.get("logconfig_namespace"):
            lookup_params["namespace"] = params["logconfig_namespace"]
        else:
            lookup_params.pop("namespace", None)
        result = get_cce_logconfigs_action(lookup_params)
        if not result.get("success"):
            return result
        matches = [
            item for item in result.get("logconfigs", [])
            if item.get("name") == logconfig_name
            and (not params.get("logconfig_namespace") or item.get("namespace") == params["logconfig_namespace"])
        ]
        if not matches:
            return {
                "success": False,
                "error": f"CCE LogConfig {logconfig_name} was not found in cluster {params['cluster_id']}",
            }
        if len(matches) > 1:
            return {
                "success": False,
                "error": f"multiple CCE LogConfigs named {logconfig_name} were found; logconfig_namespace is required",
            }
        logconfig = matches[0]
        destination = _extract_logconfig_lts_destination(logconfig)
        if logconfig.get("spec", {}).get("outputDetail", {}).get("type") != "LTS" or not all(destination.values()):
            return {
                "success": False,
                "error": f"CCE LogConfig {logconfig_name} does not have a usable LTS log group and stream destination",
            }
        return {
            "success": True,
            "collection_rule": {
                "collection_mode": "cce_logconfig",
                "rule_name": logconfig.get("name"),
                "rule_namespace": logconfig.get("namespace"),
                "rule_id": None,
                "source_type": logconfig.get("spec", {}).get("inputDetail", {}).get("type"),
            },
            **destination,
        }

    result = lts.list_access_configs(
        params["region"],
        access_config_name=access_config_name,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not result.get("success"):
        return result
    matches = [
        item for item in result.get("access_configs", [])
        if item.get("cluster_id") == params["cluster_id"]
        and (not access_config_name or item.get("access_config_name") == access_config_name)
        and (not access_config_id or item.get("access_config_id") == access_config_id)
    ]
    if not matches:
        selector = access_config_id or access_config_name
        return {
            "success": False,
            "error": f"LTS Access Config {selector} was not found for cluster {params['cluster_id']}",
        }
    if len(matches) > 1:
        return {
            "success": False,
            "error": "multiple LTS Access Config rules matched; provide access_config_id",
        }
    access_config = matches[0]
    if not access_config.get("log_group_id") or not access_config.get("log_stream_id"):
        return {
            "success": False,
            "error": f"LTS Access Config {access_config.get('access_config_name')} does not have a usable LTS log group and stream destination",
        }
    return {
        "success": True,
        "collection_rule": {
            "collection_mode": "lts_access_config",
            "rule_name": access_config.get("access_config_name"),
            "rule_namespace": None,
            "rule_id": access_config.get("access_config_id"),
            "source_type": str(access_config.get("path_type") or "").lower(),
        },
        "log_group_id": access_config["log_group_id"],
        "log_stream_id": access_config["log_stream_id"],
    }


def query_application_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    source_result = _resolve_application_log_source(params)
    if not source_result.get("success"):
        return source_result

    app_name = params.get("app_name")
    policy_name = _get_policy_name(params)
    namespace = params.get("namespace")
    custom_labels = _parse_labels(params.get("labels"))
    auto_label_candidates = {"clusterId": params["cluster_id"]}
    if app_name:
        auto_label_candidates["appName"] = app_name
    if namespace:
        auto_label_candidates["nameSpace"] = namespace
    if policy_name:
        auto_label_candidates["logconfig"] = policy_name

    index_result = lts.list_log_stream_index(
        params["region"],
        source_result["log_group_id"],
        source_result["log_stream_id"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    indexed_fields = index_result.get("indexed_fields", set()) if index_result.get("success") else set()
    auto_label_filter = {
        key: value for key, value in auto_label_candidates.items()
        if key in indexed_fields
    }
    # Explicit labels remain caller-controlled. Automatic filters are used only
    # when the stream index confirms they can be queried safely.
    final_labels = dict(auto_label_filter)
    if custom_labels:
        final_labels.update(custom_labels)

    start_time = params.get("start_time")
    end_time = params.get("end_time")
    hours = None
    if not start_time and not end_time:
        hours = _to_int(params.get("hours"), 1)
        start_time, end_time = _recent_lts_window(hours)

    result = _query_logs_with_pagination(
        params=params,
        log_group_id=source_result["log_group_id"],
        log_stream_id=source_result["log_stream_id"],
        start_time=start_time,
        end_time=end_time,
        labels=final_labels,
    )
    if hours is not None:
        result["hours"] = hours
    result.update(
        {
            "cluster_id": params["cluster_id"],
            "namespace": namespace,
            "app_name": app_name,
            "log_group_id": source_result["log_group_id"],
            "log_stream_id": source_result["log_stream_id"],
            "collection_rule": source_result["collection_rule"],
            "policy_name": policy_name,
            "auto_label_filter": auto_label_filter,
            "log_stream_index_available": index_result.get("success", False),
            "log_stream_index_error": None if index_result.get("success") else index_result.get("error"),
            "custom_labels": custom_labels,
            "final_labels": final_labels,
        }
    )
    return result


def analyze_application_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    query_params = dict(params)
    query_params.setdefault("auto_paginate", "true")
    query_params.setdefault("max_pages", "10")
    query_params.setdefault("limit", "1000")
    query_params.setdefault("is_desc", "false")

    query_params.setdefault("hours", "1")
    query_result = query_application_logs_action(query_params)
    if not query_result.get("success"):
        return query_result

    (
        error_patterns,
        warning_patterns,
        http_error_status_threshold,
        include_http_4xx,
        incident_gap_minutes,
        sample_limit,
    ) = _analysis_options(params)

    logs = query_result.get("logs", [])
    analyzed_logs = []
    anomalies = []
    status_code_counts: Dict[str, int] = {}
    reason_counts: Dict[str, int] = {}
    severity_counts = {"critical": 0, "error": 0, "warning": 0, "normal": 0}
    timestamped_logs = []

    for index, log in enumerate(logs):
        content = _content_of(log)
        timestamp_ms = _extract_log_time_ms(log)
        is_abnormal, severity, reasons, status_code = _classify_log(
            content,
            error_patterns,
            warning_patterns,
            http_error_status_threshold,
            include_http_4xx,
        )
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if status_code is not None:
            key = str(status_code)
            status_code_counts[key] = status_code_counts.get(key, 0) + 1
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        analyzed = {
            "index": index,
            "timestamp_ms": timestamp_ms,
            "time": _format_ts(timestamp_ms),
            "is_abnormal": is_abnormal,
            "severity": severity,
            "reasons": reasons,
            "status_code": status_code,
        }
        analyzed_logs.append(analyzed)
        if timestamp_ms is not None:
            timestamped_logs.append(analyzed)
        if is_abnormal:
            sample = dict(analyzed)
            sample["content"] = content[:500]
            anomalies.append(sample)

    total_logs = len(logs)
    abnormal_logs = len(anomalies)
    abnormal_ratio = round(abnormal_logs / total_logs, 6) if total_logs else 0.0
    timestamped_sorted = sorted(timestamped_logs, key=lambda item: item["timestamp_ms"])
    anomalies_sorted = sorted(anomalies, key=lambda item: (item.get("timestamp_ms") is None, item.get("timestamp_ms") or 0, item["index"]))
    first_abnormal = anomalies_sorted[0] if anomalies_sorted else None
    last_abnormal = anomalies_sorted[-1] if anomalies_sorted else None
    recovery = None
    if last_abnormal and last_abnormal.get("timestamp_ms") is not None:
        for item in timestamped_sorted:
            if item["timestamp_ms"] > last_abnormal["timestamp_ms"] and not item["is_abnormal"]:
                recovery = item
                break

    http_4xx_count = sum(count for code, count in status_code_counts.items() if 400 <= int(code) < 500)
    http_5xx_count = sum(count for code, count in status_code_counts.items() if int(code) >= 500)
    top_status_codes = sorted(status_code_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    top_patterns = sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)[:20]
    window_start = query_result.get("start_time")
    window_end = query_result.get("end_time")
    window_duration_minutes = None
    if isinstance(window_start, int) and isinstance(window_end, int) and window_end > window_start:
        window_duration_minutes = round((window_end - window_start) / 60000, 4)
    logs_per_minute = round(total_logs / window_duration_minutes, 6) if window_duration_minutes else None
    abnormal_logs_per_minute = round(abnormal_logs / window_duration_minutes, 6) if window_duration_minutes else None

    return {
        "success": True,
        "cluster_id": query_result.get("cluster_id"),
        "namespace": query_result.get("namespace"),
        "app_name": query_result.get("app_name"),
        "logconfig_name": query_result.get("collection_rule", {}).get("rule_name")
        if query_result.get("collection_rule", {}).get("collection_mode") == "cce_logconfig" else None,
        "policy_name": query_result.get("policy_name"),
        "source_type": query_result.get("collection_rule", {}).get("source_type"),
        "collection_rule": query_result.get("collection_rule"),
        "log_group_id": query_result.get("log_group_id"),
        "log_stream_id": query_result.get("log_stream_id"),
        "analysis_window": {
            "start_time": _format_ts(window_start) if isinstance(window_start, int) else window_start,
            "end_time": _format_ts(window_end) if isinstance(window_end, int) else window_end,
            "start_timestamp": window_start,
            "end_timestamp": window_end,
            "duration_minutes": window_duration_minutes,
        },
        "summary": {
            "total_logs": total_logs,
            "timestamped_logs": len(timestamped_logs),
            "abnormal_logs": abnormal_logs,
            "normal_logs": total_logs - abnormal_logs,
            "abnormal_ratio": abnormal_ratio,
            "abnormal_percent": round(abnormal_ratio * 100, 4),
            "critical_logs": severity_counts.get("critical", 0),
            "error_logs": severity_counts.get("error", 0),
            "warning_logs": severity_counts.get("warning", 0),
            "http_4xx_count": http_4xx_count,
            "http_5xx_count": http_5xx_count,
            "logs_per_minute": logs_per_minute,
            "abnormal_logs_per_minute": abnormal_logs_per_minute,
            "is_recovered": bool(recovery) if abnormal_logs else True,
        },
        "timeline": {
            "first_abnormal_time": first_abnormal.get("time") if first_abnormal else None,
            "first_abnormal_timestamp": first_abnormal.get("timestamp_ms") if first_abnormal else None,
            "last_abnormal_time": last_abnormal.get("time") if last_abnormal else None,
            "last_abnormal_timestamp": last_abnormal.get("timestamp_ms") if last_abnormal else None,
            "recovery_time": recovery.get("time") if recovery else None,
            "recovery_timestamp": recovery.get("timestamp_ms") if recovery else None,
            "recovery_observed": bool(recovery) if abnormal_logs else True,
        },
        "incident_windows": _build_incident_windows(anomalies, incident_gap_minutes),
        "top_patterns": [{"pattern": pattern, "count": count} for pattern, count in top_patterns],
        "top_status_codes": [{"status_code": code, "count": count} for code, count in top_status_codes],
        "abnormal_samples": anomalies_sorted[:sample_limit],
        "query_summary": {
            "auto_paginate": query_result.get("auto_paginate"),
            "page_limit": query_result.get("page_limit"),
            "max_pages": query_result.get("max_pages"),
            "pages_fetched": query_result.get("pages_fetched"),
            "stopped_reason": query_result.get("stopped_reason"),
            "final_labels": query_result.get("final_labels"),
            "keywords": params.get("keywords"),
            "keywords_scope_note": "When keywords is set, ratios are calculated only over logs matched by that keyword filter." if params.get("keywords") else None,
        },
    }


def analyze_pod_realtime_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Sample a running Pod twice and analyze only the newly observed log lines."""
    if _to_bool(params.get("previous"), False):
        return {"success": False, "error": "previous=true is not supported for realtime Pod log analysis"}

    wait_seconds = _to_int(params.get("wait_seconds"), 30)
    if not 1 <= wait_seconds <= 300:
        return {"success": False, "error": "wait_seconds must be between 1 and 300"}
    tail_lines = max(1, _to_int(params.get("tail_lines"), 100))
    namespace = params.get("namespace", "default")
    pod_name = params["pod_name"]
    container = params.get("container")
    pod_args = {
        "region": params["region"],
        "cluster_id": params["cluster_id"],
        "pod_name": pod_name,
        "namespace": namespace,
        "container": container,
        "tail_lines": tail_lines,
        "ak": params.get("ak"),
        "sk": params.get("sk"),
        "project_id": params.get("project_id"),
        "security_token": params.get("security_token"),
        "explicit_cli_credentials": params.get("_explicit_cli_credentials") == "true",
    }

    initial = cce.get_pod_logs(**pod_args)
    if not initial.get("success"):
        return initial
    time.sleep(wait_seconds)
    followup = cce.get_pod_logs(**pod_args)
    if not followup.get("success"):
        return followup

    new_lines, overlap_lines = _new_log_lines(initial.get("logs", ""), followup.get("logs", ""))
    (
        error_patterns,
        warning_patterns,
        http_error_status_threshold,
        include_http_4xx,
        incident_gap_minutes,
        sample_limit,
    ) = _analysis_options(params)
    anomalies = []
    severity_counts = {"critical": 0, "error": 0, "warning": 0, "normal": 0}
    reason_counts: Dict[str, int] = {}
    status_code_counts: Dict[str, int] = {}

    for index, content in enumerate(new_lines):
        timestamp_ms = _extract_log_time_ms({"content": content})
        is_abnormal, severity, reasons, status_code = _classify_log(
            content, error_patterns, warning_patterns, http_error_status_threshold, include_http_4xx
        )
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if status_code is not None:
            code = str(status_code)
            status_code_counts[code] = status_code_counts.get(code, 0) + 1
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if is_abnormal:
            anomalies.append(
                {
                    "index": index,
                    "timestamp_ms": timestamp_ms,
                    "time": _format_ts(timestamp_ms),
                    "severity": severity,
                    "reasons": reasons,
                    "status_code": status_code,
                    "content": content[:500],
                }
            )

    total_lines = len(new_lines)
    abnormal_lines = len(anomalies)
    abnormal_ratio = round(abnormal_lines / total_lines, 6) if total_lines else 0.0
    return {
        "success": True,
        "action": "analyze_pod_realtime_logs",
        "region": params["region"],
        "cluster_id": params["cluster_id"],
        "namespace": namespace,
        "pod_name": pod_name,
        "container": container,
        "access_method": followup.get("access_method"),
        "sampling": {
            "tail_lines": tail_lines,
            "wait_seconds": wait_seconds,
            "initial_line_count": len(initial.get("logs", "").splitlines()),
            "followup_line_count": len(followup.get("logs", "").splitlines()),
            "overlap_lines": overlap_lines,
            "new_line_count": total_lines,
        },
        "summary": {
            "abnormal_lines": abnormal_lines,
            "normal_lines": total_lines - abnormal_lines,
            "abnormal_ratio": abnormal_ratio,
            "abnormal_percent": round(abnormal_ratio * 100, 4),
            "critical_lines": severity_counts["critical"],
            "error_lines": severity_counts["error"],
            "warning_lines": severity_counts["warning"],
            "http_4xx_count": sum(count for code, count in status_code_counts.items() if 400 <= int(code) < 500),
            "http_5xx_count": sum(count for code, count in status_code_counts.items() if int(code) >= 500),
        },
        "incident_windows": _build_incident_windows(anomalies, incident_gap_minutes),
        "top_patterns": [
            {"pattern": pattern, "count": count}
            for pattern, count in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "top_status_codes": [
            {"status_code": code, "count": count}
            for code, count in sorted(status_code_counts.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
        "abnormal_samples": anomalies[:sample_limit],
    }


def _parse_labels(labels: Optional[str]) -> Optional[Dict[str, str]]:
    if not labels:
        return None
    if isinstance(labels, dict):
        return labels
    return json.loads(labels)
