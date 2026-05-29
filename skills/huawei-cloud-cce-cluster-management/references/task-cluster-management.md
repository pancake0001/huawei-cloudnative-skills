# 集群管理任务详解

## Overview

CCE 集群生命周期管理操作，包括创建、删除、休眠、唤醒和 EIP 绑定。

## Key Parameters

| 参数 | 说明 | 必填 |
|------|------|-----|
| `region` | 华为云区域 | 是 |
| `cluster_id` | 集群 ID | 是（除创建外） |
| `cluster_name` | 集群名称 | 创建时必填 |
| `cluster_version` | K8s 版本 | 创建时必填 |
| `flavor_id` | 集群规格 | 创建时必填 |
| `vpc_id` | VPC ID | 创建时必填 |
| `subnet_id` | 子网 ID | 创建时必填 |
| `cluster_type` | 集群类型 | 创建时可选 |
| `container_network_type` | 容器网络类型 | 创建时可选 |
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

### 创建标准集群

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=my-cluster \
  cluster_version=v1.28 \
  flavor_id=cce.s1.small \
  vpc_id=xxx \
  subnet_id=xxx
```

### 创建 Turbo 集群

Turbo 集群使用 ENI 容器网络，适合高性能场景。创建时设置 `cluster_type=VirtualMachine` 和 `container_network_type=eni`，API 会自动将 `spec.category` 设为 `Turbo`。

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=dev-turbo-cluster \
  cluster_version=v1.28 \
  cluster_type=VirtualMachine \
  container_network_type=eni \
  flavor_id=cce.s1.small \
  vpc_id=xxx \
  subnet_id=xxx
```

> **注意：Turbo 集群的节点池必须使用 ENI 兼容的 flavor（如 `c7.large.2`），且通常需要配置数据卷。**

### 删除集群（需二次确认）

```bash
# 预览删除
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx

# 确认删除
python3 huawei-cloud.py huawei_delete_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```

### 休眠集群

```bash
python3 huawei-cloud.py huawei_hibernate_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```

### 唤醒集群

```bash
python3 huawei-cloud.py huawei_awake_cce_cluster \
  region=cn-north-4 \
  cluster_id=xxx \
  confirm=true
```