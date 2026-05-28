# 节点管理任务详解

## Overview

集群节点生命周期管理，包括查询、cordon、uncordon、drain 和删除操作。

## Key Parameters

| 参数 | 说明 | 必填 |
|------|------|-----|
| `region` | 华为云区域 | 是 |
| `cluster_id` | 集群 ID | 是 |
| `node_id` | 节点 ID | 是 |
| `confirm` | 确认执行危险操作 | 危险操作必填 |

## 节点调度状态

| 状态 | 说明 |
|------|------|
| Schedulable | 可调度，新 Pod 可分配到该节点 |
| Unschedulable | 不可调度，新 Pod 不会分配到该节点 |

## 操作说明

| 操作 | 功能 | 风险等级 | 需确认 |
|------|------|---------|-------|
| 查询节点列表 | 获取所有节点 | 🟢 低 | 否 |
| 查询节点状态 | 获取调度状态 | 🟢 低 | 否 |
| cordon | 标记不可调度 | 🟡 中 | 是 |
| uncordon | 恢复可调度 | 🟡 中 | 是 |
| drain | 驱逐所有 Pod | 🟠 高 | 是 |
| delete | 删除节点 | 🟠 高 | 是 |

## 常用操作流程

### 节点维护流程

```bash
# 1. 标记节点不可调度
python3 huawei-cloud.py huawei_cce_node_cordon \
  region=cn-north-4 cluster_id=xxx node_id=xxx confirm=true

# 2. 驱逐节点上的 Pod
python3 huawei-cloud.py huawei_cce_node_drain \
  region=cn-north-4 cluster_id=xxx node_id=xxx confirm=true

# 3. 执行维护操作...

# 4. 恢复节点调度
python3 huawei-cloud.py huawei_cce_node_uncordon \
  region=cn-north-4 cluster_id=xxx node_id=xxx confirm=true
```

## Example

```bash
# 查询节点列表
python3 huawei-cloud.py huawei_list_cce_nodes \
  region=cn-north-4 cluster_id=<cluster_id>

# 查询节点状态
python3 huawei-cloud.py huawei_cce_node_status \
  region=cn-north-4 cluster_id=<cluster_id> node_id=<node_id>
```