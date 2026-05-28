# CCE SDK API 参考

## Overview

华为云 CCE Python SDK API 调用参考文档。

## SDK 安装

```bash
pip install huaweicloudsdkcore huaweicloudsdkcce huaweicloudsdkiam
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
| DeleteNode | 删除节点 | `huawei_delete_cce_node` |
| ListNodePools | 查询节点池列表 | `huawei_list_cce_nodepools` |
| UpdateNodePool | 更新节点池 | `huawei_resize_cce_nodepool` |

## 示例代码

### 查询集群列表

```python
from huaweicloudsdkcce.v3 import ListClustersRequest

request = ListClustersRequest()
response = client.list_clusters(request)
for cluster in response.items:
    print(f"Cluster: {cluster.metadata.name}, Status: {cluster.status.phase}")
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

## 官方文档

- [CCE API 参考](https://support.huaweicloud.com/api-cce/cce_02_0082.html)
- [CCE Python SDK](https://support.huaweicloud.com/sdk-python/cce_02_0101.html)