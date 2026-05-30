# Risk Rules

- This skill is read-only by default: it may query Kubernetes stdout logs, LogConfig resources, and LTS log records.
- Creating LogConfig resources is allowed only through `huawei_create_cce_logconfig`. The tool must preview first and requires `confirm=true` before it changes the cluster.
- Deleting LogConfig resources is allowed only through `huawei_delete_cce_logconfig`. The tool must preview the exact target first and requires `confirm=true`.
- Do not update workloads, LogConfig resources, log groups, log streams, or LTS data.
- Never expose AK/SK, tokens, kubeconfig certificates, or full sensitive log payloads in summaries.
- Prefer time-bounded queries. If no time range is provided, use recent logs and keep limits small.
- When logs contain secrets, credentials, cookies, authorization headers, or personal data, summarize the pattern and redact the value.
- If a user asks for remediation based on logs, provide evidence and hand off to the relevant diagnosis or remediation skill instead of changing resources here.
