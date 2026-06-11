# Risk Rules

- `R0` — high risk: destructive, disruptive, or cost/security sensitive actions. RCA may recommend only as advice/preview, never execute.
- `R1` — medium risk: runtime-impacting changes such as rollback, resize, drain, or uncertain node/nodepool actions.
- `R2` — low risk and no new cloud-resource cost: bounded scale-out, HPA configuration with `minReplicas >= currentPodCount` and `maxReplicas > currentPodCount`, cordon/uncordon.
- `R3` — read-only verification: diagnosis, query, status, Events, metrics, image/pull-secret review.
- Only allow automatic execution of diagnosis, query, and report generation actions.
- Do not directly execute scale, delete, drain, reboot, vulnerability state modification, or cluster sleep/wake operations.
- Remediation recommendations in root cause reports must distinguish between automatically verifiable actions and actions requiring user confirmation.
- Do not conclude root cause from a single alarm alone; at minimum, provide a timeline or evidence chain.
