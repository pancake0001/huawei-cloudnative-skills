# 节点池管理任务详解

## Overview

节点池生命周期管理，包括创建节点池、查询节点池列表和调整节点数量。

## 创建节点池参数

### 必填参数

| 参数 | 说明 | 示例值 |
|------|------|-------|
| `region` | 华为云区域 | `cn-north-4` |
| `cluster_id` | 集群 ID | `xxx` |
| `nodepool_name` | 节点池名称 | `dev-worker-pool` |
| `flavor` | 节点规格 | `c7.large.2` |
| `availability_zone` | 可用区 | `cn-north-4a` |
| `root_volume_size` | 系统盘大小（GB） | `40` |
| `root_volume_type` | 系统盘类型 | `GPSSD` |
| `initial_node_count` | 初始节点数 | `1` |
| `ssh_key` 或 `password` | 登录认证（必填其一） | `KeyPair-dev` 或 `MyPass123!` |

### 登录认证

`ssh_key` 和 `password` 必填其中一项，互斥：
- `ssh_key`: SSH 密钥对名称
- `password`: 节点登录密码（8-26 位，至少含大写、小写、数字、特殊字符中的三种）

> **重要：脚本会自动对 password 进行 SHA-512 加盐加密 + base64 编码，无需手动处理。但如直接调用 CCE API，必须自行加密。**

### 数据卷（data_volumes）

部分节点规格（非本地盘类型）**必须配置数据卷**，否则创建报错：
`Data volume needed for non-local-disk flavor or non-system diskType`

```bash
data_volumes='[{"size":100,"type":"SSD"}]'
```

### ENI Flavor 兼容性

Turbo（ENI 网络）集群的节点池必须使用支持 ENI 的 flavor。不兼容的 flavor 会报错：
`Flavor [xxx] 's subeni quota is 0, Eni network is not supported`

| Flavor 系列 | ENI 支持 | 推荐场景 |
|-------------|---------|---------|
| `c7` 系列（如 `c7.large.2`） | ✅ 支持 | Turbo 集群推荐 |
| `s7` 系列 | ✅ 支持 | Turbo 集群 |
| `s6` 系列（如 `s6.large.2`） | ❌ 不支持 | 仅标准集群 |
| `c6` 系列（如 `c6.large.2`） | ❌ 不支持 | 仅标准集群 |

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `os_type` | 操作系统 | `EulerOS` |
| `subnet_id` | 子网 ID | 使用集群子网 |
| `autoscaling_enabled` | 启用自动伸缩 | `false` |
| `min_node_count` | 最小节点数 | 0 |
| `max_node_count` | 最大节点数 | 0 |

## 扩缩容参数

| 参数 | 说明 | 必填 |
|------|------|-----|
| `region` | 华为云区域 | 是 |
| `cluster_id` | 集群 ID | 是 |
| `nodepool_id` | 节点池 ID | 是 |
| `node_count` | 目标节点数 | 是 |
| `confirm` | 确认执行 | 是 |

## 节点池状态

| 状态 | 说明 |
|------|------|
| Active | 正常运行 |
| Scaling | 正在扩缩容 |
| Deleting | 删除中 |
| Error | 异常状态 |

## 操作说明

### 创建节点池（标准集群）

```bash
python3 huawei-cloud.py huawei_create_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_name=dev-worker-pool \
  flavor=s6.large.2 \
  availability_zone=cn-north-4a \
  root_volume_size=40 \
  root_volume_type=GPSSD \
  initial_node_count=2 \
  ssh_key=KeyPair-dev
```

### 创建节点池（Turbo 集群）

```bash
export CCE_NODE_PASSWORD="你的密码"

python3 huawei-cloud.py huawei_create_cce_nodepool \
    region=cn-north-4 \
    cluster_id=xxx \
    nodepool_name=dev-worker-pool \
    flavor=c7.large.2 \
    availability_zone=cn-north-4a \
    root_volume_size=40 \
    root_volume_type=GPSSD \
    initial_node_count=1 \
    'data_volumes=[{"size":100,"type":"SSD"}]'
```

### 查询节点池

```bash
python3 huawei-cloud.py huawei_list_cce_nodepools \
  region=cn-north-4 \
  cluster_id=xxx
```

### 扩容节点池

```bash
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=10 \
  confirm=true
```

### 缩容节点池

```bash
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=3 \
  confirm=true
```