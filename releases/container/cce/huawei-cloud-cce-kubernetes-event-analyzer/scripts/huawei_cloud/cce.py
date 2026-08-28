"""CCE helpers used by the current Kubernetes Event query."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from . import kubectl_client


_STANDARD_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


def resolve_cce_cluster_id(
    region: str, value: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None
) -> Dict[str, Any]:
    """Validate a cluster UUID or resolve one exact CCE cluster-name match."""
    if _STANDARD_UUID_RE.fullmatch(value or ""):
        result = kubectl_client._run_hcloud("CCE", "ShowCluster", region, {"cluster_id": value}, ak, sk, project_id)
        if not result.get("success"):
            return {
                "success": False,
                "error": f"Unable to verify CCE cluster_id '{value}': {result.get('error', '')}",
                "cluster_id": value,
            }
        return {"success": True, "id": value, "resolved_from_name": False}
    # CCE ListClusters returns all items and does not accept limit or offset parameters.
    result = kubectl_client._run_hcloud("CCE", "ListClusters", region, {}, ak, sk, project_id)
    if not result.get("success"):
        return {"success": False, "error": f"Unable to list CCE clusters for cluster_id resolution: {result.get('error', '')}"}
    items = ((result.get("data") or {}).get("items") or [])
    matches = [item for item in items if ((item.get("metadata") or {}).get("name") == value)]
    if len(matches) == 1:
        cluster_id = (matches[0].get("metadata") or {}).get("uid")
        if _STANDARD_UUID_RE.fullmatch(cluster_id or ""):
            verification = kubectl_client._run_hcloud("CCE", "ShowCluster", region, {"cluster_id": cluster_id}, ak, sk, project_id)
            if not verification.get("success"):
                return {
                    "success": False,
                    "error": f"Unable to verify CCE cluster resolved from name '{value}': {verification.get('error', '')}",
                    "cluster_id": cluster_id,
                }
            return {"success": True, "id": cluster_id, "resolved_from_name": True}
    if len(matches) > 1:
        return {"success": False, "error": f"cluster_id '{value}' matched multiple CCE clusters; provide a standard UUID"}
    return {"success": False, "error": f"cluster_id must be a standard UUID. No CCE cluster named '{value}' was found"}


def get_kubernetes_events(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
    namespace: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Read and normalize CCE Events through the kubectl access strategy."""
    effective_event_type = event_type or "Warning"
    result = kubectl_client.get_cce_events_with_kubectl(
        region=region,
        cluster_id=cluster_id,
        namespace=namespace,
        event_type=effective_event_type,
        limit=limit,
        ak=ak,
        sk=sk,
        project_id=project_id,
        security_token=security_token,
    )
    if not result.get("success"):
        return result

    events = []
    for item in result.get("items") or []:
        metadata = item.get("metadata") or {}
        involved_object = item.get("involvedObject") or {}
        series = item.get("series") or {}
        events.append(
            {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "type": item.get("type"),
                "reason": item.get("reason"),
                "message": item.get("message"),
                "first_timestamp": item.get("firstTimestamp") or item.get("eventTime") or metadata.get("creationTimestamp"),
                "last_timestamp": item.get("lastTimestamp") or series.get("lastObservedTime") or item.get("eventTime"),
                "count": item.get("count") or series.get("count") or 1,
                "involved_object": {
                    "kind": involved_object.get("kind"),
                    "name": involved_object.get("name"),
                    "namespace": involved_object.get("namespace"),
                }
                if involved_object
                else None,
            }
        )

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "get_cce_events",
        "namespace": namespace or "all",
        "event_type": effective_event_type,
        "access_method": result.get("access_method"),
        "count": len(events),
        "limit": limit,
        "events": events,
    }
