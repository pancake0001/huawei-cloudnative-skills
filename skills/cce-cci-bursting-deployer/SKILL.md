---
name: cce-cci-bursting-deployer
description: Configure, deploy, and verify Huawei Cloud CCE to CCI 2.0 bursting for fast elastic capacity. Use when users ask to enable CCE elasticity to CCI, install or configure virtual-kubelet bursting, create required OBS or SWR VPCEP endpoints, run a CCI bursting smoke test, or diagnose why CCE pods do not reach Running on bursting-node.
---

# cce-cci-bursting-deployer

Use this skill to configure CCE workloads to burst into CCI 2.0 capacity. Keep the workflow preview-first: read-only checks may run immediately, but VPCEP creation, addon installation or update, and smoke workload deployment require explicit user approval before calling an action with `confirm=true`.

## Workflow

1. Run `huawei_precheck_cce_cci_bursting`, then inspect its NodeCheck result. If physical-node addon headroom is low, use `huawei_list_cce_nodepools` and preview `huawei_resize_cce_nodepool` or `huawei_create_cce_nodepool`. Apply a capacity change only after explicit user approval.
2. Inspect the two subnet roles. `cci_subnet_id` is a Neutron subnet ID for the addon. `vpcep_subnet_id` is a VPC subnet ID for VPCEP. Never swap them.
3. Run `huawei_ensure_cce_cci_vpcep` without confirmation. If the report asks for `obs_endpoint_service_name`, obtain the exact OBS endpoint service name through the Huawei Cloud service ticket. Do not guess it from a similar regional public service.
4. After explicit user approval, run `huawei_setup_cce_cci_bursting` with `confirm=true`. This ensures VPCEP dependencies, writes the resolved project ID, and installs or updates `virtual-kubelet`.
5. Run `huawei_verify_cce_cci_bursting`. When verification fails, inspect the returned diagnostics or call `huawei_diagnose_cce_cci_bursting_addon`.
6. Run `huawei_discover_cce_cci_smoke_images` to discover tenant-owned SWR basic images. After explicit user approval, run `huawei_deploy_cce_cci_smoke_workload` with `confirm=true`. The smoke action selects a tenant-owned image automatically when `image` is omitted, then run verification again with the smoke namespace and workload name.

## References

- Read `references/workflow.md` for action parameters and command examples.
- Read `references/risk-rules.md` before creating VPCEPs or changing the cluster.
- Read `references/troubleshooting.md` when the virtual node or test pods are not ready.
