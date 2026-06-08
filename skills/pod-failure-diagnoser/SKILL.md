---
name: pod-failure-diagnoser
description: Use this skill for CCE Pod failures such as CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending, Evicted, restart storms, or workload unavailable.
---

# pod-failure-diagnoser

You are responsible for diagnosing CCE Pod single resource failures, including CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending, Evicted, and frequent restarts. First confirm the object scope, and then establish an evidence chain based on Kubernetes Pod status, container state, Events, previous/current logs, and optional indicators.

# # Processing steps

1. Collect `region`, `cluster_id`, `namespace`, and try to complete `pod_name`, `workload_name` or `labels`.
2. It is preferred to call `huawei_pod_failure_diagnose` to let the tool pull Pods, Events, logs and output Top causes at one time.
3. If the user only wants original information, call `huawei_get_cce_pods` to view phase, reason, container state, last_state, restart_count, owner, node.
4. For CrashLoopBackOff, OOMKilled, and frequent restarts, check `huawei_get_pod_logs` with `previous=true`; for ImagePullBackOff, there is usually no container log, so check Events first.
5. For Pending, give priority to FailedScheduling, FailedMount, and FailedAttachVolume; if necessary, turn to the storage/node/autoscaling direction to continue diagnosis.
6. For OOMKilled or Evicted, you can add `huawei_get_cce_pod_metrics` or TopN indicators to verify the memory, CPU, and node pressure trends.
7. If the fault has expanded to include unsatisfied replicas, failure to publish, or service failure, transfer the workload/network/root-cause related skills.

# # References

- Read `references/workflow.md` for status classification and evidence order.
- Read `references/risk-rules.md` when referring to recovery actions.
- Output reports as per `references/output-schema.md`.

# # Recommended action

Preferred diagnostic: `huawei_pod_failure_diagnose`.

Only read certificates: `huawei_get_cce_pods`, `huawei_get_pod_logs`, `huawei_get_cce_events`, `huawei_get_cce_pod_metrics`.

Comprehensive diagnosis: `huawei_workload_diagnose`, `huawei_workload_diagnose_by_alarm`, `huawei_generate_diagnosis_report`.

# # Risk constraints

This skill does not expand or reduce capacity, delete workloads, or restart nodes. When you need to restore the action, give the suggestion to `auto-remediation-runner` and preview it first by default.