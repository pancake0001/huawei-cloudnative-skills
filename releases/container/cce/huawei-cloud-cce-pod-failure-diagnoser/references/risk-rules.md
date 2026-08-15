# Risk Rules

- Read-only diagnostic commands are allowed: `hcloud CCE ListClusters`, `ShowCluster`, `ShowClusterEndpoints`, and `kubectl cce ... get`, `describe`, `logs`,
  `top`, `auth can-i`, `cluster-info`.
- Kubernetes evidence must use the kubectl-cce plugin. The plugin does not write kubeconfig; do not persist credentials or proxy details in the repository.
- This skill must not run `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `drain`, `taint`, or any equivalent
  mutating operation.
- This skill must not call hcloud create/update/delete operations.
- This skill must not use Python SDK dispatchers, legacy skill execution actions, old Huawei Pod actions, or Huawei Cloud SDK imports.
- If scaling, restarting, deleting, rebuilding, node isolation, or quota changes are recommended, hand them off to `huawei-cloud-cce-auto-remediation-runner` or
  the relevant domain skill as recommendations only.
- Log output must contain only sanitized excerpts. Never copy raw passwords, tokens, AK/SK, kubectl-cce proxy credentials, Authorization headers, or image
  registry secrets into the output.
- For ImagePullBackOff, prioritize Events and image/pull-secret evidence. Do not repeatedly request logs for a container that was never created.
- For OOMKilled, PendingScheduling, Evicted, and storage/network failures, separate diagnosis from remediation. Explain the evidence and proposed next action,
  but do not mutate cluster state.
