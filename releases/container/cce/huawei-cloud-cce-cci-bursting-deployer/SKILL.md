---
id: huawei-cloud-cce-cci-bursting-deployer
name: huawei-cloud-cce-cci-bursting-deployer
description: |
  Configure, deploy, and verify Huawei Cloud CCE to CCI 2.0 bursting for fast elastic capacity using python3 scripts/huawei-cloud.py.
  Use this skill when the user wants to: (1) enable CCE elasticity to CCI, (2) install or configure virtual-kubelet bursting addon, (3) create required OBS or SWR VPCEP endpoints for CCI image pulling, (4) run a CCI bursting smoke test deployment, (5) verify virtual node readiness and workload pod status, (6) diagnose why CCE pods do not reach Running on bursting-node.
  Trigger: "CCI bursting", "CCI 弹性", "burst deployment", "弹性部署", "burst to CCI", "弹出到 CCI", "hybrid scheduling", "混合调度", "CCE-CCI burst", "CCE-CCI 弹性", "CCI workload", "CCI 工作负载"
tags: [cce, cci, bursting, hybrid-scheduling]
version: 1.0.0
---

# Huawei Cloud CCE-CCI Bursting Deployer

## Overview

This skill configures CCE workloads to burst into CCI 2.0 serverless capacity for elastic scaling. It automates the full workflow: precheck cluster readiness, ensure VPCEP dependencies for image pulling, install or update the `virtual-kubelet` addon, deploy a smoke workload, and verify the virtual node and pod status.

**Architecture**: python3 scripts/huawei-cloud.py → CCE/VPCEP/VPC API → Precheck → VPCEP creation → Addon install → Smoke deployment → Verification

**Key Principle**: Preview-first. Read-only checks run immediately, but VPCEP creation, addon installation, and smoke workload deployment require explicit user approval with `confirm=true` before execution.

**Related Skills**:
- `huawei-cloud-cce-cluster-management` - Cluster lifecycle, addon listing, kubeconfig retrieval
- `huawei-cloud-cce-pod-failure-diagnoser` - Pod failure diagnosis when bursting pods fail to reach Running
- `huawei-cloud-cce-network-failure-diagnoser` - Network diagnosis for VPCEP connectivity issues

## Prerequisites

### 1. Python Requirements (MANDATORY)

- Python 3 installed (version >= 3.8)
- Run `python3 --version` to verify installation
- `huawei-cloud.py` script available in the scripts directory
- Required packages: `huaweicloudsdkcce`, `huaweicloudsdkcore`, `huaweicloudsdkvpc`, `huaweicloudsdkvpcep`, `kubernetes`

### 2. Credential Configuration

- Valid Huawei Cloud credentials (AK/SK mode)
- **Security Rules**:
  - Never expose AK/SK values in code, conversation, or commands
  - Never use `echo` commands to check credential environment variables
  - Use environment variables: `HUAWEI_AK`, `HUAWEI_SK`, `HUAWEI_PROJECT_ID`
  - Alternative env vars: `HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`, `HW_ACCESS_KEY`, `HW_SECRET_KEY`
  - Prefer IAM users over root account for cloud operations
  - Never persist AK/SK in skill files, debug files, reports, or shell history

**Configuration Method** (Environment Variables Only):

```bash
export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_PROJECT_ID=<your-project-id>
```

### 3. IAM Permission Requirements

| API Action | Permission | Purpose |
| --- | --- | --- |
| `cce:cluster:get` | Get cluster details | Read cluster network spec (VPC, subnet, ENI) |
| `cce:addon:list` | List addons | Check virtual-kubelet installation state |
| `cce:addon:create` | Install addon | Install virtual-kubelet addon |
| `cce:addon:update` | Update addon | Configure virtual-kubelet bursting parameters |
| `vpcep:endpoint:create` | Create VPCEP | Create SWR/OBS interface endpoints |
| `vpcep:endpoint:list` | List VPCEP | Check existing VPCEP endpoints |
| `vpcep:service:list` | List VPCEP services | Discover public service details |
| `vpc:subnet:list` | List subnets | Validate subnet IDs in cluster VPC |
| `vpc:routetable:list` | List route tables | Find route table IDs for OBS gateway VPCEP |

