# Risk Rules

- This skill is read-only. Allowed operations are discovery, metric query, local parsing, and Markdown report generation.
- Allowed cloud access path: `hcloud` CLI for CCE metadata, CES metrics, and cloud-resource discovery.
- Allowed Kubernetes access path: `kubectl cce` for resource relationships and live Metrics API checks.
- Allowed observability exception: approved AOM Prometheus range-query evidence when the runtime already has a safe signing path. Do not hand-roll IAM token flows or print signed headers.
- Do not use Huawei Cloud SDK imports, Kubernetes SDK clients, generated kubeconfig, temporary kubeconfig files, or direct mutation commands.
- Do not run `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout restart`, `rollout undo`, `exec`, `attach`, or `port-forward`.
- Keep metric windows bounded. Start with 1 hour for active incidents and avoid windows over 24 hours unless the user asks.
- Redact or avoid secrets, tokens, Authorization headers, kubeconfig contents, and credential material.
- Missing AOM/CES/Metrics API series are data gaps. Do not describe missing metrics as healthy behavior.
- Thresholds are only investigation leads. Require corroborating Events, logs, alarms, topology, or user symptoms before assigning high-confidence root cause.
- Do not make automatic scaling or remediation decisions from metrics alone. Hand off to the appropriate diagnoser or remediation skill only after explicit user confirmation.
