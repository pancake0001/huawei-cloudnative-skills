# RiskRules

- Only automated diagnostics, queries, and report generation are allowed.
- Do not directly perform expansion and contraction, deletion, drain, reboot, vulnerability status modification, cluster sleep/wakeup.
- Recovery recommendations in the root cause report must distinguish between automatically verifiable actions and actions that require user confirmation.
- Instead of drawing direct conclusions from a single alarm, at least a timeline or chain of evidence must be given.