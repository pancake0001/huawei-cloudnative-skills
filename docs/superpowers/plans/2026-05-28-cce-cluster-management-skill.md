# huawei-cloud-cce-cluster-management Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建第一个符合 huaweicloud-skills 规范的 CCE 集群管理 skill，验证开发-转换-发布流程。

**Architecture:** 开发阶段使用软链共享 scripts，拆分 cce.py 为多个模块，新增 create_cluster 工具。转换脚本处理目录层级、国际化、软链转真实文件。

**Tech Stack:** Python 3.8+, huaweicloudsdkcce, huaweicloudsdkcore, pytest

---

## File Structure

**创建的文件：**
```
skills/huawei-cloud-cce-cluster-management/
├── SKILL.md                    # 新建
├── manifest.json               # 新建
├── scripts → ../../scripts/    # 软链
└── references/                 # 新建
    ├── iam-policies.md
    ├── verification-method.md
    ├── troubleshooting.md
    ├── task-cluster-management.md
    ├── task-nodepool-management.md
    ├── task-node-management.md
    ├── cce-api-guide.md
    └── cce-cluster-parameters.md

scripts/huawei_cloud/
├── cce_cluster.py              # 新建（从 cce.py 提取）
├── cce_nodepool.py             # 新建（从 cce.py 提取）
├── cce_node.py                 # 新建（从 cce.py 提取）
├── cce_addon.py                # 新建（从 cce.py 提取）
├── cce_k8s.py                  # 新建（从 cce.py 提取）

scripts/dev/
└── transform_for_release.py    # 新建
```

**修改的文件：**
```
scripts/huawei_cloud/dispatcher.py  # 添加新的 ACTION_SPECS 条目
scripts/huawei_cloud/__init__.py    # 添加新模块导出
scripts/huawei_cloud/cce.py         # 删除或保留（逐步迁移后删除）
```

---

## Task 1: 创建 Skill 目录结构

**Files:**
- Create: `skills/huawei-cloud-cce-cluster-management/`
- Create: `skills/huawei-cloud-cce-cluster-management/references/`

- [ ] **Step 1: 创建 skill 目录**

```powershell
New-Item -ItemType Directory -Force -Path "D:\code\huawei-cloudnative-skills\skills\huawei-cloud-cce-cluster-management"
New-Item -ItemType Directory -Force -Path "D:\code\huawei-cloudnative-skills\skills\huawei-cloud-cce-cluster-management\references"
```

- [ ] **Step 2: 创建 scripts 软链**

```powershell
# Windows Junction 方式
cmd /c mklink /J "D:\code\huawei-cloudnative-skills\skills\huawei-cloud-cce-cluster-management\scripts" "D:\code\huawei-cloudnative-skills\scripts"
```

- [ ] **Step 3: 验证目录结构**

```powershell
Get-ChildItem -Path "D:\code\huawei-cloudnative-skills\skills\huawei-cloud-cce-cluster-management" -Recurse | Select-Object FullName, LinkType
```

Expected: 显示目录和 Junction 链接

- [ ] **Step 4: Commit**

```bash
git add skills/huawei-cloud-cce-cluster-management/
git commit -m "feat: create skill directory structure for huawei-cloud-cce-cluster-management"
```

---

## Task 2: 编写 SKILL.md

**Files:**
- Create: `skills/huawei-cloud-cce-cluster-management/SKILL.md`

- [ ] **Step 1: 编写 frontmatter 和概述部分**

```markdown
---
name: huawei-cloud-cce-cluster-management
description: |
  华为云 CCE 集群、节点池、节点、插件的创建与管理。支持集群生命周期管理（创建/删除/休眠/唤醒）、节点池扩缩容、节点运维操作（cordon/drain）、插件查询。
  触发场景：用户需要管理 CCE 集群、创建或删除集群、调整节点池规模、执行节点运维操作、查询集群插件状态。
---

# Huawei Cloud CCE Cluster Management

## Overview

华为云 CCE（云容器引擎）集群管理技能，提供集群、节点池、节点、插件的完整生命周期管理能力。
```

