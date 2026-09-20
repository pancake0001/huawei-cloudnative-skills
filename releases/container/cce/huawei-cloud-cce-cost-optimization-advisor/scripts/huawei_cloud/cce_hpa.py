"""Read-only HPA helpers using kubectl cce."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from . import cce


SYSTEM_NAMESPACES = {"kube-system"}


def _kind(workload_type: str) -> str:
    value = (workload_type or "deployment").lower()
    if value in {"deployment", "deploy"}:
        return "Deployment"
    if value in {"statefulset", "sts"}:
        return "StatefulSet"
    raise ValueError("workload_type must be deployment or statefulset")


def build_hpa_manifest(workload_name: str, namespace: str, min_replicas: int, max_replicas: int, workload_type: str = "deployment", hpa_name: Optional[str] = None, target_cpu_utilization: Optional[int] = 60, target_memory_utilization: Optional[int] = None, behavior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not workload_name or not namespace:
        raise ValueError("workload_name and namespace are required")
    if min_replicas < 1 or max_replicas < min_replicas:
        raise ValueError("min_replicas must be at least 1 and max_replicas must not be smaller")
    metrics = []
    for resource, target in (("cpu", target_cpu_utilization), ("memory", target_memory_utilization)):
        if target is not None:
            metrics.append({"type": "Resource", "resource": {"name": resource, "target": {"type": "Utilization", "averageUtilization": target}}})
    if not metrics:
        raise ValueError("at least one resource target is required")
    manifest = {"apiVersion": "autoscaling/v2", "kind": "HorizontalPodAutoscaler", "metadata": {"name": hpa_name or f"{workload_name}-hpa", "namespace": namespace}, "spec": {"scaleTargetRef": {"apiVersion": "apps/v1", "kind": _kind(workload_type), "name": workload_name}, "minReplicas": min_replicas, "maxReplicas": max_replicas, "metrics": metrics}}
    if behavior:
        manifest["spec"]["behavior"] = behavior
    return manifest


def generate_cce_hpa_manifest(workload_name: str, namespace: str, min_replicas: int, max_replicas: int, workload_type: str = "deployment", hpa_name: Optional[str] = None, target_cpu_utilization: Optional[int] = 60, target_memory_utilization: Optional[int] = None, behavior: Any = None, output_file: Optional[str] = None) -> Dict[str, Any]:
    try:
        parsed_behavior = json.loads(behavior) if isinstance(behavior, str) else behavior
        manifest = build_hpa_manifest(workload_name, namespace, min_replicas, max_replicas, workload_type, hpa_name, target_cpu_utilization, target_memory_utilization, parsed_behavior)
        content = yaml.safe_dump(manifest, sort_keys=False)
        if output_file:
            Path(output_file).write_text(content, encoding="utf-8")
        return {"success": True, "action": "generate_cce_hpa_manifest", "manifest": manifest, "manifest_yaml": content, "output_file": output_file}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _hpa(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata, spec, status = item.get("metadata") or {}, item.get("spec") or {}, item.get("status") or {}
    return {"name": metadata.get("name"), "namespace": metadata.get("namespace"), "created": metadata.get("creationTimestamp"), "labels": metadata.get("labels") or {}, "annotations": metadata.get("annotations") or {}, "scale_target_ref": spec.get("scaleTargetRef") or {}, "min_replicas": spec.get("minReplicas"), "max_replicas": spec.get("maxReplicas"), "metrics": spec.get("metrics") or [], "current_replicas": status.get("currentReplicas"), "desired_replicas": status.get("desiredReplicas"), "current_metrics": status.get("currentMetrics") or [], "conditions": status.get("conditions") or []}


def list_cce_hpas(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: Optional[str] = None, include_system: bool = False, security_token: Optional[str] = None) -> Dict[str, Any]:
    if not namespace:
        return {"success": False, "error": "namespace is required for HPA queries; whole-cluster collection is not supported"}
    result = cce._kubectl(region, cluster_id, ["get", "hpa", "-n", namespace, "-o", "json"], ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    hpas = [_hpa(item) for item in (result.get("data") or {}).get("items") or []]
    if not include_system:
        hpas = [item for item in hpas if item.get("namespace") not in SYSTEM_NAMESPACES]
    return {"success": True, "source": "kubectl-cce", "region": region, "cluster_id": cluster_id, "namespace": namespace, "count": len(hpas), "hpas": hpas}
