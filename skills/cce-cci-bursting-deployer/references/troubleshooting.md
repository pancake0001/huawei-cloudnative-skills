# Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `virtual-kubelet` components restart or the virtual node never becomes Ready | The addon received a VPC subnet UUID instead of the Neutron subnet UUID | Run precheck and pass `cci_subnet_id` from `spec.eni_network`. |
| CCI pod is `ImagePullBackOff` or times out while pulling an image | SWR, SWR API, or OBS-compatible VPCEP is missing | Run `huawei_ensure_cce_cci_vpcep`, then verify endpoint status. |
| Docker Hub image pull times out | CCI capacity has no direct public path to Docker Hub | Use a regional SWR image for verification. |
| Workload pods stay Pending and mention a `virtual-kubelet.io/provider` taint | The workload is not using the CCI bursting scheduling profile | Use the smoke action or add `bursting.cci.io/burst-to-cci: enforce` to the workload template labels. |
| OBS gateway endpoint creation fails | The OBS service name does not match the tenant or region setup | Obtain the exact `obs_endpoint_service_name` through the Huawei Cloud service ticket. |
