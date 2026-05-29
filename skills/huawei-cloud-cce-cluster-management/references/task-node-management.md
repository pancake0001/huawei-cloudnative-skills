# 节点管理任务详解

## Overview

集群节点生命周期管理，包括创建、查询、cordon、uncordon、drain 和删除操作。

## 创建节点参数

### 必填参数

| 参数 | 说明 | 示例值 |
|------|------|-------|
| `region` | 华为云区域 | `cn-north-4` |
| `cluster_id` | 集群 ID | `xxx` |
| `flavor` | 节点规格 | `c7.large.2` |
| `availability_zone` | 可用区 | `cn-north-4a` |
| `root_volume_size` | 系统盘大小（GB） | `40` |
| `root_volume_type` | 系统盘类型 | `GPSSD` |
| `ssh_key` 或密码 | 登录认证（必填其一） | `KeyPair-dev` 或 `CCE_NODE_PASSWORD` 环境变量 |

### 登录认证

`ssh_key` 和密码必填其中一项，互斥：
- `ssh_key`: SSH 密钥对名称
- 密码: 通过 `CCE_NODE_PASSWORD` 环境变量传入（8-26 位，至少含大写、小写、数字、特殊字符中的三种）

> **重要：密码从 `CCE_NODE_PASSWORD` 环境变量读取，脚本自动进行 SHA-512 加盐加密 + base64 编码，无需手动处理。**

```bash
export CCE_NODE_PASSWORD="你的密码"
```

### 数据卷（data_volumes）

部分节点规格（非本地盘类型）**必须配置数据卷**：

```bash
data_volumes='[{"size":100,"type":"SSD"}]'
```

### ENI Flavor 兼容性

Turbo（ENI 网络）集群的节点必须使用支持 ENI 的 flavor（如 `c7` 系列），`s6`、`c6` 等不支持 ENI。

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `node_count` | 创建节点数量 | `1` |
| `os_type` | 操作系统 | `EulerOS` |
| `subnet_id` | 子网 ID | 使用集群子网 |

## 调度管理参数

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
| 创建节点 | 新增节点 | 🟢 低 | 否 |
| 查询节点列表 | 获取所有节点 | 🟢 低 | 否 |
| 查询节点状态 | 获取调度状态 | 🟢 低 | 否 |
| cordon | 标记不可调度 | 🟡 中 | 是 |
| uncordon | 恢复可调度 | 🟡 中 | 是 |
| drain | 驱逐所有 Pod | 🟠 高 | 是 |
| delete | 删除节点 | 🟠 高 | 是 |

### 创建节点（Turbo 集群）

```bash
export CCE_NODE_PASSWORD="你的密码"

python3 huawei-cloud.py huawei_create_cce_node \
    region=cn-north-4 \
    cluster_id=xxx \
    flavor=c7.large.2 \
    availability_zone=cn-north-4a \
    root_volume_size=40 \
    root_volume_type=GPSSD \
    node_count=1 \
    'data_volumes=[{"size":100,"type":"SSD"}]'
```

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