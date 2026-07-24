"""Dispatcher for the public CCE Log Analyzer tools."""

from __future__ import annotations

from typing import Any, Callable, Dict

from . import cce, cce_app_logs, lts

Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    return None if not missing else (f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required")


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _pod_logs(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_pod_logs(
        params["region"], params["cluster_id"], params["pod_name"], params.get("ak"), params.get("sk"),
        params.get("project_id"), params.get("namespace", "default"), params.get("container"),
        params.get("previous", "false").lower() == "true", _to_int(params.get("tail_lines"), 100),
    )


def _list_log_groups(params: Dict[str, str]) -> Dict[str, Any]:
    return lts.list_log_groups(
        params["region"],
        _to_int(params.get("limit"), 0),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _list_log_streams(params: Dict[str, str]) -> Dict[str, Any]:
    return lts.list_log_streams(
        params["region"],
        params.get("log_group_id"),
        _to_int(params.get("limit"), 0),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _query_logs(params: Dict[str, str]) -> Dict[str, Any]:
    return lts.query_logs(
        params["region"], params["log_group_id"], params["log_stream_id"], params.get("start_time"), params.get("end_time"),
        params.get("keywords"), _to_int(params.get("limit"), 1000), params.get("scroll_id"),
        params.get("is_desc", "true").lower() == "true", params.get("is_iterative", "false").lower() == "true",
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"),
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_get_pod_logs": (("region", "cluster_id", "pod_name"), _pod_logs),
    "huawei_list_log_groups": (("region",), _list_log_groups),
    "huawei_list_log_streams": (("region",), _list_log_streams),
    "huawei_query_lts_logs": (("region", "log_group_id", "log_stream_id"), _query_logs),
    "huawei_get_cce_logconfigs": (("region", "cluster_id"), cce_app_logs.get_cce_logconfigs_action),
    "huawei_create_cce_logconfig": (("region", "cluster_id", "logconfig_name", "source_type", "log_group_id", "log_stream_id"), cce_app_logs.create_cce_logconfig_action),
    "huawei_delete_cce_logconfig": (("region", "cluster_id", "logconfig_name"), cce_app_logs.delete_cce_logconfig_action),
    "huawei_query_cce_audit_logs": (("region", "cluster_id"), cce_app_logs.query_cce_audit_logs_action),
    "huawei_get_application_logconfigs": (("region", "cluster_id", "app_name"), cce_app_logs.get_application_logconfigs_action),
    "huawei_query_application_logs": (("region", "cluster_id", "app_name"), cce_app_logs.query_application_logs_action),
    "huawei_analyze_application_logs": (("region", "cluster_id", "app_name"), cce_app_logs.analyze_application_logs_action),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    return {"success": False, "error": error} if error else handler(params)
