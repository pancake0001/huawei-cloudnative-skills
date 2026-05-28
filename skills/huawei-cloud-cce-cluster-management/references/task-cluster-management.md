# 集群管理任务详解

## Overview

CCE 集群生命周期管理操作，包括创建、删除、休眠、唤醒和 EIP 绑定。

## Key Parameters

| 参数 | 说明 | 必填 |
|------|------|-----|
| `region` | 华为云区域 | 是 |
| `cluster_id` | 集群 ID | 是（除创建外） |
| `name` | 集群名称 | 创建时必填 |
| `version` | K8s 版本 | 创建时必填 |
| `flavor` | 集群规格 | 创建时必填 |
| `vpc_id` | VPC ID | 创建时必填 |
| `subnet_id` | 子网 ID | 创建时必填 |
| `eip_id` | EIP ID | 绑定/解绑时必填 |
| `confirm` | 确认执行危险操作 | 危险操作必填 |

## 操作分类

| 操作 | 风险等级 | 需确认 |
|------|---------|-------|
| 创建集群 | 🟢 低 | 否 |
| 删除集群 | 🔴 极高 | 是 |
| 休眠集群 | 🟠 高 | 是 |
| 唤醒集群 | 🟠 高 | 是 |
| 绑定 EIP | 🟢 低 | 否 |
| 解绑 EIP | 🟡 中 | 否 |

## Example

```bash
# 查询集群列表
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# 创建集群
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  name=my-cluster \
  version=v1.28 \
  flavor=cce.s1.small \
  vpc_id=xxx \
  subnet_id=xxx

# 删除集群（需二次确认）
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true

# 休眠集群
python3 huawei-cloud.py huawei_hibernate_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true

# 唤醒集群
python3 huawei-cloud.py huawei_awake_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```