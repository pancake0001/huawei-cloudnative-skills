---
name: root-cause-analyzer
description: Use this skill when a Huawei Cloud CCE incident spans alarms, workloads, nodes, network, and metrics, or when the user needs Top root causes and an evidence-backed diagnosis report.
---

# root-cause-analyzer

你负责把多域证据收敛成根因结论。不要一开始就给恢复动作，先建立假设、证据、反证和影响范围。

## 处理步骤

1. 明确故障现象、时间窗口、影响业务和已知对象。
2. 汇总告警、事件、Pod/Node/Network 诊断结果。
3. 对工作负载、网络、节点分别调用综合诊断工具。
4. 生成 Top3 根因，逐条附证据和置信度。
5. 如需要正式交付，调用 `huawei_generate_diagnosis_report`。
6. 恢复动作只作为建议，交给 `auto-remediation-runner` 做预览和确认。

## References

- 证据链和根因排序读 `references/workflow.md`。
- 风险边界读 `references/risk-rules.md`。
- 报告结构按 `references/output-schema.md`。

## 推荐 action

综合：`huawei_workload_diagnose`、`huawei_network_diagnose`、`huawei_node_diagnose`。

报告：`huawei_generate_diagnosis_report`、`huawei_generate_monitor_dashboard`。

告警：`huawei_analyze_aom_alarms`。

## 风险约束

本 skill 输出根因和建议，不执行变更。任何需要 `confirm=true` 的动作都必须转交 `auto-remediation-runner`。

