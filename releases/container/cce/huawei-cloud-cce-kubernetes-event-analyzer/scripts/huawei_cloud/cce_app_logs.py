"""Read CCE Event-to-LTS LogConfig custom resources through kubectl."""

from __future__ import annotations

from typing import Any, Dict, List

from . import kubectl_client


def get_cce_logconfigs_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Return LogConfig resources needed to locate CCE Event LTS streams."""
    result = kubectl_client.get_cce_resources_with_kubectl(
        region=params["region"],
        cluster_id=params["cluster_id"],
        resource="logconfigs.logging.openvessel.io",
        namespace=params.get("namespace"),
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not result.get("success"):
        return result

    logconfigs: List[Dict[str, Any]] = []
    for item in result.get("items") or []:
        metadata = item.get("metadata") or {}
        spec = item.get("spec") or {}
        input_detail = spec.get("inputDetail") or {}
        output_detail = spec.get("outputDetail") or {}
        logconfigs.append(
            {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "input_type": input_detail.get("type"),
                "output_type": output_detail.get("type"),
                "spec": spec,
                "status": item.get("status") or {},
                "api_version": item.get("apiVersion"),
            }
        )

    return {
        "success": True,
        "cluster_id": params["cluster_id"],
        "namespace": params.get("namespace") or "all",
        "access_method": result.get("access_method"),
        "count": len(logconfigs),
        "logconfigs": logconfigs,
    }
