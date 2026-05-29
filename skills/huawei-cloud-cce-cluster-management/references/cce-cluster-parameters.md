# 创建集群参数说明

## Overview

CCE 集群、节点池和节点创建所需参数详解，包含 Turbo 集群、密码加盐加密、ENI flavor 兼容性等关键约束。

## 集群必填参数

| 参数 | 说明 | 示例值 |
|------|------|-------|
| `region` | 华为云区域 | `cn-north-4` |
| `cluster_name` | 集群名称 | `my-cluster` |
| `cluster_version` | Kubernetes 版本 | `v1.28` |
| `flavor_id` | 集群规格 | `cce.s1.small` |
| `vpc_id` | VPC ID | `vpc-xxx` |
| `subnet_id` | 子网 ID | `subnet-xxx` |

## 集群可选参数

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `cluster_type` | 集群类型 | `VirtualMachine` |
| `container_network_type` | 容器网络类型 | `overlay_l2` |
| `container_network_cidr` | 容器网段 | 自动分配 |
| `eni_subnet_id` | ENI 子网 ID（Turbo 集群） | 空 |
| `description` | 集群描述 | 空 |

### Turbo 集群

创建 CCE Turbo（ENI 网络）集群时，需设置：

- `cluster_type=VirtualMachine`（Turbo 集群的 category 由 API 根据 container_network_type 自动判定）
- `container_network_type=eni`
- `flavor_id` 可使用 `cce.s1.small` 等任意规格

API 返回的 `spec.category` 会自动变为 `Turbo`。

## 集群规格

| 规格 | 说明 | 适用场景 |
|------|------|---------|
| `cce.s1.small` | 小规模，50 节点 | 开发测试 |
| `cce.s1.medium` | 中规模，200 节点 | 生产环境 |
| `cce.s1.large` | 大规模，1000 节点 | 大型应用 |
| `cce.s2.small` | 高可用小规模 | 高可用测试 |
| `cce.s2.medium` | 高可用中规模 | 高可用生产 |

## 节点池创建参数

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

### 登录认证（必填其中一项）

| 参数 | 说明 | 备注 |
|------|------|------|
| `ssh_key` | SSH 密钥对名称 | 与密码互斥 |
| 密码 | 从 `CCE_NODE_PASSWORD` 环境变量读取 | 8-26 位，需含大写、小写、数字、特殊字符中的至少三种 |

> **重要：密码通过 `CCE_NODE_PASSWORD` 环境变量传入，脚本自动进行 SHA-512 加盐加密 + base64 编码，无需手动处理。**

### CCE_NODE_PASSWORD 环境变量

创建节点/节点池时，如未提供 `ssh_key`，脚本从环境变量 `CCE_NODE_PASSWORD` 读取密码：

```bash
export CCE_NODE_PASSWORD="你的密码"
```

密码复杂度要求：
- 长度：8-26 位
- 至少包含大写字母、小写字母、数字、特殊字符中的三种
- 特殊字符：`!@$%^-_=+[]{}:,./?`

脚本自动验证密码复杂度，不符合要求时会返回错误提示。

### 密码加盐加密

> **重要：CCE API 要求 password 字段必须经过 SHA-512 加盐加密后 base64 编码，不能直接传入原始密码。**

加密步骤（Python）：

```python
from passlib.hash import sha512_crypt
import base64

hashed = sha512_crypt.using(rounds=5000).hash("原始密码")
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")
# salted_b64 即为 UserPassword.password 字段的值
```

需安装依赖：`pip install passlib`

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `os_type` | 操作系统 | `EulerOS` |
| `data_volumes` | 数据卷配置 JSON | 部分规格必填 |
| `subnet_id` | 子网 ID | 使用集群子网 |
| `autoscaling_enabled` | 是否启用自动伸缩 | `false` |
| `min_node_count` | 自动伸缩最小节点数 | 0 |
| `max_node_count` | 自动伸缩最大节点数 | 0 |

### 数据卷（data_volumes）

部分节点规格（如非本地盘类型）**必须配置数据卷**，否则创建失败。格式为 JSON 数组：

```bash
data_volumes='[{"size":100,"type":"SSD"}]'
```

### ENI Flavor 兼容性

> **重要：Turbo（ENI 网络）集群的节点池必须使用支持 ENI 的 flavor。**

不支持 ENI 的 flavor（如 `s6.large.2`, `c6.large.2`）会报错：
`Flavor [xxx] 's subeni quota is 0, Eni network is not supported`

推荐 Turbo 集群使用：`c7` 系列（如 `c7.large.2`）、`s7` 系列。

## 节点创建参数

节点直接创建（非节点池）的参数与节点池基本一致，额外包含：

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `node_count` | 创建节点数量 | `1` |

密码同样需要 SHA-512 加盐加密 + base64 编码。

## Kubernetes 版本

常用版本：`v1.27`, `v1.28`, `v1.29`, `v1.30`, `v1.31`

## 密码码加盐加密

创建节点/节点池时 `password` 字段需经 SHA-512 加盐加密后再 base64 编码，不可直接传入原始密码。

### 加盐方法

 参考：[CCE 密码加盐加密](https://support.huaweicloud.com/api-cce/add-salt.html)

 

 ### Python 示例

 ```python
from passlib.hash import sha512_crypt
import base64

 hashed = sha512_crypt.using(rounds=5000).hash("原始密码")
 salted_password = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")
 ```



### 密码复杂度要求

 - 长度：8-26 位
 - 至少包含大写字母、小写字母、数字、特殊字符中的三种
 - 特殊字符：`!@$%^-_=+[]{}:,./?`

## Example

### 创建标准集群

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=my-cluster \
  cluster_version=v1.28 \
  flavor_id=cce.s1.small \
  vpc_id=vpc-xxx \
  subnet_id=subnet-xxx
```

### 创建 Turbo 集群

```bash
python3 huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=dev-turbo-cluster \
  cluster_version=v1.28 \
  cluster_type=VirtualMachine \
  container_network_type=eni \
  flavor_id=cce.s1.small \
  vpc_id=vpc-xxx \
  subnet_id=subnet-xxx
```

### 创建节点池

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

## 注意事项

- 集群名称：1-63 字符，字母、数字、中划线
- VPC 和子网必须存在于指定区域
- 创建集群可能需要 5-15 分钟
- 集群规格创建后不可更改
- Turbo 集群节点必须使用 ENI 兼容的 flavor
- 非本地盘规格必须配置数据卷
- password 字段必须 SHA-512 加盐 + base64 编码，脚本已自动处理