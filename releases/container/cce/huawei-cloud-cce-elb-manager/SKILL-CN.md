---
id: huawei-cloud-cce-elb-manager
name: huawei-cloud-cce-elb-manager
description: 华为云 CCE 周边 ELB 管理技能，支持获取 ELB 实例列表和变更独享型 ELB L4/L7 规格。
---

# 华为云 CCE ELB 管理

本技能用于 CCE 周边 ELB 资源管理，当前包含两个动作：

| 动作 | 作用 | 风险 |
|------|------|------|
| `huawei_list_elb` | 获取指定 region 下的 ELB 实例列表，包含实例 ID、名称、类型、状态、VIP、L4/L7 规格 ID、EIP 信息等。 | R3 |
| `huawei_resize_elb_flavor` | 变更独享型 ELB 的 `l4_flavor_id` 和/或 `l7_flavor_id`。需要 `confirm=true` 才会执行。 | R0 |

## 风险规则

- `R3`：只读查询，无资源变更。
- `R2`：低风险且不涉及费用的操作，本技能当前不使用。
- `R1`：中风险操作，本技能当前不使用。
- `R0`：高风险操作。ELB 规格变更可能影响公网入口容量、费用和流量承载能力，必须用户明确授权。

## 使用边界

- 支持独享型 ELB 规格变更。
- 共享型 ELB 容量调整不在当前技能范围内。
- EIP 带宽扩容不在当前技能范围内，需要单独的 EIP/带宽变更能力。
