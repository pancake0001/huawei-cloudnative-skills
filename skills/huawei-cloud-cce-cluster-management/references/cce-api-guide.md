# CCE SDK API 参考

## Overview

华为云 CCE Python SDK API 调用参考文档，包含关键注意事项和常见问题。

## SDK 安装

```bash
pip install huaweicloudsdkcore huaweicloudsdkcce huaweicloudsdkiam
```

节点密码加盐加密需要安装 passlib，脚本从 `CCE_NODE_PASSWORD` 环境变量读取密码并自动验证复杂度：

```bash
pip install passlib
export CCE_NODE_PASSWORD="你的密码"
```

## 认证配置

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

credentials = BasicCredentials(ak, sk, project_id)
client = CceClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(CceRegion.value_of("cn-north-4")) \
    .build()
```

## 主要 API

| API | 说明 | 对应工具 |
|-----|------|---------|
| ListClusters | 查询集群列表 | `huawei_list_cce_clusters` |
| CreateCluster | 创建集群 | `huawei_create_cce_cluster` |
| DeleteCluster | 删除集群 | `huawei_delete_cce_cluster` |
| UpdateCluster | 更新集群 | `huawei_hibernate/awake_cce_cluster` |
| ListNodes | 查询节点列表 | `huawei_list_cce_nodes` |
| CreateNode | 创建节点 | `huawei_create_cce_node` |
| DeleteNode | 删除节点 | `huawei_delete_cce_node` |
| ListNodePools | 查询节点池列表 | `huawei_list_cce_nodepools` |
| CreateNodePool | 创建节点池 | `huawei_create_cce_nodepool` |
| UpdateNodePool | 更新节点池 | `huawei_resize_cce_nodepool` |
| CreateAddonInstance | 安装插件 | `huawei_install_cce_addon` |
| ShowAddonInstance | 查询插件详情 | `huawei_get_cce_addon_detail` |
| ListAddonTemplates | 查询插件模板 | 无对应工具，需直接调用 SDK |

## 示例代码

### 查询集群列表

```python
from huaweicloudsdkcce.v3 import ListClustersRequest

request = ListClustersRequest()
response = client.list_clusters(request)
for cluster in response.items:
    print(f"Cluster: {cluster.metadata.name}, Status: {cluster.status.phase}")
```

### 创建节点池（含密码加盐）

> **重要：密码从 `CCE_NODE_PASSWORD` 环境变量读取，`UserPassword.password` 字段必须传入 SHA-512 加盐加密后 base64 编码的值，不能传入原始密码。**

```python
import os
from huaweicloudsdkcce.v3 import (
    CreateNodePoolRequest, NodePool, NodePoolMetadata, NodePoolSpec,
    NodeSpec, Login, UserPassword, Volume
)
from passlib.hash import sha512_crypt
import base64

password = os.environ.get("CCE_NODE_PASSWORD")
hashed = sha512_crypt.using(rounds=5000).hash(password)
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")

login = Login()
login.user_password = UserPassword(password=salted_b64)

node_spec = NodeSpec(
    flavor="c7.large.2",
    az="cn-north-4a",
    os="EulerOS",
    root_volume=Volume(size=40, volumetype="GPSSD"),
    login=login,
)
# Turbo 集群节点池还需配置 data_volumes
node_spec.data_volumes = [Volume(size=100, volumetype="SSD")]

spec = NodePoolSpec(initial_node_count=1, node_template=node_spec)
body = NodePool(kind="NodePool", api_version="v3", metadata=NodePoolMetadata(name="my-pool"), spec=spec)

request = CreateNodePoolRequest(cluster_id="cluster-id", body=body)
response = client.create_node_pool(request)
```

### 创建节点（含密码加盐）

> **重要：SDK 没有 `CreateNodeRequestBody` 类，应使用 `Node` 对象作为请求体。`NodeSpec.count` 设置节点数量。SDK 属性名使用 snake_case。**

```python
import os
from huaweicloudsdkcce.v3 import (
    CreateNodeRequest, Node, NodeMetadata, NodeSpec,
    Volume, Login, UserPassword, NodeNicSpec
)
from passlib.hash import sha512_crypt
import base64

password = os.environ.get("CCE_NODE_PASSWORD")
hashed = sha512_crypt.using(rounds=5000).hash(password)
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")

login = Login(user_password=UserPassword(username="root", password=salted_b64))
# 注意：属性名是 snake_case: user_password, ssh_key, root_volume, data_volumes, node_nic_spec

