# 常见问题排查

## Overview

CCE 集群管理操作中常见问题及解决方案。

## 问题分类

| 错误类型 | 可能原因 | 解决方案 |
|---------|---------|---------|
| 403 权限不足 | IAM 权限缺失 | 检查 IAM 策略配置 |
| 404 资源不存在 | 集群/节点 ID 错误 | 确认资源 ID 正确 |
| 400 参数错误 | 参数格式不正确 | 检查参数格式和取值 |
| 409 状态冲突 | 资源状态不允许操作 | 等待资源状态变更后重试 |

## 常见问题

### 1. 集群查询返回空列表

**可能原因：**
- 区域参数错误
- 当前账号无集群

**解决方案：**
```bash
# 确认区域正确
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# 检查其他区域
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-east-3
```

### 2. 节点操作返回权限不足

**可能原因：**
- IAM 缺少 `cce:node:update` 权限

**解决方案：**
在 IAM 控制台为用户添加 CCE 相关权限。

### 3. 集群休眠/唤醒失败

**可能原因：**
- 集群状态不支持该操作
- 集群正在执行其他任务

**解决方案：**
```bash
# 先查询集群状态
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# 确认状态为 Available 后再操作
```

### 4. 节点池扩缩容未生效

**可能原因：**
- 忘记添加 `confirm=true` 参数
- 节点池正在扩缩容中

**解决方案：**
```bash
# 添加 confirm 参数
python3 huawei-cloud.py huawei_resize_cce_nodepool \
  region=cn-north-4 \
  cluster_id=xxx \
  nodepool_id=xxx \
  node_count=5 \
  confirm=true
```

### 5. 创建节点/节点池时报密码相关错误

**错误信息：**
- `CCE_CM.0004 - Request is invalid, Unexpected initial node password format`
- `CCE_NODE_PASSWORD environment variable is not set`
- `CCE_NODE_PASSWORD length must be 8-26 characters`
- `CCE_NODE_PASSWORD must contain at least 3 of: uppercase, lowercase, digits, special chars`

**原因：**
- 未设置 `CCE_NODE_PASSWORD` 环境变量
- 密码复杂度不符合要求（8-26 位，至少含大写、小写、数字、特殊字符中的三种）
- 直接调用 CCE API 时密码未经过 SHA-512 加盐加密 + base64 编码

**解决方案：**
```bash
# 设置密码环境变量（需符合复杂度要求）
export CCE_NODE_PASSWORD="MyPass123!"

# 脚本会自动进行 SHA-512 加盐加密 + base64 编码，无需手动处理
python3 huawei-cloud.py huawei_create_cce_nodepool ...
```

直接调用 CCE API 时需自行加密：
```python
import os
from passlib.hash import sha512_crypt
import base64

password = os.environ.get("CCE_NODE_PASSWORD")
hashed = sha512_crypt.using(rounds=5000).hash(password)
salted_b64 = base64.b64encode(hashed.encode("utf-8")).decode("utf-8")
```

### 6. 创建节点池时报 "Flavor ENI network is not supported"

**错误信息：** `Flavor [xxx] 's subeni quota is 0, Eni network is not supported`

**原因：** Turbo（ENI 网络）集群的节点池使用了不支持 ENI 的节点规格。

**不支持 ENI 的规格：** `s6` 系列、`c6` 系列等
**支持 ENI 的规格：** `c7` 系列（如 `c7.large.2`）、`s7` 系列

**解决方案：**
```bash
# Turbo 集群使用 c7 系列 flavor
python3 huawei-cloud.py huawei_create_cce_nodepool \
  flavor=c7.large.2 \
  ...
```

### 7. 创建节点池时报 "Data volume needed"

**错误信息：** `Data volume needed for non-local-disk flavor or non-system diskType`

**原因：** 部分节点规格（非本地盘类型）必须配置数据卷。

**解决方案：**
```bash
python3 huawei-cloud.py huawei_create_cce_nodepool \
  ... \
  'data_volumes=[{"size":100,"type":"SSD"}]'
```

### 8. 查询插件详情时报 "instanceID is invalid"

**错误信息：** `CCE.03400001 - Invalid request., instanceID is invalid`

**原因：** `ShowAddonInstanceRequest` 的 `id` 字段传入了错误的值。

**解决方案：**
- `id` 字段应传入插件的实例 UID（从 `huawei_list_cce_addons` 或创建响应的 `uid` 字段获取）
- 不要使用 `addon_name` 字段（已弃用），应使用 `id` 字段
- 调用 `client.show_addon_instance()` 方法，不是 `client.show_addon()`

### 9. 安装插件时报 "InstanceSpec got unexpected keyword argument 'template_name'"

**错误信息：** `InstanceSpec.__init__() got an unexpected keyword argument 'template_name'`

**原因：** CCE SDK `InstanceSpec` 类的正确字段名是 `addon_template_name`，不是 `template_name`。

**解决方案：**
```python
spec = InstanceSpec(
    addon_template_name="volcano",  # 正确
    # template_name="volcano",      # 错误
    ...
)
```

### 10. 创建节点时报 "cannot import name 'CreateNodeRequestBody'"

**错误信息：** `cannot import name 'CreateNodeRequestBody' from 'huaweicloudsdkcce.v3'`

**原因：** CCE SDK 没有 `CreateNodeRequestBody` 类，应使用 `Node` 对象作为 `CreateNodeRequest` 的 body。

**解决方案：**
```python
from huaweicloudsdkcce.v3 import CreateNodeRequest, Node, NodeMetadata, NodeSpec

body = Node(kind="Node", api_version="v3", metadata=NodeMetadata(name="my-node"), spec=node_spec)
request = CreateNodeRequest(cluster_id="cluster-id")
request.body = body
response = client.create_node(request)
```

### 11. 创建节点时 SDK 属性名报错

**错误信息：** `Login.__init__() got an unexpected keyword argument 'userPassword'` 或类似

**原因：** CCE SDK Python 包属性名使用 snake_case，不是 camelCase。

**常见错误对照：**

| 错误写法 (camelCase) | 正确写法 (snake_case) |
|----------------------|----------------------|
| `Login(userPassword=...)` | `Login(user_password=...)` |
| `Login(sshkey=...)` | `Login(ssh_key=...)` |
| `NodeSpec(rootVolume=...)` | `NodeSpec(root_volume=...)` |
| `NodeSpec(dataVolumes=...)` | `NodeSpec(data_volumes=...)` |
| `NodeSpec(nodeNicSpec=...)` | `NodeSpec(node_nic_spec=...)` |
| `NodeNicSpec(subnetId=...)` | `NodeNicSpec(primary_nic={"subnetId": "xxx"})` |

### 12. NodeNicSpec 构造报错

**错误信息：** `NodeNicSpec.__init__() got an unexpected keyword argument 'subnetId'`

**原因：** `NodeNicSpec` 不直接接受 `subnetId` 参数，需通过 `primary_nic` dict 传入。

**解决方案：**
```python
node_nic_spec = NodeNicSpec(primary_nic={"subnetId": "subnet-id"})  # 正确
# NodeNicSpec(subnetId="subnet-id")  # 错误
```