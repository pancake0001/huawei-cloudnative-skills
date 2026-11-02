"""Public action dispatcher for CCE node configuration diagnosis."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from .node_configuration import diagnose_node_configuration


Handler = Callable[[Dict[str, str]], Dict[str, Any]]

_ACTION = "huawei_diagnose_cce_node_configuration"
_CR_LIFECYCLE = "CCE-managed; the controller may delete this CR after collection completes"


def _resolve_region(params: Dict[str, str]) -> Dict[str, str]:
    result = dict(params)
    if not result.get("region") and os.environ.get("HW_REGION_NAME"):
        result["region"] = os.environ["HW_REGION_NAME"]
    return result


def _normalize_credentials(params: Dict[str, str]) -> tuple[Dict[str, str], str | None]:
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


def _integer(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _boolean(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _validate(params: Dict[str, str]) -> str | None:
    missing = [name for name in ("region", "cluster_id", "node_name") if not params.get(name)]
    if missing:
        if missing == ["region"]:
            return "region is required; provide it or set HW_REGION_NAME"
        return f"{', '.join(missing)} are required"
    for name, minimum, maximum in (("poll_timeout_seconds", 30, 300), ("warning_threshold", 1, 99), ("critical_threshold", 1, 100)):
        if params.get(name) is None:
            continue
        try:
            value = int(params[name])
        except ValueError:
            return f"{name} must be an integer between {minimum} and {maximum}"
        if not minimum <= value <= maximum:
            return f"{name} must be between {minimum} and {maximum}"
    warning = _integer(params.get("warning_threshold"), 80)
    critical = _integer(params.get("critical_threshold"), 90)
    if warning >= critical:
        return "warning_threshold must be lower than critical_threshold"
    return None


def _diagnose(params: Dict[str, str]) -> Dict[str, Any]:
    if not _boolean(params.get("confirm")):
        return {
            "success": False,
            "requires_confirmation": True,
            "risk_level": "R2",
            "error": "confirm=true is required before creating a NodeConfigurationCollection diagnostic CR",
            "preview": {
                "region": params["region"],
                "cluster_id": params["cluster_id"],
                "node_name": params["node_name"],
                "operation": "Create a uniquely named NodeConfigurationCollection, wait for CCE collection, and analyze its result.",
            },
        }
    return diagnose_node_configuration(
        region=params["region"],
        cluster_id=params["cluster_id"],
        node_name=params["node_name"],
        project_id=params.get("project_id"),
        ak=params.get("ak"),
        sk=params.get("sk"),
        security_token=params.get("security_token"),
        poll_timeout_seconds=_integer(params.get("poll_timeout_seconds"), 120),
        warning_threshold=_integer(params.get("warning_threshold"), 80),
        critical_threshold=_integer(params.get("critical_threshold"), 90),
        debug=_boolean(params.get("debug")),
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    _ACTION: (("region", "cluster_id", "node_name"), _diagnose),
}


def list_actions() -> Dict[str, tuple[str, ...]]:
    return {action: required for action, (required, _) in ACTION_SPECS.items()}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def _standardize(params: Dict[str, str], result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the public, stable response envelope for every diagnostic run."""
    preview = result.get("preview") if isinstance(result.get("preview"), dict) else None
    diagnostic_cr = result.get("diagnostic_cr") if isinstance(result.get("diagnostic_cr"), dict) else {}
    target = result.get("target") if isinstance(result.get("target"), dict) else {}
    diagnosis = result.get("diagnosis") if isinstance(result.get("diagnosis"), dict) else {}
    message = result.get("error")
    success = bool(result.get("success"))
    phase = (diagnostic_cr.get("status") or {}).get("phase") if isinstance(diagnostic_cr.get("status"), dict) else None
    if preview:
        status, error_code = "preview", "CONFIRMATION_REQUIRED"
    elif success:
        status, error_code = "succeeded", None
    elif phase in {"Failed", "Error"}:
        status, error_code = "collection_failed", "COLLECTION_FAILED"
    elif message and "timed out" in str(message).lower():
        status, error_code = "timeout", "COLLECTION_TIMEOUT"
    else:
        status, error_code = "failed", "EXECUTION_FAILED"

    return {
        "schema_version": "1.0",
        "success": success,
        "action": _ACTION,
        "risk_level": "R2",
        "status": status,
        "error": {"code": error_code, "message": str(message) if message else None},
        "execution": {
            "requires_confirmation": bool(result.get("requires_confirmation")),
            "preview": preview,
        },
        "target": {
            "region": target.get("region", params.get("region")),
            "project_id": target.get("project_id", params.get("project_id")),
            "cluster_id": target.get("cluster_id", params.get("cluster_id")),
            "cluster_name": target.get("cluster_name"),
            "node_name": target.get("node_name", params.get("node_name")),
            "node_provider_id": target.get("node_provider_id"),
        },
        "diagnostic_cr": {
            "name": diagnostic_cr.get("name"),
            "manifest": diagnostic_cr.get("manifest"),
            "status": diagnostic_cr.get("status"),
            "lifecycle": diagnostic_cr.get("lifecycle", _CR_LIFECYCLE),
        },
        "diagnosis": {
            "health": diagnosis.get("health", "unknown"),
            "baseline_summary": diagnosis.get("baseline_summary") if isinstance(diagnosis.get("baseline_summary"), dict) else {
                "total": 0, "passed": 0, "warning": 0, "critical": 0, "unavailable": 0, "informational": 0,
            },
            "baseline_checks": diagnosis.get("baseline_checks") if isinstance(diagnosis.get("baseline_checks"), list) else [],
            "findings": diagnosis.get("findings") if isinstance(diagnosis.get("findings"), list) else [],
            "data_gaps": diagnosis.get("data_gaps") if isinstance(diagnosis.get("data_gaps"), list) else [],
            "observations": diagnosis.get("observations") if isinstance(diagnosis.get("observations"), dict) else {
                "component_status": [], "resource_usage": {}, "network": {}, "system": {}, "collection_status": {},
            },
        },
        "debug_trace": result.get("debug_trace") if isinstance(result.get("debug_trace"), list) else [],
    }


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    params, error = _normalize_credentials(params)
    if error:
        return _standardize(params, {"success": False, "error": error})
    params = _resolve_region(params)
    if error := _validate(params):
        return _standardize(params, {"success": False, "error": error})
    try:
        result = ACTION_SPECS[action][1](params)
    except Exception as exc:  # Keep unexpected implementation errors inside the stable public envelope.
        result = {"success": False, "error": f"Unexpected diagnostic error: {exc}"}
    return _standardize(params, result)
