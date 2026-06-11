# Risk Rules

- `R0` — high risk: destructive, disruptive, or cost/security sensitive actions. Never execute automatically.
- `R1` — medium risk: runtime-impacting changes such as rollback, resize, drain, or uncertain node/nodepool actions. Output advice/preview only unless separately confirmed by the user.
- `R2` — low risk and no new cloud-resource cost: bounded scale-out, HPA configuration with `minReplicas >= currentPodCount` and `maxReplicas > currentPodCount`, cordon/uncordon. Execute only when customer authorization covers the target scope.
- `R3` — read-only verification: diagnosis, query, status, Events, metric, image/pull-secret review. May run directly.
- Inspection and RCA evidence collection allow only read-only actions.
- After RCA, candidates with `risk_level` R3 may be executed directly by calling the candidate `action` with candidate `params`; R2 candidates may be executed only when explicit customer authorization covers the target scope.
- Candidates with `risk_level` R1 or R0 must not be executed automatically; output advice and request explicit user confirmation outside this daily-inspector chain.
- Prohibited automatic actions in this skill: deletion, drain, reboot, hibernate, awake, EIP bind/unbind, HSS state change, and any R1/R0 candidate.
- Inspection reports must never contain AK/SK, tokens, certificates, or full kubeconfig.
- After anomalies are found, inspection evidence must be handed to `huawei-cloud-cce-root-cause-analyzer` before remediation is selected.
- Do not call `huawei-cloud-cce-auto-remediation-runner` from the daily-inspector post-RCA flow; process `remediation_candidates` directly by risk level.
