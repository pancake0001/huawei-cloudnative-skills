---
name: daily-cluster-inspector
description: Use this skill for daily Huawei Cloud CCE health checks, quick checks, cluster inspections, heartbeat summaries, and continuous operations reports.
---

# daily-cluster-inspector

You are responsible for conducting periodic, low-risk CCE inspections. Prioritize quick inspections and conduct in-depth diagnosis after abnormalities are discovered to avoid performing heavy inspections during every inspection.

# # Processing steps

1. Collect region, cluster_id, inspection scope and report expectations.
2. Call `huawei_cce_quick_check` or `huawei_cce_auto_inspection` first.
3. Output a short health summary when normal.
4. Call in-depth diagnosis or parallel inspection when an exception occurs, and group them by Pod, Node, Event, AOM, and ELB.
5. When abnormalities are found, package the inspection result as root-cause input and forward it to `root-cause-analyzer`, including region, cluster_id, time window, affected objects, symptoms, evidence, severity, and data gaps.
6. The P0-P5 severity level is judged by AI based on the inspection results, impact scope, duration, alarm status and root cause evidence; the classification is only used for summary and suggestions, and the tool is not required to return fixed fields.
7. Call the export report action when a report is needed.

# # References

- Quick inspection and deep inspection are separated into `references/workflow.md`.
- Patrol read-only boundary read `references/risk-rules.md`.
- When inspection findings are abnormal, forward the summarized evidence to `../root-cause-analyzer/SKILL.md` for root-cause analysis before selecting remediation.
- Inspection summary is in `references/output-schema.md`.

# # Recommended action

Quick check: `huawei_cce_quick_check`, `huawei_cce_auto_inspection`.

Deep inspection: `huawei_cce_deep_diagnosis`, `huawei_cce_cluster_inspection_parallel`, `huawei_pod_status_inspection`, `huawei_node_status_inspection`, `huawei_aom_alarm_inspection`.

Report: `huawei_export_inspection_report`.

# # Risk constraints

This skill only performs inspection and reporting, and does not perform repair actions. After discovering risks, suggestions are output and forwarded to `root-cause-analyzer` first; remediation suggestions that require action are then handed off to `auto-remediation-runner`.
