# Workflow

# # Reusability and gaps

The current warehouse already has the following reusability capabilities:

- Kubernetes objects: `huawei_get_cce_pvcs`, `huawei_get_cce_pvs`, `huawei_get_cce_pods`, `huawei_get_kubernetes_nodes`, `huawei_get_cce_events`, `huawei_get_pod_logs`.
- Huawei Cloud Storage: `huawei_list_evs`, `huawei_get_evs_metrics`, `huawei_list_sfs`, `huawei_list_sfs_turbo`.
- Network certification: `huawei_list_security_groups`, `huawei_list_vpc_acls`, which can reuse the security group/ACL ideas of network-failure-diagnoser.
- Logs and reports: There are output modes for Pod logs, AOM/LTS logs, and Markdown/HTML report-type diagnosers.
- The external huawei-cloud skill also covers ECS/EVS/VPC/ELB/EIP/SFS, CCE Pod/PVC/PV/Event, Pod logs, AOM/LTS, network diagnosis, workload diagnosis and complete report generation; this skill reuses the read-only tools and the habit of "obtaining evidence step by step first, and then outputting the complete report".

Atomic abilities complemented by this skill:

- `huawei_get_cce_storageclasses`: Read the provisioner, parameters, `volumeBindingMode` of StorageClass.
- `huawei_get_cce_volumeattachments`: Read `attached`, `attachError`, `detachError` of VolumeAttachment.
- `huawei_get_cce_node_stats_summary`: Read node `/stats/summary` through API Server agent, parse PVC `usedBytes/capacityBytes` and inode.
- `huawei_get_cce_everest_csi_logs`: Read Everest CSI driver/controller log fragments in `kube-system` and automatically desensitize them.
- `huawei_storage_failure_diagnose`: arrange PVC/PV/SC/Pod/Node/Event/VolumeAttachment/CSI logs/stats in one go, and generate structured findings and Markdown reports.

Capabilities that still require manual or subsequent expansion:

- No `kubectl exec`, node SSH, dmesg, native fsck or active NFS/OBS connectivity probes.
- Do not directly call cloud side detach/force detach, modify IAM delegation, expand PVC, or delete finalizer.
- ConfigMap/Secret's `resourceVersion` has no natural update time; only `managedFields.time`, Pod time and FailedMount event can be used as circumstantial evidence.

# # Input and main process

The minimum input is `region`, `cluster_id`. It is recommended to complete:

- `namespace`, `pvc_name`: PVC Pending, Terminating, and provided first when capacity is exhausted.
- `pod_name`: Pod Pending, ContainerCreating, Running, but will be provided first when IO exception occurs.
- `failure_symptom`: For example, "PVC Pending" "FailedMount mount.nfs timeout" "OBS 403" "Read-only file system" "no space left on device" "PVC Terminating".

Main process:

1. Call `huawei_storage_failure_diagnose`, default `include_stats=true`, `include_logs=true`, `include_cloud=false`.
2. If you need to supplement the cloud side inventory, set `include_cloud=true`, and the EVS/SFS/SFS Turbo and security group/ACL read-only information will be read according to the hit storage type.
3. If the main tool returns `report_markdown`, the final output will be based on this Markdown, and do not discard the evidence matrix.
4. If the main tool fails, follow the four stages below to manually recover.

# # 1. Supply period failure

Admission: PVC `status=Pending`.

Universal preset:

- Read the `volumeBindingMode` of the StorageClass.
- If it is `WaitForFirstConsumer` and there is no associated Pod, the output is "normal behavior, waiting for Pod scheduling to trigger dynamic creation", with high confidence.

Branch:

- EVS: The PVC event hits `FailedProvisioning` + `QuotaExceeded`, which indicates that the EVS cloud disk quota is insufficient.
- SFS/SFS Turbo: The event hits `Subnet IP insufficiency`, or provisioning failure returns `400/403` and the text points to subnet/mount/ip, targeting VPC subnet available IP or mount point allocation issues.
- OBS: The event hits `BucketAlreadyExists` or `InvalidBucketName` and is located as a bucket name conflict or illegal naming.

