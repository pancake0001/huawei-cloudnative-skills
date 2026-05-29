# Risk Rules

- 允许自动执行 Service、Ingress、ELB、EIP、NAT、安全组、ACL 的只读查询。
- 不修改安全组、ACL、ELB 监听器、EIP 绑定关系。
- `huawei_network_verify_pod_scheduling` 仅用于验证，不替代扩缩容执行。
- 任何网络变更建议必须说明影响范围、回滚方式和验证标准。

