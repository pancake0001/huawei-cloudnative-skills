# Workflow

1. Default: run quick check first; if healthy, output heartbeat summary directly.
2. Quick check scope is fixed: AOM Critical/Major firing alarms, Kubernetes abnormal Events, Pod CPU/Memory TopN, and Node CPU/Memory/Disk TopN. It only answers whether anomalies exist.
3. Quick check must not inspect application root cause, Deployment replica details, Pod lifecycle details, ELB, EIP, NAT, or other peripheral resource state.
4. If quick check finds anomalies, escalate to deep diagnosis.
5. Deep diagnosis merges AOM alarm groups and correlates them with quick-check symptoms.
6. Deep diagnosis analyzes abnormal Events, affected Pod/Deployment objects, related application metadata, and application fault evidence such as Pod states and replica mismatches.
7. Deep diagnosis summarizes Pod/Node monitoring abnormal time windows so the root-cause analyzer can correlate alarm, event, and metric order.
8. When ingress/network signals are present, deep diagnosis also correlates Service/Ingress-discovered ELB, EIP, and NAT state and metrics.
9. Label each risk as P0/P1/P2 with recommended responsible owner.
10. After inspection completes with abnormal findings, build a root-cause handoff package for `huawei-cloud-cce-root-cause-analyzer`: region, cluster_id, namespace, target object, time window, symptoms, evidence, severity, impact scope, and data gaps.
11. Use `huawei-cloud-cce-root-cause-analyzer` first to analyze root cause, evidence chain, confidence, impact scope, and remediation hints. The inspector must not select final remediation from inspection evidence alone.
12. Pass the root-cause-backed remediation hints to `huawei-cloud-cce-auto-remediation-runner`.
13. `huawei-cloud-cce-auto-remediation-runner` outputs recovery advice by default, or performs recovery actions only when the customer has explicitly authorized the action under its risk rules.
14. Output read-only inspection report plus root-cause and recovery handoff status.

## Quick vs Deep Boundary

| Stage | Does | Does Not Do |
|-------|------|-------------|
| Quick check | Alarm/Event/Pod TopN/Node TopN existence check | Root cause, workload detail, ELB/EIP/NAT analysis, remediation |
| Deep diagnosis | Evidence merge, application context, abnormal metric windows, peripheral resource status | Final root-cause decision or mutation action |
| Root cause analyzer | Root cause, evidence chain, confidence, remediation hints | Direct recovery execution |
| Auto remediation runner | Recovery advice, preview, or authorized execution | Independent root-cause analysis |
