# Risk Rules

## R1 只读验证

- Pod、Node、Events、诊断和状态查询可以自动执行。

## R2 影响运行态

- `huawei_scale_cce_workload`
- `huawei_resize_cce_workload`
- `huawei_resize_cce_nodepool`
- `huawei_cce_node_cordon`
- `huawei_cce_node_uncordon`
- `huawei_start_ecs_instance`
- `huawei_stop_ecs_instance`
- `huawei_bind_cce_cluster_eip`
- `huawei_unbind_cce_cluster_eip`

规则：必须先预览，禁止自动添加 `confirm=true`。

## R3 高风险或破坏性

- `huawei_delete_cce_cluster`
- `huawei_delete_cce_node`
- `huawei_delete_cce_workload`
- `huawei_cce_node_drain`
- `huawei_reboot_ecs`
- `huawei_hibernate_cce_cluster`
- `huawei_awake_cce_cluster`
- `huawei_hss_change_vul_status`

规则：必须用户明确确认动作和对象后才能传 `confirm=true`。执行后必须验证。禁止自动、批量、模糊对象执行。

