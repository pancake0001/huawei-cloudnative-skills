"""Read-only HPA helpers using kubectl cce."""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import cce


SYSTEM_NAMESPACES = {"kube-system"}


def _hpa(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata, spec, status = item.get("metadata") or {}, item.get("spec") or {}, item.get("status") or {}
    return {"name": metadata.get("name"), "namespace": metadata.get("namespace"), "created": metadata.get("creationTimestamp"), "labels": metadata.get("labels") or {}, "annotations": metadata.get("annotations") or {}, "scale_target_ref": spec.get("scaleTargetRef") or {}, "min_replicas": spec.get("minReplicas"), "max_replicas": spec.get("maxReplicas"), "metrics": spec.get("metrics") or [], "behavior": spec.get("behavior") or {}, "current_replicas": status.get("currentReplicas"), "desired_replicas": status.get("desiredReplicas"), "current_metrics": status.get("currentMetrics") or [], "conditions": status.get("conditions") or []}


def list_cce_hpas(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: Optional[str] = None, include_system: bool = False, security_token: Optional[str] = None, hpa_name: Optional[str] = None) -> Dict[str, Any]:
    if not namespace:
        return {"success": False, "error": "namespace is required for HPA queries; whole-cluster collection is not supported"}
    arguments = ["get", "hpa"] + ([hpa_name] if hpa_name else []) + ["-n", namespace, "-o", "json"]
    result = cce._kubectl(region, cluster_id, arguments, ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    data = result.get("data") or {}
    items = data.get("items") or ([data] if data.get("metadata") else [])
    hpas = [_hpa(item) for item in items]
    if not include_system:
        hpas = [item for item in hpas if item.get("namespace") not in SYSTEM_NAMESPACES]
    return {"success": True, "source": "kubectl-cce", "region": region, "cluster_id": cluster_id, "namespace": namespace, "count": len(hpas), "hpas": hpas}