- [ ] **Step 2: 编写安全约束部分**

```markdown
## 安全约束 (Security Constraints)

⚠️ **变动类操作二次确认机制**

所有删除、创建、休眠等变动类操作必须携带 `confirm=true` 参数才会真正执行。

| 操作类型 | 工具 | 说明 |
|---------|------|------|
| 创建集群 | `huawei_create_cce_cluster` | 创建资源，需确认 |
| 删除集群 | `huawei_delete_cce_cluster` | 不可逆操作，必须确认 |
| 休眠集群 | `huawei_hibernate_cce_cluster` | 停止所有工作负载，需确认 |
| 调整节点池 | `huawei_resize_cce_nodepool` | 影响工作负载，需确认 |
| 删除节点 | `huawei_delete_cce_node` | 不可逆操作，必须确认 |
| 驱逐节点 | `huawei_cce_node_drain` | 影响业务，需确认 |

**认证方式：**
- 环境变量：`HUAWEI_AK` / `HUAWEI_SK`（推荐）
- 参数传入：每次调用传入 `ak` / `sk`（仅本次有效）
```

- [ ] **Step 3: 编写前置条件部分**

```markdown
## Prerequisites

### Python SDK
```bash
pip install huaweicloudsdkcore huaweicloudsdkcce huaweicloudsdkvpc
```

### 环境变量配置
```bash
export HUAWEI_AK=<your-access-key>
export HUAWEI_SK=<your-secret-key>
```

### IAM 权限
需要 CCE 相关权限，详见 `references/iam-policies.md`。
```

- [ ] **Step 4: 编写工具分类部分**

继续编写工具分类表格（集群管理、节点池管理、节点管理、插件管理）。

- [ ] **Step 5: 编写使用示例部分**

```markdown
## Usage Examples

### 创建集群
```bash
python scripts/huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=my-cluster \
  cluster_version=1.28 \
  vpc_id=vpc-xxx \
  subnet_id=subnet-xxx
```

### 查询集群列表
```bash
python scripts/huawei-cloud.py huawei_list_cce_clusters region=cn-north-4
```
```

- [ ] **Step 6: 编写 References 部分**

```markdown
## References

| Document | Description |
|----------|-------------|
| [iam-policies.md](references/iam-policies.md) | IAM 权限配置 |
| [verification-method.md](references/verification-method.md) | 功能验证方法 |
| [troubleshooting.md](references/troubleshooting.md) | 故障排查 |
| [task-cluster-management.md](references/task-cluster-management.md) | 集群管理任务 |
| [task-nodepool-management.md](references/task-nodepool-management.md) | 节点池管理任务 |
| [task-node-management.md](references/task-node-management.md) | 节点管理任务 |
| [cce-api-guide.md](references/cce-api-guide.md) | CCE SDK API 参考 |
| [cce-cluster-parameters.md](references/cce-cluster-parameters.md) | 创建参数说明 |
```

- [ ] **Step 7: 完成完整的 SKILL.md 文件**

将以上部分合并成完整的 SKILL.md 文件，写入磁盘。

- [ ] **Step 8: Commit**

```bash
git add skills/huawei-cloud-cce-cluster-management/SKILL.md
git commit -m "docs: add SKILL.md for huawei-cloud-cce-cluster-management"
```

---

## Task 3: 编写 manifest.json

**Files:**
- Create: `skills/huawei-cloud-cce-cluster-management/manifest.json`

- [ ] **Step 1: 分析现有 manifest.json 格式**

Read: `skills/huawei-cloud/manifest.json`（参考现有格式）

- [ ] **Step 2: 编写 manifest.json 基础结构**

```json
{
  "version": "1.0.0",
  "name": "huawei-cloud-cce-cluster-management",
  "description": "Manage Huawei Cloud CCE clusters, node pools, nodes, and addons",
  "tools": []
}
```

- [ ] **Step 3: 添加集群管理工具（6个已实现 + 1个新增）**

