"""CLI dispatch helpers for modular Huawei Cloud actions."""

from __future__ import annotations

from typing import Any, Callable, Dict

import json

from . import aom, cce, cce_metrics, ecs, elb, hss, identity, network, storage
from . import cce_inspection
from . import cce_diagnosis
from . import cce_auto_inspection
from . import chart_generator
from . import common

# cce_app_logs and lts require huaweicloudsdklts which may not be installed
try:
    from . import cce_app_logs as _cce_app_logs_mod
    from . import lts as _lts_mod
    _lts_available = True
except ImportError:
    _lts_available = False
    _cce_app_logs_mod = None
    _lts_mod = None


Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    if missing:
        return f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required"
    return None


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _parse_json_param(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)


def _list_ecs(params: Dict[str, str]) -> Dict[str, Any]:
    return ecs.list_ecs_instances(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _get_ecs_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return ecs.get_ecs_metrics(params["region"], params["instance_id"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_flavors(params: Dict[str, str]) -> Dict[str, Any]:
    return ecs.list_ecs_flavors(params["region"], params.get("az"), params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _list_vpc(params: Dict[str, str]) -> Dict[str, Any]:
    return network.list_vpc_networks(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _list_vpc_subnets(params: Dict[str, str]) -> Dict[str, Any]:
    return network.list_vpc_subnets(params["region"], params.get("vpc_id"), params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _list_security_groups(params: Dict[str, str]) -> Dict[str, Any]:
    return network.list_security_groups(params["region"], params.get("vpc_id"), params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _list_vpc_acls(params: Dict[str, str]) -> Dict[str, Any]:
    return network.list_vpc_acls(params["region"], params.get("vpc_id"), params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_eip(params: Dict[str, str]) -> Dict[str, Any]:
    return network.list_eip_addresses(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100))


def _get_eip_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return network.get_eip_metrics(params["region"], params["eip_id"], _to_int(params.get("hours"), 1), _to_int(params.get("period"), 300), params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_nat(params: Dict[str, str]) -> Dict[str, Any]:
    return network.list_nat_gateways(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0), params.get("id"), params.get("name"), params.get("description"), params.get("spec"), params.get("router_id"), params.get("internal_network_id"), params.get("status"), None if params.get("admin_state_up") is None else params.get("admin_state_up", "").lower() == "true", params.get("created_at"))


def _get_nat_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return network.get_nat_gateway_metrics(params["region"], params["nat_gateway_id"], _to_int(params.get("hours"), 1), _to_int(params.get("period"), 300), params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_evs(params: Dict[str, str]) -> Dict[str, Any]:
    return storage.list_evs_volumes(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0), params.get("volume_type"), params.get("availability_zone"))


def _get_evs_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return storage.get_evs_metrics(params["region"], params["volume_id"], params["instance_id"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_sfs(params: Dict[str, str]) -> Dict[str, Any]:
    return storage.list_sfs(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _list_sfs_turbo(params: Dict[str, str]) -> Dict[str, Any]:
    return storage.list_sfs_turbo(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _list_elb(params: Dict[str, str]) -> Dict[str, Any]:
    return elb.list_elb_loadbalancers(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), params.get("marker"))


def _list_elb_listeners(params: Dict[str, str]) -> Dict[str, Any]:
    return elb.list_elb_listeners(params["region"], params.get("loadbalancer_id"), params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100))


def _get_elb_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return elb.get_elb_metrics(params["region"], params["elb_id"], _to_int(params.get("hours"), 1), _to_int(params.get("period"), 300), params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_projects(params: Dict[str, str]) -> Dict[str, Any]:
    return identity.list_projects(params.get("ak"), params.get("sk"), params.get("domain_id"), params.get("region"))


def _get_project_by_region(params: Dict[str, str]) -> Dict[str, Any]:
    return identity.get_project_by_region(params["region"], params.get("ak"), params.get("sk"))


def _list_cce_clusters(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_clusters(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _delete_cce_cluster(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.delete_cce_cluster(params["region"], params["cluster_id"], params.get("confirm", "").lower() == "true", params.get("delete_evs", "").lower() == "true", params.get("delete_net", "").lower() == "true", params.get("delete_obs", "").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_cce_nodes(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_cluster_nodes(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _get_cce_nodes(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_cce_nodes(params["region"], params["cluster_id"], params.get("node_name"), params.get("ak"), params.get("sk"), params.get("project_id"))


def _delete_cce_node(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.delete_cce_node(params["region"], params["cluster_id"], params["node_id"], params.get("confirm", "").lower() == "true", params.get("scale_down", "true").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_cce_nodepools(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_node_pools(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _get_cce_kubeconfig(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_cce_kubeconfig(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("duration"), 30))


def _list_cce_addons(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_addons(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _get_cce_addon_detail(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_cce_addon_detail(params["region"], params["cluster_id"], params["addon_name"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _resize_cce_nodepool(params: Dict[str, str]) -> Dict[str, Any]:
    scale_group_names = None
    if params.get("scale_group_names"):
        scale_group_names = [name.strip() for name in params["scale_group_names"].split(",") if name.strip()]
    return cce.resize_node_pool(params["region"], params["cluster_id"], params["nodepool_id"], int(params["node_count"]), params.get("confirm", "").lower() == "true", scale_group_names, params.get("ak"), params.get("sk"), params.get("project_id"))


def _get_cce_pods(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_pods(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"), params.get("labels"))


def _get_pod_logs(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_pod_logs(
        params["region"],
        params["cluster_id"],
        params["pod_name"],
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
        params.get("namespace", "default"),
        params.get("container"),
        params.get("previous", "false").lower() == "true",
        _to_int(params.get("tail_lines"), 100)
    )


def _get_cce_namespaces(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_namespaces(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _get_cce_deployments(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_deployments(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"))


def _scale_cce_workload(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.scale_cce_workload(params["region"], params["cluster_id"], params["workload_type"], params["name"], params["namespace"], int(params["replicas"]), params.get("confirm", "").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _resize_cce_workload(params: Dict[str, str]) -> Dict[str, Any]:
    replicas = int(params["replicas"]) if params.get("replicas") else None
    return cce.resize_cce_workload(
        params["region"], params["cluster_id"], params["workload_type"], params["name"], params["namespace"],
        replicas=replicas,
        cpu_limit=params.get("cpu_limit"),
        memory_limit=params.get("memory_limit"),
        cpu_request=params.get("cpu_request"),
        memory_request=params.get("memory_request"),
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id")
    )


def _delete_cce_workload(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.delete_cce_workload(params["region"], params["cluster_id"], params["workload_type"], params["name"], params["namespace"], params.get("confirm", "").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _get_kubernetes_nodes(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_nodes(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _get_cce_events(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_events(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"), _to_int(params.get("limit"), 500))


def _get_cce_pvcs(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_pvcs(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"))


def _get_cce_pvs(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_pvs(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _get_cce_services(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_services(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"))


def _get_cce_ingresses(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.get_kubernetes_ingresses(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"))


def _list_cce_configmaps(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_configmaps(params["region"], params["cluster_id"], params.get("namespace"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0), params.get("include_data", "false").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_cce_secrets(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_secrets(params["region"], params["cluster_id"], params.get("namespace"), _to_int(params.get("limit"), 100), params.get("include_data", "false").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_cce_daemonsets(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_daemonsets(params["region"], params["cluster_id"], params.get("namespace"), _to_int(params.get("limit"), 100), params.get("include_data", "false").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_cce_statefulsets(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_statefulsets(params["region"], params["cluster_id"], params.get("namespace"), _to_int(params.get("limit"), 100), params.get("include_data", "false").lower() == "true", params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_aom_instances(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_instances(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("prom_type"))


def _get_aom_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.get_aom_prom_metrics_http(params["region"], params["aom_instance_id"], params["query"], None if params.get("start") is None else int(params["start"]), None if params.get("end") is None else int(params["end"]), _to_int(params.get("step"), 60), _to_int(params.get("hours"), 1), params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_aom_alerts(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_alerts(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("alert_status"), params.get("severity"), _to_int(params.get("limit"), 100))


def _list_aom_alarm_rules(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_alarm_rules(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("limit"), 100), _to_int(params.get("offset"), 0))


def _list_aom_action_rules(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_action_rules(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_aom_mute_rules(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_mute_rules(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_aom_current_alarms(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_current_alarms(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("event_type", "active_alert"), params.get("event_severity"), params.get("time_range"), _to_int(params.get("limit"), 100))


def _list_aom_alarms(params: Dict[str, str]) -> Dict[str, Any]:
    return aom.list_aom_alarms(
        region=params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        hours=_to_int(params.get("hours"), 1),
        event_severity=params.get("event_severity"),
        cluster_name=params.get("cluster_name"),
        limit=_to_int(params.get("limit"), 500),
    )


def _list_log_groups(params: Dict[str, str]) -> Dict[str, Any]:
    return _lts_mod.list_log_groups(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))


def _list_log_streams(params: Dict[str, str]) -> Dict[str, Any]:
    return _lts_mod.list_log_streams(params["region"], params.get("log_group_id"), params.get("ak"), params.get("sk"), params.get("project_id"))


def _query_logs(params: Dict[str, str]) -> Dict[str, Any]:
    labels = _parse_json_param(params.get("labels"))
    return _lts_mod.query_logs(params["region"], params["log_group_id"], params["log_stream_id"], params.get("start_time"), params.get("end_time"), params.get("keywords"), _to_int(params.get("limit"), 1000), params.get("scroll_id"), params.get("is_desc", "true").lower() == "true", params.get("is_iterative", "false").lower() == "true", labels, params.get("ak"), params.get("sk"), params.get("project_id"))


def _get_recent_logs(params: Dict[str, str]) -> Dict[str, Any]:
    labels = _parse_json_param(params.get("labels"))
    return _lts_mod.get_recent_logs(params["region"], params["log_group_id"], params["log_stream_id"], _to_int(params.get("hours"), 1), _to_int(params.get("limit"), 1000), params.get("keywords"), labels, params.get("ak"), params.get("sk"), params.get("project_id"))


def _query_aom_logs(params: Dict[str, str]) -> Dict[str, Any]:
    return _lts_mod.query_aom_logs(params["region"], params["cluster_id"], params.get("namespace"), params.get("pod_name"), params.get("container_name"), params.get("start_time"), params.get("end_time"), params.get("keywords"), _to_int(params.get("limit"), 100), params.get("ak"), params.get("sk"), params.get("project_id"))


def _inspection_action(handler: Callable[[Dict[str, str]], Dict[str, Any]], params: Dict[str, str]) -> Dict[str, Any]:
    return handler(params)


def _metric_action(handler: Callable[..., Dict[str, Any]], *args: Any, **kwargs: Any) -> Dict[str, Any]:
    return handler(*args, **kwargs)



def _inspection_check_action(fn, params):
    """通用巡检action封装：直接调用fn并返回 {success, check, issues}"""
    check, issues = fn(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    return {"success": True, "check": check, "issues": issues}


def _addon_pod_inspection_action(params):
    aom_id = cce_inspection._get_aom_instance(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))
    cluster_name = cce_inspection._get_cluster_name(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    all_pods_map = cce_inspection._get_all_pods_map(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    check, issues = cce_inspection.addon_pod_monitoring_inspection(
        params["region"], params["cluster_id"], aom_id, cluster_name,
        params.get("ak"), params.get("sk"), params.get("project_id"), all_pods_map
    )
    return {"success": True, "check": check, "issues": issues}


def _biz_pod_inspection_action(params):
    aom_id = cce_inspection._get_aom_instance(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))
    cluster_name = cce_inspection._get_cluster_name(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    all_pods_map = cce_inspection._get_all_pods_map(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    all_namespaces = cce_inspection._get_all_namespaces(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    check, issues = cce_inspection.biz_pod_monitoring_inspection(
        params["region"], params["cluster_id"], aom_id, cluster_name,
        params.get("ak"), params.get("sk"), params.get("project_id"), all_pods_map, all_namespaces
    )
    return {"success": True, "check": check, "issues": issues}


def _node_resource_inspection_action(params):
    aom_id = cce_inspection._get_aom_instance(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))
    cluster_name = cce_inspection._get_cluster_name(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    check, issues = cce_inspection.node_resource_monitoring_inspection(
        params["region"], params["cluster_id"], aom_id, cluster_name,
        params.get("ak"), params.get("sk"), params.get("project_id")
    )
    return {"success": True, "check": check, "issues": issues}


def _aom_alarm_inspection_action(params):
    cluster_name = cce_inspection._get_cluster_name(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    check, issues = cce_inspection.aom_alarm_inspection(
        params["region"], params["cluster_id"], cluster_name,
        params.get("ak"), params.get("sk"), params.get("project_id")
    )
    return {"success": True, "check": check, "issues": issues}


def _elb_monitoring_inspection_action(params):
    aom_id = cce_inspection._get_aom_instance(params["region"], params.get("ak"), params.get("sk"), params.get("project_id"))
    cluster_name = cce_inspection._get_cluster_name(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))
    check, issues = cce_inspection.elb_monitoring_inspection(
        params["region"], params["cluster_id"], aom_id, cluster_name,
        params.get("ak"), params.get("sk"), params.get("project_id")
    )
    return {"success": True, "check": check, "issues": issues}


def _aggregate_results_action(params):
    try:
        return cce_inspection.aggregate_subagent_results(json.loads(params["results"]), json.loads(params["cluster_info"]))
    except Exception as exc:
        return {"success": False, "error": str(exc)}



# ---- Diagnosis action helpers (inlined from diagnosis_actions.py) ----

def _network_diagnose_action(params):
    try:
        return cce_diagnosis.network_diagnose(
            params["region"], params["cluster_id"],
            params.get("workload_name"), params.get("namespace", "default"),
            params.get("ak"), params.get("sk"), params.get("project_id")
        )
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__, "stage": "huawei_network_diagnose"}


def _network_diagnose_by_alarm_action(params):
    return cce_diagnosis.network_diagnose_by_alarm(
        params["region"], params["cluster_id"], params["alarm_info"],
        params.get("ak"), params.get("sk"), params.get("project_id")
    )


def _network_verify_pod_scheduling_action(params):
    return cce_diagnosis.verify_pod_scheduling_after_scale(
        params["region"], params["cluster_id"], params["workload_name"],
        params.get("namespace", "default"),
        params.get("ak"), params.get("sk"), params.get("project_id")
    )


def _node_batch_diagnose_action(params):
    node_ips = [ip.strip() for ip in params.get("node_ips", "").split(",") if ip.strip()] or None
    return cce_diagnosis.batch_node_diagnose(
        params["region"], params["cluster_id"], node_ips,
        params.get("ak"), params.get("sk"), params.get("project_id")
    )


def _node_diagnose_action(params):
    import re
    from .common import get_credentials_with_region
    from .cce import get_kubernetes_nodes
    from .cce_metrics import get_cce_node_metrics

    region = params["region"]
    cluster_id = params["cluster_id"]
    ak = params.get("ak")
    sk = params.get("sk")
    project_id = params.get("project_id")
    node_ip = params.get("node_ip")
    node_name = params.get("node_name")

    if not node_ip and node_name:
        access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
        if "." in node_name and all(part.isdigit() for part in node_name.split(".") if part):
            node_ip = node_name

        if not node_ip:
            k8s_result = get_kubernetes_nodes(region, cluster_id, access_key, secret_key, proj_id)
            if k8s_result.get("success"):
                for node in k8s_result.get("nodes", []):
                    if node_name == node.get("name", "") or node_name == node.get("internal_ip", ""):
                        node_ip = node.get("internal_ip", "")
                        break

        if not node_ip:
            k8s_result = get_kubernetes_nodes(region, cluster_id, access_key, secret_key, proj_id) if not k8s_result.get("success") else k8s_result
            if not k8s_result.get("success"):
                return {"success": False, "error": "Cannot find node and failed to get kubernetes nodes"}

            return {
                "success": False,
                "error": f"Cannot automatically convert CCE node name '{node_name}' to IP.",
                "note": "CCE node names cannot be automatically resolved to IPs via API.",
                "hint": "Use node_ip parameter instead.",
                "available_k8s_ips": [n.get("internal_ip") for n in k8s_result.get("nodes", [])],
            }

    if not node_ip:
        return {"success": False, "error": "node_ip or node_name is required"}

    cluster_name = cce_diagnosis.get_cluster_name(region, cluster_id, ak, sk, project_id)
    diagnose_result = cce_diagnosis.diagnose_single_node(node_ip, region, cluster_id, ak, sk, project_id)
    if isinstance(diagnose_result, dict) and "success" in diagnose_result:
        return diagnose_result
    return {"success": True, "region": region, "action": "node_diagnose", "cluster_id": cluster_id, "node_ip": node_ip, "result": diagnose_result}


def _flatten_diagnosis_result(raw):
    """workload_diagnose 返回 {success, diagnosis, report}，展平 diagnosis 到顶层"""
    if not raw.get("success"):
        return raw
    diag = raw.get("diagnosis", {})
    report = raw.get("report", {})
    flat = dict(diag)
    flat["success"] = True
    flat["report"] = report
    return flat


def _workload_diagnose_action(params):
    try:
        raw = cce_diagnosis.workload_diagnose(
            params["region"], params["cluster_id"],
            params.get("workload_name"), params.get("namespace", "default"),
            params.get("ak"), params.get("sk"), params.get("project_id"),
            params.get("fault_time"),
            int(params.get("hours", 6))
        )
        return _flatten_diagnosis_result(raw)
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__, "stage": "workload_diagnose"}


def _workload_diagnose_by_alarm_action(params):
    try:
        raw = cce_diagnosis.workload_diagnose_by_alarm(
            params["region"], params["cluster_id"], params["alarm_info"],
            params.get("ak"), params.get("sk"), params.get("project_id"),
            int(params.get("hours", 6))
        )
        return _flatten_diagnosis_result(raw)
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__, "stage": "workload_diagnose_by_alarm"}


def _hibernate_cce_cluster_action(params):
    return cce.hibernate_cce_cluster(
        region=params["region"], cluster_id=params["cluster_id"],
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"),
        confirm=params.get("confirm", "").lower() == "true"
    )


def _awake_cce_cluster_action(params):
    return cce.awake_cce_cluster(
        region=params["region"], cluster_id=params["cluster_id"],
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"),
        confirm=params.get("confirm", "").lower() == "true"
    )


def _stop_ecs_instance_action(params):
    return ecs.stop_ecs_instance(
        params["region"], params["instance_id"],
        params.get("stop_type", "SOFT"),
        params.get("ak"), params.get("sk"), params.get("project_id"),
        params.get("confirm", "false").lower() == "true"
    )


def _start_ecs_instance_action(params):
    return ecs.start_ecs_instance(
        params["region"], params["instance_id"],
        params.get("ak"), params.get("sk"), params.get("project_id")
    )


def _list_cce_cronjobs(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.list_cce_cronjobs(
        params["region"], params["cluster_id"],
        params.get("namespace"),
        params.get("ak"), params.get("sk"), params.get("project_id")
    )


# ---- HSS handlers ----
def _hss_list_vul_host_hosts(params: Dict[str, str]) -> Dict[str, Any]:
    return hss.list_vul_host_hosts(region=params["region"], ak=params.get("ak"), sk=params.get("sk"))

def _hss_list_host_vuls_all(params: Dict[str, str]) -> Dict[str, Any]:
    return hss.list_host_vuls_all(
        region=params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        host_id=params.get("host_id"),
        host_name=params.get("host_name"),
        status=params.get("status"),
        repair_priority=params.get("repair_priority"),
        severity_level=params.get("severity_level"),
        limit=int(params.get("limit", 100)),
        enterprise_project_id=params.get("enterprise_project_id", "all_granted_eps"),
    )

def _hss_change_vul_status(params: Dict[str, str]) -> Dict[str, Any]:
    return hss.change_vul_status(
        region=params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        operate_type=params["operate_type"],
        vul_ids=params.get("vul_ids"),
        host_ids=params.get("host_ids"),
        vul_type=params.get("vul_type", "linux_vul"),
        remark=params.get("remark"),
        select_type=params.get("select_type"),
        confirm=params.get("confirm", "").lower() == "true",
        enterprise_project_id=params.get("enterprise_project_id", "all_granted_eps"),
    )


def _cce_node_cordon(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.cce_node_cordon(
        region=params["region"], cluster_id=params["cluster_id"], node_name=params["node_name"],
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))

def _cce_node_uncordon(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.cce_node_uncordon(
        region=params["region"], cluster_id=params["cluster_id"], node_name=params["node_name"],
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))

def _cce_node_drain(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.cce_node_drain(
        region=params["region"], cluster_id=params["cluster_id"], node_name=params["node_name"],
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))

def _cce_node_status(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.cce_node_status(
        region=params["region"], cluster_id=params["cluster_id"], node_name=params["node_name"],
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))

def _bind_cce_cluster_eip(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.bind_cce_cluster_eip(
        region=params["region"], cluster_id=params["cluster_id"], eip_id=params["eip_id"],
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))


def _unbind_cce_cluster_eip(params: Dict[str, str]) -> Dict[str, Any]:
    return cce.unbind_cce_cluster_eip(
        region=params["region"], cluster_id=params["cluster_id"],
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))


def _generate_monitor_dashboard(params: Dict[str, str]) -> Dict[str, Any]:
    extra_promql = None
    if params.get("extra_promql"):
        try:
            extra_promql = json.loads(params["extra_promql"])
        except (json.JSONDecodeError, TypeError):
            extra_promql = None
    return chart_generator.generate_monitor_dashboard(
        region=params["region"],
        cluster_id=params["cluster_id"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        namespace=params.get("namespace"),
        label_selector=params.get("label_selector"),
        hours=_to_int(params.get("hours"), 1),
        include_network=params.get("include_network", "true").lower() != "false",
        top_n=_to_int(params.get("top_n"), 10),
        output_file=params.get("output_file"),
        title=params.get("title"),
        tz_offset_hours=_to_int(params.get("tz_offset_hours"), 8),
        inline_js=params.get("inline_js", "true").lower() != "false",
        extra_promql=extra_promql,
    )


def _generate_diagnosis_report(params: Dict[str, str]) -> Dict[str, Any]:
    """Dispatch wrapper for generate_diagnosis_report."""
    return chart_generator.generate_diagnosis_report(
        region=params["region"],
        cluster_id=params["cluster_id"],
        workload_name=params["workload_name"],
        namespace=params.get("namespace", "default"),
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        fault_time=params.get("fault_time"),
        hours=_to_int(params.get("hours"), 1),
        output_file=params.get("output_file"),
    )


def _analyze_aom_alarms(params: Dict[str, str]) -> Dict[str, Any]:
    """Dispatch wrapper for analyze_aom_alarms."""
    return aom.analyze_aom_alarms(
        region=params["region"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        cluster_name=params.get("cluster_name"),
        hours=_to_int(params.get("hours"), 1),
        chronic_threshold=_to_int(params.get("chronic_threshold"), 5),
        sudden_window_minutes=_to_int(params.get("sudden_window_minutes"), 10),
    )


def _cce_quick_check_action(params: Dict[str, str]) -> Dict[str, Any]:
    """快检：3 个 API，< 30s，判断是否有异常"""
    # Parse optional thresholds
    thresholds = None
    if params.get("thresholds"):
        try:
            thresholds = json.loads(params["thresholds"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Parse optional elb_ids
    elb_ids = None
    if params.get("elb_ids"):
        elb_ids = [e.strip() for e in params["elb_ids"].split(",") if e.strip()]

    return cce_auto_inspection.cce_quick_check(
        region=params["region"],
        cluster_id=params["cluster_id"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        thresholds=thresholds,
        elb_ids=elb_ids,
    )


def _cce_deep_diagnosis_action(params: Dict[str, str]) -> Dict[str, Any]:
    """深度诊断：快检发现异常后调用，6+ 个 API 全链路诊断"""
    quick_check_result = None
    if params.get("quick_check_result"):
        try:
            quick_check_result = json.loads(params["quick_check_result"])
        except (json.JSONDecodeError, TypeError):
            pass

    return cce_auto_inspection.cce_deep_diagnosis(
        region=params["region"],
        cluster_id=params["cluster_id"],
        quick_check_result=quick_check_result,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        notify_email=params.get("notify_email"),
        report_file=params.get("report_file"),
    )


def _cce_auto_inspection_action(params: Dict[str, str]) -> Dict[str, Any]:
    """自动巡检：快检 + 判断 + (诊断 | HEARTBEAT_OK) 一步到位"""
    thresholds = None
    if params.get("thresholds"):
        try:
            thresholds = json.loads(params["thresholds"])
        except (json.JSONDecodeError, TypeError):
            pass

    elb_ids = None
    if params.get("elb_ids"):
        elb_ids = [e.strip() for e in params["elb_ids"].split(",") if e.strip()]

    return cce_auto_inspection.cce_auto_inspection(
        region=params["region"],
        cluster_id=params["cluster_id"],
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        thresholds=thresholds,
        elb_ids=elb_ids,
        notify_email=params.get("notify_email"),
    )


def _reboot_ecs(params: Dict[str, str]) -> Dict[str, Any]:
    return ecs.reboot_ecs_instance(
        region=params["region"], instance_id=params["instance_id"],
        reboot_type=params.get("reboot_type", "SOFT"),
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"))


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_list_ecs": (("region",), _list_ecs),
    "huawei_get_ecs_metrics": (("region", "instance_id"), _get_ecs_metrics),
    "huawei_list_flavors": (("region",), _list_flavors),
    "huawei_stop_ecs_instance": (("region", "instance_id"), _stop_ecs_instance_action),
    "huawei_start_ecs_instance": (("region", "instance_id"), _start_ecs_instance_action),
    "huawei_list_vpc": (("region",), _list_vpc),
    "huawei_list_vpc_subnets": (("region",), _list_vpc_subnets),
    "huawei_list_security_groups": (("region",), _list_security_groups),
    "huawei_list_vpc_acls": (("region",), _list_vpc_acls),
    "huawei_list_eip": (("region",), _list_eip),
    "huawei_get_eip_metrics": (("region", "eip_id"), _get_eip_metrics),
    "huawei_list_nat": (("region",), _list_nat),
    "huawei_get_nat_gateway_metrics": (("region", "nat_gateway_id"), _get_nat_metrics),
    "huawei_list_evs": (("region",), _list_evs),
    "huawei_get_evs_metrics": (("region", "volume_id", "instance_id"), _get_evs_metrics),
    "huawei_list_sfs": (("region",), _list_sfs),
    "huawei_list_sfs_turbo": (("region",), _list_sfs_turbo),
    "huawei_list_elb": (("region",), _list_elb),
    "huawei_list_elb_listeners": (("region",), _list_elb_listeners),
    "huawei_get_elb_metrics": (("region", "elb_id"), _get_elb_metrics),
    "huawei_list_supported_regions": ((), lambda params: identity.list_supported_regions()),
    "huawei_list_projects": ((), _list_projects),
    "huawei_get_project_by_region": (("region",), _get_project_by_region),
    "huawei_list_cce_clusters": (("region",), _list_cce_clusters),
    "huawei_delete_cce_cluster": (("region", "cluster_id"), _delete_cce_cluster),
    "huawei_list_cce_nodes": (("region", "cluster_id"), _list_cce_nodes),
    "huawei_get_cce_nodes": (("region", "cluster_id"), _get_cce_nodes),
    "huawei_delete_cce_node": (("region", "cluster_id", "node_id"), _delete_cce_node),
    "huawei_list_cce_nodepools": (("region", "cluster_id"), _list_cce_nodepools),
    "huawei_get_cce_kubeconfig": (("region", "cluster_id"), _get_cce_kubeconfig),
    "huawei_list_cce_addons": (("region", "cluster_id"), _list_cce_addons),
    "huawei_get_cce_addon_detail": (("region", "cluster_id", "addon_name"), _get_cce_addon_detail),
    "huawei_resize_cce_nodepool": (("region", "cluster_id", "nodepool_id", "node_count"), _resize_cce_nodepool),
    "huawei_get_cce_pods": (("region", "cluster_id"), _get_cce_pods),
    "huawei_get_pod_logs": (("region", "cluster_id", "pod_name"), _get_pod_logs),
    "huawei_get_cce_namespaces": (("region", "cluster_id"), _get_cce_namespaces),
    "huawei_get_cce_deployments": (("region", "cluster_id"), _get_cce_deployments),
    "huawei_scale_cce_workload": (("region", "cluster_id", "workload_type", "name", "namespace", "replicas"), _scale_cce_workload),
    "huawei_resize_cce_workload": (("region", "cluster_id", "workload_type", "name", "namespace"), _resize_cce_workload),
    "huawei_delete_cce_workload": (("region", "cluster_id", "workload_type", "name", "namespace"), _delete_cce_workload),
    "huawei_get_kubernetes_nodes": (("region", "cluster_id"), _get_kubernetes_nodes),
    "huawei_get_cce_events": (("region", "cluster_id"), _get_cce_events),
    "huawei_get_cce_pvcs": (("region", "cluster_id"), _get_cce_pvcs),
    "huawei_get_cce_pvs": (("region", "cluster_id"), _get_cce_pvs),
    "huawei_get_cce_services": (("region", "cluster_id"), _get_cce_services),
    "huawei_get_cce_ingresses": (("region", "cluster_id"), _get_cce_ingresses),
    "huawei_list_cce_configmaps": (("region", "cluster_id"), _list_cce_configmaps),
    "huawei_list_cce_secrets": (("region", "cluster_id"), _list_cce_secrets),
    "huawei_list_cce_daemonsets": (("region", "cluster_id"), _list_cce_daemonsets),
    "huawei_list_cce_statefulsets": (("region", "cluster_id"), _list_cce_statefulsets),
    "huawei_list_cce_cronjobs": (("region", "cluster_id"), _list_cce_cronjobs),
    "huawei_list_aom_instances": (("region",), _list_aom_instances),
    "huawei_get_aom_metrics": (("region", "aom_instance_id", "query"), _get_aom_metrics),
    "huawei_list_aom_alerts": (("region",), _list_aom_alerts),
    "huawei_list_aom_alarm_rules": (("region",), _list_aom_alarm_rules),
    "huawei_list_aom_action_rules": (("region",), _list_aom_action_rules),
    "huawei_list_aom_mute_rules": (("region",), _list_aom_mute_rules),
    "huawei_list_aom_current_alarms": (("region",), _list_aom_current_alarms),
    "huawei_list_aom_alarms": (("region",), _list_aom_alarms),
    "huawei_list_log_groups": (("region",), _list_log_groups),
    "huawei_list_log_streams": (("region",), _list_log_streams),
    "huawei_query_logs": (("region", "log_group_id", "log_stream_id"), _query_logs),
    "huawei_get_recent_logs": (("region", "log_group_id", "log_stream_id"), _get_recent_logs),
    "huawei_query_aom_logs": (("region", "cluster_id"), _query_aom_logs),
    "huawei_cce_cluster_inspection": (("region", "cluster_id"), lambda params: cce_inspection.cce_cluster_inspection(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))),
    "huawei_cce_cluster_inspection_parallel": (("region", "cluster_id"), lambda params: cce_inspection.cce_cluster_inspection_parallel(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), int(params.get("max_workers", 4)))),
    "huawei_cce_cluster_inspection_subagent": (("region", "cluster_id"), lambda params: cce_inspection.generate_auto_subagent_info(params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"))),
    "huawei_aggregate_inspection_results": (("results", "cluster_info"), _aggregate_results_action),
    "huawei_export_inspection_report": (("region", "cluster_id"), lambda params: cce_inspection.export_inspection_report(params["region"], params["cluster_id"], params.get("output_file", f"/tmp/cce_inspection_report_{params['cluster_id'][:8]}.html"), params.get("ak"), params.get("sk"))),
    "huawei_pod_status_inspection": (("region", "cluster_id"), lambda params: _inspection_check_action(cce_inspection.pod_status_inspection, params)),
    "huawei_addon_pod_monitoring_inspection": (("region", "cluster_id"), _addon_pod_inspection_action),
    "huawei_biz_pod_monitoring_inspection": (("region", "cluster_id"), _biz_pod_inspection_action),
    "huawei_node_status_inspection": (("region", "cluster_id"), lambda params: _inspection_check_action(cce_inspection.node_status_inspection, params)),
    "huawei_node_resource_inspection": (("region", "cluster_id"), _node_resource_inspection_action),
    "huawei_node_vul_inspection": (("region", "cluster_id"), lambda params: _inspection_check_action(cce_inspection.node_vul_inspection, params)),
    "huawei_event_inspection": (("region", "cluster_id"), lambda params: _inspection_check_action(cce_inspection.event_inspection, params)),
    "huawei_aom_alarm_inspection": (("region", "cluster_id"), _aom_alarm_inspection_action),
    "huawei_elb_monitoring_inspection": (("region", "cluster_id"), _elb_monitoring_inspection_action),
    "huawei_get_cce_logconfigs": (("region", "cluster_id"), lambda params: _cce_app_logs_mod.get_cce_logconfigs_action(params)),
    "huawei_get_application_log_stream": (("region", "cluster_id", "app_name"), lambda params: _cce_app_logs_mod.get_application_log_stream_action(params)),
    "huawei_query_application_logs": (("region", "cluster_id", "app_name"), lambda params: _cce_app_logs_mod.query_application_logs_action(params)),
    "huawei_query_application_recent_logs": (("region", "cluster_id", "app_name"), lambda params: _cce_app_logs_mod.query_application_recent_logs_action(params)),
    "huawei_get_cce_pod_metrics_topN": (("region", "cluster_id"), lambda params: _metric_action(cce_metrics.get_cce_pod_metrics_topN, params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"), params.get("label_selector"), _to_int(params.get("top_n"), 10), _to_int(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"), params.get("node_ip"))),
    "huawei_get_cce_pod_metrics": (("region", "cluster_id", "pod_name"), lambda params: _metric_action(cce_metrics.get_cce_pod_metrics, params["region"], params["cluster_id"], params["pod_name"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("namespace"), _to_int(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"))),
    "huawei_get_cce_node_metrics_topN": (("region", "cluster_id"), lambda params: _metric_action(cce_metrics.get_cce_node_metrics_topN, params["region"], params["cluster_id"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("top_n"), 10), _to_int(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"), params.get("disk_query"))),
    "huawei_get_cce_node_metrics": (("region", "cluster_id", "node_ip"), lambda params: _metric_action(cce_metrics.get_cce_node_metrics, params["region"], params["cluster_id"], params["node_ip"], params.get("ak"), params.get("sk"), params.get("project_id"), _to_int(params.get("hours"), 1), params.get("cpu_query"), params.get("memory_query"), params.get("disk_query"))),
    "huawei_network_diagnose": (("region", "cluster_id"), _network_diagnose_action),
    "huawei_network_diagnose_by_alarm": (("region", "cluster_id", "alarm_info"), _network_diagnose_by_alarm_action),
    "huawei_workload_diagnose": (("region", "cluster_id"), _workload_diagnose_action),
    "huawei_workload_diagnose_by_alarm": (("region", "cluster_id", "alarm_info"), _workload_diagnose_by_alarm_action),
    "huawei_hibernate_cce_cluster": (("region", "cluster_id"), _hibernate_cce_cluster_action),
    "huawei_awake_cce_cluster": (("region", "cluster_id"), _awake_cce_cluster_action),

    "huawei_network_verify_pod_scheduling": (("region", "cluster_id", "workload_name"), _network_verify_pod_scheduling_action),
    "huawei_node_batch_diagnose": (("region", "cluster_id"), _node_batch_diagnose_action),
    "huawei_node_diagnose": (("region", "cluster_id"), _node_diagnose_action),

    # HSS vulnerability management
    "huawei_hss_list_hosts": (("region",), _hss_list_vul_host_hosts),
    "huawei_hss_list_host_vuls_all": (("region", "host_id"), _hss_list_host_vuls_all),
    "huawei_hss_change_vul_status": (("region",), _hss_change_vul_status),

    # CCE node operations
    "huawei_cce_node_cordon": (("region", "cluster_id", "node_name"), _cce_node_cordon),
    "huawei_cce_node_uncordon": (("region", "cluster_id", "node_name"), _cce_node_uncordon),
    "huawei_cce_node_drain": (("region", "cluster_id", "node_name"), _cce_node_drain),
    "huawei_cce_node_status": (("region", "cluster_id", "node_name"), _cce_node_status),

    # ECS operations
    "huawei_reboot_ecs": (("region", "instance_id"), _reboot_ecs),

    # CCE EIP operations
    "huawei_bind_cce_cluster_eip": (("region", "cluster_id", "eip_id"), _bind_cce_cluster_eip),
    "huawei_unbind_cce_cluster_eip": (("region", "cluster_id"), _unbind_cce_cluster_eip),

    # Monitor dashboard generation
    "huawei_generate_monitor_dashboard": (("region", "cluster_id"), _generate_monitor_dashboard),

    # Diagnosis report generation
    "huawei_generate_diagnosis_report": (("region", "cluster_id", "workload_name"), _generate_diagnosis_report),

    # Alarm filtering & analysis
    "huawei_analyze_aom_alarms": (("region",), _analyze_aom_alarms),

    # ===== Auto Inspection (Quick Check + Deep Diagnosis) =====
    "huawei_cce_quick_check": (("region", "cluster_id"), _cce_quick_check_action),
    "huawei_cce_deep_diagnosis": (("region", "cluster_id"), _cce_deep_diagnosis_action),
    "huawei_cce_auto_inspection": (("region", "cluster_id"), _cce_auto_inspection_action),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    if error:
        return {"success": False, "error": error}
    return handler(params)
