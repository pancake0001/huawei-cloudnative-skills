# Workflow

1. Default: run quick check first; if healthy, output heartbeat summary directly.
1. Inspection time window is unified across AOM alarms, Pod/Node/CoreDNS metrics, deep monitoring, and peripheral resource metrics. Default is the past 6 hours; if `inspection_period_minutes`, `inspection_period_hours`, `inspection_window_minutes`, or `inspection_window_hours` is provided, use that value instead.
2. Quick check scope is fixed: AOM Critical/Major firing alarms, Kubernetes abnormal Events, Pod CPU/Memory TopN, Node CPU/Memory/Disk TopN, and CoreDNS CPU/success-rate/latency checks. It only answers whether anomalies exist.
3. Quick check must not inspect application root cause, Deployment replica details, Pod lifecycle details, ELB, EIP, NAT, or other peripheral resource state.
4. If quick check finds anomalies, escalate to deep inspection.
5. Deep inspection merges raw signal sources that should be merged: AOM alarms, Kubernetes abnormal Events, Pod TopN, Node TopN, and CoreDNS monitoring evidence.
6. Deep inspection builds `abnormal_object_analysis`: object kind, namespace, name, symptoms, first_seen/last_seen, source detail, and read-only relationship evidence.
7. If abnormal objects involve surrounding resources, deep inspection also runs monitoring/status inspection for related ELB, EIP, NAT, and ECS resources.
8. Deep inspection must not infer the final root cause or generate recovery strategy.
9. Root cause conclusion, confidence, impact reasoning, and recovery planning belong to downstream skills.
10. Label inspection severity and owner separately from remediation risk. Remediation risk is assigned by RCA remediation candidates using R0-R3.
11. After inspection completes with abnormal findings, build a root-cause handoff package for `huawei-cloud-cce-root-cause-analyzer`: region, cluster_id, namespace, abnormal target objects, abnormal time window, symptoms, abnormal-only evidence, severity, impact scope, and data gaps. Healthy/normal check items must stay in the inspection report and must not enter RCA handoff evidence.
12. Use `huawei-cloud-cce-root-cause-analyzer` first to analyze root cause, evidence chain, confidence, impact scope, and remediation hints. The inspector must not select final remediation from inspection evidence alone.
13. Process root-cause-backed `remediation_candidates` directly.
14. Execute candidates whose `risk_level` is `R3` directly, and execute `R2` candidates only when explicit customer authorization covers the target scope; do not call `huawei-cloud-cce-auto-remediation-runner` in this daily-inspector chain.
15. For `R1` and `R0` candidates, output advice only: action, target, reason, impact scope, verification method, and confirmation requirements.
16. Output inspection report plus root-cause result, R3/R2-authorized execution results, and R1/R0 recovery advice.

## Quick vs Deep Boundary

| Stage | Does | Does Not Do |
|-------|------|-------------|
| Quick check | Alarm/Event/Pod TopN/Node TopN/CoreDNS existence check | Root cause, workload detail, ELB/EIP/NAT/ECS inspection, remediation |
| Deep inspection | Alarm/Event/TopN/CoreDNS merge, abnormal objects, object relationship evidence, related ELB/EIP/NAT/ECS monitoring inspection | Final root cause, confidence judgment, recovery strategy, remediation |
| Root cause analyzer | Root cause, evidence chain, confidence, remediation candidates | Direct recovery execution |
| Direct recovery step | Executes RCA R3 candidate actions and authorized R2 candidate actions; advises on R1/R0 candidates | Independent root-cause analysis, R1/R0 execution without user approval |
