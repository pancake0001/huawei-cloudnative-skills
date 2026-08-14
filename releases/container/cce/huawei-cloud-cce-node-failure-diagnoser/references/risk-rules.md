# Risk Rules

- Allowed hcloud operations are read-only CCE discovery and metadata operations. Kubernetes evidence must use `kubectl cce ...` through the kubectl-cce plugin.
- Allowed kubectl operations are read-only: `cluster-info`, `auth can-i`, `get`, `describe`, `logs`, and `top`.
- Kubernetes evidence must use the kubectl-cce plugin. Do not generate or store kubeconfig in the repository.
- Do not run `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `uncordon`, `drain`, `taint`, or equivalent mutating operations.
- Do not run CCE node update, reset, delete, ECS reboot, ECS stop, or host repair operations.
- Do not use Python SDK dispatcher commands, legacy dispatcher scripts or actions, or Huawei Cloud SDK imports.
- Do not run node shell commands, SSH, packet capture, or host log collection unless a separate explicitly authorized workflow exists.
- If remediation is needed, provide a candidate action, expected impact, rollback consideration, and handoff to `huawei-cloud-cce-auto-remediation-runner` or the node operations owner.
- Never output AK, SK, security tokens, kubectl-cce proxy credentials, Authorization headers, or secret values.
- Treat metrics absence as a verification gap. Do not switch to Python SDK, AOM SDK, or unsigned/signed direct API calls to fill the gap inside this skill.
