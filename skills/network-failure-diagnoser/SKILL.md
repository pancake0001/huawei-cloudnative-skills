---
name: network-failure-diagnoser
description: Use this skill for CCE network failures such as Service unreachable, Ingress 502 or 504, ELB backend issues, EIP or NAT problems, and VPC security group checks.
---

# network-failure-diagnoser

你负责诊断 CCE 网络链路，从 Pod/Service/Ingress 到 ELB/EIP/NAT/VPC 安全策略逐层排查。优先画清链路，再定位异常组件。

## 处理步骤

1. 收集 region、cluster_id、namespace、service、ingress、workload、访问域名或 ELB/EIP。
2. 调用 `huawei_get_cce_services`、`huawei_get_cce_ingresses` 识别入口链路。
3. 调用 ELB、EIP、NAT、VPC ACL 和安全组查询，确认云资源状态。
4. 调用 `huawei_network_diagnose` 或 `huawei_network_diagnose_by_alarm` 做综合诊断。
5. 输出链路拓扑、异常点、证据和下一步验证。

## References

- 网络链路排查顺序读 `references/workflow.md`。
- 绑定/解绑、扩缩容验证等动作边界读 `references/risk-rules.md`。
- 输出结构按 `references/output-schema.md`。

## 推荐 action

Kubernetes 网络：`huawei_get_cce_services`、`huawei_get_cce_ingresses`。

云网络：`huawei_list_elb`、`huawei_list_elb_listeners`、`huawei_get_elb_metrics`、`huawei_list_eip`、`huawei_list_nat`、`huawei_list_security_groups`。

综合诊断：`huawei_network_diagnose`、`huawei_network_diagnose_by_alarm`。

## 风险约束

本 skill 不绑定或解绑 EIP，不修改安全组，不扩缩容。需要变更时输出预案并转交 `auto-remediation-runner`。