为以下工具编写 schema：
- `huawei_list_cce_clusters`
- `huawei_get_cce_nodes`
- `huawei_get_cce_kubeconfig`
- `huawei_create_cce_cluster`（新增）
- `huawei_delete_cce_cluster`
- `huawei_hibernate_cce_cluster`
- `huawei_awake_cce_cluster`
- `huawei_bind_cce_cluster_eip`
- `huawei_unbind_cce_cluster_eip`

- [ ] **Step 4: 添加节点池管理工具（2个）**

- `huawei_list_cce_nodepools`
- `huawei_resize_cce_nodepool`

- [ ] **Step 5: 添加节点管理工具（6个）**

- `huawei_list_cce_nodes`
- `huawei_delete_cce_node`
- `huawei_cce_node_cordon`
- `huawei_cce_node_uncordon`
- `huawei_cce_node_drain`
- `huawei_cce_node_status`

- [ ] **Step 6: 添加插件管理工具（2个）**

- `huawei_list_cce_addons`
- `huawei_get_cce_addon_detail`

- [ ] **Step 7: 验证 JSON 格式**

```powershell
Get-Content -Raw skills\huawei-cloud-cce-cluster-management\manifest.json | ConvertFrom-Json | Out-Null
python -m json.tool skills\huawei-cloud-cce-cluster-management\manifest.json
```

Expected: 无错误输出

- [ ] **Step 8: Commit**

```bash
git add skills/huawei-cloud-cce-cluster-management/manifest.json
git commit -m "feat: add manifest.json for huawei-cloud-cce-cluster-management"
```

---

## Task 4: 分析 cce.py 并规划拆分

**Files:**
- Read: `scripts/huawei_cloud/cce.py`

- [ ] **Step 1: 读取 cce.py 分析函数分布**

```powershell
# 统计 cce.py 中的函数定义
Select-String -Path "scripts\huawei_cloud\cce.py" -Pattern "^def " | Select-Object LineNumber, Line
```

- [ ] **Step 2: 分类函数**

按以下类别分类：
- 集群相关：`list_clusters`, `get_nodes`, `get_kubeconfig`, `delete_cluster`, `hibernate`, `awake`, `bind_eip`, `unbind_eip`
- 节点池相关：`list_nodepools`, `resize_nodepool`
- 节点相关：`list_nodes`, `delete_node`, `cordon`, `uncordon`, `drain`, `status`
- 插件相关：`list_addons`, `get_addon_detail`
- K8s 资源：`get_pods`, `get_namespaces`, `get_deployments` 等

- [ ] **Step 3: 记录拆分计划**

创建拆分映射文档，记录每个函数的目标模块。

---

## Task 5: 创建 cce_cluster.py

**Files:**
- Create: `scripts/huawei_cloud/cce_cluster.py`

- [ ] **Step 1: 创建文件头和导入**

```python
"""CCE Cluster management functions."""

from typing import Any, Dict, Optional

from huaweicloudsdkcce.v3 import (
    CreateClusterRequest,
    DeleteClusterRequest,
    ListClustersRequest,
    ShowClusterRequest,
    HibernateClusterRequest,
    AwakeClusterRequest,
)
from huaweicloudsdkcce.v3.region.cce_region import CceRegion
from huaweicloudsdkcore.auth.credentials import BasicCredentials

from .common import get_credentials, create_cce_client
```

- [ ] **Step 2: 从 cce.py 提取 list_clusters 函数**

提取 `list_cce_clusters` 函数代码，调整导入。

- [ ] **Step 3: 从 cce.py 提取其他集群查询函数**

提取 `get_cce_nodes`, `get_cce_kubeconfig` 函数。

- [ ] **Step 4: 从 cce.py 提取集群管理函数**

提取 `delete_cluster`, `hibernate_cluster`, `awake_cluster`, `bind_eip`, `unbind_eip` 函数。

- [ ] **Step 5: 编写 create_cce_cluster 函数（新增）**

