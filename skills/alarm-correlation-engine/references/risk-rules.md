# RiskRules

- Alarm query, alarm analysis, action rule query, and silent rule query are all read-only operations.
- Allows creation, modification and deletion of AOM alert rules, but must be previewed first; execution with `confirm=true` is only allowed after explicit confirmation by the user.
- Modification of action rules, silent rules or other cloud resources is prohibited.
- Do not interpret the absence of active alarms as no problem; the history must be checked.
- No AK/SK, token or full sensitive logs should be exposed in the output.
- If the user requires scaling, restarting, draining or other recovery actions, only the suggestions are output and forwarded to `auto-remediation-runner`.