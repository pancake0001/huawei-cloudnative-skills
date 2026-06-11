# Workflow

1. Prefer calling `huawei_root_cause_analyze`.
2. Start RCA only when at least one resource has abnormal object evidence, repeated Events/alarms, user-visible impact, abnormal metric windows, or a recent change correlated with the failure window.
3. If `abnormal_object_analysis` is present, use it only as scope hints: suspected objects, symptoms, first_seen/last_seen, and object relationships. Do not rank root causes from inspector output alone.
4. Classify the affected resources before drill-down:
   - Pod/Workload: runtime, image, rollout, probe, quota/admission, resource pressure.
   - Node: NotReady, pressure, taints, scheduling failures, many affected Pods on one node.
   - Service/Ingress: selector/backend mismatch, no ready backends, ingress rule/TLS/backend failure.
   - ELB/EIP/NAT: backend health, connection, bandwidth, EIP/NAT state, peripheral relation from Service/Ingress.
   - AOM Alarm: Critical/Major or repeated alarm groups correlated with objects, Events, or metric windows.
   - Change: deployment/config/image/HPA/network/security/nodepool/addon changes before failure.
5. Collect RCA-owned runtime evidence: Kubernetes Events, Pod status, Node status/conditions, Pod TopN metrics, Node TopN metrics, and relevant logs/metrics when enabled.
6. Establish the fault timeline from RCA-collected Event times, alarm trigger time, deployment/configuration change time, monitoring windows, and user-perceived time. Inspector timestamps may only seed the query window.
7. Supplement the scope hints with rollout, dependency, change, network, node/pod, and AOM alarm diagnoser actions.
8. Workload drill-down must decide whether the issue is change-induced, traffic/resource saturation, runtime/probe/image/config, or node-related: generation/observedGeneration, ReplicaSet, Pod Ready, Events, Logs, command/args, probes, image, Pod metrics, recent changes, and Pod node distribution.
9. Node drill-down must decide whether the issue is node resource pressure, system/runtime/kubelet issue, scheduling constraints, or underlying ECS/network/storage: conditions, taints, allocatable/capacity, Node TopN metrics, affected Pods, node Events, and ECS/peripheral context when available.
10. For resource-usage incidents:
    - Pod high + Node normal + no rollout/Event/alarm/dependency abnormality => conclude application performance bottleneck, traffic/resource saturation, or Pod quota too small.
    - Node metrics over threshold or abnormal Node conditions => conclude node capacity/system bottleneck.
    - Healthy rollout is counter-evidence only and must not be ranked above a verified resource bottleneck.
11. For dependency impact scope, use Service selector, Ingress backend, Pod Ready, Node distribution, ELB/EIP relationships, and peripheral status to determine propagation paths.
12. For change impact scope, use audit logs, K8s historical events, AOM alarms, current topology, and RCA runtime evidence to verify the "change occurred before failure" causal chain.
13. For each root cause candidate, record supporting RCA-collected evidence, counter-evidence, data gaps, and structured `remediation_candidates` for `huawei-cloud-cce-auto-remediation-runner`.
    Dependency propagation and alarm correlation are supporting findings only; they must not be ranked as Top root causes unless another diagnoser proves them as the direct fault origin.
14. Sort by impact scope, timeline alignment, evidence strength, and recoverability.
15. Output Top3 root causes, supporting findings, verification steps, impact scope, remediation recommendations, and machine-readable remediation candidates.
16. Clearly label low-confidence conclusions with required supplementary data.

Do not start RCA for healthy heartbeat, isolated informational alarms, one-time low-impact metric spikes, inventory/status-only requests, or recovery execution requests that do not include root-cause evidence.

## Remediation Candidate Mapping

| Root cause type | Preferred candidate | Follow-up candidates | Notes |
| --- | --- | --- | --- |
| `ApplicationPerformanceOrQuotaBottleneck` | `scale_workload_out` / `huawei_scale_cce_workload` | `configure_hpa`, `resize_workload` | Scale out first to reduce immediate pressure; configure HPA to keep elasticity. Scale/HPA are R2 only when they do not add cloud-resource cost; resize is R1 fallback when limits/requests are too small. |
| `DnsPerformanceBottleneck` | `scale_coredns_out` / `huawei_scale_cce_workload` | CoreDNS metric verification | Scale `Deployment/kube-system/coredns` replicas first when CoreDNS CPU is high or P99 DNS latency exceeds 100ms; this is R2 only when current CoreDNS Pod count is known and it does not add cloud-resource cost, otherwise R1 preview. |
| `NodeCapacityOrSystemBottleneck` | `cordon_node` / `huawei_cce_node_cordon` | `drain_node_after_cordon`, node pool scale-out preview | Cordon isolates the affected node from new scheduling and is R2; drain is R1 because it evicts existing Pods. |
| `NodeConditionAbnormal` | `cordon_node` when node is concrete | node repair/observation preview | If no concrete node is identified, require manual node selection. |
| `SchedulingOrNodeConstraint` | node pool scale-out or scheduling adjustment preview | workload request/affinity/taint review | Do not cordon a node unless RCA proves a concrete abnormal node. |
| `ImagePullBlocked` | R3 image and pull-secret verification | `rollback_previous_revision` | Do not invent credentials; rollback is R1 when a bad new revision is unavailable. |
| rollout/startup failures | `rollback_previous_revision` | image/probe/config fix preview | Applies to command missing, CrashLoop, probe failure, bad image, or rollout timeout with a previous stable revision. |
