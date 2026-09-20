# Capability Map

## Reusable Capabilities

From the current repository:

- Internal HPA collector: Read HPA spec, current/desired replicas, current metrics, and conditions.
- Internal CCE collectors: Identify CCE elastic engine, metrics/AOM/Prometheus addons; read node-pool scaling groups, Pod resource state, workload replica state, and scoped HPA/Pod/Scheduler Events.
- Internal AOM collectors: Supplement Pod and node metric evidence.
- `huawei-cloud-cce-pod-failure-diagnoser`, `huawei-cloud-cce-workload-failure-diagnoser`, `huawei-cloud-cce-node-failure-diagnoser` can handle deep-dive escalation.
- `huawei-cloud-cce-cost-optimization-advisor` and `huawei-cloud-cce-capacity-trend-forecaster` already cover HPA coverage, node pool autoscaling, request/usage, and capacity trend analysis; their governance recommendations are reusable.

Transferable experience from external `pancake0001/cce-skills`:

- Security boundary: AK/SK must not be written to disk; dangerous operations must require secondary confirmation.
- CCE tool family: cluster, node pool, addon, Pod, Deployment, Events, AOM, monitoring, and diagnosis report capabilities already cover most of the base evidence needed for autoscaling diagnosis.
- Output convention: list diagnosis steps first, then output the complete report; reports must include evidence, conclusions, and recommendations.

## Supplemented Capabilities

- `huawei_diagnose_cce_hpa_autoscaling` and `huawei_diagnose_cce_cluster_autoscaler`: Read-only HPA and Cluster Autoscaler diagnosis actions.
- Automated Gateway: intent recognition, HPA/CA capability discovery, Path A/B/C routing.
- Automated Markdown report generation: includes investigation process, evidence, conclusion, confidence, recommendations, and data gaps.
- Core root cause identification: HPA not configured, missing request, metric missing, threshold not met, maxReplicas, CA not installed/outdated version, node pool autoscaling not enabled, max_nodes, no Pending, resource-insufficient Pending, affinity/taint conflict, subnet IP/quota/permission suspicious signals, scale-down protection signals.
- **CA Pod log analysis**: Automatically discover CA component Pods in `kube-system` (CCE elastic engine/Cluster Autoscaler), retrieve their standard-output logs through the internal scoped collector, match key signals against 16 diagnostic patterns (NoExpansionOptions, MaxNodeGroupSize, QuotaExceeded, SubnetIPExhausted, IAM permission, safe-to-evict protection, node not removable, etc.), and merge high-confidence findings into issues and evidence.

## Recommended Atomic Capabilities to Add

These are not required for the first release but would significantly improve diagnosis confidence:

- `huawei_get_cce_hpa_events`: Read historical events per HPA object precisely, avoiding reliance on the current Event window only.
- `huawei_get_k8s_api_resources`: Confirm `metrics.k8s.io`, `custom.metrics.k8s.io`, `external.metrics.k8s.io` APIService availability.
- `huawei_get_cce_pdbs`: Read PodDisruptionBudget for scale-down blocking determination.
- `huawei_get_cce_pod_annotations`: Read full annotation key/value pairs; confirm `safe-to-evict=false` value rather than only key existence.
- `huawei_get_cce_resourcequotas`: Distinguish Namespace ResourceQuota from cluster/cloud resource quota issues.
- `huawei_get_cce_ca_logs`: ~~Read CCE elastic engine/Cluster Autoscaler logs to confirm NoExpansionOptions, MaxNodeGroupSizeReached, QuotaExceeded, SubnetIPExhausted, IAM denied reasons.~~ Implemented within `huawei_diagnose_cce_cluster_autoscaler` through CA Pod discovery and the internal scoped log collector. A future iteration may expose a separate log query only when a standalone use case is established.
- `huawei_get_ecs_quotas` or unified cloud resource quota query: Confirm whether ECS, EVS, EIP quotas are blocking node expansion.
- `huawei_get_vpc_subnet_ip_usage`: Confirm remaining IPs in node pool subnets.
- `huawei_get_cce_agency_status`: Confirm whether CCE agency/IAM permissions have been deleted or narrowed.
- `huawei_get_workload_selector_context`: Read workload selector and Pod template labels to precisely detect selector mismatches.
