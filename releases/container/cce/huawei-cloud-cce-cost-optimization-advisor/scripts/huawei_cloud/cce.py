"""CCE and Kubernetes read helpers for autoscaling diagnosis.

Cloud resources use hcloud. Kubernetes resources use kubectl cce and never create a
kubeconfig or invoke the Kubernetes Python client.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional

from . import common


def _hcloud(region: str, operation: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str] = None, **params: str) -> Dict[str, Any]:
    command = common._hcloud_command(region, operation, ak, sk, project_id, security_token, *[f"--{key}={value}" for key, value in params.items() if value is not None])
    return common._run_hcloud_json(command)


def _kubectl(region: str, cluster_id: str, arguments: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
    command = ["kubectl", "cce", "--cluster-id", cluster_id, "--region", region, "--cce-insecure-upstream-tls=true"]
    if project_id:
        command.extend(["--cli-project-id", project_id])
    if ak:
        command.extend(["--cli-access-key", ak])
    if sk:
        command.extend(["--cli-secret-key", sk])
    if security_token:
        command.extend(["--cli-security-token", security_token])
    command.extend(arguments)
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=75, check=False)
    except FileNotFoundError:
        return {"success": False, "error": "kubectl cce is required but was not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "kubectl cce request timed out"}
    if completed.returncode:
        return {"success": False, "error": (completed.stderr or completed.stdout or "kubectl cce request failed").strip()[:500]}
    if not expect_json:
        return {"success": True, "output": completed.stdout}
    try:
        return {"success": True, "data": json.loads(completed.stdout)}
    except json.JSONDecodeError:
        return {"success": False, "error": "kubectl cce returned an invalid JSON response"}


def _namespace_error(namespace: Optional[str]) -> Optional[Dict[str, Any]]:
    if namespace:
        return None
    return {"success": False, "error": "namespace is required for Kubernetes resource queries; whole-cluster collection is not supported"}


def _items(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    return ((result.get("data") or {}).get("items") or []) if result.get("success") else []


def list_cce_clusters(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, offset: int = 0, security_token: Optional[str] = None) -> Dict[str, Any]:
    result = _hcloud(region, "ListClusters", ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    clusters = []
    for item in _items(result):
        metadata, spec, status = item.get("metadata") or {}, item.get("spec") or {}, item.get("status") or {}
        clusters.append({"id": metadata.get("uid"), "name": metadata.get("name"), "status": status.get("phase", "Unknown"), "type": spec.get("type"), "version": spec.get("version")})
    return {"success": True, "source": "hcloud", "region": region, "count": len(clusters), "clusters": clusters[offset:offset + limit]}


def list_cce_node_pools(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, offset: int = 0, security_token: Optional[str] = None) -> Dict[str, Any]:
    result = _hcloud(region, "ListNodePools", ak, sk, project_id, security_token, cluster_id=cluster_id)
    if not result.get("success"):
        return result
    pools = []
    for item in _items(result):
        metadata, spec, status = item.get("metadata") or {}, item.get("spec") or {}, item.get("status") or {}
        scaling = spec.get("autoscaling") or spec.get("scaling") or {}
        pools.append({"id": metadata.get("uid"), "name": metadata.get("name"), "status": status.get("phase"), "min_node_count": scaling.get("minNodeCount", scaling.get("min_node_count")), "max_node_count": scaling.get("maxNodeCount", scaling.get("max_node_count")), "current_node_count": status.get("currentNode", status.get("currentNodeCount", status.get("current_node_count"))), "autoscaling_enabled": bool(scaling.get("enable") or scaling.get("enabled"))})
    return {"success": True, "source": "hcloud", "region": region, "cluster_id": cluster_id, "count": len(pools), "nodepools": pools[offset:offset + limit]}


def list_cce_addons(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    result = _hcloud(region, "ListAddonInstances", ak, sk, project_id, security_token, cluster_id=cluster_id)
    if not result.get("success"):
        return result
    addons = []
    for item in _items(result):
        metadata, spec, status = item.get("metadata") or {}, item.get("spec") or {}, item.get("status") or {}
        addons.append({"id": metadata.get("uid"), "name": metadata.get("name") or spec.get("name"), "template_name": spec.get("templateName") or spec.get("template_name"), "version": spec.get("version"), "status": status.get("phase") or status.get("status"), "description": spec.get("description")})
    return {"success": True, "source": "hcloud", "region": region, "cluster_id": cluster_id, "count": len(addons), "addons": addons}


def get_cce_addon_detail(region: str, cluster_id: str, addon_name: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    listed = list_cce_addons(region, cluster_id, ak, sk, project_id, security_token)
    if not listed.get("success"):
        return listed
    matches = [item for item in listed["addons"] if addon_name in {item.get("id"), item.get("name")}]
    if len(matches) != 1:
        return {"success": False, "error": f"addon '{addon_name}' was not found uniquely in cluster {cluster_id}"}
    result = _hcloud(region, "ShowAddonInstance", ak, sk, project_id, security_token, id=matches[0]["id"], cluster_id=cluster_id)
    if not result.get("success"):
        return result
    return {"success": True, "source": "hcloud", "region": region, "cluster_id": cluster_id, "addon": result.get("data")}


def get_prom_instance_id(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """Read the CCE cie-collector configuration through hcloud to locate AOM Prometheus."""
    detail = get_cce_addon_detail(region, cluster_id, "cie-collector", ak, sk, project_id, security_token)
    if not detail.get("success"):
        return detail
    root = detail.get("addon") or {}
    spec = root.get("spec") or {}
    for candidate in (spec.get("custom"), spec.get("values"), (spec.get("values") or {}).get("custom")):
        if isinstance(candidate, dict) and candidate.get("aom_instance_id"):
            return {"success": True, "aom_instance_id": candidate["aom_instance_id"], "source": "hcloud CCE ShowAddonInstance"}
    return {"success": False, "error": "cie-collector does not contain aom_instance_id"}


def list_aom_prom_instances(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """List CCE-backed AOM Prometheus instances through hcloud."""
    command = [
        "hcloud", "AOM", "ListPromInstance", f"--cli-region={region}", "--cli-output=json",
        "--cli-connect-timeout=10", "--cli-read-timeout=60",
        *common._credential_args(ak, sk, project_id, security_token),
        "--Enterprise-Project-Id=all_granted_eps", "--cce_cluster_enable=true",
    ]
    result = common._run_hcloud_json(command)
    if not result.get("success"):
        return result
    instances = [
        {
            "id": item.get("prom_id"),
            "name": item.get("prom_name"),
            "enterprise_project_id": item.get("enterprise_project_id"),
        }
        for item in (result.get("data") or {}).get("prometheus", [])
        if item.get("prom_id") and item.get("prom_type") == "CCE"
    ]
    return {"success": True, "source": "hcloud AOM ListPromInstance", "instances": instances}


def _pod(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata, spec, status = item.get("metadata") or {}, item.get("spec") or {}, item.get("status") or {}
    states = {row.get("name"): row for row in status.get("containerStatuses") or []}
    containers = []
    for container in spec.get("containers") or []:
        state = states.get(container.get("name"), {})
        containers.append({"name": container.get("name"), "resources": container.get("resources") or {}, "ready": state.get("ready"), "state": state.get("state") or {}})
    owners = metadata.get("ownerReferences") or []
    owner = owners[0] if owners else {}
    return {"name": metadata.get("name"), "namespace": metadata.get("namespace"), "labels": metadata.get("labels") or {}, "phase": status.get("phase"), "status": status.get("phase"), "node_name": spec.get("nodeName"), "owner_kind": owner.get("kind"), "owner_name": owner.get("name"), "containers": containers}


def get_kubernetes_pods(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: Optional[str] = None, labels: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    if error := _namespace_error(namespace):
        return error
    args = ["get", "pods", "-n", namespace, "-o", "json"]
    if labels:
        args.extend(["-l", labels])
    result = _kubectl(region, cluster_id, args, ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    pods = [_pod(item) for item in _items(result)]
    return {"success": True, "source": "kubectl-cce", "region": region, "cluster_id": cluster_id, "namespace": namespace, "count": len(pods), "pods": pods}


def _workloads(region: str, cluster_id: str, resource: str, key: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str], namespace: Optional[str], security_token: Optional[str] = None) -> Dict[str, Any]:
    if error := _namespace_error(namespace):
        return error
    result = _kubectl(region, cluster_id, ["get", resource, "-n", namespace, "-o", "json"], ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    rows = []
    for item in _items(result):
        metadata, spec, status = item.get("metadata") or {}, item.get("spec") or {}, item.get("status") or {}
        rows.append({"name": metadata.get("name"), "namespace": metadata.get("namespace"), "labels": metadata.get("labels") or {}, "replicas": spec.get("replicas"), "desired_replicas": spec.get("replicas"), "current_replicas": status.get("replicas"), "ready_replicas": status.get("readyReplicas"), "selector": (spec.get("selector") or {}).get("matchLabels") or {}})
    return {"success": True, "source": "kubectl-cce", "region": region, "cluster_id": cluster_id, "namespace": namespace, "count": len(rows), key: rows}


def get_kubernetes_deployments(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    return _workloads(region, cluster_id, "deployments", "deployments", ak, sk, project_id, namespace, security_token)


def list_cce_statefulsets(region: str, cluster_id: str, namespace: Optional[str] = None, limit: int = 100, include_data: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    result = _workloads(region, cluster_id, "statefulsets", "statefulsets", ak, sk, project_id, namespace, security_token)
    if result.get("success"):
        result["statefulsets"] = result["statefulsets"][:limit]
    return result


def get_kubernetes_events(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: Optional[str] = None, limit: int = 500, security_token: Optional[str] = None) -> Dict[str, Any]:
    if error := _namespace_error(namespace):
        return error
    result = _kubectl(region, cluster_id, ["get", "events", "-n", namespace, "-o", "json"], ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    events = []
    for item in _items(result)[:limit]:
        metadata, involved, source = item.get("metadata") or {}, item.get("involvedObject") or {}, item.get("source") or {}
        events.append({"name": metadata.get("name"), "namespace": metadata.get("namespace"), "reason": item.get("reason"), "message": item.get("message"), "type": item.get("type"), "count": item.get("count"), "involved_object": involved, "source": source, "last_timestamp": item.get("lastTimestamp") or item.get("eventTime")})
    return {"success": True, "source": "kubectl-cce", "region": region, "cluster_id": cluster_id, "namespace": namespace, "count": len(events), "events": events}


def get_kubernetes_nodes(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, node_name: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    args = ["get", "node"] + ([node_name] if node_name else []) + ["-o", "json"]
    result = _kubectl(region, cluster_id, args, ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    raw = result.get("data") or {}
    items = raw.get("items") or ([raw] if raw.get("metadata") else [])
    nodes = [{"name": (item.get("metadata") or {}).get("name"), "labels": (item.get("metadata") or {}).get("labels") or {}, "conditions": (item.get("status") or {}).get("conditions") or []} for item in items]
    return {"success": True, "source": "kubectl-cce", "region": region, "cluster_id": cluster_id, "count": len(nodes), "nodes": nodes}


def get_pod_logs(region: str, cluster_id: str, pod_name: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: Optional[str] = None, container: Optional[str] = None, previous: bool = False, tail_lines: int = 200, security_token: Optional[str] = None) -> Dict[str, Any]:
    if error := _namespace_error(namespace):
        return error
    args = ["logs", pod_name, "-n", namespace, f"--tail={tail_lines}"]
    if container:
        args.extend(["-c", container])
    if previous:
        args.append("--previous")
    result = _kubectl(region, cluster_id, args, ak, sk, project_id, security_token, expect_json=False)
    return {"success": True, "source": "kubectl-cce", "logs": result.get("output", "")} if result.get("success") else result