**Permission Failure Handling**: When any command fails due to IAM permission errors, verify the permissions listed above, guide the user to create custom IAM policies, and pause execution until permissions are confirmed.

## Core Tools

All tools are invoked through `python3 scripts/huawei-cloud.py` with key=value parameters.

### 1. Precheck (Read-Only)

```bash
python3 scripts/huawei-cloud.py huawei_precheck_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id>
```

Inspects cluster networking, resolves subnet roles, checks addon state, and reports any blocking issues. The cluster must be a Turbo/ENI cluster for CCI bursting.

### 2. Ensure VPCEP Dependencies

```bash
# Preview (no mutation)
python3 scripts/huawei-cloud.py huawei_ensure_cce_cci_vpcep region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id>

# Apply after user approval
python3 scripts/huawei-cloud.py huawei_ensure_cce_cci_vpcep region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id> confirm=true
```

Creates or reuses SWR, SWR-API, and OBS-compatible VPCEP interface endpoints in the cluster VPC. If OBS information is missing, pass `obs_endpoint_service_name` obtained from the Huawei Cloud service ticket (do not guess).

### 3. Setup CCI Bursting

```bash
# Preview
python3 scripts/huawei-cloud.py huawei_setup_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id>

# Apply after user approval
python3 scripts/huawei-cloud.py huawei_setup_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id> confirm=true
```

Ensures VPCEP dependencies, installs `virtual-kubelet` if absent, and configures CCI network parameters. Idempotent: updates existing addon configuration without uninstalling.

### 4. Verify Bursting Readiness (Read-Only)

```bash
python3 scripts/huawei-cloud.py huawei_verify_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id>
```

Checks addon state, virtual node readiness, and optional workload pod status. Returns `ready=true` when the virtual node is Ready and all workload pods are Running on it.

### 5. Deploy Smoke Workload

```bash
# Preview
python3 scripts/huawei-cloud.py huawei_deploy_cce_cci_smoke_workload region=cn-north-4 cluster_id=<cluster-id> replicas=2

# Apply after user approval
python3 scripts/huawei-cloud.py huawei_deploy_cce_cci_smoke_workload region=cn-north-4 cluster_id=<cluster-id> replicas=2 confirm=true
```

Creates or patches a small Deployment forced onto CCI capacity using the `bursting.cci.io/burst-to-cci: enforce` label. Uses a regional SWR image by default.

### 6. Verify Smoke Workload (Read-Only)

```bash
python3 scripts/huawei-cloud.py huawei_verify_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> namespace=cci2-burst-lab workload_name=cci2-burst-demo
```

Confirms test pods reach `Running` on the virtual node (`bursting-node` or `virtual-kubelet`).

## Parameter Reference

### Common Parameters

| Parameter | Required/Optional | Description | Default |
| --- | --- | --- | --- |
| `region` | Required | Huawei Cloud region ID | `HUAWEI_AK` env region |
| `cluster_id` | Required | CCE cluster ID | N/A |
| `ak` | Optional | Access Key (overrides env var) | `HUAWEI_AK` env |
| `sk` | Optional | Secret Key (overrides env var) | `HUAWEI_SK` env |
| `project_id` | Optional | Project ID (overrides env var) | Auto-resolved via IAM |

### Precheck Parameters

| Parameter | Required/Optional | Description | Notes |
| --- | --- | --- | --- |
| `vpcep_subnet_id` | Optional | VPC subnet ID for VPCEP placement | Defaults to cluster host subnet |

### VPCEP Parameters

