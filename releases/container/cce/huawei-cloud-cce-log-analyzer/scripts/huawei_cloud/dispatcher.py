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


def _normalize_cli_credentials(params: Dict[str, str]) -> tuple[Dict[str, str], str | None]:
    """Map explicit CLI credentials and prevent fallback to local credential sources."""
    cli_keys = ("cli_access_key", "cli_secret_key", "cli_security_token")
    if not any(params.get(key) for key in cli_keys):
        return params, None
    if not params.get("cli_access_key") or not params.get("cli_secret_key"):
        return params, "cli_access_key and cli_secret_key must be provided together"
    normalized = dict(params)
    normalized.update(
        {
            "ak": params["cli_access_key"],
            "sk": params["cli_secret_key"],
            "security_token": params.get("cli_security_token"),
            "_explicit_cli_credentials": "true",
        }
    )
    if params.get("cli_project_id"):
        normalized["project_id"] = params["cli_project_id"]
    return normalized, None


def _pod_logs(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_pod_logs(
        params["region"], params["cluster_id"], params["pod_name"], params.get("ak"), params.get("sk"),
        params.get("project_id"), params.get("namespace", "default"), params.get("container"),
        params.get("previous", "false").lower() == "true", _to_int(params.get("tail_lines"), 1000),
        params.get("security_token"), params.get("_explicit_cli_credentials") == "true",
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_get_pod_stdout_logs": (("region", "cluster_id", "pod_name"), _pod_logs),
    "huawei_analyze_pod_stdout_realtime_logs": (("region", "cluster_id", "pod_name"), cce_app_logs.analyze_pod_realtime_logs_action),
    "huawei_list_lts_access_configs": (("region",), lambda params: lts.list_access_configs(params["region"], params.get("access_config_name"), params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token"))),
    "huawei_create_lts_access_config": (("region", "access_config_name"), lts.create_access_config_action),
    "huawei_delete_lts_access_config": (("region", "access_config_id"), lts.delete_access_config_action),
    "huawei_get_cce_logconfigs": (("region", "cluster_id"), cce_app_logs.get_cce_logconfigs_action),
    "huawei_create_cce_logconfig": (("region", "cluster_id", "logconfig_name", "source_type"), cce_app_logs.create_cce_logconfig_action),
    "huawei_delete_cce_logconfig": (("region", "cluster_id", "logconfig_name"), cce_app_logs.delete_cce_logconfig_action),
    "huawei_query_cce_audit_logs": (("region", "cluster_id"), cce_app_logs.query_cce_audit_logs_action),
    "huawei_analyze_cce_audit_timeline": (("region", "cluster_id"), cce_app_logs.analyze_cce_audit_timeline_action),
    "huawei_query_kube_apiserver_logs": (("region", "cluster_id"), cce_app_logs.query_kube_apiserver_logs_action),
    "huawei_analyze_kube_apiserver_logs": (("region", "cluster_id"), cce_app_logs.analyze_kube_apiserver_logs_action),
    "huawei_query_kube_scheduler_logs": (("region", "cluster_id"), cce_app_logs.query_kube_scheduler_logs_action),
    "huawei_analyze_kube_scheduler_logs": (("region", "cluster_id"), cce_app_logs.analyze_kube_scheduler_logs_action),
    "huawei_query_application_logs": (("region", "cluster_id"), cce_app_logs.query_application_logs_action),
    "huawei_analyze_application_logs": (("region", "cluster_id"), cce_app_logs.analyze_application_logs_action),
}


def list_actions() -> Dict[str, tuple[str, ...]]:
    """Return public actions with their required parameters."""
    return {action: required for action, (required, _) in sorted(ACTION_SPECS.items())}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    params, credential_error = _normalize_cli_credentials(params)
    if credential_error:
        return {"success": False, "error": credential_error}
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    return {"success": False, "error": error} if error else handler(params)
