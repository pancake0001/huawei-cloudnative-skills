# Workflow

1. Resolve `region`, `project_id`, `cluster_id`, and cluster name with `hcloud CCE`.
2. Define a bounded time window. Default to the last 1 hour for active incidents.
3. Query active and historical alarm Events with `hcloud AOM ListEvents`.
4. Normalize alarm records into name, severity, status, resource, namespace, workload, Pod, node, component, timestamps, and message.
5. Group by resource, namespace, workload, node, component, alarm type, and severity.
6. Detect:
   - first alarm near the user symptom,
   - burst alarms in a short window,
   - chronic alarms that predate the incident,
   - newly resolved alarms around recovery,
   - alarm/resource fan-out that indicates impact scope.
7. Query alarm rules, action rules, or mute rules only when notification behavior is part of the question.
8. Route follow-up:
   - Pod or workload signals -> Pod/workload diagnoser.
   - Node signals -> node diagnoser.
   - ELB, Ingress, DNS, EIP, NAT signals -> network diagnoser.
   - PVC, mount, attach, disk latency signals -> storage diagnoser.
   - Multiple domains -> root-cause analyzer.
9. Report summary, root-cause signal, and next actions before raw alarm groups.

Do not mutate alarm rules from this workflow.
