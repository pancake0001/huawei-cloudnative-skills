# Workflow

1. Default: run quick check first; if healthy, output heartbeat summary directly.
2. If quick check finds anomalies, escalate to deep diagnosis or parallel inspection.
3. Classify and summarize issues by domain: Pod, Node, Event, AOM, ELB, Resource.
4. Label each risk as P0/P1/P2 with recommended responsible owner.
5. For abnormal findings, build a root-cause handoff package for `huawei-cloud-cce-root-cause-analyzer`: region, cluster_id, namespace, target object, time window, symptoms, evidence, severity, impact scope, and data gaps.
6. Use `huawei-cloud-cce-root-cause-analyzer` to analyze root cause before selecting remediation actions. The inspector should not infer a final root cause from inspection evidence alone when deeper diagnosis is needed.
7. Output read-only report — no automatic remediation.
8. For actionable items, provide a root-cause-backed handoff checklist to `huawei-cloud-cce-auto-remediation-runner` for confirmed execution.
