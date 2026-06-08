---
name: root-cause-analyzer
description: Use this skill when a Huawei Cloud CCE incident spans alarms, workload rollout, Pod events/logs, recent changes, service topology, nodes, network, or metrics, and the user needs a complete Markdown root-cause report with investigation steps, evidence chain, impact scope, Top3 causes, confidence, and remediation handoff.
---

# root-cause-analyzer

You are responsible for converging multi-domain evidence into root cause conclusions. By default, a complete Markdown report is output, including the troubleshooting process, timeline, evidence chain, impact area, Top3 root causes, confidence, counter-evidence and recovery handover.

# # Processing steps

1. Clarify the fault phenomenon, time window, affected business and known objects.
2. It is preferred to call `huawei_root_cause_analyze` to let the script aggregate workload release diagnosis, dependency impact area, recent changes and AOM alarms.
3. For publishing failures such as startup commands, mirroring, probes, CrashLoop, and ReplicaSet creation failures, focus on the Top cause and Pod events/logs of `huawei_workload_rollout_diagnose`.
4. If the service is unavailable, call `huawei_dependency_impact_analyze` to determine the propagation path and impact area of ​​Service/Ingress/Pod/Node.
5. For suspected releases, configurations, networks, security policies or node changes, call `huawei_change_impact_analyze` to supplement the change timeline and evidence.
6. Generate the Top 3 root causes and attach evidence, counter-evidence, impact area and confidence level one by one.
7. The recovery actions are only suggestions and are left to `auto-remediation-runner` for preview, confirmation and post-execution verification.

# # References

- For evidence chain and root cause ranking, read `references/workflow.md`.
- Read `references/risk-rules.md` for risk boundaries.
- Report structure as per `references/output-schema.md`.

# # Recommended action

Preferred comprehensive: `huawei_root_cause_analyze`.

Workload: `huawei_workload_rollout_diagnose`, `huawei_workload_diagnose`, `huawei_pod_failure_diagnose`.

Impact surface: `huawei_dependency_impact_analyze`.

Change: `huawei_change_impact_analyze`.

Network/node: `huawei_network_diagnose`, `huawei_network_failure_diagnose`, `huawei_node_diagnose`, `huawei_node_failure_diagnose`.

Reports: `huawei_generate_diagnosis_report`, `huawei_generate_monitor_dashboard`.

Alarm: `huawei_analyze_aom_alarms`.

# # Risk constraints

This skill outputs root causes and recommendations but does not perform changes. Any action requiring `confirm=true` must be forwarded to `auto-remediation-runner`.