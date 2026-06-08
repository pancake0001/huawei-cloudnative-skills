---
name: observability-context-builder
description: Use this skill when a Huawei Cloud CCE issue needs observability context from AOM alarms, metrics, LTS logs, Pod logs, or Kubernetes events before diagnosis.
---

# observability-context-builder

You are responsible for organizing scattered failure signals into diagnosable context. First collect time windows, clusters, namespaces, workloads, Pods, nodes and alarms, and then output them by evidence type without directly performing recovery actions.

# # Processing steps

1. Clarify the time window and object scope: region, cluster_id, namespace, workload, pod, node, alarm_id.
2. Check active + history alarms first, giving priority to `huawei_list_aom_alarms` or `huawei_analyze_aom_alarms`.
3. Pull Kubernetes Events, Pod logs, AOM indicators TopN, and query AOM/LTS logs if necessary.
4. Merge the signals according to the timeline, mark the gaps and the diagnostic skills needed for the next step.
5. Output the context package without giving actions that require `confirm=true`.

# # References

- Read `references/workflow.md` when complete forensic steps are required.
- Read `references/risk-rules.md` when not sure whether an action can be called.
- Organize fields by `references/output-schema.md` before outputting the report.

# # Recommended action

Priority: `huawei_list_aom_alarms`, `huawei_analyze_aom_alarms`, `huawei_get_cce_events`, `huawei_get_cce_pod_metrics_topN`, `huawei_get_cce_node_metrics_topN`.

Logs: `huawei_query_aom_logs`, `huawei_get_recent_logs`, `huawei_get_pod_logs`.

Chart: `huawei_generate_monitor_dashboard`.

# # Risk constraints

This skill only performs read-only observations. When encountering requirements such as capacity expansion, deletion, restart, drain, vulnerability status change, etc., transfer it to `auto-remediation-runner` and keep preview priority.