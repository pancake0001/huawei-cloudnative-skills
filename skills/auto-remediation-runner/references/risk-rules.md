# RiskRules

# # R1 read-only verification

- Pods, Nodes, Events, diagnostics and status queries can be automated.

# # R2 affects the running state

- `huawei_scale_cce_workload`
- `huawei_resize_cce_workload`
- `huawei_resize_cce_nodepool`
- `huawei_cce_node_cordon`
- `huawei_cce_node_uncordon`
- `huawei_start_ecs_instance`
- `huawei_stop_ecs_instance`
- `huawei_bind_cce_cluster_eip`
- `huawei_unbind_cce_cluster_eip`
- `huawei_configure_cce_hpa`
- `huawei_rollback_cce_workload`
- `huawei_auto_remediation_run` (when the policy is Deployment rollback, scale, resize and other running state changes)

Rules: Must be previewed first, automatic addition of `confirm=true` is prohibited.

# # R3 High Risk or Disruptive

- `huawei_delete_cce_cluster`
- `huawei_delete_cce_node`
- `huawei_delete_cce_workload`
- `huawei_cce_node_drain`
- `huawei_reboot_ecs`
- `huawei_hibernate_cce_cluster`
- `huawei_awake_cce_cluster`
- `huawei_hss_change_vul_status`

Rules: The user must explicitly confirm the action and object before passing `confirm=true`. Must be verified after execution. Automatic, batch, and fuzzy object execution are prohibited.