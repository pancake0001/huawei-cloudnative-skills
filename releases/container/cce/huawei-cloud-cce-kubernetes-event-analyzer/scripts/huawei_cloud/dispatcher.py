"""Dispatcher for the public CCE Kubernetes Event Analyzer tools."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from . import cce, cce_events_lts, common, event_analysis

Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _resolve_region(params: Dict[str, str]) -> Dict[str, str]:
    """Prefer an explicit region and otherwise use the configured region."""
    resolved = dict(params)
    if not resolved.get("region") and os.environ.get("HW_REGION_NAME"):
        resolved["region"] = os.environ["HW_REGION_NAME"]
    return resolved


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    if not missing:
        return None
    if missing == ["region"]:
        return "region is required; provide region or set HW_REGION_NAME"
    return f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required"


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _get_cce_events(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_events(
        region=params["region"],
        cluster_id=params["cluster_id"],
        namespace=params.get("namespace"),
        event_type=params.get("event_type"),
        limit=_to_int(params.get("limit"), 500),
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_get_cce_events": (("region", "cluster_id"), _get_cce_events),
    "huawei_query_k8s_events_from_lts": (
        ("region", "cluster_id", "start_time", "end_time"),
        cce_events_lts.query_k8s_events_from_lts_action,
    ),
    "huawei_analyze_cce_events": ((), event_analysis.analyze_cce_events_action),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    try:
        with common.credential_context(_resolve_region(params)) as normalized:
            required, handler = ACTION_SPECS[action]
            error = _require(normalized, *required)
            if error:
                return {"success": False, "error": error}
            resolution = None
            if normalized.get("cluster_id"):
                resolution = cce.resolve_cce_cluster_id(
                    normalized["region"], normalized["cluster_id"], normalized.get("ak"), normalized.get("sk"), normalized.get("project_id")
                )
                if not resolution.get("success"):
                    return resolution
                normalized["cluster_id"] = resolution["id"]
            result = handler(normalized)
            if resolution and resolution.get("resolved_from_name") and result.get("success"):
                result["resolved_resource_ids"] = [{"parameter": "cluster_id", "input": params["cluster_id"], "resolved_id": resolution["id"]}]
            return result
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
