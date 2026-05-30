# Risk Rules

- This skill is read-only: it only queries Kubernetes events and lists related resources. No modifications are made.
- Do not expose sensitive data such as node names, pod names, or workload names that could identify production systems in public outputs. Use redacted or fictional examples in summaries when possible.
- If event analysis reveals a clear remediation path, provide evidence and hand off to the appropriate diagnosis or remediation skill instead of executing recovery actions here.
- Keep event queries time-bounded. Prefer recent windows (hours=1-24) to avoid overwhelming results.
- If the user asks to take action based on event findings, redirect to `auto-remediation-runner` with the evidence summarized.