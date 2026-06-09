# Risk Rules

## R0 — Read-Only Verification

- Pod, Node, Events, diagnosis, and status queries may be executed automatically without `confirm=true`.

## R1 — Low-Risk Authorized Actions

- `huawei_scale_cce_workload` when the target replica count is higher than the current replica count.
- `huawei_resize_cce_nodepool` when the target node count is higher than the current node count.
- `huawei_configure_cce_hpa` only when the current Pod count is known, `minReplicas >= currentPodCount`, and `maxReplicas > currentPodCount`.
- `huawei_cce_node_cordon`
- `huawei_cce_node_uncordon`
- `huawei_auto_remediation_run` when the policy contains only the approved R1 actions above.

**Rule:** Low risk. If the customer has explicitly authorized the target cluster, namespace, workload, node, or node pool for automatic R1 actions, the action can be executed directly and must be verified after execution. Without such authorization, generate a preview first and wait for confirmation.

## R2 — Runtime Impact

- `huawei_scale_cce_workload` when scaling down or when the direction is unknown.
- `huawei_resize_cce_workload`
- `huawei_resize_cce_nodepool` when scaling down or when the direction is unknown.
- `huawei_cce_node_drain`
- `huawei_start_ecs_instance`
- `huawei_configure_cce_hpa` when `minReplicas < currentPodCount`, `maxReplicas <= currentPodCount`, reducing limits, changing scale-in behavior, or when the current Pod count or direction is unknown.
- `huawei_rollback_cce_workload`
- `huawei_auto_remediation_run` (when the policy is Deployment rollback, workload resize, scale-in, node pool resize with unknown direction, and other runtime state changes)

**Rule:** Must preview first. Auto-adding `confirm=true` is prohibited.

## R3 — High Risk / Destructive

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

**Rule:** Must receive explicit user confirmation of the action and target object before passing `confirm=true`. Post-execution verification is mandatory. Auto, batch, or fuzzy-target execution is prohibited.
