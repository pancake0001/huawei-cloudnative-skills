# Risk Rules

Risk levels are ordered from highest to lowest risk:

- `R0` — high risk
- `R1` — medium risk
- `R2` — low risk, no new cloud-resource cost
- `R3` — read-only verification

## R3 — Read-Only Verification

- Pod, Node, Events, diagnosis, metrics, image/pull-secret review, and status queries.

**Rule:** May run directly without `confirm=true`.

## R2 — Low-Risk Authorized Actions

- `huawei_scale_cce_workload` when the target replica count is higher than the current replica count and does not add cloud-resource cost.
- `huawei_configure_cce_hpa` only when the current Pod count is known, `minReplicas >= currentPodCount`, `maxReplicas > currentPodCount`, and the change does not add cloud-resource cost.
- `huawei_cce_node_cordon`
- `huawei_cce_node_uncordon`
- `huawei_auto_remediation_run` when the policy contains only the approved R2 actions above.

**Rule:** Low risk. If the customer has explicitly authorized the target cluster, namespace, workload, node, or node pool for automatic R2 actions, the action can be executed directly and must be verified after execution. Without such authorization, generate a preview first and wait for confirmation.

## R1 — Medium Risk

- `huawei_scale_cce_workload` when scaling down, when the direction is unknown, or when the action may create scheduling pressure.
- `huawei_resize_cce_workload`
- `huawei_resize_cce_nodepool`
- `huawei_cce_node_drain`
- `huawei_start_ecs_instance`
- `huawei_configure_cce_hpa` when `minReplicas < currentPodCount`, `maxReplicas <= currentPodCount`, reducing limits, changing scale-in behavior, or when the current Pod count or direction is unknown.
- `huawei_rollback_cce_workload`
- `huawei_auto_remediation_run` when the policy is Deployment rollback, workload resize, scale-in, node pool resize, drain, and other runtime state changes.

**Rule:** Must preview first. Auto-adding `confirm=true` is prohibited.

## R0 — High Risk / Destructive / Cost or Security Sensitive

- `huawei_delete_cce_cluster`
- `huawei_delete_cce_node`
- `huawei_delete_cce_workload`
- `huawei_reboot_ecs`
- `huawei_stop_ecs_instance`
- `huawei_hibernate_cce_cluster`
- `huawei_awake_cce_cluster`
- `huawei_bind_cce_cluster_eip`
- `huawei_unbind_cce_cluster_eip`
- `huawei_hss_change_vul_status`
- Node pool scale-out or any action that may add cloud-resource cost without an explicit cost-aware approval path.

**Rule:** Must receive explicit user confirmation of the action, target object, risk, and cost/security impact before passing `confirm=true`. Post-execution verification is mandatory. Auto, batch, or fuzzy-target execution is prohibited.
