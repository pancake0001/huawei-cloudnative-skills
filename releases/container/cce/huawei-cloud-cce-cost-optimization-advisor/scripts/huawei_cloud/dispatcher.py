"""Public read-only actions for CCE cost optimization advice."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from . import aom, cce, cce_cost_optimization, cce_hpa, cce_metrics, common


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
    return cce_cost_optimization.analyze_cce_cost_optimization(region=params["region"], cluster_id=params["cluster_id"], hours=_integer(params.get("hours"), 24), top_n=_integer(params.get("top_n"), 20), **_cluster_kwargs(params))


def _generate_cost_report(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_cost_optimization.generate_cce_cost_optimization_report(
        region=params["region"],
        cluster_id=params["cluster_id"],
        analysis_date=params.get("analysis_date"),
        analysis_days=_integer(params.get("analysis_days"), 1),
        top_n=_integer(params.get("top_n"), 20),
        exclude_namespaces=params.get("exclude_namespaces"),
        output_file=params.get("output_file"),
        output_format=params.get("output_format", "html"),
        **_cluster_kwargs(params),
    )


def _pod_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_metrics.get_cce_pod_metrics_topN(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"), params.get("label_selector"), _integer(params.get("top_n"), 10), _integer(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"), params.get("node_ip"))


def _node_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_metrics.get_cce_node_metrics_topN(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), _integer(params.get("top_n"), 10), _integer(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"), params.get("disk_query"))


def _aom_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.get_aom_prom_metrics_http(params["region"], params["aom_instance_id"], params["query"], hours=_integer(params.get("hours"), 1), ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))


def _hpa_manifest(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_hpa.generate_cce_hpa_manifest(params["workload_name"], params["namespace"], _integer(params.get("min_replicas"), 1), _integer(params.get("max_replicas"), 3), params.get("workload_type", "deployment"), params.get("hpa_name"), _integer(params.get("target_cpu_utilization"), 60), params.get("target_memory_utilization"), params.get("behavior"), params.get("output_file"))


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_analyze_cce_cost_optimization": (("region", "cluster_id"), _diagnose),
    "huawei_generate_cce_cost_optimization_report": (("region", "cluster_id"), _generate_cost_report),
    "huawei_list_cce_clusters": (("region",), _list_clusters),
    "huawei_list_cce_hpas": (("region", "cluster_id", "namespace"), _hpas),
    "huawei_list_cce_addons": (("region", "cluster_id"), _list_addons),
    "huawei_get_cce_addon_detail": (("region", "cluster_id", "addon_name"), _addon_detail),
    "huawei_list_cce_nodepools": (("region", "cluster_id"), _list_nodepools),
    "huawei_get_kubernetes_nodes": (("region", "cluster_id"), _nodes),
    "huawei_get_cce_pods": (("region", "cluster_id", "namespace"), _pods),
    "huawei_get_cce_deployments": (("region", "cluster_id", "namespace"), _deployments),
    "huawei_list_cce_statefulsets": (("region", "cluster_id", "namespace"), _statefulsets),
    "huawei_get_cce_events": (("region", "cluster_id", "namespace"), _events),
    "huawei_get_cce_pod_metrics_topN": (("region", "cluster_id"), _pod_metrics),
    "huawei_get_cce_node_metrics_topN": (("region", "cluster_id"), _node_metrics),
    "huawei_get_aom_metrics": (("region", "aom_instance_id", "query"), _aom_metrics),
    "huawei_generate_cce_hpa_manifest": (("workload_name", "namespace"), _hpa_manifest),
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
