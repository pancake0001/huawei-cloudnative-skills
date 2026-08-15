# Workflow

1. Confirm scope: region, project_id, cluster_id, namespace, target object, user-visible symptom, fault_time, and analysis window.
2. Build or reuse an observability context package with `huawei-cloud-cce-observability-context-builder`: alarms, Events, logs, metrics, topology hints,
   timeline, and data gaps.
3. Read `references/kubectl-cce.md`, verify `hcloud`, `kubectl`, and `kubectl-cce`, and resolve the target cluster with `hcloud CCE ListClusters` /
   `ShowCluster`.
4. Collect current Kubernetes evidence with `kubectl cce`: Pods, workloads, ReplicaSets, Services, Ingresses, Endpoints/EndpointSlices, Nodes, Events,
   PVC/PV/StorageClass, and NetworkPolicies when relevant.
5. Build the timeline: user symptom, alarm, Event, rollout/change, metric/log, and recovery attempt.
6. Route evidence to dependent skills:
   - workload/pod signals -> workload and pod diagnosers;
   - node signals -> node diagnoser;
   - service/DNS/ingress/network signals -> network diagnoser;
   - PVC/PV/CSI signals -> storage diagnoser;
   - topology/blast-radius questions -> dependency-impact analyzer;
   - recent change signals -> change-impact analyzer;
   - alarm/event/metric gaps -> alarm, event, and metric analyzers.
7. Normalize each domain finding into a root cause candidate with domain, title, supporting evidence, counter-evidence, data gaps, affected scope, confidence,
   and next verification.
8. Rank Top3 causes by timeline alignment, directness of evidence, known failure signature, blast radius, counter-evidence, and recoverability.
9. Put Summary, Root Cause Analysis, and Next Actions at the top of the report. Move command details and raw evidence to later sections.
10. Hand remediation to `huawei-cloud-cce-auto-remediation-runner` only as recommendation or preview request; this skill does not mutate resources.
