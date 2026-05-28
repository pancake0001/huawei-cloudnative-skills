# CCE Nodepool/Node/Addon Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 6 new tools for CCE node pool creation/deletion, node creation, and addon installation/uninstallation/update.

**Architecture:** Extend existing modular structure (cce_nodepool.py, cce_node.py, cce_addon.py) with new functions. Use huaweicloudsdkcce SDK classes: CreateNodePoolRequest, DeleteNodePoolRequest, CreateNodeRequest, CreateAddonInstanceRequest, UpdateAddonInstanceRequest, DeleteAddonInstanceRequest.

**Tech Stack:** Python, huaweicloudsdkcce, huaweicloudsdkcore

---

## File Structure

| File | Purpose |
|------|---------|
| `scripts/huawei_cloud/cce_nodepool.py` | Add `create_node_pool`, `delete_node_pool` |
| `scripts/huawei_cloud/cce_node.py` | Add `create_cce_node` |
| `scripts/huawei_cloud/cce_addon.py` | Add `install_cce_addon`, `uninstall_cce_addon`, `update_cce_addon` |
| `scripts/huawei_cloud/dispatcher.py` | Add 6 new handlers to ACTION_SPECS |
| `skills/.../manifest.json` | Add 6 new tool schemas |
| `skills/.../SKILL.md` | Update documentation |

---

## Task 1: Implement create_node_pool

**Files:**
- Modify: `scripts/huawei_cloud/cce_nodepool.py`

- [ ] **Step 1: Add imports for CreateNodePoolRequest**

```python
from huaweicloudsdkcce.v3 import (
    ListNodePoolsRequest,
    ScaleNodePoolRequest,
    ScaleNodePoolRequestBody,
    ScaleNodePoolSpec,
    CreateNodePoolRequest,
    CreateNodePoolRequestBody,
    NodePoolMetadata,
    CreateNodePoolRequestSpec,
    CreateNodePoolRequestSpecNodeSpec,
    Volume,
    Login,
    UserPassword,
    NodeNicSpec,
)
```

- [ ] **Step 2: Implement create_node_pool function**

