# Risk Rules

- Alarm query, alarm analysis, action rule query, and mute rule query are all read-only operations.
- Creating and batch configuring AOM alarm rules is R2 and must be previewed first; only after explicit user confirmation may `confirm=true` be added to execute.
- Updating, disabling, enabling, and deleting AOM alarm rules is allowed only with the documented risk controls and confirmation workflow.
- Modifying action rules, mute rules, or other cloud resources is prohibited.
- Do not interpret absence of active alarms as "no problem"; always cross-reference history alarms.
- Output must never expose AK/SK, tokens, or complete sensitive logs.
- If the user requests scaling, rebooting, draining, or other remediation actions, output recommendations only and hand off to `huawei-cloud-cce-auto-remediation-runner`.
