# Risk Rules

- This skill is read-only. Allowed operations are discovery, log/event/metric/alarm query, local summarization, and Markdown report generation.
- Use `hcloud` for CCE cloud metadata and supported AOM/LTS/CES read-only evidence.
- Use `kubectl cce` for Kubernetes resource state, Events, bounded logs, and Metrics API checks.
- Do not use Huawei Cloud SDK imports, Kubernetes SDK clients, generated kubeconfig, temporary kubeconfig files, direct IAM HTTP flows, or old dispatcher actions.
- Do not run mutation commands: `apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout restart`, `rollout undo`, `cordon`, `drain`, cloud bind/unbind,
  hibernate, awake, start, stop, or reboot.
- Do not run interactive or streaming commands such as `exec`, `attach`, `port-forward`, `logs -f`, or `watch`.
- Keep log collection bounded with `--tail`, explicit Pod/container scope, and short time windows where possible.
- Redact secrets in log output. If a credential-like value appears, report only source, object, container, and approximate line/time.
- Missing AOM, LTS, Metrics API, logs, or RBAC evidence is a data gap; do not treat absence of evidence as healthy state.
- This skill prepares context. It should recommend the next diagnoser instead of making high-confidence root-cause claims from partial evidence.
