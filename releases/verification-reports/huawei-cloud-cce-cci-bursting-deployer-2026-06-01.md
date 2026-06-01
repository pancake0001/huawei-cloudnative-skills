# huawei-cloud-cce-cci-bursting-deployer 验证报告

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Skill | `huawei-cloud-cce-cci-bursting-deployer` |
| 验证工具 | `aicli v1.0.0-beta.2` |
| 验证环境 | CCE 集群 `aicli` 命名空间，Pod `aicli-dcfcf5595-4gf22` |
| 验证时间 | 2026-06-01 |
| 区域 | `cn-north-4` |
| 集群 ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| 操作性质 | 预检查（preview） |

## 验证结果

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 触发 | 通过 | aicli 正确加载并识别该 skill |
| CCE to CCI 预检查 | 通过 | `huawei_precheck_cce_cci_bursting` 返回 `success=true`，`issues=0` |
| 安全边界 | 通过 | 未执行部署或变更，仅做预检查 |
| 凭证安全 | 通过 | 未输出 AK/SK/Token |

## 关键发现

- 预检查链路正常，集群当前无阻碍 bursting 的问题
- 仅执行预检查，未创建测试负载，符合安全边界

## 修复记录

| 编号 | 类型 | 问题 | 修复 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 参数兼容性 | CLI dispatcher 仅支持 `key=value` 格式 | 增强 `_parse_cli_params` 支持 `key=value`、`--key=value`、`--key value` |

## 最终结论

**通过**。预检查功能正常，安全边界完好。

## aicli 实际输出

```json
{
  "success": true,
  "action": "precheck_cce_cci_bursting",
  "region": "cn-north-4",
  "cluster_id": "1d450236-5b28-11f1-a7f6-0255ac10026a",
  "network": {
    "cluster_id": "1d450236-5b28-11f1-a7f6-0255ac10026a",
    "cluster_name": "cce-ai-diagnoses",
    "category": "Turbo",
    "container_network_mode": "eni",
    "vpc_id": "550bb667-9b99-4649-9ff7-836e44e0a90d",
    "host_vpc_subnet_id": "3b83808b-fc2a-4a67-b941-b4b47cb17510",
    "cci_neutron_subnet_id": "b41ec4fe-79db-4c81-8a71-c2351e24378a"
  },
  "subnet_roles": {
    "cci_addon_neutron_subnet_id": "b41ec4fe-79db-4c81-8a71-c2351e24378a",
    "vpcep_vpc_subnet_id": "3b83808b-fc2a-4a67-b941-b4b47cb17510",
    "note": "These are different ID namespaces. Do not swap them."
  },
  "virtual_kubelet": {
    "name": "virtual-kubelet",
    "uid": "50fa5b88-c522-4453-8403-93a0234112ab",
    "template_name": null,
    "version": "1.5.82",
    "status": "available",
    "description": "An add-on that schedules CCE pods onto CCI clusters.",
    "created_at": "2026-05-30"
  },
  "vpc_subnets": [
    {

... (共       50 行，此处截取前 30 行)
```