# # 2. Scheduling and binding period failures

Admission: PVC `Bound`, associated Pod `Pending/Unschedulable`.

EVS:

- Read PV `spec.nodeAffinity`, usually reflects a single AZ.
- Read Pod `nodeSelector`, tolerations and FailedScheduling events.
- Query Ready node labels, taints, and scheduled events.
- If a `volume node affinity conflict` occurs, there are no Ready nodes in the PV AZ, or all nodes in the AZ are blocked by intolerable stains or insufficient resources, the output is "EVS's strong single availability zone attribute causes the Pod to be unable to be scheduled to the AZ where the storage is located".

Local:

- Read PV `nodeAffinity` bound node.
- If the node `Ready=False/Unknown`, "The host to which the local storage belongs is down/offline" is output, with the highest confidence.

# # 3. Failure during mounting period

Admission: Pod stuck on `ContainerCreating`, or event contains `FailedAttachVolume`/`FailedMount`.

EVS:

- Filter VolumeAttachment by PV and target Node.
- VolumeAttachment does not exist: the K8s control plane has not yet issued the mount command.
- `attached=false` and `attachError` hits max/limit/exceed: the upper limit of the number of ECS single-node mount disks.
- `attached=false` and `attachError` hits in-use/attached/lock/status: EVS is occupied by residual nodes or the underlying lock is not released.
- `attached=true` but FailedMount: The cloud side has been mounted, enter the host kernel/file system mounting failure branch.

SFS/SFS Turbo:

- `FailedMount` text contains `mount.nfs` and `timed out`: suspected network data plane blocking.
- Output SFS endpoint and NetworkPolicy circumstantial evidence, and remind you to focus on checking the node security group, SFS security group, VPC ACL and 2049 port.

OBS:

- Read Everest CSI logs, combined with PV/event keywords.
- Hitting `403 Forbidden`, `SignatureDoesNotMatch`, `failed to save temporary ak sk file`, `obsfs: ak size is invalid`, `fuse_opt_parse fail`: locates that the IAM delegation has been changed, the AK/SK Secret is invalid, the Secret field/format is incorrect, or the bucket permission is abnormal.

Permission exception:

- When an event occurs with `permission denied`, `forbidden`, or `access denied`, it will be output as an independent permission candidate; OBS 403 will take the OBS credential branch first.

# # 4. Abnormalities during running and logout periods

Capacity and inode:

- Parse PVC `usedBytes/capacityBytes` and `inodesUsed/inodes` via `/stats/summary`.
- Capacity usage > 95%: Capacity exhausted, highest confidence.
- inode usage > 95%: inode exhaustion, too many small files, highest confidence.

Read-only file system:

- User symptom or event contains `Read-only file system`.
- If there are `DiskPressure`, `KernelOops` or similar events on the same node, "The host triggered the Linux read-only protection mechanism" is output. It is recommended to migrate the workload and check the underlying storage link of the node.

ConfigMap/Secret subPath:

- Pod is mounted using ConfigMap/Secret `subPath`.
- Subsequently, events such as `FailedMount`, `subPath`, `not a directory`, `stale file handle`, etc. appear, and subPath mount point protection/deadlock problems are output.

PVC removal protection:- PVC has `deletionTimestamp` and finalizers include `kubernetes.io/pvc-protection`.
- Traverse all Pods. If the PVC is still referenced, output "Deletion protection takes effect: Please delete residual Pods first" with the highest confidence.

# # Conclusion synthesis

Conclusions are ordered by strength of evidence rather than fixed priorities by stage:

1. Make it clear that event/status fields point directly to cloud quota, bucket name, VolumeAttachment, capacity, or PVC protection: high confidence.
2. The scheduling event is consistent with the PV nodeAffinity/node label: high confidence; only the resource shortage text is medium-high confidence.
3. NFS timeout, read-only file system, IO error: usually medium confidence, and cloud-side security group/node log verification is required.
4. When there is no clear hit, output the evidence gap and do not write the guess as a conclusion.