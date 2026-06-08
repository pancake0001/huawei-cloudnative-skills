---
name: workload-failure-diagnoser
description: Use this skill for CCE workload rollout failures such as release failed, rolling update stuck, replicas unavailable, Deployment new ReplicaSet not creating Pods, StatefulSet or DaemonSet update blocked, and probe-related readiness failures.
---

# workload-failure-diagnoser

You are responsible for diagnosing CCE workload release and replica availability issues, covering Deployment, StatefulSet, DaemonSet. First establish evidence from the controller status, version ownership and event tree, and then transfer the abnormal Pod to the existing Pod to drill down the diagnostic logic.

# # Processing steps

1. Collect `region`, `cluster_id`, `namespace`, `kind`, `name`; `kind` supports `Deployment`, `StatefulSet`, `DaemonSet`.
2. It is preferred to call `huawei_workload_rollout_diagnose`, which will collect the cleaned Events of Workload, ReplicaSet, Pod and UID, and output the rollout funnel and Top causes.
3. If you only need the original context or want to verify evidence, call `huawei_get_workload_rollout_context`.
4. When the NewRS Pod has been created but is not Ready, reuse `huawei_pod_failure_diagnose`, `huawei_get_pod_logs` and Pod indicators, and do not repeat the CrashLoop/ImagePull/OOM/Pending logic.
5. If the evidence points to scheduling, node pressure, or network dependencies, then turn to `node-failure-diagnoser` or `network-failure-diagnoser`.
6. When recovery actions such as capacity expansion, resource adjustment, deletion and reconstruction, drain, and restart are required, only suggestions are output and forwarded to `auto-remediation-runner`.

# # References

- Release funnel and version lock process read `references/workflow.md`.
- Output schema as per `references/output-schema.md`.
- Read `references/risk-rules.md` for risk boundaries.

# # Recommended action

Preferred diagnostic: `huawei_workload_rollout_diagnose`.

Only collect evidence: `huawei_get_workload_rollout_context`.

Pod drill-down: `huawei_pod_failure_diagnose`, `huawei_get_pod_logs`, `huawei_get_cce_pod_metrics`, `huawei_get_cce_pod_metrics_topN`.

Scheduling/storage/network drill-down: `huawei_get_cce_pvcs`, `huawei_get_cce_pvs`, `huawei_node_diagnose`, `huawei_network_diagnose`.

# # Risk constraints

This skill only performs read-only diagnostics. No expansion or contraction, no workload deletion, no modification of resource specifications, no cordon/drain/reboot nodes. All changes that require confirmation are previewed by the `auto-remediation-runner`.