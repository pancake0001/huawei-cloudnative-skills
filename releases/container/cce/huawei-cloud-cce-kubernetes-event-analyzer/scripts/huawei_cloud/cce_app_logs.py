"""Read CCE Event-to-LTS LogConfig custom resources."""

from __future__ import annotations

import base64
import tempfile
from typing import Any, Dict, List, Tuple

from .common import (
    _register_cert_file,
    _safe_delete_file,
    create_cce_client,
    get_credentials_with_region,
    k8s_client,
)


def _logconfig_cr_combinations() -> List[Tuple[str, str, str]]:
    return [
        ("logging.openvessel.io", "v1", "logconfigs"),
        ("lts.opentelekomcloud.com", "v1", "logconfigs"),
        ("lts.huaweicloud.com", "v1", "logconfigs"),
        ("lts.io", "v1", "logconfigs"),
        ("logging.huaweicloud.com", "v1", "logconfigs"),
        ("lts.opentelekomcloud.com", "v1alpha1", "logconfigs"),
        ("lts.opentelekomcloud.com", "v1beta1", "logconfigs"),
    ]


def _get_cce_custom_objects_api(params: Dict[str, str]) -> tuple[Any, List[str]]:
    if k8s_client is None:
        raise RuntimeError("Kubernetes SDK is required to discover CCE LogConfig resources")

    region = params["region"]
    cluster_id = params["cluster_id"]
    ak, sk, project_id = get_credentials_with_region(region, params.get("ak"), params.get("sk"), params.get("project_id"))
    if not ak or not sk:
        raise RuntimeError("credentials are required to discover CCE LogConfig resources")

    from huaweicloudsdkcce.v3.model.cluster_cert_duration import ClusterCertDuration
    from huaweicloudsdkcce.v3.model.create_kubernetes_cluster_cert_request import CreateKubernetesClusterCertRequest

    request = CreateKubernetesClusterCertRequest(cluster_id=cluster_id, body=ClusterCertDuration(duration=1))
    kubeconfig = create_cce_client(region, ak, sk, project_id).create_kubernetes_cluster_cert(request).to_dict()
    cluster = next((item for item in kubeconfig.get("clusters", []) if "external" in item.get("name", "") and "TLS" not in item.get("name", "")), None)
    cluster = cluster or next(iter(kubeconfig.get("clusters", [])), None)
    if not cluster:
        raise RuntimeError("CreateKubernetesClusterCert returned no cluster endpoint")

    user = next((item.get("user", {}) for item in kubeconfig.get("users", []) if item.get("name") == "user"), {})
    configuration = k8s_client.Configuration()
    configuration.host = (cluster.get("cluster") or {}).get("server")
    configuration.verify_ssl = False
    temp_files: List[str] = []
    for source_key, target_key, suffix in (
        ("client_certificate_data", "cert_file", ".crt"),
        ("client_key_data", "key_file", ".key"),
    ):
        encoded = user.get(source_key)
        if not encoded:
            continue
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=suffix) as handle:
            handle.write(base64.b64decode(encoded))
            path = handle.name
        setattr(configuration, target_key, path)
        temp_files.append(path)
        _register_cert_file(path)

    k8s_client.Configuration.set_default(configuration)
    return k8s_client.CustomObjectsApi(), temp_files


def get_cce_logconfigs_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Return LogConfig resources needed to locate CCE Event LTS streams."""
    namespace = params.get("namespace")
    temp_files: List[str] = []
    try:
        custom_api, temp_files = _get_cce_custom_objects_api(params)
        logconfigs: List[Dict[str, Any]] = []
        tried: List[str] = []
        for group, version, plural in _logconfig_cr_combinations():
            tried.append(f"{group}/{version}/{plural}")
            try:
                response = (
                    custom_api.list_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural)
                    if namespace
                    else custom_api.list_cluster_custom_object(group=group, version=version, plural=plural)
                )
            except Exception:
                continue
            for item in response.get("items", []):
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                input_detail = spec.get("inputDetail", {})
                output_detail = spec.get("outputDetail", {})
                logconfigs.append(
                    {
                        "name": metadata.get("name"),
                        "namespace": metadata.get("namespace"),
                        "input_type": input_detail.get("type"),
                        "output_type": output_detail.get("type"),
                        "spec": spec,
                        "status": item.get("status", {}),
                        "api_version": f"{group}/{version}",
                    }
                )
            if logconfigs:
                break
        return {
            "success": True,
            "cluster_id": params["cluster_id"],
            "namespace": namespace or "all",
            "count": len(logconfigs),
            "tried_api_combinations": tried,
            "logconfigs": logconfigs,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
    finally:
        for path in temp_files:
            _safe_delete_file(path)
