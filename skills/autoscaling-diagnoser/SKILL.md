---
name: autoscaling-diagnoser
description: Use this skill for Huawei Cloud CCE autoscaling failures, including HPA not increasing Pod replicas, Cluster Autoscaler or CCE elastic engine not adding or removing nodes, missing metrics, missing CPU or memory requests, maxReplicas or max_nodes limits, Pending Pods, scheduling constraints, subnet IP exhaustion, ECS quota, IAM agency permission issues, and HPA-to-CA cascade diagnosis. The skill must output a complete Markdown diagnosis report with process, evidence, conclusion, confidence, and recommendations.
---

# autoscaling-diagnoser

You are responsible for diagnosing CCE automatic elastic link failures and ultimately output a complete Markdown report. It is important to distinguish between two layers of closed loops: whether HPA adjusts the number of workload copies from N to N+1, and whether the CCE cluster elastic engine/Cluster Autoscaler adjusts the number of nodes from M to M+1 after the insufficient resources Pending Pod appears.

# # Quick Path

1. Collect `region`, `cluster_id`, try to complete `namespace`, `workload_name`, `workload_type` and the user’s original question `question`.
2. It is preferred to call `huawei_autoscaling_diagnose`. It performs intent identification, HPA/CA capability discovery, path A/B/C routing, evidence collection, and returns `report_markdown`.
3. Only the main body of the Markdown report is ultimately output to the customer; the report must include the investigation process, key evidence, root cause conclusions, confidence, data gaps and next step recommendations.
4. If the main tool fails, press `references/workflow.md` again to manually call the atomic tool to find out. Do not skip the Gateway routing.

# # References

- Routing matrix, path A/B/C diagnostic tree and manual reading of `references/workflow.md`.
- Main tool return fields and Markdown templates read `references/output-schema.md`.
- Read `references/capability-map.md` for a list of reusable script capabilities, current gaps and future atomic capabilities.
- Change action boundaries read `references/risk-rules.md`.

# # Recommended Action

Main path: `huawei_autoscaling_diagnose`.

Read-only supplementary certificates: `huawei_list_cce_hpas`, `huawei_list_cce_addons`, `huawei_list_cce_nodepools`, `huawei_get_cce_pods`, `huawei_get_cce_deployments`, `huawei_ list_cce_statefulsets`, `huawei_get_cce_events`, `huawei_get_cce_pod_metrics_topN`, `huawei_get_cce_node_metrics_topN`, `huawei_get_aom_metrics`.

Relevant drill-down: Pod runtime exceptions will be redirected to `pod-failure-diagnoser`; workload rollout exceptions will be redirected to `workload-failure-diagnoser`; node NotReady/stress will be redirected to `node-failure-diagnoser`; resource management and trend optimization will be redirected to `capacity-trend-forecaster` or `cost-optimization-advisor`.

# # Risk constraints

This skill is read-only for diagnostics by default. It does not directly create/modify HPA, does not scale workloads, does not modify node pool min/max, does not install/upgrade plug-ins, does not expand subnets, and does not apply for quotas. When rectification is required, only preview, YAML or execution plan will be given and transferred to `auto-remediation-runner` or manual change process. Actual execution must be explicitly authorized by the customer.