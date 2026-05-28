# 功能验证步骤

## Overview

CCE 集群管理技能的功能验证流程。

## 验证清单

| 序号 | 验证项 | 命令示例 |
|-----|-------|---------|
| 1 | 查询集群列表 | `huawei_list_cce_clusters region=cn-north-4` |
| 2 | 查询节点列表 | `huawei_list_cce_nodes region=cn-north-4 cluster_id=xxx` |
| 3 | 查询节点池列表 | `huawei_list_cce_nodepools region=cn-north-4 cluster_id=xxx` |
| 4 | 获取 kubeconfig | `huawei_get_cce_kubeconfig region=cn-north-4 cluster_id=xxx` |
| 5 | 节点调度状态 | `huawei_cce_node_status region=cn-north-4 cluster_id=xxx node_id=xxx` |

## 验证步骤

### Step 1: 环境检查

```bash
# 检查 Python 环境
python3 --version

# 检查依赖
pip show huaweicloudsdkcce
```

### Step 2: 验证查询功能

```bash
# 查询集群列表
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# 预期结果：返回集群列表，包含 cluster_id、name、status 等字段
```

### Step 3: 验证节点管理

```bash
# 查询节点调度状态
python3 huawei-cloud.py huawei_cce_node_status \
  region=cn-north-4 \
  cluster_id=<cluster_id> \
  node_id=<node_id>

# 预期结果：返回 "Schedulable" 或 "Unschedulable"
```

### Step 4: 验证危险操作确认机制

```bash
# 不带 confirm 参数调用删除命令
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx

# 预期结果：返回预览和警告，不执行删除
```

## Example

```bash
# 完整验证流程
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4
python3 huawei-cloud.py huawei_list_cce_nodes region=cn-north-4 cluster_id=<cluster_id>
```