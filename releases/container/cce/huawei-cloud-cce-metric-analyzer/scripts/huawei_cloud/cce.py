"""Minimal CCE helpers required by metric queries."""

from __future__ import annotations

import base64
import os
import ssl
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .common import (
    K8S_AVAILABLE,
    K8S_IMPORT_ERROR,
    _register_cert_file,
    _safe_delete_file,
    get_credentials,
    k8s_client,
    run_hcloud,
)


def list_cce_clusters(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """List CCE clusters via hcloud."""
    result = run_hcloud(
        "CCE",
        "ListClusters",
        region,
        {"project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    clusters = []
    for cluster in (result.get("data") or {}).get("items", []) or []:
        metadata = cluster.get("metadata") or {}
        spec = cluster.get("spec") or {}
        status = cluster.get("status") or {}
        network = spec.get("network") or {}
        item = {
            "id": metadata.get("uid"),
            "name": metadata.get("name"),
            "status": status.get("phase", "Unknown"),
            "type": spec.get("type", "Unknown"),
            "version": spec.get("version", "Unknown"),
            "created_at": metadata.get("creationTimestamp") or metadata.get("creation_timestamp"),
        }
        if network:
            item["network"] = {
                "vpc_id": network.get("vpc") or network.get("vpc_id"),
                "subnet_id": network.get("subnet") or network.get("subnet_id"),
            }
        clusters.append(item)

    return {
        "success": True,
        "region": region,
        "action": "list_cce_clusters",
        "source": "hcloud",
        "count": len(clusters),
        "clusters": clusters[offset:offset + limit],
    }


def list_cce_cluster_nodes(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """List CCE cluster nodes via hcloud."""
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    result = run_hcloud(
        "CCE",
        "ListNodes",
        region,
        {"cluster_id": cluster_id, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    nodes = []
    for node in (result.get("data") or {}).get("items", []) or []:
        metadata = node.get("metadata") or {}
        spec = node.get("spec") or {}
        status = node.get("status") or {}
        nodes.append({
            "id": metadata.get("uid"),
            "name": metadata.get("name"),
            "status": status.get("phase", "Unknown"),
            "flavor": spec.get("flavor"),
            "availability_zone": spec.get("az"),
        })

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "list_cce_cluster_nodes",
        "source": "hcloud",
        "count": len(nodes),
        "nodes": nodes[offset:offset + limit],
    }


def _setup_k8s_client(region: str, cluster_id: str, access_key: str, secret_key: str, proj_id: str, cert_prefix: str):
    result = run_hcloud(
        "CCE",
        "CreateKubernetesClusterCert",
        region,
        {"cluster_id": cluster_id, "duration": 1, "project_id": proj_id},
        ak=access_key,
        sk=secret_key,
        project_id=proj_id,
    )
    if not result.get("success"):
        raise RuntimeError(result.get("error", "failed to create Kubernetes cluster certificate"))
    kubeconfig_data = result.get("data") or {}

    external_cluster = None
    for cluster in kubeconfig_data.get("clusters", []):
        name = cluster.get("name", "")
        if "external" in name and "TLS" not in name:
            external_cluster = cluster
            break
    external_cluster = external_cluster or (kubeconfig_data.get("clusters") or [{}])[0]
    server = external_cluster.get("cluster", {}).get("server")
    if not server:
        raise RuntimeError("Could not find cluster endpoint")

    configuration = k8s_client.Configuration()
    configuration.host = server
    configuration.verify_ssl = False

    user_data = {}
    for user in kubeconfig_data.get("users", []):
        if user.get("name") == "user":
            user_data = user.get("user", {})
            break

    cert_file = None
    key_file = None
    if user_data.get("client_certificate_data"):
        cert_file = f"/tmp/cce_{cert_prefix}_client_{os.getpid()}.crt"
        with open(cert_file, "wb") as cert_handle:
            cert_handle.write(base64.b64decode(user_data["client_certificate_data"]))
        configuration.cert_file = cert_file
        _register_cert_file(cert_file)

    if user_data.get("client_key_data"):
        key_file = f"/tmp/cce_{cert_prefix}_client_{os.getpid()}.key"
        with open(key_file, "wb") as key_handle:
            key_handle.write(base64.b64decode(user_data["client_key_data"]))
        configuration.key_file = key_file
        _register_cert_file(key_file)

    k8s_client.Configuration.set_default(configuration)
    return configuration, cert_file, key_file


def _k8s_preflight(cluster_id: str, access_key: Optional[str], secret_key: Optional[str]) -> Optional[Dict[str, Any]]:
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided. Set HUAWEI_AK/HUAWEI_SK for Kubernetes API details."}
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if not K8S_AVAILABLE:
        return {"success": False, "error": f"Kubernetes SDK not installed: {K8S_IMPORT_ERROR}"}
    return None


def get_kubernetes_pods(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    labels: Optional[str] = None,
) -> Dict[str, Any]:
    """List Kubernetes pods for optional label-based metric filtering."""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    error = _k8s_preflight(cluster_id, access_key, secret_key)
    if error:
        return error

    cert_file = None
    key_file = None
    try:
        _, cert_file, key_file = _setup_k8s_client(region, cluster_id, access_key, secret_key, proj_id, "pods")
        v1 = k8s_client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace, label_selector=labels) if namespace else v1.list_pod_for_all_namespaces(label_selector=labels)

        pod_list = []
        for pod in pods.items:
            pod_list.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip,
                "created": str(pod.metadata.creation_timestamp) if pod.metadata.creation_timestamp else None,
                "labels": pod.metadata.labels or {},
            })

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "get_kubernetes_pods",
            "namespace": namespace or "all",
            "count": len(pod_list),
            "pods": pod_list,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
    finally:
        _safe_delete_file(cert_file)
        _safe_delete_file(key_file)


def _node_addresses(node: Any) -> Dict[str, Optional[str]]:
    result = {"internal_ip": None, "external_ip": None}
    for address in getattr(getattr(node, "status", None), "addresses", None) or []:
        if address.type == "InternalIP":
            result["internal_ip"] = address.address
        elif address.type == "ExternalIP":
            result["external_ip"] = address.address
    return result


def get_kubernetes_nodes(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """List Kubernetes nodes for node metric enrichment."""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    error = _k8s_preflight(cluster_id, access_key, secret_key)
    if error:
        return error

    cert_file = None
    key_file = None
    try:
        _, cert_file, key_file = _setup_k8s_client(region, cluster_id, access_key, secret_key, proj_id, "nodes")
        v1 = k8s_client.CoreV1Api()
        nodes = v1.list_node()

        node_list: List[Dict[str, Any]] = []
        for node in nodes.items:
            addresses = _node_addresses(node)
            conditions = {
                condition.type: condition.status
                for condition in (getattr(node.status, "conditions", None) or [])
            }
            node_list.append({
                "name": node.metadata.name,
                "ip": addresses.get("internal_ip") or node.metadata.name,
                "internal_ip": addresses.get("internal_ip"),
                "external_ip": addresses.get("external_ip"),
                "status": "Ready" if conditions.get("Ready") == "True" else "NotReady",
                "kubelet_version": getattr(getattr(node.status, "node_info", None), "kubelet_version", ""),
                "os": getattr(getattr(node.status, "node_info", None), "os_image", ""),
                "container_runtime": getattr(getattr(node.status, "node_info", None), "container_runtime_version", ""),
                "labels": node.metadata.labels or {},
            })

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "get_kubernetes_nodes",
            "count": len(node_list),
            "nodes": node_list,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
    finally:
        _safe_delete_file(cert_file)
        _safe_delete_file(key_file)


def _decode_tls_certificate(pem_data: bytes) -> Dict[str, Any]:
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as handle:
            temp_file = handle.name
            handle.write(pem_data)

        cert = ssl._ssl._test_decode_cert(temp_file)
        not_after_raw = cert.get("notAfter")
        expires_at = None
        days_remaining = None
        if not_after_raw:
            expires_at = datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds() // 86400)

        def _flatten_name(items):
            values = []
            for item in items or []:
                for key, value in item:
                    values.append(f"{key}={value}")
            return ", ".join(values)

        return {
            "not_after": expires_at.isoformat() if expires_at else None,
            "days_remaining": days_remaining,
            "subject": _flatten_name(cert.get("subject")),
            "issuer": _flatten_name(cert.get("issuer")),
            "serial_number": cert.get("serialNumber"),
        }
    finally:
        _safe_delete_file(temp_file)


def get_ingress_tls_certificates(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    warning_days: int = 30,
) -> Dict[str, Any]:
    """List Ingress TLS certificates and calculate expiration status."""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    error = _k8s_preflight(cluster_id, access_key, secret_key)
    if error:
        return error

    cert_file = None
    key_file = None
    try:
        _, cert_file, key_file = _setup_k8s_client(region, cluster_id, access_key, secret_key, proj_id, "ingress_tls")
        networking_v1 = k8s_client.NetworkingV1Api()
        core_v1 = k8s_client.CoreV1Api()
        ingresses = (
            networking_v1.list_namespaced_ingress(namespace)
            if namespace
            else networking_v1.list_ingress_for_all_namespaces()
        )

        secret_hosts: Dict[tuple[str, str], set[str]] = {}
        for ingress in ingresses.items:
            ingress_namespace = ingress.metadata.namespace
            for tls in getattr(ingress.spec, "tls", None) or []:
                if not tls.secret_name:
                    continue
                key = (ingress_namespace, tls.secret_name)
                secret_hosts.setdefault(key, set()).update(tls.hosts or [])

        certificates: List[Dict[str, Any]] = []
        expired_count = 0
        expiring_soon_count = 0
        for (secret_namespace, secret_name), hosts in sorted(secret_hosts.items()):
            item = {
                "namespace": secret_namespace,
                "secret_name": secret_name,
                "hosts": sorted(hosts),
                "status": "unknown",
            }
            try:
                secret = core_v1.read_namespaced_secret(secret_name, secret_namespace)
                crt_b64 = (secret.data or {}).get("tls.crt")
                if not crt_b64:
                    item["error"] = "tls.crt not found in secret"
                else:
                    cert_info = _decode_tls_certificate(base64.b64decode(crt_b64))
                    item.update(cert_info)
                    days_remaining = cert_info.get("days_remaining")
                    if days_remaining is None:
                        item["status"] = "unknown"
                    elif days_remaining < 0:
                        item["status"] = "expired"
                        expired_count += 1
                    elif days_remaining <= warning_days:
                        item["status"] = "expiring_soon"
                        expiring_soon_count += 1
                    else:
                        item["status"] = "valid"
            except Exception as exc:
                item["error"] = str(exc)
                item["error_type"] = type(exc).__name__
            certificates.append(item)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "get_ingress_tls_certificates",
            "namespace": namespace or "all",
            "warning_days": warning_days,
            "total_tls_secrets": len(certificates),
            "expired_count": expired_count,
            "expiring_soon_count": expiring_soon_count,
            "certificates": certificates,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
    finally:
        _safe_delete_file(cert_file)
        _safe_delete_file(key_file)
