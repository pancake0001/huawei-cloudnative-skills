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

## Example

```bash
# 排查权限问题
# 1. 检查 IAM 策略
# 2. 验证 AK/SK 配置
# 3. 确认区域参数正确
```