| Parameter | Required/Optional | Description | Notes |
| --- | --- | --- | --- |
| `vpcep_subnet_id` | Optional | VPC subnet ID for VPCEP | Defaults from precheck |
| `obs_endpoint_service_name` | Optional | Exact OBS VPCEP service name | Obtain from Huawei Cloud service ticket; do not guess |
| `route_table_ids` | Optional | Route table IDs for OBS gateway | Auto-resolved if omitted; comma-separated |
| `confirm` | Required for mutation | Approve VPCEP creation | `true` to apply, omit to preview |

### Setup Parameters

| Parameter | Required/Optional | Description | Notes |
| --- | --- | --- | --- |
| `vpcep_subnet_id` | Optional | VPC subnet ID for VPCEP | Defaults from precheck |
| `cci_subnet_id` | Optional | Neutron subnet ID for addon | Defaults from `spec.eni_network` |
| `obs_endpoint_service_name` | Optional | OBS VPCEP service name | Required if precheck reports missing OBS |
| `route_table_ids` | Optional | Route table IDs for OBS gateway | Auto-resolved if omitted |
| `addon_version` | Optional | virtual-kubelet addon version | Defaults to `1.5.82` or existing version |
| `confirm` | Required for mutation | Approve setup | `true` to apply, omit to preview |

### Smoke Workload Parameters

| Parameter | Required/Optional | Description | Default |
| --- | --- | --- | --- |
| `namespace` | Optional | Smoke namespace | `cci2-burst-lab` |
| `workload_name` | Optional | Smoke Deployment name | `cci2-burst-demo` |
| `image` | Optional | Container image | Regional SWR nginx image |
| `replicas` | Optional | Pod replica count | `2` |
| `confirm` | Required for mutation | Approve deployment | `true` to apply, omit to preview |

### Verify Parameters

| Parameter | Required/Optional | Description | Notes |
| --- | --- | --- | --- |
| `namespace` | Optional | Workload namespace | Filter pods and deployments |
| `workload_name` | Optional | Workload name | Filter pods by `app` label |

### Subnet Role Reference

| Parameter | ID Type | Used By |
| --- | --- | --- |
| `cci_subnet_id` | Neutron subnet UUID | `virtual-kubelet` addon `networkID`, `subnet_id`, `subnets[].subnetID` |
| `vpcep_subnet_id` | VPC subnet UUID | VPCEP interface endpoint placement |

**These are different ID namespaces. Never swap them.** For a Turbo/ENI cluster, `huawei_precheck_cce_cci_bursting` resolves `cci_subnet_id` from `spec.eni_network`. Pass `vpcep_subnet_id` explicitly when a dedicated endpoint subnet is preferred.

## Output Format

All tools return JSON with the following structure:

| Field | Description |
| --- | --- |
| `success` | Boolean: `true` if operation succeeded, `false` otherwise |
| `action` | Action name that was executed |
| `region` | Huawei Cloud region |
| `cluster_id` | CCE cluster ID |

**Precheck Output**:

| Field | Description |
| --- | --- |
| `network` | Cluster network context (VPC, subnets, ENI) |
| `subnet_roles` | Resolved `cci_subnet_id` and `vpcep_subnet_id` |
| `virtual_kubelet` | Existing addon info or `null` |
| `issues` | List of blocking issues (empty if ready) |

**Verify Output**:

| Field | Description |
| --- | --- |
| `ready` | Boolean: addon installed, virtual node Ready, workload pods Running |
| `addon` | virtual-kubelet addon details |
| `virtual_nodes` | List of virtual nodes in the cluster |
| `workload.phase_distribution` | Pod phase counts (Running, Pending, etc.) |
| `workload.node_distribution` | Pod node assignment counts |
| `warning_events` | Recent warning events for the workload |

## Verification

### Step-by-step Verification Checklist

