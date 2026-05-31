# CCE to CCI 2.0 Bursting Workflow

## Action Sequence

| Step | Action | Mutation | Purpose |
| --- | --- | --- | --- |
| 1 | `huawei_precheck_cce_cci_bursting` | No | Resolve cluster networking, subnet roles, and addon state. |
| 2 | `huawei_ensure_cce_cci_vpcep` | Only with `confirm=true` | Reuse or create SWR, SWR API, and OBS-compatible VPCEPs. |
| 3 | `huawei_setup_cce_cci_bursting` | Only with `confirm=true` | Ensure VPCEPs, install `virtual-kubelet` if absent, and apply CCI network parameters. |
| 4 | `huawei_verify_cce_cci_bursting` | No | Verify addon state, virtual node readiness, and optional workload result. |
| 5 | `huawei_deploy_cce_cci_smoke_workload` | Only with `confirm=true` | Create or patch a small Deployment forced to CCI capacity. |
| 6 | `huawei_verify_cce_cci_bursting` | No | Confirm test pods reach `Running` on `bursting-node` or `virtual-kubelet`. |

## Subnet Roles

| Parameter | ID Type | Used By |
| --- | --- | --- |
| `cci_subnet_id` | Neutron subnet UUID | `virtual-kubelet` addon `networkID`, `subnet_id`, and `subnets[].subnetID` |
| `vpcep_subnet_id` | VPC subnet UUID | VPCEP interface endpoint placement |

For a Turbo/ENI cluster, `huawei_precheck_cce_cci_bursting` normally resolves `cci_subnet_id` from `spec.eni_network`. Pass `vpcep_subnet_id` explicitly when a larger or dedicated endpoint subnet is preferred.

**These are different ID namespaces. Do not swap them.**

## Examples

Preview (no mutation):

```bash
python3 scripts/huawei-cloud.py huawei_precheck_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id>
python3 scripts/huawei-cloud.py huawei_setup_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id>
```

Apply after explicit user approval:

```bash
python3 scripts/huawei-cloud.py huawei_setup_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> vpcep_subnet_id=<vpc-subnet-id> confirm=true
python3 scripts/huawei-cloud.py huawei_deploy_cce_cci_smoke_workload region=cn-north-4 cluster_id=<cluster-id> replicas=2 confirm=true
python3 scripts/huawei-cloud.py huawei_verify_cce_cci_bursting region=cn-north-4 cluster_id=<cluster-id> namespace=cci2-burst-lab workload_name=cci2-burst-demo
```

If the precheck reports that OBS information is missing, obtain the exact service name through the Huawei Cloud service ticket and pass:

```bash
obs_endpoint_service_name=<exact-service-name> route_table_ids=<route-table-id>
```

## Official References

- [CCI 2.0 network configuration](https://support.huaweicloud.com/intl/zh-cn/usermanual-cci2/cci_01_0005.html)
- [CCI image pulling FAQ](https://support.huaweicloud.com/intl/en-us/cci_faq/cci_faq_0095.html)

## Related Skills

- `huawei-cloud-cce-cluster-management` — Cluster lifecycle, addon listing, kubeconfig retrieval
- `huawei-cloud-cce-pod-failure-diagnoser` — Pod failure diagnosis when bursting pods fail
- `huawei-cloud-cce-network-failure-diagnoser` — Network diagnosis for VPCEP connectivity issues