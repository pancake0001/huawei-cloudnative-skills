# Workflow

1. Scope: confirm region, project_id, cluster_id, namespace, pvc_name, pod_name, volume_id, failure_symptom, and time window.
2. Read `references/kubectl-cce.md`, verify `hcloud`, `kubectl`, and `kubectl-cce`, and resolve cluster metadata with hcloud.
3. Collect current Kubernetes storage state through `kubectl cce`: PVC, PV, StorageClass, VolumeAttachment, Pods, Nodes, Events, and relevant CSI Pods/logs.
4. Collect cloud-side read-only metadata with hcloud only when IDs are known or safely correlated: EVS volume, SFS/SFS Turbo share, OBS bucket context, VPC/security group/ACL.
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
