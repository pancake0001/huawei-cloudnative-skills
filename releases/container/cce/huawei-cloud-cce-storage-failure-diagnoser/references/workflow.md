# Workflow

1. Scope: confirm region, project_id, cluster_id, namespace, app_name, workload_type, pvc_name, pod_name, pv_name, volume_id, failure_symptom, and time window. Require `namespace + app_name`, `namespace + pvc_name`, or a specific `pv_name`; never list PVCs or Pods for candidate discovery. For app scope, resolve only the named Deployment/StatefulSet, its selector-matched Pods, and their referenced PVCs.
2. Read `kubectl-cce.md`, verify `hcloud`, `kubectl`, and `kubectl-cce`, and resolve cluster metadata with hcloud.
3. Collect the smallest current Kubernetes evidence set through `kubectl cce`: resolve Pod -> PVC -> PV -> StorageClass -> VolumeAttachment. Do not use `-A`; collect at most 100 Warning Events and 200 CSI log lines by default.
4. Extract the cloud backend ID from PV CSI fields/attributes first. Collect cloud-side read-only metadata with hcloud only when IDs are known or safely correlated: EVS volume, SFS/SFS Turbo share, OBS bucket context,
   VPC/security group/ACL.
5. Classify the failure stage:
   - provisioning/PVC Pending;
   - binding/topology/scheduling;
   - attach/detach/VolumeAttachment;
   - mount/ContainerCreating;
   - runtime I/O/read-only filesystem/capacity/inode;
   - SFS/SFS Turbo/NFS network path;
   - OBS/IAM/credential;
   - teardown/PVC Terminating/finalizer.
6. For each candidate, record direct evidence, counter-evidence, data gaps, confidence, and next verification.
7. Hand node or network findings to the node/network diagnosers when storage symptoms are secondary.
8. Put Summary, Root Cause Analysis, and Next Actions at the top of the Markdown report.
