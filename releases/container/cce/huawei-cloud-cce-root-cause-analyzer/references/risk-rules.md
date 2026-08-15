# Risk Rules

- Read-only only: allow discovery, diagnosis, metric/log/event query, and report generation.
- Do not scale, delete, patch, restart, drain, reboot, bind/unbind EIP, change routing, modify security groups, modify NetworkPolicy/RBAC, sleep/wake clusters,
  or change vulnerability state.
- Do not use Python SDK dispatcher commands, legacy dispatcher scripts or actions, kubeconfig generation, direct IAM HTTP flows, or Huawei Cloud SDK imports.
- Use `kubectl cce` for Kubernetes evidence and `hcloud` for cloud-side read-only evidence. If either path fails, report a sanitized data gap and reduce
  confidence.
- Treat the observability context package as first-pass evidence. Re-check high-risk or contradictory findings before assigning high-confidence root cause.
- Do not conclude root cause from a single alarm or isolated object update. Require a timeline or evidence chain.
- Each root cause candidate must include supporting evidence, counter-evidence, data gaps, confidence, and next verification.
- Do not expose AK/SK, security tokens, kubeconfig content, Authorization headers, registry secrets, application secrets, or kubectl-cce credential material.
- Remediation recommendations must identify which actions require user confirmation and should be handed to `huawei-cloud-cce-auto-remediation-runner`.
