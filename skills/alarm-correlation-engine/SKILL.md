---
name: alarm-correlation-engine
description: Use this skill when Huawei Cloud AOM alarms need active and historical correlation, deduplication, severity grouping, or rule inspection.
---

# alarm-correlation-engine

你负责把 AOM 告警从噪声整理成可行动的告警线索。必须同时考虑 active 和 history，避免漏掉已经恢复但影响诊断的资源类告警。

## 处理步骤

1. 明确 region、cluster_name、时间窗口、严重级别和业务对象。
2. 优先调用 `huawei_list_aom_alarms` 获取 active + history 合并结果。
3. 用 `huawei_analyze_aom_alarms` 去重、分级、识别突发和长期告警。
4. 必要时核对告警规则、动作规则、静默规则。
5. 输出告警时间线、同源合并结果、Top 关注项和推荐诊断 skill。

## References

- 告警归并步骤读 `references/workflow.md`。
- 只读边界和误报处理读 `references/risk-rules.md`。
- 输出结构按 `references/output-schema.md`。

## 推荐 action

优先：`huawei_list_aom_alarms`、`huawei_analyze_aom_alarms`、`huawei_aom_alarm_inspection`。

规则核对：`huawei_list_aom_alarm_rules`、`huawei_list_aom_action_rules`、`huawei_list_aom_mute_rules`。

指标补证：`huawei_get_aom_metrics`。

## 风险约束

本 skill 不修改告警规则，不创建静默，不执行恢复动作。涉及变更时只输出建议并转交对应 skill。

