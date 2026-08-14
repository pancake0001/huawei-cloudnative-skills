# Risk Rules

- Allowed hcloud CCE operations are cluster discovery and metadata reads. Kubernetes evidence must use `kubectl cce ...` through the kubectl-cce plugin.
- Allowed cloud-network hcloud operations are read-only list/show operations for ELB, VPC, EIP, and NAT.
- Allowed kubectl operations are read-only: `cluster-info`, `auth can-i`, `get`, `describe`, `logs`, and `top`.
- Kubernetes evidence must use the kubectl-cce plugin. Do not generate or store kubeconfig in the repository.
- Do not run `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, or restart controller/CoreDNS/workload components.
- Do not run hcloud create/update/delete operations for ELB, VPC, EIP, NAT, CCE, or any other service.
- The kubectl-cce plugin blocks `exec`, `attach`, and `port-forward`. Do not bypass that boundary with kubeconfig, SDK, packet capture, active traffic generation,
  or stress tests. Hand active connectivity testing to an approved test path after explicit authorization.
- Do not use Python SDK dispatcher commands, legacy dispatcher scripts or actions, or Huawei Cloud SDK imports.
- If a network change is recommended, describe expected impact, rollback consideration, verification criteria, and handoff owner. Do not apply the change.
- Never output AK, SK, security tokens, kubectl-cce proxy credentials, Authorization headers, cookies, or application secrets from logs.
