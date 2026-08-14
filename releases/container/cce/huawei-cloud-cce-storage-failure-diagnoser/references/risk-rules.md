# Risk Rules

- Read-only storage diagnosis only.
- Do not create, patch, delete, or resize PVC/PV/Pod/StorageClass resources.
- Do not remove finalizers, force detach/attach EVS disks, modify IAM delegations, edit Secrets, edit security groups/ACLs, run fsck, run node SSH, or run `kubectl exec`.
- Do not use Python SDK dispatcher commands, legacy dispatcher scripts or actions, kubeconfig generation, direct IAM HTTP flows, or Huawei Cloud SDK imports.
- Use `kubectl cce` for Kubernetes storage evidence and `hcloud` for cloud-side read-only storage/network metadata.
- Keep CSI logs bounded with `--tail` and sanitize secrets, tokens, endpoints containing credentials, bucket credentials, and application Secret data.
- If RBAC denies VolumeAttachment/CSI logs, cloud volume ID is unknown, or metrics are unavailable, write it as a data gap and lower confidence.
- Remediation must be handed off to `huawei-cloud-cce-auto-remediation-runner` after explicit user confirmation.
