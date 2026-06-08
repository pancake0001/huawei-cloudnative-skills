# RiskRules

- Allows automated read-only queries for Service, Ingress, EndpointSlice, NetworkPolicy, Pod, Node, Events, Pod logs, ELB, EIP, NAT, Security Groups, ACL.
- Allow generation of Markdown diagnostic reports and read-only validation command suggestions.
- Does not modify Service, Ingress, NetworkPolicy, CoreDNS ConfigMap, Security Groups, ACLs, ELB listeners, ELB backends, EIP bindings, or NAT rules.
- Do not perform `kubectl exec`, packet capture, stress testing, or active traffic injection unless the user explicitly requests it and confirms the risks.
- `huawei_network_verify_pod_scheduling` is only used for verification and does not replace the execution of capacity expansion and contraction.
- Any network change proposal must describe the scope of impact, rollback method and verification criteria, and be forwarded to the `auto-remediation-runner` for preview.