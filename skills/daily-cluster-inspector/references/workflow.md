# Workflow

1. By default, the quick test is run first, and when normal, the heartbeat summary is output directly.
2. Run in-depth diagnosis or parallel inspection when the quick inspection is abnormal.
3. Classify and summarize issues by Pod, Node, Event, AOM, ELB, and Resource.
4. AI performs severity grading based on inspection evidence, and the grading results are written into the inspection summary and are not solidified into the tool code or tool output field.
5. For abnormal findings, build a root-cause handoff package for `root-cause-analyzer`: region, cluster_id, namespace, target object, time window, symptoms, evidence, severity, impact scope, and data gaps.
6. Use `root-cause-analyzer` to analyze root cause before selecting remediation actions. The inspector should not infer a final root cause from inspection evidence alone when deeper diagnosis is needed.
7. Read-only output report, no automatic repair.
8. Provide a confirmation list for forwarding root-cause-backed remediation candidates to `auto-remediation-runner` for items that require action.

# # AI severity level judgment caliber

When AI generates an inspection summary, it can mark abnormal items according to P0-P5, but the judgment must be based on the factual evidence returned by the tool, and it must not supplement the status not collected by the tool out of thin air.

- P0: Cluster-level serious failure. The control plane is unavailable, all nodes are NotReady, core system components are unavailable in large areas, or the entire business is interrupted and no detour path is available.
- P1: Key services are unavailable. The available replicas of the core Deployment/StatefulSet are 0, key entrances are unavailable, and multiple key Pods cannot be started, which has directly affected business continuity.
- P2: Root cause of persistent failure. Problems such as image pull failure, CrashLoopBackOff, scheduling failure, PVC mounting failure, node NotReady, etc. persist and affect the recovery of some workloads.
- P3: Resource and capacity risks. The usage of CPU, memory, disk, network, ELB layer 4/layer 7, etc. exceeds the threshold, or a sudden alarm occurs, but it has not been confirmed that the service is unavailable.
- P4: Historical repeated alarms and items of concern. Recovered alarms, repeated alarms, normal alarms, and low-impact anomalies are suitable for subsequent observation, noise reduction, or rule optimization.
- P5: Health items. Inspect and confirm normal clusters, nodes, workloads, ELB or alarm check items.

Prioritize instructions when grading:

- Scope of influence: cluster level, namespace level, workload level, single Pod/single node.
- Current status: active alarm or recovered, replica is available, node is Ready.
- First appearance and persistence: sudden, persistent, regular recurrence.
- Root cause evidence: Pod status, events, AOM alarms, indicator peaks, ELB usage, node conditions, etc.
- Next step suggestions: root-cause analysis handoff, read-only troubleshooting suggestions, or transfer actions that require user confirmation after root-cause analysis.
