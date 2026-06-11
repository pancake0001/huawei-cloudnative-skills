# Workflow

1. Convert the user's intent, root cause conclusion, or RCA `remediation_candidates` into an action, object, parameters, risk level, and verification criteria.
   - Preferred RCA handoff call: `huawei_auto_remediation_run region=<region> cluster_id=<cluster_id> remediation_candidates='<RCA remediation_candidates JSON>'`.
   - Do not pass resource bottleneck cases as rollback-only `strategy=rollback_previous_revision` calls; rollback-only orchestration checks rollout health and may stop at `HealthyOrConverging`.
2. If the root cause is that a Deployment's new version is unavailable due to startup command, image, probe, or CrashLoop, prefer `rollback_previous_revision` strategy.
3. Check action risk level:
   - R3: read-only verification.
   - R2: customer-authorized workload scale-out, cordon, and uncordon when the action does not add cloud-resource cost. HPA configuration is R2 only when current Pod count is known, `minReplicas >= currentPodCount`, and `maxReplicas > currentPodCount`.
   - R1: workload resize, Deployment rollback, scale-in, node pool resize, HPA changes outside the R2 condition, drain, and ECS start.
   - R0: delete, ECS reboot/stop, cluster EIP bind/unbind, hibernate/awake, HSS status change, and cost/security-sensitive actions.
4. R3 can run directly. R2 can run directly only when the customer has explicitly authorized automatic R2 actions for the target scope; otherwise generate a preview first.
5. R1 and R0 calls must first be made without `confirm=true` to obtain preview/risk prompt.
6. Output preview results, impact scope, rollback method, and post-execution verification plan. For candidate handoff, return `candidate_preview` instead of failing on unsupported strategy names.
7. Wait for explicit user confirmation when required. Confirmation must include at least: action, target object, region, cluster_id.
8. Only after confirmation may call again with `confirm=true`, except for R2 actions covered by explicit customer automatic-action authorization.
9. After execution, call read-only verification actions to check Pod, Node, Workload, Events, vulnerability status.
10. For automatic recovery plans, output complete Markdown execution report including diagnosis basis, action results, verification results.
