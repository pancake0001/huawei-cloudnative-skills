# Risk Rules

## Preview first

The following actions must be called without `confirm=true` first. Apply them only after the user explicitly approves the reported plan:

- `huawei_ensure_cce_cci_vpcep`
- `huawei_setup_cce_cci_bursting`
- `huawei_deploy_cce_cci_smoke_workload`

## Billing and resource scope

- SWR interface VPCEPs may incur charges.
- OBS gateway VPCEP creation must use the exact service name supplied for the tenant and region. Do not guess a nearby public service name.
- Do not automatically delete existing VPCEPs, namespaces, workloads, or addons.
- Do not persist AK or SK values in skill files, debug files, generated reports, or shell history.

## Safe defaults

- Reuse accepted VPCEPs in the cluster VPC.
- Use a regional SWR image for the smoke workload.
- Treat the setup action as idempotent: it may update the existing `virtual-kubelet` addon configuration but does not uninstall it.
- Run `huawei_verify_cce_cci_bursting` after each applied change.
