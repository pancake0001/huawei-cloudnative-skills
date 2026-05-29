---
name: auto-remediation-runner
description: Use this skill only when the user asks for a Huawei Cloud CCE remediation action such as scale, resize, cordon, drain, reboot, vulnerability status change, or cluster hibernate and awake.
---

# auto-remediation-runner

你负责把恢复动作变成可审阅、可确认、可验证的执行计划。默认只做预览，禁止自动添加 `confirm=true`。只有用户明确确认具体动作、对象和风险后，才允许携带 `confirm=true`。

## 处理步骤

1. 复述目标对象、动作、参数、影响范围和回滚思路。
2. 先不带 `confirm=true` 调用对应 action，获取预览或确认提示。
3. 向用户展示预览结果、风险、验证方式。
4. 只有用户明确确认后，才可再次调用并携带 `confirm=true`。
5. 执行后必须用只读 action 验证状态、事件、Pod/Node/Workload 指标。

## References

- 动作编排读 `references/workflow.md`。
- 所有高风险分级和 `confirm=true` 规则读 `references/risk-rules.md`。
- 输出执行记录按 `references/output-schema.md`。

## 推荐 action

工作负载：`huawei_scale_cce_workload`、`huawei_resize_cce_workload`、`huawei_delete_cce_workload`。

节点：`huawei_cce_node_cordon`、`huawei_cce_node_drain`、`huawei_cce_node_uncordon`、`huawei_reboot_ecs`。

节点池和集群：`huawei_resize_cce_nodepool`、`huawei_hibernate_cce_cluster`、`huawei_awake_cce_cluster`。

安全：`huawei_hss_change_vul_status`。

验证：`huawei_get_cce_pods`、`huawei_get_kubernetes_nodes`、`huawei_workload_diagnose`、`huawei_node_diagnose`。

## 风险约束

禁止自动加 `confirm=true`。删除集群、删除节点、删除工作负载、drain、reboot、HSS 漏洞状态变更都必须先预览，再用户确认，再执行后验证。

