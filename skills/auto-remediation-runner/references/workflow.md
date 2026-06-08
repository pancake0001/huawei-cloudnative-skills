# Workflow

1. Convert user intentions or root cause conclusions into actions, objects, parameters and verification standards.
2. If the root cause is that the Deployment new version startup command/image/probe/CrashLoop is unavailable, give priority to `rollback_previous_revision`.
3. Check the action risk level. Deployment rollback, scale, resize, cordon, and uncordon belong to R2; delete, drain, reboot, and HSS status changes belong to R3.
4. The first call must be without `confirm=true` to get a preview or risk prompt.
5. Output preview results, impact scope, rollback method, and post-execution verification plan.
6. Wait for explicit confirmation from the user. The confirmation content should at least include action, object, region, and cluster_id.
7. The user is allowed to carry `confirm=true` only after confirmation.
8. After execution, call the read-only tool to verify the Pod, Node, Workload, Events or vulnerability status.
9. For automatic recovery arrangement, output a complete Markdown execution report, including diagnosis basis, action results and verification results.