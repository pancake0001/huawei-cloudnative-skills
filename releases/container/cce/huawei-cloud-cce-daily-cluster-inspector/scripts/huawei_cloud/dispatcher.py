"""Public read-only actions for CCE daily inspection."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict

from . import aom, cce, cce_daily_inspection, cce_hpa, cce_metrics, common


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


def _inspection_hours(params: Dict[str, str]) -> tuple[int | None, str | None]:
    value = params.get("hours", "1")
    try:
        hours = int(value)
    except (TypeError, ValueError):
        return None, "hours must be an integer from 1 to 24"
    if not 1 <= hours <= 24:
        return None, "hours must be between 1 and 24"
    return hours, None


def _cluster_kwargs(params: Dict[str, str]) -> Dict[str, Any]:
    return {"ak": params.get("ak"), "sk": params.get("sk"), "project_id": params.get("project_id"), "security_token": params.get("security_token")}


def _list_clusters(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_clusters(params["region"], **_cluster_kwargs(params))


def _list_nodepools(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_node_pools(params["region"], params["cluster_id"], limit=_integer(params.get("limit"), 100), offset=_integer(params.get("offset"), 0), **_cluster_kwargs(params))


def _list_addons(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_addons(params["region"], params["cluster_id"], **_cluster_kwargs(params))


def _addon_detail(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_cce_addon_detail(params["region"], params["cluster_id"], params["addon_name"], **_cluster_kwargs(params))


def _pods(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_pods(params["region"], params["cluster_id"], namespace=params["namespace"], labels=params.get("labels"), **_cluster_kwargs(params))


def _deployments(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_deployments(params["region"], params["cluster_id"], namespace=params["namespace"], **_cluster_kwargs(params))


def _statefulsets(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_statefulsets(params["region"], params["cluster_id"], namespace=params["namespace"], limit=_integer(params.get("limit"), 100), **_cluster_kwargs(params))


def _events(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_events(params["region"], params["cluster_id"], namespace=params["namespace"], limit=_integer(params.get("limit"), 500), **_cluster_kwargs(params))


def _nodes(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_nodes(params["region"], params["cluster_id"], node_name=params.get("node_name"), **_cluster_kwargs(params))


def _hpas(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_hpa.list_cce_hpas(params["region"], params["cluster_id"], namespace=params["namespace"], include_system=params.get("include_system", "false").lower() == "true", **_cluster_kwargs(params))


def _diagnose(params: Dict[str, str]) -> Dict[str, Any]:
    hours, error = _inspection_hours(params)
    if error:
        return {"success": False, "error": error}
    return cce_daily_inspection.inspect_cluster(params["region"], params["cluster_id"], params.get("namespace"), hours, _integer(params.get("top_n"), 10), params.get("mode", "auto"), **_cluster_kwargs(params))


def _quick_check(params: Dict[str, str]) -> Dict[str, Any]:
    hours, error = _inspection_hours(params)
    if error:
        return {"success": False, "error": error}
    return cce_daily_inspection.quick_check(params["region"], params["cluster_id"], _integer(params.get("event_limit"), 200), _integer(params.get("pod_limit"), 200), _integer(params.get("alarm_limit"), 200), hours=hours, **_cluster_kwargs(params))


def _pod_status(params: Dict[str, str]) -> Dict[str, Any]:
    hours, error = _inspection_hours(params)
    if error:
        return {"success": False, "error": error}
    return cce_daily_inspection.inspect_pods(
        params["region"],
        params["cluster_id"],
        params["namespace"],
        hours=hours,
        pod_limit=_integer(params.get("pod_limit"), 200),
        **_cluster_kwargs(params),
    )


def _node_status(params: Dict[str, str]) -> Dict[str, Any]:
    hours, error = _inspection_hours(params)
    if error:
        return {"success": False, "error": error}
    return cce_daily_inspection.inspect_nodes(params["region"], params["cluster_id"], hours=hours, **_cluster_kwargs(params))


def _node_resources(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_daily_inspection.inspect_node_resources(params["region"], params["cluster_id"], _integer(params.get("hours"), 1), _integer(params.get("top_n"), 10), **_cluster_kwargs(params))


def _event_inspection(params: Dict[str, str]) -> Dict[str, Any]:
    hours, error = _inspection_hours(params)
    if error:
        return {"success": False, "error": error}
    # event_limit is the documented parameter; keep limit as a legacy alias.
    event_limit = _integer(params.get("event_limit", params.get("limit")), 200)
    return cce_daily_inspection.inspect_events(params["region"], params["cluster_id"], params["namespace"], event_limit, hours=hours, **_cluster_kwargs(params))


def _alarm_inspection(params: Dict[str, str]) -> Dict[str, Any]:
    hours, error = _inspection_hours(params)
    if error:
        return {"success": False, "error": error}
    return cce_daily_inspection.inspect_aom_alarm_configuration_and_events(
        params["region"],
        params["cluster_id"],
        hours=hours,
        alarm_limit=_integer(params.get("alarm_limit"), 200),
        **_cluster_kwargs(params),
    )


def _elb_inspection(params: Dict[str, str]) -> Dict[str, Any]:
    hours, error = _inspection_hours(params)
    if error:
        return {"success": False, "error": error}
    return cce_daily_inspection.inspect_elb(params["region"], params["cluster_id"], hours=hours, **_cluster_kwargs(params))


def _aggregate(params: Dict[str, str]) -> Dict[str, Any]:
    try:
        results = json.loads(params["results"])
    except (KeyError, json.JSONDecodeError) as exc:
        return {"success": False, "error": f"results must be a JSON array: {exc}"}
    return cce_daily_inspection.aggregate(results, "aggregate_inspection_results")


def _export(params: Dict[str, str]) -> Dict[str, Any]:
    try:
        result = json.loads(params["result"])
    except (KeyError, json.JSONDecodeError) as exc:
        return {"success": False, "error": f"result must be a JSON object: {exc}"}
    return cce_daily_inspection.export_report(result, params["output_file"])


def _pod_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_metrics.get_cce_pod_metrics_topN(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"), params.get("label_selector"), _integer(params.get("top_n"), 10), _integer(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"), params.get("node_ip"))


def _node_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_metrics.get_cce_node_metrics_topN(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), _integer(params.get("top_n"), 10), _integer(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"), params.get("disk_query"))


def _aom_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.get_aom_prom_metrics_http(params["region"], params["aom_instance_id"], params["query"], hours=_integer(params.get("hours"), 1), ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_cce_quick_check": (("region", "cluster_id"), _quick_check),
    "huawei_cce_deep_diagnosis": (("region", "cluster_id"), _diagnose),
    "huawei_pod_status_inspection": (("region", "cluster_id", "namespace"), _pod_status),
    "huawei_node_status_inspection": (("region", "cluster_id"), _node_status),
    "huawei_event_inspection": (("region", "cluster_id", "namespace"), _event_inspection),
    "huawei_aom_alarm_inspection": (("region", "cluster_id"), _alarm_inspection),
    "huawei_elb_monitoring_inspection": (("region", "cluster_id"), _elb_inspection),
    "huawei_export_inspection_report": (("result", "output_file"), _export),
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
