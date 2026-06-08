# RiskRules

- Allows automated read-only queries of PVC, PV, StorageClass, Pod, Node, Event, VolumeAttachment, NetworkPolicy, Kubelet `/stats/summary`, Everest CSI logs, EVS/SFS/SFS Turbo, Security Groups and VPC ACLs.
- Allows generation of Markdown diagnostic reports, read-only validation command suggestions, and recovery plans.
- No PVC/PV/Pod deletion, no patch finalizer, no force detach/attach EVS, no modification of StorageClass, StorageClass parameters, PV reclaim policy, IAM delegation, AK/SK Secret, security group, ACL or VPC routing.
- Do not perform `kubectl exec`, node SSH, packet capture, stress testing, fsck, dmesg collection or active NFS/OBS read and write detection unless the user explicitly requests and confirms the risk.
- Any action that will change the data plane or control plane must be handed over to `auto-remediation-runner`, and the impact scope, rollback method, data consistency risk and verification criteria must be output first.
- Do not directly recommend removing the `kubernetes.io/pvc-protection` finalizer during PVC Terminating; you must first prove that there are no Pod references and business data risks.
- In EVS residual mounting or read-only file system scenarios, it is not recommended to force uninstall, force mount, or directly restart database workloads before confirming the consistency of the file system.