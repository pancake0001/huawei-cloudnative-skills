# Risk Rules

- This skill is read-only topology and impact analysis only.
- Do not modify Services, Ingresses, EndpointSlices, Deployments, NetworkPolicies, ELB, EIP, NAT, VPC, security groups, or Nodes.
- Do not use Python SDK dispatcher commands, legacy `huawei-cloud[.]py` entrypoints,
  `skill action=exec`, old dependency-impact actions, kubeconfig generation, direct IAM
  curl flows, or Huawei Cloud SDK imports.
- Use `kubectl cce` for Kubernetes topology evidence and `hcloud` only for read-only cluster/cloud metadata.
- Static topology alone proves possible impact paths, not real traffic impact. Require logs, metrics, alarms, or user symptoms before claiming actual traffic loss.
- If RBAC denies a resource, EndpointSlice is unavailable, namespace is unknown, or traffic logs are absent, write a confidence limit instead of hiding the gap.
- Never expose AK/SK, tokens, kubeconfig content, Authorization headers, application secrets, or kubectl-cce credential material.
- Do not run `exec`, `attach`, `port-forward`, packet capture, stress tests, or active traffic generation from this skill.
- Do not retrieve Secret values or include sensitive ConfigMap/application data in topology evidence.