node_spec = NodeSpec(
    flavor="c7.large.2",
    az="cn-north-4a",
    os="EulerOS 2.9",
    root_volume=Volume(size=40, volumetype="SSD"),
    login=login,
    data_volumes=[Volume(size=100, volumetype="SSD")],  # snake_case, 不是 dataVolumes
    node_nic_spec=NodeNicSpec(primary_nic={"subnetId": "subnet-id"}),  # 注意：primary_nic 是 dict
    count=1,  # 节点数量在 NodeSpec.count 中设置
)

body = Node(
    kind="Node",
    api_version="v3",
    metadata=NodeMetadata(name="node-clusterid8"),
    spec=node_spec,
)

request = CreateNodeRequest(cluster_id="cluster-id")
request.body = body
response = client.create_node(request)
```

### 安装插件

> **重要：`InstanceSpec` 使用 `addon_template_name` 字段，不是 `template_name`。**

```python
from huaweicloudsdkcce.v3 import (
    CreateAddonInstanceRequest, AddonInstance, AddonMetadata, InstanceSpec
)

spec = InstanceSpec(
    cluster_id="cluster-id",
    version="1.21.7",
    addon_template_name="volcano",  # 注意：字段名是 addon_template_name，不是 template_name
    values={"basic": {"category": "small", "flavor": 1},
            "custom": {"default_scheduler": True}}
)

body = AddonInstance(
    kind="Addon", api_version="v3",
    metadata=AddonMetadata(annotations={"addon.install/type": "install"}),
    spec=spec
)

request = CreateAddonInstanceRequest(body=body)
response = client.create_addon_instance(request)
```

### 查询插件详情

> **重要：`ShowAddonInstanceRequest` 使用 `id` 字段，不是 `addon_name`。且使用 `show_addon_instance` 方法，不是 `show_addon`。**

```python
from huaweicloudsdkcce.v3 import ShowAddonInstanceRequest

request = ShowAddonInstanceRequest()
request.cluster_id = "cluster-id"
request.id = "addon-instance-id"  # 注意：字段名是 id，不是 addon_name

response = client.show_addon_instance(request)  # 注意：方法名是 show_addon_instance，不是 show_addon
print(f"Addon: {response.metadata.name}, Status: {response.status}")
```

### 查询插件模板版本

安装插件前需查询可用版本：

```python
from huaweicloudsdkcce.v3 import ListAddonTemplatesRequest

request = ListAddonTemplatesRequest()
request.cluster_id = "cluster-id"
request.addon_template_name = "volcano"

response = client.list_addon_templates(request)
for item in response.items:
    for v in item.spec.versions:
        print(f"  Version: {v.version}, Stable: {v.stable}")
```

### 更新节点调度状态

```python
from huaweicloudsdkcce.v3 import UpdateNodeRequest, NodeMetadata, NodeSpec

request = UpdateNodeRequest(
    cluster_id="cluster-id",
    node_id="node-id",
    body=NodeUpdateRequest(
        metadata=NodeMetadata(unschedulable=True)
    )
)
client.update_node(request)
```

## SDK 关键注意事项

| 问题 | 说明 |
|------|------|
| `InstanceSpec.template_name` | ❌ 错误字段名，应使用 `addon_template_name` |
| `ShowAddonInstanceRequest.addon_name` | ❌ 错误字段名，应使用 `id`（值为 addon 实例 UID） |
| `client.show_addon()` | ❌ 错误方法名，应使用 `client.show_addon_instance()` |
| `UserPassword.password` 原始密码 | ❌ 不能直接传入原始密码，必须 SHA-512 加盐 + base64 编码，脚本从 `CCE_NODE_PASSWORD` 环境变量读取并自动处理 |
| `CreateNodeRequestBody` | ❌ 不存在此类，应使用 `Node` 对象作为 `CreateNodeRequest` 的 body |
| SDK 属性名 camelCase | ❌ 部分旧示例使用 camelCase，SDK 实际使用 snake_case：`user_password`, `ssh_key`, `root_volume`, `data_volumes`, `node_nic_spec` |
| `NodeNicSpec(subnetId=...)` | ❌ 错误构造方式，应使用 `NodeNicSpec(primary_nic={"subnetId": "xxx"})` |
| `CreateNodeRequestBody.count` | ❌ 不存在，节点数量通过 `NodeSpec.count` 设置 |
| Turbo 集群节点 flavor | 必须使用 ENI 兼容的规格（如 `c7` 系列），`s6`、`c6` 等不支持 ENI |
| 非本地盘节点 data_volumes | 部分规格必须配置数据卷，否则创建失败 |

## 官方文档

- [CCE API 参考](https://support.huaweicloud.com/api-cce/cce_02_0082.html)
- [CCE Python SDK](https://support.huaweicloud.com/sdk-python/cce_02_0101.html)
- [密码加盐加密方法](https://support.huaweicloud.com/api-cce/add-salt.html)