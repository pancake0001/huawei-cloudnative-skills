# Risk Rules

- This skill is read-only. It may query and analyze alarms, rules, action rules, mute rules, and CCE metadata.
- Do not create, update, enable, disable, delete, configure, or clean alarm rules or notification rules from this skill.
- Use `hcloud` for AOM, CCE, and IAM/project evidence.
- Do not use Huawei Cloud SDK imports, legacy dispatcher actions, hand-written IAM curl flows, or out-of-band cloud APIs.
- Do not use Kubernetes commands for alarm evidence unless a downstream diagnoser is explicitly invoked.
- Output must never expose AK/SK, security tokens, Authorization headers, profile secrets, or raw signed payloads.
- Absence of active alarms does not prove health. Always check historical alarms when the incident time is known.
- Alarm evidence alone is rarely a complete root cause. Correlate with Events, metrics, logs, topology, or change history before assigning high confidence.
- If the user asks to modify alarms, provide a preview-style recommendation and hand off to a dedicated alarm-management or remediation workflow.
