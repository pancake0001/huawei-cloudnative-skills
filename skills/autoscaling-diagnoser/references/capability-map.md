# CapabilityMap

# # Already reusable

From the current repository:

- `huawei_list_cce_hpas`: Read HPA specifications, current/desired replicas, current metrics, and conditions.
- `huawei_generate_cce_hpa_manifest`, `huawei_configure_cce_hpa`: generate HPA YAML and configuration preview, and reuse them during rectification, but this diagnosis is not executed directly.
- `huawei_list_cce_addons`, `huawei_get_cce_addon_detail`: identify plug-ins such as CCE elastic engine, metrics/AOM/Prometheus and so on.
- `huawei_list_cce_nodepools`: Read node pool, scaling group, autoscaling enable, min/max, and current number of nodes.
- `huawei_get_cce_pods`: Read Pod phase, owner, container state, resources.requests/limits, and annotation keys.
- `huawei_get_cce_deployments`, `huawei_list_cce_statefulsets`: Read target workload desired/current/ready replicas.
- `huawei_get_cce_events`: Read HPA, Pod, Scheduler events, identify FailedScheduling, FailedGetResourceMetric, etc.
- `huawei_get_cce_pod_metrics_topN`, `huawei_get_cce_node_metrics_topN`, `huawei_get_aom_metrics`: Supplement AOM/Prometheus metric evidence.
- The existing `pod-failure-diagnoser`, `workload-failure-diagnoser` and `node-failure-diagnoser` can undertake drill-down.
- `cost-optimization-advisor` and `capacity-trend-forecaster` already have HPA coverage, node pool autoscaling, request/usage, capacity trend analysis, and can reuse governance suggestions.

Transferable experience from external `pancake0001/cce-skills`:

- Safety boundary: AK/SK will not be placed on the market, and dangerous operations must be confirmed twice.
- CCE tool family: cluster, node pool, plug-in, Pod, Deployment, Events, AOM, monitoring, and diagnostic reporting capabilities have covered most of the basic evidence required for autoscaling diagnosis.
- Output habits: List the diagnostic steps first, and then output a complete report; the report needs to contain evidence, conclusions, and suggestions.

# # Capacity added

- `huawei_autoscaling_diagnose`: Added read-only combined diagnostic action.
- Automatically complete Gateway: intent identification, HPA/CA capability discovery, path A/B/C routing.
- Automatically generate Markdown reports: including investigation process, evidence, conclusions, confidence, recommendations and data gaps.
- Identify core root causes: HPA not configured, missing request, missing indicators, threshold not met, maxReplicas, CA not installed/low version, node pool not enabled for scaling, max_nodes, no Pending, insufficient resources Pending, affinity/taint conflicts, subnet IP/quota/permission suspicious signals, shrinkage protection signals.
- **CA Pod log analysis**: Automatically discover the CA component Pod (CCE elastic engine/Cluster Autoscaler) under `kube-system`, pull its standard output log through `huawei_get_pod_logs`, and match key signals according to 16 diagnostic modes (NoExpansionOptions, MaxNodeGroupSize, QuotaExceeded, SubnetIPExhausted, IAM permissions, safe-to-evict protection, node non-removable, etc.), incorporating high-confidence findings into issues and evidence.

# # Still recommended for completed atomic abilities

These capabilities are not required for the first release, but will significantly increase diagnostic confidence:

- `huawei_get_cce_hpa_events`: Accurately read historical events by HPA object to avoid relying only on the current Event window.
- `huawei_get_k8s_api_resources`: Confirm `metrics.k8s.io`, `custom.metrics.k8s.io`, `external.metrics.k8s.io` APIService availability.
- `huawei_get_cce_pdbs`: Read the PodDisruptionBudget, which is used for shrinking and blocking determination.
- `huawei_get_cce_pod_annotations`: Read the complete annotation key/value and confirm that `safe-to-evict=false` is present instead of just the key.
- `huawei_get_cce_resourcequotas`: Distinguish between Namespace ResourceQuota and cluster/cloud resource quota issues.
- `huawei_get_cce_ca_logs`: ~~Read the CCE elastic engine/Cluster Autoscaler log to confirm the reasons such as NoExpansionOptions, MaxNodeGroupSizeReached, QuotaExceeded, SubnetIPExhausted, IAM denied and other reasons. ~~ ✅ **Achieved through `huawei_autoscaling_diagnose` built-in CA Pod discovery + `huawei_get_pod_logs` combination**. The first version of diagnostics already covers 16 key signals in CA logs. In the future, you can consider encapsulating it into an independent atomic tool to support more flexible log queries (such as specified time range, LTS integration, debug level logs).
- `huawei_get_ecs_quotas` or unified cloud resource quota query: Confirm whether ECS, EVS, EIP and other quotas block expansion nodes.
- `huawei_get_vpc_subnet_ip_usage`: Confirm the remaining IPs of the node pool subnet.
- `huawei_get_cce_agency_status`: Confirm whether CCE delegation/IAM permissions have been deleted or narrowed.
- `huawei_get_workload_selector_context`: Read workload selector and Pod template labels to accurately determine selector mismatch.