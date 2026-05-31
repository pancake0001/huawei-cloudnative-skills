# Risk Rules

## Preview First

The following actions must be called without `confirm=true` first. Apply them only after the user explicitly approves the reported plan:

- `huawei_ensure_cce_cci_vpcep`
- `huawei_setup_cce_cci_bursting`
- `huawei_deploy_cce_cci_smoke_workload`

## Billing and Resource Scope

- SWR interface VPCEPs may incur charges. Always preview before creation.
- OBS gateway VPCEP creation must use the exact service name supplied for the tenant and region. Do not guess a nearby public service name.
- Do not automatically delete existing VPCEPs, namespaces, workloads, or addons.
- Do not persist AK or SK values in skill files, debug files, generated reports, or shell history.

## Safe Defaults

- Reuse accepted VPCEPs in the cluster VPC. The `huawei_ensure_cce_cci_vpcep` action checks for existing endpoints before proposing new ones.
- Use a regional SWR image for the smoke workload. Docker Hub images timeout in CCI capacity.
- Treat the setup action as idempotent: `huawei_setup_cce_cci_bursting` may update the existing `virtual-kubelet` addon configuration but does not uninstall it.
- Run `huawei_verify_cce_cci_bursting` after each applied change to confirm progress.

## Cross-Skill References

- Cluster management operations (addon uninstall, node operations): delegate to `huawei-cloud-cce-cluster-management`
- Pod failure diagnosis when bursting pods fail: delegate to `huawei-cloud-cce-pod-failure-diagnoser`
- Network failure diagnosis for VPCEP issues: delegate to `huawei-cloud-cce-network-failure-diagnoser`