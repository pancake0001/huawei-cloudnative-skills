# Workflow

1. 确认访问路径：client -> DNS -> EIP/ELB -> Ingress -> Service -> Endpoint/Pod。
2. 检查 Service selector 和后端 Pod 是否匹配。
3. 检查 Ingress 规则、注解、证书和关联 ELB。
4. 检查 ELB 监听器、后端健康、状态码、P99、QPS、连接数。
5. 检查 EIP 带宽、NAT 网关、VPC ACL、安全组方向规则。
6. 关联 Events、AOM 告警和网络诊断结果。
7. 输出异常链路组件、证据和验证命令。

