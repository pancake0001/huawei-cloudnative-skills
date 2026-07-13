# Risk Rules

- Allowed hcloud operations are read-only CCE discovery and metadata operations plus `CCE CreateKubernetesClusterCert` for short-lived kubeconfig acquisition.
- Allowed kubectl operations are read-only: `cluster-info`, `auth can-i`, `get`, `describe`, `logs`, and `top`.
- `CreateKubernetesClusterCert` is allowed only for diagnosis. Store kubeconfig outside the repository, restrict permissions where possible, and delete it after the run if temporary.
- Do not run `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `uncordon`, `drain`, `taint`, or equivalent mutating operations.
- Do not run CCE node update, reset, delete, ECS reboot, ECS stop, or host repair operations.
- Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, old `huawei_node_*` actions, or Huawei Cloud SDK imports.
- Do not run node shell commands, SSH, packet capture, or host log collection unless a separate explicitly authorized workflow exists.
- If remediation is needed, provide a candidate action, expected impact, rollback consideration, and handoff to `huawei-cloud-cce-auto-remediation-runner` or the node operations owner.
- Never output AK, SK, security tokens, kubeconfig certificate data, Authorization headers, or secret values.
- Treat metrics absence as a verification gap. Do not switch to Python SDK, AOM SDK, or unsigned/signed direct API calls to fill the gap inside this skill.
