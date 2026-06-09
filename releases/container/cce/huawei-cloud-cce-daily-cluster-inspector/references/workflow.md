# Workflow

1. Default: run quick check first; if healthy, output heartbeat summary directly.
2. Quick check scope is fixed: AOM Critical/Major firing alarms, Kubernetes abnormal Events, Pod CPU/Memory TopN, and Node CPU/Memory/Disk TopN. It only answers whether anomalies exist.
3. Quick check must not inspect application root cause, Deployment replica details, Pod lifecycle details, ELB, EIP, NAT, or other peripheral resource state.
4. If quick check finds anomalies, escalate to deep diagnosis.
5. Deep diagnosis first analyzes the three symptom sources in detail: AOM alarms, abnormal Kubernetes Events, and Pod/Node monitoring TopN.
6. Deep diagnosis builds `abnormal_object_analysis`: abnormal objects, symptoms, first_seen, last_seen, and evidence source per object.
7. Deep diagnosis enriches object relationships: Pod->Node/Workload/Service, Service->Ingress/ELB/EIP, Ingress->Service, Node->affected Pods, and Cluster->peripheral summary.
8. When related Service/Ingress resources point to ELB/EIP/NAT, deep diagnosis correlates peripheral status and metrics.
9. Label each risk as P0/P1/P2 with recommended responsible owner.
10. After inspection completes with abnormal findings, build a root-cause handoff package for `huawei-cloud-cce-root-cause-analyzer`: region, cluster_id, namespace, target objects, time window, symptoms, evidence, severity, impact scope, and data gaps.
11. Use `huawei-cloud-cce-root-cause-analyzer` first to analyze root cause, evidence chain, confidence, impact scope, and remediation hints. The inspector must not select final remediation from inspection evidence alone.
12. Pass the root-cause-backed remediation hints to `huawei-cloud-cce-auto-remediation-runner`.
13. `huawei-cloud-cce-auto-remediation-runner` outputs recovery advice by default, or performs recovery actions only when the customer has explicitly authorized the action under its risk rules.
14. Output read-only inspection report plus root-cause and recovery handoff status.

## Quick vs Deep Boundary

| Stage | Does | Does Not Do |
|-------|------|-------------|
| Quick check | Alarm/Event/Pod TopN/Node TopN existence check | Root cause, workload detail, ELB/EIP/NAT analysis, remediation |
| Deep diagnosis | Detailed symptom analysis, abnormal object timeline, object relationships, peripheral resource status | Final root-cause decision or mutation action |
| Root cause analyzer | Root cause, evidence chain, confidence, remediation hints | Direct recovery execution |
| Auto remediation runner | Recovery advice, preview, or authorized execution | Independent root-cause analysis |
