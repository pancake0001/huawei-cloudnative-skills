"""CCE Node Pool management functions."""

from typing import Any, Dict, List, Optional

from huaweicloudsdkcce.v3 import ListNodePoolsRequest, ScaleNodePoolRequest, ScaleNodePoolRequestBody, ScaleNodePoolSpec
from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException

from .common import (
    SDK_AVAILABLE,
    IMPORT_ERROR,
    get_credentials,
    create_cce_client,
)


def list_cce_node_pools(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """List node pools in a CCE cluster with pagination"""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = ListNodePoolsRequest()
        request.cluster_id = cluster_id

        response = client.list_node_pools(request)

        nodepools = []
        if hasattr(response, 'items') and response.items:
            for nodepool in response.items:
                scale_groups = []
                
                if hasattr(nodepool, 'spec'):
                    default_sg_info = {
                        "name": "default",
                        "type": "default",
                        "initial_node_count": nodepool.spec.initial_node_count if hasattr(nodepool.spec, 'initial_node_count') else None,
                    }
                    
                    if hasattr(nodepool.spec, 'node_template'):
                        node_template = nodepool.spec.node_template
                        default_sg_info["flavor"] = node_template.flavor if hasattr(node_template, 'flavor') else None
                        default_sg_info["availability_zone"] = node_template.az if hasattr(node_template, 'az') else None
                        if hasattr(node_template, 'root_volume'):
                            default_sg_info["root_volume"] = node_template.root_volume.to_dict() if hasattr(node_template.root_volume, 'to_dict') else str(node_template.root_volume)
                        if hasattr(node_template, 'data_volumes'):
                            default_sg_info["data_volumes"] = [dv.to_dict() if hasattr(dv, 'to_dict') else str(dv) for dv in node_template.data_volumes]
                    
                    if hasattr(nodepool.spec, 'autoscaling'):
                        default_sg_info["autoscaling"] = {
                            "enable": nodepool.spec.autoscaling.enable if hasattr(nodepool.spec.autoscaling, 'enable') else None,
                            "min_node_count": nodepool.spec.autoscaling.min_node_count if hasattr(nodepool.spec.autoscaling, 'min_node_count') else None,
                            "max_node_count": nodepool.spec.autoscaling.max_node_count if hasattr(nodepool.spec.autoscaling, 'max_node_count') else None,
                            "scale_down_cooldown_time": nodepool.spec.autoscaling.scale_down_cooldown_time if hasattr(nodepool.spec.autoscaling, 'scale_down_cooldown_time') else None,
                            "priority": nodepool.spec.autoscaling.priority if hasattr(nodepool.spec.autoscaling, 'priority') else None,
                        }
                    
                    scale_groups.append(default_sg_info)
                
                extension_scale_groups = []
                if hasattr(nodepool, 'spec') and hasattr(nodepool.spec, 'extension_scale_groups'):
                    extension_scale_groups = nodepool.spec.extension_scale_groups or []
                for sg in extension_scale_groups:
                    sg_info = {
                        "type": "extension",
                    }
                    if hasattr(sg, 'metadata'):
                        sg_info["name"] = sg.metadata.name if hasattr(sg.metadata, 'name') else None
                        sg_info["uid"] = sg.metadata.uid if hasattr(sg.metadata, 'uid') else None
                    if hasattr(sg, 'spec'):
                        sg_spec = sg.spec
                        sg_info["flavor"] = sg_spec.flavor if hasattr(sg_spec, 'flavor') else None
                        sg_info["availability_zone"] = sg_spec.az if hasattr(sg_spec, 'az') else None
                        sg_info["initial_node_count"] = sg_spec.initial_node_count if hasattr(sg_spec, 'initial_node_count') else None
                        sg_info["min_node_count"] = sg_spec.min_node_count if hasattr(sg_spec, 'min_node_count') else None
                        sg_info["max_node_count"] = sg_spec.max_node_count if hasattr(sg_spec, 'max_node_count') else None
                        if hasattr(sg_spec, 'autoscaling'):
                            sg_info["autoscaling"] = {
                                "enable": sg_spec.autoscaling.enable if hasattr(sg_spec.autoscaling, 'enable') else None,
                                "extension_priority": sg_spec.autoscaling.extension_priority if hasattr(sg_spec.autoscaling, 'extension_priority') else None,
                            }
                    scale_groups.append(sg_info)
                
                scale_group_statuses = []
                raw_scale_group_statuses = []
                if hasattr(nodepool, 'status') and hasattr(nodepool.status, 'scale_group_statuses'):
                    raw_scale_group_statuses = nodepool.status.scale_group_statuses or []
                for sgs in raw_scale_group_statuses:
                    sgs_info = {}
                    if hasattr(sgs, 'name'):
                        sgs_info["name"] = sgs.name
                    if hasattr(sgs, 'current_node_count'):
                        sgs_info["current_node_count"] = sgs.current_node_count
                    if hasattr(sgs, 'status'):
                        sgs_info["status"] = sgs.status
                    scale_group_statuses.append(sgs_info)
                
                pool_info = {
                    "id": nodepool.metadata.uid,
                    "name": nodepool.metadata.name,
                    "flavor": nodepool.spec.flavor if hasattr(nodepool, 'spec') and hasattr(nodepool.spec, 'flavor') else None,
                    "initial_node_count": nodepool.spec.initial_node_count if hasattr(nodepool, 'spec') and hasattr(nodepool.spec, 'initial_node_count') else None,
                    "autoscaling_enabled": nodepool.spec.autoscaling.enabled if hasattr(nodepool, 'spec') and hasattr(nodepool.spec, 'autoscaling') and hasattr(nodepool.spec.autoscaling, 'enabled') else False,
                    "scale_groups": scale_groups,
                    "scale_group_statuses": scale_group_statuses,
                    "created_at": str(nodepool.metadata.creation_timestamp) if hasattr(nodepool, 'metadata') and hasattr(nodepool.metadata, 'creation_timestamp') else None,
                }
                nodepools.append(pool_info)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "list_cce_nodepools",
            "count": len(nodepools),
            "nodepools": nodepools
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


list_cce_nodepools = list_cce_node_pools


def resize_node_pool(
    region: str,
    cluster_id: str,
    nodepool_id: str,
    node_count: int,
    confirm: bool = False,
    scale_group_names: Optional[List[str]] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """Resize (scale up or down) a CCE node pool to the specified number of nodes

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        nodepool_id: Node pool ID to resize
        node_count: Target node count (desired number of nodes)
        confirm: True to confirm and execute (default: False)
        scale_group_names: List of scale group names to use (default: ["default"])
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with operation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not nodepool_id:
        return {
            "success": False,
            "error": "nodepool_id is required"
        }

    if node_count is None or node_count < 0:
        return {
            "success": False,
            "error": "node_count must be a non-negative integer"
        }

    if not confirm:
        sg_note = f" (using scale groups: {', '.join(scale_group_names)})" if scale_group_names else ""
        return {
            "success": False,
            "requires_confirmation": True,
            "operation": "resize_nodepool",
            "warning": f"Warning: Resizing node pool '{nodepool_id}' to {node_count} nodes{sg_note}",
            "cluster_id": cluster_id,
            "nodepool_id": nodepool_id,
            "target_node_count": node_count,
            "scale_group_names": scale_group_names,
            "hint": "Add confirm=true parameter to confirm the operation",
            "note": "This operation will affect cluster resources and billing",
            "example": f"resize_node_pool region={region} cluster_id={cluster_id} nodepool_id={nodepool_id} node_count={node_count} scale_group_names={','.join(scale_group_names)} confirm=true" if scale_group_names else f"resize_node_pool region={region} cluster_id={cluster_id} nodepool_id={nodepool_id} node_count={node_count} confirm=true"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        nodepool_result = list_cce_node_pools(region, cluster_id, ak, sk, project_id)
        if not nodepool_result.get("success"):
            return nodepool_result
        
        target_nodepool = None
        nodepool_name = None
        nodepool_uid = None
        for np in nodepool_result.get("nodepools", []):
            np_id = np.get("id")
            np_name = np.get("name")
            if (np_id and np_id.strip() == nodepool_id.strip()) or (np_name and np_name.strip() == nodepool_id.strip()):
                target_nodepool = np
                nodepool_name = np_name
                nodepool_uid = np_id
                break
        if not target_nodepool:
            return {
                "success": False,
                "error": f"Node pool {nodepool_id} not found in cluster {cluster_id}"
            }
        
        if not scale_group_names:
            scale_group_names = ["default"]

        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = ScaleNodePoolRequest()
        request.cluster_id = cluster_id
        request.nodepool_id = nodepool_uid
        
        scale_body = ScaleNodePoolRequestBody()
        scale_body.node_num = node_count
        scale_body.kind = 'NodePool'
        scale_body.api_version = 'v3'
        
        spec = ScaleNodePoolSpec()
        spec.desired_node_count = node_count
        spec.scale_groups = scale_group_names
        
        scale_body.spec = spec
        request.body = scale_body
        
        try:
            response = client.scale_node_pool(request)
        except ClientRequestException as e:
            if "Nodepool not found" in str(e) or "Invalid nodepool uuid" in str(e):
                request.nodepool_id = nodepool_name
                response = client.scale_node_pool(request)
            else:
                raise

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "nodepool_id": nodepool_id,
            "action": "resize_node_pool",
            "target_node_count": node_count,
            "scale_group_names_used": scale_group_names,
            "message": f"Node pool resize request submitted successfully",
            "response": response.to_dict() if hasattr(response, 'to_dict') else str(response)
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None),
            "hint": "Check if the target node count is valid for the node pool"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


resize_cce_nodepool = resize_node_pool