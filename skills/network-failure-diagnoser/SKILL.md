---
name: network-failure-diagnoser
description: Use this skill for CCE Kubernetes network failures such as Service unreachable, DNS/CoreDNS errors, Ingress 502/504, NetworkPolicy blocks, ELB backend health issues, EIP/NAT/VPC/security-group problems, and end-to-end Markdown diagnosis reports.
---

# network-failure-diagnoser

You are responsible for diagnosing CCE network links, from node base, DNS, Service/EndpointSlice, NetworkPolicy, Ingress to cloud ELB/EIP/NAT/VPC security policies layer by layer. By default, a complete Markdown report is produced, which must include the investigation process, evidence, conclusion, confidence level and verification standards.

# # Processing steps

1. Collect `region`, `cluster_id`, `namespace`, and try to complete `target_kind`, `target_name`, `service_name`, `ingress_name`, `source_pod`, `destination_pod`, `domain`, `failure_symptom` or `elb_id`.
2. It is preferred to call `huawei_network_failure_diagnose` to collect K8s and cloud side read-only snapshots at one time and return `report_markdown`.
3. If the user only needs the original object, call `huawei_get_cce_services`, `huawei_get_cce_ingresses`, `huawei_get_cce_pods`, `huawei_get_kubernetes_nodes`, `huawei_get_cce_events`, `huawei_get_pod_logs` as needed.
4. If it is an external access link, add `huawei_get_elb_backend_status`, `huawei_get_elb_metrics`, `huawei_list_security_groups`, `huawei_list_vpc_acls`, `huawei_list_eip`, `huawei_list_nat`.
5. The output must reference specific objects, events, log fragments or cloud API fields; if there is no evidence, write "insufficient evidence" and do not write guesses as conclusions.

# # References

- Read `references/workflow.md` for reusability, gapping and hierarchical diagnostic pipelines.
- For action boundaries such as binding/unbinding, capacity expansion and contraction verification, read `references/risk-rules.md`.
- Output schema as per `references/output-schema.md`.

# # Recommended action

Preferred diagnosis: `huawei_network_failure_diagnose`. This action returns structured fields and the complete `report_markdown`.

Kubernetes evidence: `huawei_get_cce_services`, `huawei_get_cce_ingresses`, `huawei_get_cce_pods`, `huawei_get_kubernetes_nodes`, `huawei_get_cce_events`, `huawei_get_pod_logs`.

Cloud network evidence: `huawei_get_elb_backend_status`, `huawei_get_elb_metrics`, `huawei_list_elb`, `huawei_list_elb_listeners`, `huawei_list_eip`, ` huawei_get_eip_metrics`, `huawei_list_nat`, `huawei_get_nat_gateway_metrics`, `huawei_list_security_groups`, `huawei_list_vpc_acls`.

Compatible with old processes: `huawei_network_diagnose`, `huawei_network_diagnose_by_alarm`, `huawei_network_verify_pod_scheduling`.

# # Risk constraints

This skill only performs read-only query and report generation, does not bind or unbind EIP, does not modify security groups/ACLs/ELB listeners, does not expand or shrink, or restart components. When changes are required, output the plan and forward it to `auto-remediation-runner`.