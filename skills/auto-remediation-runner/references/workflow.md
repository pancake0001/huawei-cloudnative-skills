# Workflow

1. Convert user intentions or root cause conclusions into actions, objects, parameters and verification standards.
2. If the root cause is that the Deployment new version startup command/image/probe/CrashLoop is unavailable, give priority to `rollback_previous_revision`.
3. Check the action risk level. Read-only verification belongs to R0. Customer-authorized workload scale-out, node pool scale-out, cordon, and uncordon belong to R1. HPA configuration belongs to R1 only when the current Pod count is known, `minReplicas >= currentPodCount`, and `maxReplicas > currentPodCount`. Workload resize, Deployment rollback, scale-in, node pool resize with unknown direction, HPA changes outside the R1 condition, drain, and ECS start belong to R2. Delete, ECS reboot/stop, cluster EIP bind/unbind, and HSS status changes belong to R3.
4. R0 can run directly. R1 can run directly only when the customer has explicitly authorized automatic R1 actions for the target scope; otherwise generate a preview first.
5. R2 and R3 calls must first be made without `confirm=true` to get a preview or risk prompt.
6. Output preview results, impact scope, rollback method, and post-execution verification plan.
7. Wait for explicit confirmation from the user when required. The confirmation content should at least include action, object, region, and cluster_id.
8. The user is allowed to carry `confirm=true` only after confirmation, except for R1 actions covered by explicit customer automatic-action authorization.
9. After execution, call the read-only tool to verify the Pod, Node, Workload, Events or vulnerability status.
10. For automatic recovery arrangement, output a complete Markdown execution report, including diagnosis basis, action results and verification results.
