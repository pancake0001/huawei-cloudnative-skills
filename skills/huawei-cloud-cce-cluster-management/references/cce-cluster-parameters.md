# 创建集群参数说明

## Overview

CCE 集群创建所需参数详解。

## 必填参数

| 参数 | 说明 | 示例值 |
|------|------|-------|
| `region` | 华为云区域 | `cn-north-4` |
| `name` | 集群名称 | `my-cluster` |
| `version` | Kubernetes 版本 | `v1.28` |
| `flavor` | 集群规格 | `cce.s1.small` |
| `vpc_id` | VPC ID | `vpc-xxx` |
| `subnet_id` | 子网 ID | `subnet-xxx` |

## 可选参数

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `description` | 集群描述 | 空 |
| `cluster_type` | 集群类型 | `VirtualMachine` |
| `container_network_type` | 容器网络类型 | `overlay_l2` |
| `container_network_cidr` | 容器网段 | 自动分配 |
| `eni_subnet_id` | ENI 子网 ID | 空 |
| `authentication_mode` | 认证模式 | `rbac` |

## 集群规格

| 规格 | 说明 | 适用场景 |
|------|------|---------|
| `cce.s1.small` | 小规模，50 节点 | 开发测试 |
| `cce.s1.medium` | 中规模，200 节点 | 生产环境 |
| `cce.s1.large` | 大规模，1000 节点 | 大型应用 |
| `cce.s2.small` | 高可用小规模 | 高可用测试 |
| `cce.s2.medium` | 高可用中规模 | 高可用生产 |

## Kubernetes 版本

```bash
# 查询支持的版本
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4
```

常用版本：`v1.27`, `v1.28`, `v1.29`

## Example

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  name=my-cluster \
  version=v1.28 \
  flavor=cce.s1.small \
  vpc_id=vpc-xxx \
  subnet_id=subnet-xxx
```

## 注意事项

- 集群名称：1-63 字符，字母、数字、中划线
- VPC 和子网必须存在于指定区域
- 创建集群可能需要 5-15 分钟
- 集群规格创建后不可更改