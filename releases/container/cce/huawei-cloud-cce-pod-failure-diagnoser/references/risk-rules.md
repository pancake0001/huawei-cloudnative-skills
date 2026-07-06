# Risk Rules

- Read-only diagnostic commands are allowed: `hcloud CCE ListClusters`, `ShowCluster`, `ShowClusterEndpoints`, `CreateKubernetesClusterCert`, and `kubectl get`, `describe`, `logs`, `top`, `auth can-i`, `cluster-info`.
- `CreateKubernetesClusterCert` is allowed only to obtain short-lived kubeconfig for read-only diagnosis. Store kubeconfig outside the repository or in a temporary ignored path, restrict permissions where possible, and clean it up when no longer needed.
- This skill must not run `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `drain`, `taint`, or any equivalent mutating operation.
- This skill must not call hcloud create/update/delete operations except `CCE CreateKubernetesClusterCert`.
- This skill must not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, old `huawei_pod_*` actions, or Huawei Cloud SDK imports.
- If scaling, restarting, deleting, rebuilding, node isolation, or quota changes are recommended, hand them off to `huawei-cloud-cce-auto-remediation-runner` or the relevant domain skill as recommendations only.
- Log output must contain only sanitized excerpts. Never copy raw passwords, tokens, AK/SK, kubeconfig certificate data, Authorization headers, or image registry secrets into the output.
- For ImagePullBackOff, prioritize Events and image/pull-secret evidence. Do not repeatedly request logs for a container that was never created.
- For OOMKilled, PendingScheduling, Evicted, and storage/network failures, separate diagnosis from remediation. Explain the evidence and proposed next action, but do not mutate cluster state.
