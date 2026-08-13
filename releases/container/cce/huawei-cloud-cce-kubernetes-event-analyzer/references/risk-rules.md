# Risk Rules

- Query and analyze Events only; never create, update, delete, scale, restart, or remediate cluster resources.
- Use `kubectl cce` for current Kubernetes Events. Do not generate kubeconfig, use external kubeconfig fallback, call Kubernetes SDKs, or use Python SDK dispatcher actions.
- Use hcloud LTS only for bounded historical Event queries when the Event LogConfig and LTS IDs are known.
- Keep queries bounded. Default to Warning Events and a recent window unless the user asks for broader output.
- If RBAC denies Events, LTS is not configured, or Event retention has expired, report a data gap and reduce confidence.
- Do not expose secrets, tokens, Authorization headers, kubeconfig content, or application Secret data.
- Event analysis suggests likely causes; hand off cause-level diagnosis to the relevant domain diagnoser.
