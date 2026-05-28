# 节点池管理任务详解

## Overview

节点池生命周期管理，包括查询节点池列表和调整节点数量。

## Key Parameters

| 参数 | 说明 | 必填 |
|------|------|-----|
| `region` | 华为云区域 | 是 |
| `cluster_id` | 集群 ID | 是 |
| `nodepool_id` | 节点池 ID | 扩缩容时必填 |
| `node_count` | 目标节点数 | 扩缩容时必填 |
| `confirm` | 确认执行 | 扩缩容时必填 |

## 节点池状态

| 状态 | 说明 |
|------|------|
| Active | 正常运行 |
| Scaling | 正在扩缩容 |
| Deleting | 删除中 |
| Error | 异常状态 |

## 操作说明

### 查询节点池

```bash
python3 huawei-cloud.py huawei_list_cce_nodepools \
  region=cn-north-4 \
  cluster_id=xxx
```

### 扩容节点池

扩容会增加节点数量，可能产生额外费用。

```bash
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=10 \
  confirm=true
```

### 缩容节点池

缩容会减少节点数量，可能影响业务调度。

```bash
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=3 \
  confirm=true
```

## Example

```bash
# 查询节点池
python3 huawei-cloud.py huawei_list_cce_nodepools \
  region=cn-north-4 \
  cluster_id=<cluster_id>

# 扩容到 5 节点
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=<cluster_id> \
  nodepool_id=<nodepool_id> \
  node_count=5 \
  confirm=true
```