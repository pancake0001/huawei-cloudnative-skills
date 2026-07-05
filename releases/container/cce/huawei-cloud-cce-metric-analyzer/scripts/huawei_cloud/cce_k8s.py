"""Minimal CCE Kubernetes helpers used by metric aggregation."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, Optional

from .common import (
    K8S_AVAILABLE,
    K8S_IMPORT_ERROR,
    _register_cert_file,
    _safe_delete_file,
    get_credentials,
    k8s_client,
    run_hcloud,
)


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


def get_cce_services(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
) -> Dict[str, Any]:
    """List Kubernetes Services in a CCE cluster."""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided. Set HUAWEI_AK/HUAWEI_SK or configure hcloud."}
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if not K8S_AVAILABLE:
        return {"success": False, "error": f"Kubernetes SDK not installed: {K8S_IMPORT_ERROR}"}

    cert_file = None
    key_file = None
    try:
        _, cert_file, key_file = _setup_k8s_client(region, cluster_id, access_key, secret_key, proj_id, "services")
        v1 = k8s_client.CoreV1Api()
        if namespace:
            services = v1.list_namespaced_service(namespace)
        else:
            services = v1.list_service_for_all_namespaces()

        service_list = []
        for svc in services.items:
            ingress = getattr(getattr(svc.status, "load_balancer", None), "ingress", None) or []
            service_list.append({
                "name": svc.metadata.name,
                "namespace": svc.metadata.namespace,
                "type": svc.spec.type,
                "cluster_ip": svc.spec.cluster_ip,
                "external_ips": svc.spec.external_i_ps or [],
                "load_balancer_ip": svc.spec.load_balancer_ip,
                "load_balancer_ingress": [
                    {"ip": getattr(item, "ip", None), "hostname": getattr(item, "hostname", None)}
                    for item in ingress
                ],
            })

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "get_cce_services",
            "namespace": namespace or "all",
            "count": len(service_list),
            "services": service_list,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
    finally:
        _safe_delete_file(cert_file)
        _safe_delete_file(key_file)