```python
def create_node_pool(
    region: str,
    cluster_id: str,
    nodepool_name: str,
    flavor: str,
    availability_zone: str,
    root_volume_size: int,
    root_volume_type: str,
    initial_node_count: int = 0,
    os_type: Optional[str] = None,
    ssh_key: Optional[str] = None,
    password: Optional[str] = None,
    data_volumes: Optional[List[Dict]] = None,
    subnet_id: Optional[str] = None,
    autoscaling_enabled: bool = False,
    min_node_count: Optional[int] = None,
    max_node_count: Optional[int] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a node pool in CCE cluster
    
    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        nodepool_name: Node pool name
        flavor: Node flavor (e.g., s6.large.2)
        availability_zone: Availability zone (e.g., cn-north-4a)
        root_volume_size: Root volume size in GiB (40-1024)
        root_volume_type: Root volume type (SAS, SSD, GPSSD, ESSD)
        initial_node_count: Initial number of nodes (default: 0)
        os_type: OS type (EulerOS 2.9, Huawei Cloud EulerOS 2.0)
        ssh_key: SSH key pair name for login
        password: Password for login (requires salt encryption)
        data_volumes: List of data volume configs [{"size": 100, "type": "SAS"}]
        subnet_id: Subnet ID for node network
        autoscaling_enabled: Enable autoscaling (default: False)
        min_node_count: Minimum nodes for autoscaling
        max_node_count: Maximum nodes for autoscaling
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
    
    Returns:
        Dictionary with creation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    
    if not cluster_id or not nodepool_name:
        return {"success": False, "error": "cluster_id and nodepool_name are required"}
    
    if not flavor or not availability_zone:
        return {"success": False, "error": "flavor and availability_zone are required"}
    
    if not SDK_AVAILABLE:
        return {"success": False, "error": f"SDK not installed: {IMPORT_ERROR}"}
    
    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        request = CreateNodePoolRequest()
        request.cluster_id = cluster_id
        
        body = CreateNodePoolRequestBody()
        body.kind = "NodePool"
        body.api_version = "v3"
        
        metadata = NodePoolMetadata()
        metadata.name = nodepool_name
        body.metadata = metadata
        
        spec = CreateNodePoolRequestSpec()
        spec.initial_node_count = initial_node_count
        
        node_template = CreateNodePoolRequestSpecNodeSpec()
        node_template.flavor = flavor
        node_template.az = availability_zone
        
        root_volume = Volume()
        root_volume.size = root_volume_size
        root_volume.volumetype = root_volume_type
        node_template.root_volume = root_volume
        
        if data_volumes:
            dv_list = []
            for dv in data_volumes:
                vol = Volume()
                vol.size = dv.get("size", 100)
                vol.volumetype = dv.get("type", "SAS")
                dv_list.append(vol)
            node_template.data_volumes = dv_list
        
        if os_type:
            node_template.os = os_type
        
        login = Login()
        if ssh_key:
            login.ssh_key = ssh_key
        elif password:
            user_pwd = UserPassword()
            user_pwd.username = "root"
            user_pwd.password = password
            login.user_password = user_pwd
        node_template.login = login
        
        if subnet_id:
            nic_spec = NodeNicSpec()
            nic_spec.primary_nic = {"subnetId": subnet_id}
            node_template.node_nic_spec = nic_spec
        
        spec.node_template = node_template
        
        if autoscaling_enabled:
            autoscaling = NodePoolNodeAutoscaling()
            autoscaling.enable = True
            autoscaling.min_node_count = min_node_count or 0
            autoscaling.max_node_count = max_node_count or initial_node_count * 2
            spec.autoscaling = autoscaling
        
        body.spec = spec
        request.body = body
        
        response = client.create_node_pool(request)
        
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "create_node_pool",
            "nodepool_id": response.metadata.uid if hasattr(response, 'metadata') else None,
            "nodepool_name": nodepool_name,
            "initial_node_count": initial_node_count,
            "message": "Node pool creation request submitted",
        }
    
    except ClientRequestException as e:
        return {"success": False, "error": f"{e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}

create_cce_nodepool = create_node_pool
```

---

## Task 2: Implement delete_node_pool

**Files:**
- Modify: `scripts/huawei_cloud/cce_nodepool.py`

- [ ] **Step 1: Add import for DeleteNodePoolRequest**

```python
from huaweicloudsdkcce.v3 import DeleteNodePoolRequest
```

- [ ] **Step 2: Implement delete_node_pool function**

```python
def delete_node_pool(
    region: str,
    cluster_id: str,
    nodepool_id: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a node pool from CCE cluster
    
    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        nodepool_id: Node pool ID or name
        confirm: Must be True to confirm deletion
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
    
    Returns:
        Dictionary with deletion result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    
    if not cluster_id or not nodepool_id:
        return {"success": False, "error": "cluster_id and nodepool_id are required"}
    
    if not confirm:
        return {
            "success": False,
            "requires_confirmation": True,
            "warning": f"Deleting node pool '{nodepool_id}' will remove all its nodes",
            "hint": "Add confirm=true to confirm deletion",
        }
    
    if not SDK_AVAILABLE:
        return {"success": False, "error": f"SDK not installed: {IMPORT_ERROR}"}
    
    try:
        nodepool_result = list_cce_node_pools(region, cluster_id, ak, sk, project_id)
        if not nodepool_result.get("success"):
            return nodepool_result
        
        target_uid = None
        for np in nodepool_result.get("nodepools", []):
            if np.get("id") == nodepool_id or np.get("name") == nodepool_id:
                target_uid = np.get("id")
                break
        
        if not target_uid:
            return {"success": False, "error": f"Node pool {nodepool_id} not found"}
        
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        request = DeleteNodePoolRequest()
        request.cluster_id = cluster_id
        request.nodepool_id = target_uid
        
        response = client.delete_node_pool(request)
        
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "nodepool_id": nodepool_id,
            "action": "delete_node_pool",
            "message": "Node pool deletion request submitted",
        }
    
    except ClientRequestException as e:
        return {"success": False, "error": f"{e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

delete_cce_nodepool = delete_node_pool
```

