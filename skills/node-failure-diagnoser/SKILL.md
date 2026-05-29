---
name: node-failure-diagnoser
description: Use this skill for CCE node issues such as NotReady, resource pressure, NPD events, node vulnerability checks, or node-level scheduling failures.
---

# node-failure-diagnoser

你负责诊断节点健康和节点承载的工作负载影响。先看 Kubernetes Node 状态，再看 CCE 节点、资源指标、NPD/事件、安全组和 HSS 漏洞。

## 处理步骤

1. 收集 region、cluster_id、node_name 或 node_ip。
2. 调用 `huawei_get_kubernetes_nodes`、`huawei_get_cce_nodes` 确认状态和规格。
3. 调用 `huawei_get_cce_node_metrics` 或 TopN 指标判断 CPU、内存、磁盘、网络压力。
4. 调用 `huawei_node_diagnose` 或 `huawei_node_batch_diagnose` 做深度节点诊断。
5. 涉及漏洞时读取 HSS 主机和漏洞清单。
6. 输出节点影响范围、证据链和需要确认的恢复动作建议。

## References

- 节点 NotReady 和资源压力流程读 `references/workflow.md`。
- cordon、drain、reboot、漏洞修复边界读 `references/risk-rules.md`。
- 输出字段按 `references/output-schema.md`。

## 推荐 action

节点诊断：`huawei_get_kubernetes_nodes`、`huawei_get_cce_node_metrics`、`huawei_node_diagnose`、`huawei_node_batch_diagnose`。

巡检项：`huawei_node_status_inspection`、`huawei_node_resource_inspection`、`huawei_node_vul_inspection`。

安全：`huawei_hss_list_hosts`、`huawei_hss_list_host_vuls_all`。

## 风险约束

本 skill 不 cordon、不 drain、不 reboot、不修改漏洞状态。需要动作时转交 `auto-remediation-runner`，并要求用户确认。