1. Verify AK/SK credentials are configured via environment variables
2. Run `huawei_precheck_cce_cci_bursting` and confirm `issues` is empty
3. Verify the cluster is Turbo/ENI type (`container_network_mode` = `eni`)
4. Run `huawei_ensure_cce_cci_vpcep` preview and confirm VPCEP plan is correct
5. After user approval, apply VPCEP with `confirm=true`
6. Run `huawei_setup_cce_cci_bursting` preview, then apply with `confirm=true`
7. Run `huawei_verify_cce_cci_bursting` and confirm `ready=true`
8. Deploy smoke workload with preview, then `confirm=true`
9. Run final verification with namespace and workload_name parameters
10. Confirm all pods are `Running` on `bursting-node` or `virtual-kubelet`

## Best Practices

1. **Always precheck first**: Run `huawei_precheck_cce_cci_bursting` before any mutation to identify blocking issues
2. **Preview before apply**: Always run mutation actions without `confirm=true` first, review the plan, then re-run with `confirm=true` after explicit user approval
3. **Never swap subnet IDs**: `cci_subnet_id` (Neutron UUID) and `vpcep_subnet_id` (VPC UUID) are different ID namespaces; swapping them causes addon failure
4. **Use regional SWR images**: Docker Hub images timeout in CCI capacity; always use a regional SWR image for verification workloads
5. **Obtain OBS service name from service ticket**: Never guess the `obs_endpoint_service_name` from a similar regional public service
6. **Verify after each change**: Run `huawei_verify_cce_cci_bursting` after each applied change to confirm progress
7. **Setup is idempotent**: `huawei_setup_cce_cci_bursting` updates existing addon configuration without uninstalling; safe to re-run
8. **Reuse existing VPCEPs**: The tool reuses accepted VPCEPs in the cluster VPC; no duplicate creation
9. **Do not delete resources automatically**: Never auto-delete VPCEPs, namespaces, workloads, or addons

## Reference Documents

| Document | Description |
| --- | --- |
| [Workflow](references/workflow.md) | Action sequence, subnet roles, and command examples |
| [Risk Rules](references/risk-rules.md) | Preview-first constraints, billing scope, and safe defaults |
| [Troubleshooting](references/troubleshooting.md) | Symptom-cause-action table for common bursting failures |

## Notes

- **Preview-first by design** — VPCEP creation, addon installation, and workload deployment return a preview without `confirm=true`; apply only after explicit user approval
- **Idempotent setup** — `huawei_setup_cce_cci_bursting` may update the existing `virtual-kubelet` addon configuration but never uninstalls it
- **Turbo/ENI required** — CCE to CCI bursting requires a Turbo cluster with ENI container network mode
- **No credential persistence** — AK/SK exists only during API calls; never written to disk, logs, or reports
- **Cross-skill escalation** — If bursting pods show CrashLoopBackOff or ImagePullBackOff, hand off to `huawei-cloud-cce-pod-failure-diagnoser`; if VPCEP connectivity fails, hand off to `huawei-cloud-cce-network-failure-diagnoser`

## Common Pitfalls

| Pitfall | Symptom | Quick Fix |
| --- | --- | --- |
| Swapped subnet IDs | virtual-kubelet restarts, virtual node never Ready | Run precheck; use `cci_subnet_id` from `spec.eni_network` (Neutron UUID), not the VPC subnet UUID |
| Missing SWR VPCEPs | CCI pod `ImagePullBackOff` or image pull timeout | Run `huawei_ensure_cce_cci_vpcep` to create SWR endpoints |
| Docker Hub image in CCI | Image pull timeout | Use a regional SWR image for the smoke workload |
| Missing bursting label | Workload pods stay Pending on real nodes | Add `bursting.cci.io/burst-to-cci: enforce` label to pod template |
| Guessed OBS service name | OBS gateway VPCEP creation fails | Obtain exact `obs_endpoint_service_name` from Huawei Cloud service ticket |
| Non-ENI cluster | Precheck reports CCI bursting not supported | Use a Turbo/ENI cluster; overlay_l2 clusters cannot burst to CCI |