# Skill API 参数处理规范

> **适用范围**: 所有 huawei-cloud 系列技能
> **创建日期**: 2026-05-29
> **版本**: 1.0

---

## 一、参数分类与处置策略

### 1.1 必填参数分类

| 类型 | 特征 | 处置策略 | 示例 |
|------|------|---------|------|
| **用户输入型** | 名字、标签等业务标识 | 提供推荐格式，用户决定具体值 | `cluster_name`, `nodepool_name` |
| **资源查询型** | VPC、子网等已存在资源 | 先查询已有资源，返回人类可读属性供用户选择；无则提示创建 | `vpc_id`, `subnet_id` |
| **配置型** | 规格、版本等技术参数 | 提供推荐值（基于最佳实践） | `flavor`, `cluster_version` |

### 1.2 可选参数策略

| 类型 | 处置策略 | 示例 |
|------|---------|------|
| **技术配置** | 推荐默认值，说明可选范围 | `container_network_type: overlay_l2` |
| **高级选项** | 说明用途，用户按需设置 | `autoscaling_enabled`, `taints` |

---

## 二、具体实施规则

### 2.1 用户输入型参数

**规则**: 提供命名规范推荐值

**实施方式**: 在 tool description 中说明推荐格式

```json
{
  "name": "huawei_create_cce_cluster",
  "description": "Create a CCE cluster. Recommended naming: '<env>-<app>-cluster' (e.g., 'prod-web-cluster', 'dev-api-cluster').",
  "parameters": {
    "cluster_name": {
      "description": "Cluster name. Recommended format: '<env>-<app>-cluster'. Example: 'prod-web-cluster'"
    }
  }
}
```

**命名规范推荐**:
- 集群: `<env>-<app>-cluster` (如 `prod-web-cluster`)
- 节点池: `<env>-<role>-pool` (如 `prod-worker-pool`)
- 节点: `<env>-<role>-node-<index>` (如 `prod-worker-node-01`)

---

### 2.2 资源查询型参数

**规则**: 先查询已有资源，返回人类可读属性供用户选择

**实施方式**:
1. 提供专门的查询工具（如 `huawei_list_vpc`, `huawei_list_vpc_subnets`）
2. 查询结果包含人类可读属性（网段、名称、状态等）
3. 无可用资源时提示用户创建或返回默认创建建议

**查询结果格式要求**:

```json
{
  "success": true,
  "vpcs": [
    {
      "id": "vpc-xxx",
      "name": "prod-vpc",
      "cidr": "10.0.0.0/16",
      "status": "Active",
      "created_at": "2026-01-01"
    }
  ],
  "hint": "Use 'vpc_id' from above. If no suitable VPC found, consider creating one first or use default CIDR 10.0.0.0/16"
}
```

**关键字段要求**:
| 资源类型 | 必须返回的人类可读属性 |
|---------|---------------------|
| VPC | `name`, `cidr`, `status` |
| 子网 | `name`, `cidr`, `availability_zone` |
| 安全组 | `name`, `description` |
| 集群 | `name`, `status`, `version` |

---

### 2.3 配置型参数（技术规格）

**规则**: 推荐基于最佳实践的默认值

**CCE 专属推荐**:

| 参数 | 推荐值 | 原因 |
|------|-------|------|
| `cluster_type` | `Turbo` | Turbo集群支持云原生网络2.0，性能更高，ENI直通 |
| `container_network_type` | `eni` (Turbo) / `overlay_l2` (Standard) | Turbo用eni获得最佳性能 |
| `flavor` | `cce.s2.small` | 高可用三控制节点，最小规模50节点适合开发 |
| `cluster_version` | 不指定（API自动选最新） | 避免版本过时 |

**实施方式**: 在 description 中标注推荐值

```json
{
  "cluster_type": {
    "description": "Cluster type. Recommended: 'Turbo' for best performance with ENI network. Options: VirtualMachine, Turbo"
  },
  "container_network_type": {
    "description": "Container network type. Recommended: 'eni' for Turbo clusters (cloud-native network 2.0). Options: overlay_l2, vpc-router, eni"
  }
}
```

---

### 2.4 可选参数策略

**规则**: 使用安全默认值，说明可选范围

**示例**:

```json
{
  "autoscaling_enabled": {
    "description": "Enable autoscaling. Default: false. Set to true for dynamic scaling based on load.",
    "default": false
  },
  "initial_node_count": {
    "description": "Initial node count. Recommended: start with 2 for HA, or 0 for autoscaling-only pools.",
    "default": 0
  }
}
```

---

## 三、工具描述模板

### 3.1 创建类工具模板

```
Create a <resource>. 

**Required parameters**:
- <param1>: <description>. Recommended: <推荐值或格式>
- <param2>: <description>. Use `huawei_list_<resource>` to find available options.

**Recommended defaults**:
- <param3>: <推荐值> (<原因>)
- <param4>: <推荐值> (<原因>)

**Example**: <完整示例命令>
```

### 3.2 查询类工具模板

```
List <resources> in the specified region. Returns human-readable attributes: <列出关键属性>.

Use this tool to:
1. Find existing resources for reuse
2. Check resource status before operations
3. Get resource IDs for other tools

If no resources found, consider <建议操作>.
```

---

## 四、异常处理

### 4.1 无可用资源时的提示

当查询结果为空时，返回格式：

```json
{
  "success": true,
  "count": 0,
  "items": [],
  "hint": "No existing <resource> found. Options: (1) Create a new one first using `huawei_create_<resource>`; (2) Proceed with auto-create if supported"
}
```

### 4.2 参数缺失时的提示

```json
{
  "success": false,
  "error": "Required parameter '<param>' missing.",
  "hint": "Recommended value: '<推荐值>'. Example: '<param>=<推荐值>'"
}
```

---

## 五、实施清单

每个创建类工具应具备：

- [ ] 查询工具配套（`huawei_list_<resource>`）
- [ ] Description 包含推荐值
- [ ] Description 包含人类可读属性说明
- [ ] 无资源时的创建提示
- [ ] 最佳实践推荐（Turbo集群、eni网络等）

---

## 六、后续 Skill 参考

此规范适用于：

- `huawei-cloud-cce-*` 系列
- `huawei-cloud-ecs-*` 系列
- `huawei-cloud-vpc-*` 系列
- `huawei-cloud-obs-*` 系列
- 所有涉及资源创建的 skill

---

## References

- CCE Turbo集群优势: https://support.huaweicloud.com/productdesc-cce/cce_01_0321.html
- 云原生网络2.0: https://support.huaweicloud.com/usermanual-cce/cce_01_0304.html