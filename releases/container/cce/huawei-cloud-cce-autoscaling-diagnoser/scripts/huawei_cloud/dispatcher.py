"""Public read-only actions for CCE autoscaling diagnosis."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from . import autoscaling_diagnosis, common


Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _resolve_region(params: Dict[str, str]) -> Dict[str, str]:
    result = dict(params)
    if not result.get("region") and os.environ.get("HW_REGION_NAME"):
        result["region"] = os.environ["HW_REGION_NAME"]
    return result


def _normalize_cli_credentials(params: Dict[str, str]) -> tuple[Dict[str, str], str | None]:
    result = dict(params)
    for source, target in (("cli_access_key", "ak"), ("cli_secret_key", "sk"), ("cli_security_token", "security_token")):
        value = result.pop(source, None)
        if value:
            if result.get(target) and result[target] != value:
                return params, f"{source} and {target} must not provide different values"
            result[target] = value
    if bool(result.get("ak")) != bool(result.get("sk")):
        return params, "cli_access_key and cli_secret_key must be provided together"
    if result.get("security_token") and not result.get("ak"):
        return params, "cli_security_token requires cli_access_key and cli_secret_key"
    return result, None


def _require(params: Dict[str, str], *required: str) -> str | None:
    missing = [item for item in required if not params.get(item)]
    if missing == ["region"]:
        return "region is required; provide it or set HW_REGION_NAME"
    return None if not missing else f"{', '.join(missing)} are required"


def _integer(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _validate_tuning_parameters(params: Dict[str, str]) -> str | None:
    for name, minimum, maximum in (("hours", 1, 24), ("event_limit", 1, 500)):
        value = params.get(name)
        if value is None:
            continue
        try:
            parsed = int(value)
        except ValueError:
            return f"{name} must be an integer between {minimum} and {maximum}"
        if not minimum <= parsed <= maximum:
            return f"{name} must be between {minimum} and {maximum}"
    for name in ("include_metrics", "include_ca_logs", "include_raw"):
        value = params.get(name)
        if value is not None and value.lower() not in {"true", "false"}:
            return f"{name} must be true or false"
    return None


def _cluster_kwargs(params: Dict[str, str]) -> Dict[str, Any]:
    return {"ak": params.get("ak"), "sk": params.get("sk"), "project_id": params.get("project_id"), "security_token": params.get("security_token")}


def _diagnose_hpa(params: Dict[str, str]) -> Dict[str, Any]:
    return autoscaling_diagnosis.diagnose_cce_autoscaling(
        region=params["region"], cluster_id=params["cluster_id"], namespace=params["namespace"],
        action="huawei_diagnose_cce_hpa_autoscaling", question=params.get("question", ""), target="workload",
        hpa_name=params.get("hpa_name"), workload_name=params.get("workload_name"), workload_type=params.get("workload_type"),
        include_metrics=params.get("include_metrics", "true").lower() == "true", include_ca_logs=False,
        include_raw=params.get("include_raw", "false").lower() == "true", hours=_integer(params.get("hours"), 1),
        event_limit=_integer(params.get("event_limit"), 200),
        output_file=params.get("output_file"), **_cluster_kwargs(params),
    )


def _diagnose_cluster_autoscaler(params: Dict[str, str]) -> Dict[str, Any]:
    return autoscaling_diagnosis.diagnose_cce_autoscaling(
        region=params["region"], cluster_id=params["cluster_id"], namespace=params["namespace"],
        action="huawei_diagnose_cce_cluster_autoscaler", question=params.get("question", ""), target="node",
        scale_direction=params.get("scale_direction"), include_metrics=params.get("include_metrics", "true").lower() == "true",
        include_ca_logs=params.get("include_ca_logs", "true").lower() == "true",
        include_raw=params.get("include_raw", "false").lower() == "true", hours=_integer(params.get("hours"), 1),
        event_limit=_integer(params.get("event_limit"), 200),
        output_file=params.get("output_file"), **_cluster_kwargs(params),
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_diagnose_cce_hpa_autoscaling": (("region", "cluster_id", "namespace"), _diagnose_hpa),
    "huawei_diagnose_cce_cluster_autoscaler": (("region", "cluster_id", "namespace"), _diagnose_cluster_autoscaler),
}


def list_actions() -> Dict[str, tuple[str, ...]]:
    return {action: required for action, (required, _) in sorted(ACTION_SPECS.items())}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    params, error = _normalize_cli_credentials(params)
    if error:
        return {"success": False, "error": error}
    params = _resolve_region(params)
    required, handler = ACTION_SPECS[action]
    if error := _require(params, *required):
        return {"success": False, "error": error}
    if error := _validate_tuning_parameters(params):
        return {"success": False, "error": error}
    source_id = params.get("cluster_id")
    if source_id:
        resolved = common.resolve_cce_cluster_id(params["region"], source_id, **_cluster_kwargs(params))
        if not resolved.get("success"):
            return resolved
        params["cluster_id"] = resolved["id"]
    result = handler(params)
    if source_id and result.get("success") and source_id != params["cluster_id"]:
        result["resolved_resource_ids"] = [{"parameter": "cluster_id", "input": source_id, "resolved_id": params["cluster_id"]}]
    return result
