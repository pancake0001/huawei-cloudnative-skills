# Risk Rules

- 允许自动执行 Service、Ingress、EndpointSlice、NetworkPolicy、Pod、Node、Events、Pod logs、ELB、EIP、NAT、安全组、ACL 的只读查询。
- 允许生成 Markdown 诊断报告和只读验证命令建议。
- 不修改 Service、Ingress、NetworkPolicy、CoreDNS ConfigMap、安全组、ACL、ELB 监听器、ELB 后端、EIP 绑定关系或 NAT 规则。
- 不执行 `kubectl exec`、抓包、压测、主动流量注入，除非用户明确要求并确认风险。
- `huawei_network_verify_pod_scheduling` 仅用于验证，不替代扩缩容执行。
- 任何网络变更建议必须说明影响范围、回滚方式和验证标准，并转交 `auto-remediation-runner` 预览。