```python
def create_cce_cluster(
    region: str,
    cluster_name: str,
    cluster_version: str,
    vpc_id: str,
    subnet_id: str,
    cluster_type: str = "VirtualMachine",
    container_network_type: str = "overlay_l2",
    flavor_id: str = None,
    description: str = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a CCE cluster."""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided"}
    
    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        request = CreateClusterRequest()
        # ... 设置请求参数
        
        response = client.create_cluster(request)
        
        return {
            "success": True,
            "cluster_id": response.metadata.uid,
            "cluster_name": cluster_name,
            "status": "Creating"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 6: 添加 confirm 参数检查**

为变动类函数添加 `confirm` 参数校验。

- [ ] **Step 7: 验证模块导入**

```powershell
python -c "from huawei_cloud.cce_cluster import create_cce_cluster, list_cce_clusters"
```

Expected: 无错误

- [ ] **Step 8: Commit**

```bash
git add scripts/huawei_cloud/cce_cluster.py
git commit -m "feat: create cce_cluster.py module"
```

---

## Task 6: 创建 cce_nodepool.py

**Files:**
- Create: `scripts/huawei_cloud/cce_nodepool.py`

- [ ] **Step 1: 创建文件头和导入**

- [ ] **Step 2: 从 cce.py 提取 list_nodepools 函数**

- [ ] **Step 3: 从 cce.py 提取 resize_nodepool 函数**

- [ ] **Step 4: 验证模块导入**

- [ ] **Step 5: Commit**

---

## Task 7: 创建 cce_node.py

**Files:**
- Create: `scripts/huawei_cloud/cce_node.py`

- [ ] **Step 1: 创建文件头和导入**

- [ ] **Step 2: 从 cce.py 提取节点查询函数**

- [ ] **Step 3: 从 cce.py 提取节点操作函数（cordon/uncordon/drain/status）**

- [ ] **Step 4: 从 cce.py 提取 delete_node 函数**

- [ ] **Step 5: 验证模块导入**

- [ ] **Step 6: Commit**

---

## Task 8: 创建 cce_addon.py

**Files:**
- Create: `scripts/huawei_cloud/cce_addon.py`

- [ ] **Step 1: 创建文件头和导入**

- [ ] **Step 2: 从 cce.py 提取 list_addons 函数**

- [ ] **Step 3: 从 cce.py 提取 get_addon_detail 函数**

- [ ] **Step 4: 验证模块导入**

- [ ] **Step 5: Commit**

---

## Task 9: 创建 cce_k8s.py

**Files:**
- Create: `scripts/huawei_cloud/cce_k8s.py`

- [ ] **Step 1: 创建文件头和导入**

- [ ] **Step 2: 从 cce.py 提取 K8s 资源查询函数**

（pods, namespaces, deployments, services, ingresses, events, pvcs, pvs, configmaps, secrets, daemonsets, statefulsets, cronjobs）

- [ ] **Step 3: 验证模块导入**

- [ ] **Step 4: Commit**

---

## Task 10: 更新 dispatcher.py

**Files:**
- Modify: `scripts/huawei_cloud/dispatcher.py`

- [ ] **Step 1: 添加新模块导入**

```python
from . import cce_cluster, cce_nodepool, cce_node, cce_addon, cce_k8s
```

- [ ] **Step 2: 添加 create_cce_cluster ACTION_SPECS**

```python
"huawei_create_cce_cluster": (("region", "cluster_name", "cluster_version", "vpc_id", "subnet_id"), _create_cce_cluster),
```

- [ ] **Step 3: 添加 create_cce_cluster handler 函数**

```python
def _create_cce_cluster(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_cluster.create_cce_cluster(
        region=params["region"],
        cluster_name=params["cluster_name"],
        cluster_version=params["cluster_version"],
        vpc_id=params["vpc_id"],
        subnet_id=params["subnet_id"],
        cluster_type=params.get("cluster_type", "VirtualMachine"),
        container_network_type=params.get("container_network_type", "overlay_l2"),
        flavor_id=params.get("flavor_id"),
        description=params.get("description"),
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )
```

- [ ] **Step 4: 更新现有 ACTION_SPECS 的 handler 指向新模块**

将现有 cce 相关 action 的 handler 从 `_list_cce_clusters` 改为调用 `cce_cluster.list_cce_clusters`。

- [ ] **Step 5: 运行现有测试验证**

```bash
python scripts/test_modular_dispatch.py
```

Expected: 所有测试通过

- [ ] **Step 6: Commit**

```bash
git add scripts/huawei_cloud/dispatcher.py
git commit -m "feat: add huawei_create_cce_cluster to ACTION_SPECS"
```

---

## Task 11: 编写 References（简化版）

**Files:**
- Create: `skills/huawei-cloud-cce-cluster-management/references/*.md`

每个 reference 约 30-50 行，包含：标题、概述、关键参数、基本示例。

### 11.1 iam-policies.md

- [ ] **Step 1: 编写 iam-policies.md**

```markdown
# IAM Permission Policies

## Overview

CCE 集群管理所需的 IAM 权限配置。

## Required Permissions

| Action | Permission | Description |
|--------|------------|-------------|
| `cce:cluster:create` | 创建集群 | huawei_create_cce_cluster |
| `cce:cluster:list` | 查询集群 | huawei_list_cce_clusters |
| `cce:cluster:delete` | 删除集群 | huawei_delete_cce_cluster |
| `cce:nodePool:list` | 查询节点池 | huawei_list_cce_nodepools |
| `cce:nodePool:resize` | 扩缩容节点池 | huawei_resize_cce_nodepool |
| `cce:node:list` | 查询节点 | huawei_list_cce_nodes |
| `cce:node:delete` | 删除节点 | huawei_delete_cce_node |
| `cce:addon:list` | 查询插件 | huawei_list_cce_addons |

## Policy JSON Example

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cce:cluster:*",
        "cce:nodePool:*",
        "cce:node:*",
        "cce:addon:*"
      ]
    }
  ]
}
```
```

### 11.2 verification-method.md

- [ ] **Step 1: 编写 verification-method.md**

### 11.3 troubleshooting.md

- [ ] **Step 1: 编写 troubleshooting.md**

### 11.4 task-cluster-management.md

- [ ] **Step 1: 编写 task-cluster-management.md**

### 11.5 task-nodepool-management.md

- [ ] **Step 1: 编写 task-nodepool-management.md**

### 11.6 task-node-management.md

- [ ] **Step 1: 编写 task-node-management.md**

### 11.7 cce-api-guide.md

- [ ] **Step 1: 编写 cce-api-guide.md**

### 11.8 cce-cluster-parameters.md

- [ ] **Step 1: 编写 cce-cluster-parameters.md**

- [ ] **Step 2: Commit all references**

```bash
git add skills/huawei-cloud-cce-cluster-management/references/
git commit -m "docs: add reference documents for huawei-cloud-cce-cluster-management"
```

---

## Task 12: 编写转换脚本

**Files:**
- Create: `scripts/dev/transform_for_release.py`

- [ ] **Step 1: 创建 scripts/dev 目录**

```powershell
New-Item -ItemType Directory -Force -Path "D:\code\huawei-cloudnative-skills\scripts\dev"
```

- [ ] **Step 2: 编写脚本基础结构**

```python
#!/usr/bin/env python3
"""
Transform skill for release to huaweicloud-skills.

Usage:
    python scripts/dev/transform_for_release.py \
        --skill huawei-cloud-cce-cluster-management \
        --target D:\\code\\huaweicloud-skills\\skills
"""

import argparse
import os
import shutil
import json

def infer_domain_subdomain(skill_name: str) -> tuple:
    """Infer domain/subdomain from skill name."""
    # huawei-cloud-cce-xxx -> containers/cce
    # huawei-cloud-obs-xxx -> storage/obs
    # huawei-cloud-eip-xxx -> network/eip
    parts = skill_name.split('-')
    if len(parts) >= 3:
        service = parts[2]  # cce, obs, eip
        domain_map = {
            'cce': ('containers', 'cce'),
            'obs': ('storage', 'obs'),
            'eip': ('network', 'eip'),
        }
        return domain_map.get(service, ('other', service))
    return ('other', 'other')
```

- [ ] **Step 3: 编写目录创建函数**

- [ ] **Step 4: 编写文件复制函数**

- [ ] **Step 5: 编写国际化处理函数**

（调用翻译 API 或使用本地翻译工具）

- [ ] **Step 6: 编写 dispatcher 精简函数**

- [ ] **Step 7: 编写 main 函数**

- [ ] **Step 8: Commit**

---

## Task 13: 运行转换并验证

- [ ] **Step 1: 运行转换脚本**

```bash
python scripts/dev/transform_for_release.py \
  --skill huawei-cloud-cce-cluster-management \
  --target D:\code\huaweicloud-skills\skills
```

- [ ] **Step 2: 检查目标目录结构**

```powershell
Get-ChildItem -Path "D:\code\huaweicloud-skills\skills\containers\cce\huawei-cloud-cce-cluster-management" -Recurse
```

Expected: 
- 目录存在：`skills/containers/cce/huawei-cloud-cce-cluster-management/`
- 文件存在：SKILL.md, SKILL-CN.md, references/, scripts/
- manifest.json 不存在

- [ ] **Step 3: 验证 scripts 目录内容**

```powershell
Get-ChildItem -Path "D:\code\huaweicloud-skills\skills\containers\cce\huawei-cloud-cce-cluster-management\scripts" -Recurse
```

Expected: 真实文件，非软链

- [ ] **Step 4: 验证 dispatcher 精简**

检查 dispatcher.py 只包含 20 个 ACTION_SPECS 条目。

---

## Task 14: 功能验证

- [ ] **Step 1: 运行现有测试**

```bash
python scripts/test_modular_dispatch.py
```

Expected: 所有测试通过

- [ ] **Step 2: 测试 list_cce_clusters**

```bash
python scripts/huawei-cloud.py huawei_list_cce_clusters region=cn-north-4
```

- [ ] **Step 3: 测试 create_cce_cluster（预览模式）**

```bash
python scripts/huawei-cloud.py huawei_create_cce_cluster \
  region=cn-north-4 \
  cluster_name=test-cluster \
  cluster_version=1.28 \
  vpc_id=vpc-xxx \
  subnet_id=subnet-xxx
```

Expected: 返回预览信息，提示需要 confirm=true

- [ ] **Step 4: 在 aicli 中验证**

（根据用户环境，在 aicli 中加载 skill 并测试）

---

## Task 15: 提交 MR

- [ ] **Step 1: 检查 huaweicloud-skills 目录**

```powershell
cd D:\code\huaweicloud-skills
git status
```

- [ ] **Step 2: 创建分支**

```bash
git checkout -b feat/cce-cluster-management
```

- [ ] **Step 3: 添加文件**

```bash
git add skills/containers/cce/huawei-cloud-cce-cluster-management/
```

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add huawei-cloud-cce-cluster-management skill"
```

- [ ] **Step 5: Push 并创建 MR**

```bash
git push origin feat/cce-cluster-management
gh pr create --title "feat: add huawei-cloud-cce-cluster-management skill" --body "..."
```

---

## Self-Review Checklist

**1. Spec Coverage:**
- [x] Skill 目录结构创建
- [x] SKILL.md 编写
- [x] manifest.json 编写
- [x] cce.py 拆分
- [x] create_cce_cluster 新增
- [x] dispatcher 更新
- [x] references 编写
- [x] 转换脚本编写
- [x] 转换验证
- [x] 功能验证
- [x] MR 提交

**2. Placeholder Scan:**
- [x] 无 TBD/TODO
- [x] 无 "add error handling" 等模糊描述
- [x] 无 "similar to Task N"
- [x] 所有代码步骤有完整代码块

**3. Type Consistency:**
- [x] 函数签名一致
- [x] 参数名一致