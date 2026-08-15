# Risk Rules

- This skill is read-only change correlation and report generation only.
- Do not roll back, scale, patch, delete, restart, drain, reboot, modify ConfigMap/Secret, modify Service/Ingress/Gateway, modify NetworkPolicy/RBAC, or change
  cloud network resources.
- Do not use Python SDK dispatcher commands, legacy `huawei-cloud[.]py` entrypoints, `skill action=exec`, old change/query actions, kubeconfig generation,
  direct IAM curl flows, or Huawei Cloud SDK imports.
- Use `kubectl cce` for current Kubernetes evidence, hcloud for read-only cloud metadata, and dedicated event/alarm/metric/log skills for historical or
  observability evidence.
- Do not claim causality from an object update alone. Require temporal order plus response evidence or a focused diagnosis finding.
- Treat missing audit logs, missing LTS streams, missing rollout history, and RBAC denials as data gaps that lower confidence.
- Never expose AK/SK, tokens, kubeconfig content, Authorization headers, registry credentials, application secrets, or kubectl-cce credential material.
- Never retrieve or report Kubernetes Secret values. Collect ConfigMap/Secret metadata only unless the user supplies a sanitized ConfigMap before/after
  artifact.
- Current resourceVersion, managed fields, creation time, retained ReplicaSets, and current cloud state do not by themselves prove a historical change or actor.
- Remediation must be handed off to `huawei-cloud-cce-auto-remediation-runner` after explicit user confirmation.
