# Workflow

1. Convert the user's intent or root cause conclusion into an action, object, parameters, and verification criteria.
2. If the root cause is that a Deployment's new version is unavailable due to startup command, image, probe, or CrashLoop, prefer `rollback_previous_revision` strategy.
3. Check action risk level:
   - R0: read-only verification.
   - R1: customer-authorized workload scale-out, node pool scale-out, cordon, and uncordon. HPA configuration is R1 only when current Pod count is known, `minReplicas >= currentPodCount`, and `maxReplicas > currentPodCount`.
   - R2: workload resize, Deployment rollback, scale-in, node pool resize with unknown direction, HPA changes outside the R1 condition, drain, and ECS start.
   - R3: delete, ECS reboot/stop, cluster EIP bind/unbind, hibernate/awake, and HSS status change.
4. R0 can run directly. R1 can run directly only when the customer has explicitly authorized automatic R1 actions for the target scope; otherwise generate a preview first.
5. R2 and R3 calls must first be made without `confirm=true` to obtain preview/risk prompt.
6. Output preview results, impact scope, rollback method, and post-execution verification plan.
7. Wait for explicit user confirmation when required. Confirmation must include at least: action, target object, region, cluster_id.
8. Only after confirmation may call again with `confirm=true`, except for R1 actions covered by explicit customer automatic-action authorization.
9. After execution, call read-only verification actions to check Pod, Node, Workload, Events, vulnerability status.
10. For automatic recovery plans, output complete Markdown execution report including diagnosis basis, action results, verification results.