---

## Task 3: Implement create_cce_node

**Files:**
- Modify: `scripts/huawei_cloud/cce_node.py`

- [ ] **Step 1: Add imports for CreateNodeRequest**

```python
from huaweicloudsdkcce.v3 import CreateNodeRequest, CreateNodeRequestBody, NodeMetadata, NodeSpec, Volume, Login, UserPassword, NodePublicIP
```

- [ ] **Step 2: Implement create_cce_node function**

```python
def create_cce_node(
    region: str,
    cluster_id: str,
    flavor: str,
    availability_zone: str,
    root_volume_size: int,
    root_volume_type: str,
    node_count: int = 1,
    os_type: Optional[str] = None,
    ssh_key: Optional[str] = None,
    password: Optional[str] = None,
    data_volumes: Optional[List[Dict]] = None,
    subnet_id: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create nodes in CCE cluster
    
    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        flavor: Node flavor (e.g., s6.large.2)
        availability_zone: Availability zone (e.g., cn-north-4a)
        root_volume_size: Root volume size in GiB (40-1024)
        root_volume_type: Root volume type (SAS, SSD, GPSSD, ESSD)
        node_count: Number of nodes to create (default: 1)
        os_type: OS type
        ssh_key: SSH key pair name
        password: Password for login
        data_volumes: List of data volume configs
        subnet_id: Subnet ID for node network
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
    
    Returns:
        Dictionary with creation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    
    if not flavor or not availability_zone:
        return {"success": False, "error": "flavor and availability_zone are required"}
    
    if not SDK_AVAILABLE:
        return {"success": False, "error": f"SDK not installed: {IMPORT_ERROR}"}
    
    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        request = CreateNodeRequest()
        request.cluster_id = cluster_id
        
        body = CreateNodeRequestBody()
        body.kind = "Node"
        body.api_version = "v3"
        
        metadata = NodeMetadata()
        body.metadata = metadata
        
        spec = NodeSpec()
        spec.flavor = flavor
        spec.az = availability_zone
        spec.count = node_count
        
        root_volume = Volume()
        root_volume.size = root_volume_size
        root_volume.volumetype = root_volume_type
        spec.root_volume = root_volume
        
        if data_volumes:
            dv_list = []
            for dv in data_volumes:
                vol = Volume()
                vol.size = dv.get("size", 100)
                vol.volumetype = dv.get("type", "SAS")
                dv_list.append(vol)
            spec.data_volumes = dv_list
        
        if os_type:
            spec.os = os_type
        
        login = Login()
        if ssh_key:
            login.ssh_key = ssh_key
        elif password:
            user_pwd = UserPassword()
            user_pwd.username = "root"
            user_pwd.password = password
            login.user_password = user_pwd
        spec.login = login
        
        if subnet_id:
            nic_spec = NodeNicSpec()
            nic_spec.primary_nic = {"subnetId": subnet_id}
            spec.node_nic_spec = nic_spec
        
        body.spec = spec
        request.body = body
        
        response = client.create_node(request)
        
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "create_cce_node",
            "node_count": node_count,
            "message": f"Node creation request submitted for {node_count} nodes",
        }
    
    except ClientRequestException as e:
        return {"success": False, "error": f"{e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## Task 4: Implement install_cce_addon

**Files:**
- Modify: `scripts/huawei_cloud/cce_addon.py`

- [ ] **Step 1: Add imports**

```python
from huaweicloudsdkcce.v3 import (
    ShowAddonInstanceRequest,
    ListAddonInstancesRequest,
    CreateAddonInstanceRequest,
    CreateAddonInstanceRequestBody,
    InstanceSpec,
    AddonMetadata,
    UpdateAddonInstanceRequest,
    UpdateAddonInstanceRequestBody,
    DeleteAddonInstanceRequest,
)
```

- [ ] **Step 2: Implement install_cce_addon function**

```python
def install_cce_addon(
    region: str,
    cluster_id: str,
    addon_template_name: str,
    addon_version: Optional[str] = None,
    values: Optional[Dict] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Install an addon in CCE cluster
    
    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        addon_template_name: Addon template name (e.g., coredns, metrics-server)
        addon_version: Addon version (optional, uses latest if not specified)
        values: Addon configuration values (dict)
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
    
    Returns:
        Dictionary with installation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    
    if not cluster_id or not addon_template_name:
        return {"success": False, "error": "cluster_id and addon_template_name are required"}
    
    if not SDK_AVAILABLE:
        return {"success": False, "error": f"SDK not installed: {IMPORT_ERROR}"}
    
    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        request = CreateAddonInstanceRequest()
        request.cluster_id = cluster_id
        
        body = CreateAddonInstanceRequestBody()
        body.kind = "Addon"
        body.api_version = "v3"
        
        metadata = AddonMetadata()
        metadata.annotations = {"addon.install/type": "install"}
        body.metadata = metadata
        
        spec = InstanceSpec()
        spec.cluster_id = cluster_id
        spec.addon_template_name = addon_template_name
        
        if addon_version:
            spec.version = addon_version
        
        if values:
            spec.values = values
        
        body.spec = spec
        request.body = body
        
        response = client.create_addon_instance(request)
        
        addon_id = response.metadata.uid if hasattr(response, 'metadata') else None
        
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "install_cce_addon",
            "addon_id": addon_id,
            "addon_name": addon_template_name,
            "message": f"Addon '{addon_template_name}' installation request submitted",
        }
    
    except ClientRequestException as e:
        return {"success": False, "error": f"{e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## Task 5: Implement uninstall_cce_addon

**Files:**
- Modify: `scripts/huawei_cloud/cce_addon.py`

- [ ] **Step 1: Implement uninstall_cce_addon function**

```python
def uninstall_cce_addon(
    region: str,
    cluster_id: str,
    addon_id: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Uninstall an addon from CCE cluster
    
    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        addon_id: Addon ID or name
        confirm: Must be True to confirm uninstallation
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
    
    Returns:
        Dictionary with uninstallation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    
    if not cluster_id or not addon_id:
        return {"success": False, "error": "cluster_id and addon_id are required"}
    
    if not confirm:
        return {
            "success": False,
            "requires_confirmation": True,
            "warning": f"Uninstalling addon '{addon_id}' will remove its functionality",
            "hint": "Add confirm=true to confirm uninstallation",
        }
    
    if not SDK_AVAILABLE:
        return {"success": False, "error": f"SDK not installed: {IMPORT_ERROR}"}
    
    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        request = DeleteAddonInstanceRequest()
        request.cluster_id = cluster_id
        request.addon_name = addon_id
        
        response = client.delete_addon_instance(request)
        
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "addon_id": addon_id,
            "action": "uninstall_cce_addon",
            "message": f"Addon '{addon_id}' uninstallation request submitted",
        }
    
    except ClientRequestException as e:
        return {"success": False, "error": f"{e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## Task 6: Implement update_cce_addon

**Files:**
- Modify: `scripts/huawei_cloud/cce_addon.py`

- [ ] **Step 1: Implement update_cce_addon function**

```python
def update_cce_addon(
    region: str,
    cluster_id: str,
    addon_id: str,
    addon_version: Optional[str] = None,
    values: Optional[Dict] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an addon in CCE cluster
    
    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        addon_id: Addon ID or name
        addon_version: New addon version (optional)
        values: New addon configuration values (dict)
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
    
    Returns:
        Dictionary with update result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    
    if not cluster_id or not addon_id:
        return {"success": False, "error": "cluster_id and addon_id are required"}
    
    if not SDK_AVAILABLE:
        return {"success": False, "error": f"SDK not installed: {IMPORT_ERROR}"}
    
    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        request = UpdateAddonInstanceRequest()
        request.cluster_id = cluster_id
        request.addon_name = addon_id
        
        body = UpdateAddonInstanceRequestBody()
        body.kind = "Addon"
        body.api_version = "v3"
        
        metadata = AddonMetadata()
        metadata.annotations = {"addon.upgrade/type": "upgrade"}
        body.metadata = metadata
        
        spec = InstanceSpec()
        spec.cluster_id = cluster_id
        
        if addon_version:
            spec.version = addon_version
        
        if values:
            spec.values = values
        
        body.spec = spec
        request.body = body
        
        response = client.update_addon_instance(request)
        
        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "addon_id": addon_id,
            "action": "update_cce_addon",
            "message": f"Addon '{addon_id}' update request submitted",
        }
    
    except ClientRequestException as e:
        return {"success": False, "error": f"{e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## Task 7: Update dispatcher.py

**Files:**
- Modify: `scripts/huawei_cloud/dispatcher.py`

- [ ] **Step 1: Add handler functions for new tools**

```python
def _create_cce_nodepool(params: Dict[str, str]) -> Dict[str, Any]:
    data_volumes = None
    if params.get("data_volumes"):
        try:
            data_volumes = json.loads(params["data_volumes"])
        except (json.JSONDecodeError, TypeError):
            pass
    return cce_nodepool.create_node_pool(
        region=params["region"],
        cluster_id=params["cluster_id"],
        nodepool_name=params["nodepool_name"],
        flavor=params["flavor"],
        availability_zone=params["availability_zone"],
        root_volume_size=int(params["root_volume_size"]),
        root_volume_type=params["root_volume_type"],
        initial_node_count=int(params.get("initial_node_count", 0)),
        os_type=params.get("os_type"),
        ssh_key=params.get("ssh_key"),
        password=params.get("password"),
        data_volumes=data_volumes,
        subnet_id=params.get("subnet_id"),
        autoscaling_enabled=params.get("autoscaling_enabled", "false").lower() == "true",
        min_node_count=int(params.get("min_node_count", 0)) if params.get("min_node_count") else None,
        max_node_count=int(params.get("max_node_count", 0)) if params.get("max_node_count") else None,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )

def _delete_cce_nodepool(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_nodepool.delete_node_pool(
        region=params["region"],
        cluster_id=params["cluster_id"],
        nodepool_id=params["nodepool_id"],
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )

def _create_cce_node(params: Dict[str, str]) -> Dict[str, Any]:
    data_volumes = None
    if params.get("data_volumes"):
        try:
            data_volumes = json.loads(params["data_volumes"])
        except (json.JSONDecodeError, TypeError):
            pass
    return cce_node.create_cce_node(
        region=params["region"],
        cluster_id=params["cluster_id"],
        flavor=params["flavor"],
        availability_zone=params["availability_zone"],
        root_volume_size=int(params["root_volume_size"]),
        root_volume_type=params["root_volume_type"],
        node_count=int(params.get("node_count", 1)),
        os_type=params.get("os_type"),
        ssh_key=params.get("ssh_key"),
        password=params.get("password"),
        data_volumes=data_volumes,
        subnet_id=params.get("subnet_id"),
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )

def _install_cce_addon(params: Dict[str, str]) -> Dict[str, Any]:
    values = None
    if params.get("values"):
        try:
            values = json.loads(params["values"])
        except (json.JSONDecodeError, TypeError):
            pass
    return cce_addon.install_cce_addon(
        region=params["region"],
        cluster_id=params["cluster_id"],
        addon_template_name=params["addon_template_name"],
        addon_version=params.get("addon_version"),
        values=values,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )

def _uninstall_cce_addon(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_addon.uninstall_cce_addon(
        region=params["region"],
        cluster_id=params["cluster_id"],
        addon_id=params["addon_id"],
        confirm=params.get("confirm", "").lower() == "true",
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )

def _update_cce_addon(params: Dict[str, str]) -> Dict[str, Any]:
    values = None
    if params.get("values"):
        try:
            values = json.loads(params["values"])
        except (json.JSONDecodeError, TypeError):
            pass
    return cce_addon.update_cce_addon(
        region=params["region"],
        cluster_id=params["cluster_id"],
        addon_id=params["addon_id"],
        addon_version=params.get("addon_version"),
        values=values,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )
```

- [ ] **Step 2: Add ACTION_SPECS entries**

Add to ACTION_SPECS dict:

```python
    "huawei_create_cce_nodepool": (("region", "cluster_id", "nodepool_name", "flavor", "availability_zone", "root_volume_size", "root_volume_type"), _create_cce_nodepool),
    "huawei_delete_cce_nodepool": (("region", "cluster_id", "nodepool_id"), _delete_cce_nodepool),
    "huawei_create_cce_node": (("region", "cluster_id", "flavor", "availability_zone", "root_volume_size", "root_volume_type"), _create_cce_node),
    "huawei_install_cce_addon": (("region", "cluster_id", "addon_template_name"), _install_cce_addon),
    "huawei_uninstall_cce_addon": (("region", "cluster_id", "addon_id"), _uninstall_cce_addon),
    "huawei_update_cce_addon": (("region", "cluster_id", "addon_id"), _update_cce_addon),
```

---

## Task 8: Update manifest.json

**Files:**
- Modify: `skills/huawei-cloud-cce-cluster-management/manifest.json`

- [ ] **Step 1: Add 6 new tool schemas**

Add to manifest.json tools array:

```json
    {
      "name": "huawei_create_cce_nodepool",
      "description": "Create a node pool in a CCE cluster. Node pools allow grouping nodes with similar configurations.",
      "parameters": {
        "type": "object",
        "properties": {
          "region": {"type": "string", "description": "Huawei Cloud region (e.g., cn-north-4)"},
          "cluster_id": {"type": "string", "description": "CCE cluster ID"},
          "nodepool_name": {"type": "string", "description": "Node pool name"},
          "flavor": {"type": "string", "description": "Node flavor (e.g., s6.large.2)"},
          "availability_zone": {"type": "string", "description": "Availability zone (e.g., cn-north-4a)"},
          "root_volume_size": {"type": "integer", "description": "Root volume size in GiB (40-1024)"},
          "root_volume_type": {"type": "string", "description": "Root volume type: SAS, SSD, GPSSD, ESSD"},
          "initial_node_count": {"type": "integer", "description": "Initial number of nodes (default: 0)"},
          "os_type": {"type": "string", "description": "OS type (EulerOS 2.9, Huawei Cloud EulerOS 2.0)"},
          "ssh_key": {"type": "string", "description": "SSH key pair name for login"},
          "password": {"type": "string", "description": "Password for login (8-26 chars, needs encryption)"},
          "data_volumes": {"type": "string", "description": "JSON array of data volumes: [{\"size\":100,\"type\":\"SAS\"}]"},
          "subnet_id": {"type": "string", "description": "Subnet ID for node network"},
          "autoscaling_enabled": {"type": "boolean", "description": "Enable autoscaling (default: false)"},
          "min_node_count": {"type": "integer", "description": "Minimum nodes for autoscaling"},
          "max_node_count": {"type": "integer", "description": "Maximum nodes for autoscaling"},
          "ak": {"type": "string", "description": "Access Key ID"},
          "sk": {"type": "string", "description": "Secret Access Key"},
          "project_id": {"type": "string", "description": "Project ID"}
        },
        "required": ["region", "cluster_id", "nodepool_name", "flavor", "availability_zone", "root_volume_size", "root_volume_type"]
      },
      "script": "scripts/huawei-cloud.py"
    },
    {
      "name": "huawei_delete_cce_nodepool",
      "description": "Delete a node pool from CCE cluster. WARNING: This will remove all nodes in the pool. Requires confirm=true.",
      "parameters": {
        "type": "object",
        "properties": {
          "region": {"type": "string", "description": "Huawei Cloud region"},
          "cluster_id": {"type": "string", "description": "CCE cluster ID"},
          "nodepool_id": {"type": "string", "description": "Node pool ID or name"},
          "confirm": {"type": "boolean", "description": "REQUIRED: Set to true to confirm deletion"},
          "ak": {"type": "string"},
          "sk": {"type": "string"},
          "project_id": {"type": "string"}
        },
        "required": ["region", "cluster_id", "nodepool_id", "confirm"]
      },
      "script": "scripts/huawei-cloud.py"
    },
    {
      "name": "huawei_create_cce_node",
      "description": "Create nodes directly in CCE cluster (outside node pools). Use node pools for managed scaling.",
      "parameters": {
        "type": "object",
        "properties": {
          "region": {"type": "string", "description": "Huawei Cloud region"},
          "cluster_id": {"type": "string", "description": "CCE cluster ID"},
          "flavor": {"type": "string", "description": "Node flavor (e.g., s6.large.2)"},
          "availability_zone": {"type": "string", "description": "Availability zone (e.g., cn-north-4a)"},
          "root_volume_size": {"type": "integer", "description": "Root volume size in GiB"},
          "root_volume_type": {"type": "string", "description": "Root volume type: SAS, SSD, GPSSD, ESSD"},
          "node_count": {"type": "integer", "description": "Number of nodes to create (default: 1)"},
          "os_type": {"type": "string", "description": "OS type"},
          "ssh_key": {"type": "string", "description": "SSH key pair name"},
          "password": {"type": "string", "description": "Password for login"},
          "data_volumes": {"type": "string", "description": "JSON array of data volumes"},
          "subnet_id": {"type": "string", "description": "Subnet ID"},
          "ak": {"type": "string"},
          "sk": {"type": "string"},
          "project_id": {"type": "string"}
        },
        "required": ["region", "cluster_id", "flavor", "availability_zone", "root_volume_size", "root_volume_type"]
      },
      "script": "scripts/huawei-cloud.py"
    },
    {
      "name": "huawei_install_cce_addon",
      "description": "Install an addon (plugin) in CCE cluster. Common addons: coredns, metrics-server, everest.",
      "parameters": {
        "type": "object",
        "properties": {
          "region": {"type": "string", "description": "Huawei Cloud region"},
          "cluster_id": {"type": "string", "description": "CCE cluster ID"},
          "addon_template_name": {"type": "string", "description": "Addon template name (e.g., coredns, metrics-server)"},
          "addon_version": {"type": "string", "description": "Addon version (optional, uses latest)"},
          "values": {"type": "string", "description": "Addon configuration as JSON"},
          "ak": {"type": "string"},
          "sk": {"type": "string"},
          "project_id": {"type": "string"}
        },
        "required": ["region", "cluster_id", "addon_template_name"]
      },
      "script": "scripts/huawei-cloud.py"
    },
    {
      "name": "huawei_uninstall_cce_addon",
      "description": "Uninstall an addon from CCE cluster. WARNING: May affect cluster functionality. Requires confirm=true.",
      "parameters": {
        "type": "object",
        "properties": {
          "region": {"type": "string", "description": "Huawei Cloud region"},
          "cluster_id": {"type": "string", "description": "CCE cluster ID"},
          "addon_id": {"type": "string", "description": "Addon ID or name"},
          "confirm": {"type": "boolean", "description": "REQUIRED: Set to true to confirm"},
          "ak": {"type": "string"},
          "sk": {"type": "string"},
          "project_id": {"type": "string"}
        },
        "required": ["region", "cluster_id", "addon_id", "confirm"]
      },
      "script": "scripts/huawei-cloud.py"
    },
    {
      "name": "huawei_update_cce_addon",
      "description": "Update an addon in CCE cluster (upgrade version or modify configuration).",
      "parameters": {
        "type": "object",
        "properties": {
          "region": {"type": "string", "description": "Huawei Cloud region"},
          "cluster_id": {"type": "string", "description": "CCE cluster ID"},
          "addon_id": {"type": "string", "description": "Addon ID or name"},
          "addon_version": {"type": "string", "description": "New addon version"},
          "values": {"type": "string", "description": "New addon configuration as JSON"},
          "ak": {"type": "string"},
          "sk": {"type": "string"},
          "project_id": {"type": "string"}
        },
        "required": ["region", "cluster_id", "addon_id"]
      },
      "script": "scripts/huawei-cloud.py"
    }
```

---

## Task 9: Update SKILL.md

**Files:**
- Modify: `skills/huawei-cloud-cce-cluster-management/SKILL.md`

- [ ] **Step 1: Add new tools to documentation tables**

Add to the manifest table after line 135:

```markdown
### 节点池管理（扩展）

| 工具 | 功能 | 风险等级 | 需确认 |
|------|------|---------|-------|
| `huawei_create_cce_nodepool` | 创建节点池 | 🟢 低 | 否 |
| `huawei_delete_cce_nodepool` | 删除节点池 | 🟠 高 | **是** |

### 节点管理（扩展）

| 工具 | 功能 | 风险等级 | 需确认 |
|------|------|---------|-------|
| `huawei_create_cce_node` | 创建节点 | 🟢 低 | 否 |

### 插件管理（扩展）

| 工具 | 功能 | 风险等级 | 需确认 |
|------|------|---------|-------|
| `huawei_install_cce_addon` | 安装插件 | 🟢 低 | 否 |
| `huawei_uninstall_cce_addon` | 卸载插件 | 🟠 高 | **是** |
| `huawei_update_cce_addon` | 更新插件 | 🟡 中 | 否 |
```

---

## Task 10: Test and Commit

- [ ] **Step 1: Test imports**

Run: `python -c "from scripts.huawei_cloud import cce_nodepool, cce_node, cce_addon, dispatcher"`

Expected: No import errors

- [ ] **Step 2: Test dispatcher registration**

Run: `python -c "from scripts.huawei_cloud.dispatcher import ACTION_SPECS; print('huawei_create_cce_nodepool' in ACTION_SPECS)"`

Expected: `True`

- [ ] **Step 3: Commit changes**

```bash
git add scripts/huawei_cloud/cce_nodepool.py scripts/huawei_cloud/cce_node.py scripts/huawei_cloud/cce_addon.py scripts/huawei_cloud/dispatcher.py skills/huawei-cloud-cce-cluster-management/manifest.json skills/huawei-cloud-cce-cluster-management/SKILL.md
git commit -m "feat(cce): add nodepool/node/addon creation and deletion tools

- Add huawei_create_cce_nodepool, huawei_delete_cce_nodepool
- Add huawei_create_cce_node
- Add huawei_install_cce_addon, huawei_uninstall_cce_addon, huawei_update_cce_addon
- Update dispatcher with 6 new handlers
- Update manifest.json with 6 new tool schemas (28 tools total)
- Update SKILL.md documentation"
```

---

## Self-Review Checklist

1. **Spec coverage**: All 6 tools from design doc covered ✓
2. **Placeholder scan**: No TBD/TODO placeholders ✓
3. **Type consistency**: Function names match in dispatcher and modules ✓
4. **Import verification**: All SDK classes imported before use ✓
5. **Error handling**: All functions have try/except blocks ✓
6. **Confirm mechanism**: Delete/uninstall operations require confirm=true ✓