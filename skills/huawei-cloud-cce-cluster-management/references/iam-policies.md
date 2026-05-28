# CCE IAM 权限配置

## Overview

华为云 CCE 集群管理所需的 IAM 权限策略说明。

## Key Parameters

| 权限 | 说明 |
|------|------|
| `cce:cluster:list` | 查询集群列表 |
| `cce:cluster:get` | 查询集群详情 |
| `cce:cluster:create` | 创建集群 |
| `cce:cluster:delete` | 删除集群 |
| `cce:cluster:update` | 更新集群（休眠/唤醒/EIP 绑定） |
| `cce:node:list` | 查询节点列表 |
| `cce:node:get` | 查询节点详情 |
| `cce:node:delete` | 删除节点 |
| `cce:node:update` | 更新节点（cordon/uncordon/drain） |
| `cce:nodepool:list` | 查询节点池列表 |
| `cce:nodepool:update` | 更新节点池（扩缩容） |
| `cce:addon:list` | 查询插件列表 |
| `cce:addon:get` | 查询插件详情 |

## Minimum Required Policy (JSON)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cce:cluster:list",
        "cce:cluster:get",
        "cce:cluster:create",
        "cce:cluster:delete",
        "cce:cluster:update",
        "cce:node:list",
        "cce:node:get",
        "cce:node:delete",
        "cce:node:update",
        "cce:nodepool:list",
        "cce:nodepool:update",
        "cce:addon:list",
        "cce:addon:get"
      ],
      "Resource": ["CCE:*:*:cluster:*", "CCE:*:*:node:*", "CCE:*:*:nodepool:*"]
    }
  ]
}
```

## System Policies

| 系统策略 | 适用场景 |
|---------|---------|
| `CCE Administrator` | 完整集群管理权限 |
| `CCE Viewer` | 只读权限，查看集群信息 |
| `CES ReadOnlyAccess` | 查询监控指标 |

## Example

```bash
# 推荐组合：CCE Administrator + CES ReadOnlyAccess
# 在 IAM 控制台为用户组添加以上策略
```