# Troubleshooting

| Symptom | Likely Cause | Action |
| --- | --- | --- |
| `virtual-kubelet` components restart or the virtual node never becomes Ready | The addon received a VPC subnet UUID instead of the Neutron subnet UUID | Run precheck and pass `cci_subnet_id` from `spec.eni_network`. See subnet roles in [workflow.md](workflow.md). |
| CCI pod is `ImagePullBackOff` or times out while pulling an image | SWR, SWR API, or OBS-compatible VPCEP is missing | Run `huawei_ensure_cce_cci_vpcep`, then verify endpoint status. |
| Docker Hub image pull times out | CCI capacity has no direct public path to Docker Hub | Use a regional SWR image for verification. Pass `image=<regional-swr-image>` to the smoke deployment. |
| Workload pods stay Pending and mention a `virtual-kubelet.io/provider` taint | The workload is not using the CCI bursting scheduling profile | Use the smoke action or add `bursting.cci.io/burst-to-cci: enforce` to the workload template labels. |
| OBS gateway endpoint creation fails | The OBS service name does not match the tenant or region setup | Obtain the exact `obs_endpoint_service_name` through the Huawei Cloud service ticket. Do not guess from a nearby public service name. |
| Precheck reports the cluster is not ENI/Turbo | CCI bursting requires a Turbo cluster with ENI container network mode | Create or use a Turbo cluster with `container_network_type=eni`. Overlay_l2 clusters cannot burst to CCI. |
| VPCEP creation returns `requires_confirmation` without `confirm=true` | Preview-first safety gate is active | Review the plan in the response, then re-run with `confirm=true` after explicit user approval. |

## Escalation Paths

- Pod failures (CrashLoopBackOff, OOMKilled): escalate to `huawei-cloud-cce-pod-failure-diagnoser`
- Network/VPCEP connectivity issues: escalate to `huawei-cloud-cce-network-failure-diagnoser`
- Cluster management (addon uninstall, node drain): escalate to `huawei-cloud-cce-cluster-management`