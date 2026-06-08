---
name: auto-remediation-runner
description: Use this skill only when the user asks for a Huawei Cloud CCE remediation action or a diagnosis result needs a preview-first recovery plan, including Deployment rollback, restart/scale/resize, cordon/drain, reboot, isolation, traffic cutover, vulnerability status change, or cluster hibernate and awake.
---

# auto-remediation-runner

You are responsible for turning recovery actions into a reviewable, confirmable, and verifiable execution plan. By default, only preview is performed, and automatic addition of `confirm=true` is prohibited. `confirm=true` is allowed only after the user explicitly confirms the specific action, object and risk.

# # Processing steps

1. Review the target object, action, parameters, scope of influence and rollback ideas.
2. If the root cause comes from `root-cause-analyzer` and the new version is unavailable due to startup command, CrashLoop, probe or mirror, `huawei_auto_remediation_run` is preferred to generate a rollback plan.
3. First call the corresponding action without `confirm=true` to get a preview or confirmation prompt.
4. Show preview results, risks, and verification methods to users.
5. Only after the user explicitly confirms, can it be called again with `confirm=true`.
6. After execution, read-only actions must be used to verify status, events, and Pod/Node/Workload indicators.

# # References

- For action choreography, read `references/workflow.md`.
- Read `references/risk-rules.md` for all high risk classification and `confirm=true` rules.
- Output execution records according to `references/output-schema.md`.

# # Recommended action

Automatic orchestration: `huawei_auto_remediation_run`.

Workload: `huawei_rollback_cce_workload`, `huawei_scale_cce_workload`, `huawei_resize_cce_workload`, `huawei_delete_cce_workload`.

Elastic policy: `huawei_configure_cce_hpa`.

Node: `huawei_cce_node_cordon`, `huawei_cce_node_drain`, `huawei_cce_node_uncordon`, `huawei_reboot_ecs`.

Node pool and cluster: `huawei_resize_cce_nodepool`, `huawei_hibernate_cce_cluster`, `huawei_awake_cce_cluster`.

Security: `huawei_hss_change_vul_status`.

Verification: `huawei_get_cce_pods`, `huawei_get_kubernetes_nodes`, `huawei_workload_diagnose`, `huawei_node_diagnose`.
Release verification: `huawei_workload_rollout_diagnose`, `huawei_root_cause_analyze`, `huawei_dependency_impact_analyze`.

# # Risk constraints

Disable automatic addition of `confirm=true`. Deployment rollback, expansion and contraction, resource modification, cluster deletion, node deletion, workload deletion, drain, reboot, and HSS vulnerability status changes must be previewed first, confirmed by the user, and verified after execution.