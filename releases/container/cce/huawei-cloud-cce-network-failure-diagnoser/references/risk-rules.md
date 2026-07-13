# Risk Rules

- Allowed hcloud CCE operations are cluster discovery and `CCE CreateKubernetesClusterCert`.
- Allowed cloud-network hcloud operations are read-only list/show operations for ELB, VPC, EIP, and NAT.
- Allowed kubectl operations are read-only: `cluster-info`, `auth can-i`, `get`, `describe`, `logs`, and `top`.
- `CreateKubernetesClusterCert` is allowed only for diagnosis. Store kubeconfig outside the repository, restrict permissions where possible, and delete it after the run if temporary.
- Do not run `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, or restart controller/CoreDNS/workload components.
- Do not run hcloud create/update/delete operations for ELB, VPC, EIP, NAT, CCE, or any other service.
- Do not run `kubectl exec`, packet capture, active traffic generation, or stress tests unless the user explicitly requests the test and accepts the risk.
- Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, old `huawei_network_*` actions, or Huawei Cloud SDK imports.
- If a network change is recommended, describe expected impact, rollback consideration, verification criteria, and handoff owner. Do not apply the change.
- Never output AK, SK, security tokens, kubeconfig certificate data, Authorization headers, cookies, or application secrets from logs.
