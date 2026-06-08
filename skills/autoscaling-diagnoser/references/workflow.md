# Workflow

# # 1. Gateway Phase

Do dual routing first, don't go directly into HPA or CA details.

Semantic intent:

- Hit Pod, Workload, Deployment, StatefulSet, Replica, Instance: `Target=WORKLOAD`.
- Hit Node, node, ECS, virtual machine, server, host: `Target=NODE`.
- "Why is it not automatically expanded?" and other vague descriptions: `Target=UNKNOWN`.

Ability discovery:

- `Has_HPA`: `huawei_list_cce_hpas` returns the total number of HPAs or target range matching HPAs.
- `Has_CA`: `huawei_list_cce_addons` identifies the CCE elastic engine/Cluster Autoscaler, or there is a node pool with autoscaling enabled in `huawei_list_cce_nodepools`.

Routing matrix:

| Target | Has_HPA / Has_CA | Path |
| --- | --- | --- |
| WORKLOAD | Any | A: Workload Resiliency Diagnostics |
| NODE | Any | B: Node Resilience Diagnosis |
| UNKNOWN | True/False | A: Workload resiliency diagnostics |
| UNKNOWN | False / True | B: Node Resilience Diagnosis |
| UNKNOWN | True / True | C: Two-level cascade diagnosis |
| Any | False / False | Blocking: Automatic resiliency not configured |

# # 2. Path A: Pod layer HPA closed loop

Objective: Explain why the number of replicas does not increase from N to N+1.

Check order:

1. Whether HPA exists and scaleTargetRef points to the correct Deployment/StatefulSet.
2. HPA status: `currentReplicas`, `desiredReplicas`, `minReplicas`, `maxReplicas`, conditions.
3. HPA Events: `FailedGetResourceMetric`, `FailedComputeMetricsReplicas`, `FailedGetScale`, `Selector`, `missing request`.
4. Indicator conditions: Whether the current CPU/memory or custom indicators exceed the target threshold; if the ratio falls within the HPA tolerance, mark it as "condition not met".
5. Resource requests: CPU/Memory utilization HPA must check whether the target Pod container has corresponding `resources.requests`.
6. Metric components: metrics-server, AOM, Prometheus or whether the custom/external metrics link is visible.
7. Upper limit and cooling: `maxReplicas`, `ScalingLimited`, behavior/stabilization/cooldown related events.

Typical root causes:

- The HPA is not configured or the HPA does not match the target workload.
- Missing CPU/Memory request, HPA cannot calculate utilization.
- Missing metrics or broken metrics/AOM/Prometheus flow.
- The current indicator does not exceed the threshold, or is within the default tolerance of about 10%.
- Reach `maxReplicas`.
- mismatch in scaleTargetRef, selector or labels.

# # 3. Path B: Node layer CA closed loop

Goal: Explain why the number of nodes does not increase from M to M+1, or why scaling is blocked by the protection policy.

**Pre-priority step: Analyze CA component Pod logs. **

The CA component (CCE Cluster Autoscaler) runs in the `kube-system` namespace as a Pod. Its standard output log is the most direct and most confident source of evidence to determine node scaling issues. Prioritize pulling the CA Pod log before troubleshooting:

- Use `huawei_get_cce_pods` to locate Pods under `kube-system` whose names contain `autoscaler`/`cce-elastic`/`elastic-engine`.
- Use `huawei_get_pod_logs` (`tail_lines=200`) to pull the Pod log.
- Retrieve key signals in the log (the `huawei_autoscaling_diagnose` main tool has automatically performed this step).

**CA log key signal quick check:**

| Signal | Meaning | Severity level |
| --- | --- | --- |
| `No expansion options` | CA has no expansion options available, usually because the node pool specification/AZ/subnet does not meet the needs of the Pods to be scheduled | critical |
| `max node group size reached` | The node group has reached the max_nodes upper limit | critical |
| `Scale-up: final scale-up plan is empty` | The final scale-up plan is empty and all node groups are skipped | critical |
| `Quota exceeded` / `quota limit` | Cloud resource (ECS/EVS/EIP) quota is insufficient | critical |
| `subnet ip exhausted` / `no available ip` | VPC subnet available IP exhausted | critical |
| `iam` / `permission denied` / `agency` / `forbidden` | IAM delegation or permission exception | critical |
| `Failed to refresh` / `cannot connect` | CA cannot connect to cloud API or control plane | high |
| `skipping node group` | CA skips a node group and the reason will be noted in the log | high |
| `pod ... is unschedulable` | CA has identified an unschedulable Pod | info |
| `ScaleDown: no candidates` | No node candidates for scaling | info |
| `node ... is not suitable for removal` | The node does not meet the shrinkage conditions | high |
| `not safe to evict` / `safe-to-evict=false` | PDB or annotation protection to prevent eviction | high |

Expansion check sequence:

1. **Check CA Pod logs first**: The main tool `huawei_autoscaling_diagnose` has automatically pulled and analyzed. Prioritize this step when manually checking for details - CA logs often directly expose the root cause.
2. Whether the CCE cluster elastic engine/Cluster Autoscaler is installed and whether the version is lower than 1.13.8.
3. Whether autoscaling is enabled in the node pool/scaling group and whether min/max is configured.
4. Whether there is a Pending Pod, especially `FailedScheduling` and containing `Insufficient cpu/memory/pods/ephemeral-storage`.
5. Whether the node pool reaches `max_nodes`.
6. Is Pending caused by affinity, anti-affinity, nodeSelector, taint/tolerance mismatch? This situation may not be solved by simply adding nodes.
7. Cloud resource signals: Insufficient VPC subnet IPs, insufficient ECS/EVS/EIP quotas, and abnormal IAM delegation permissions (CA logs usually contain clear error messages).

Shrinking check sequence:

1. **Check the CA Pod log first**: Downsizing signals such as `not suitable for removal`, `not safe to evict`, and `no candidates` are clearly recorded in the CA log.
2. Whether node requests are lower than the shrinkage threshold and continue to meet the cooling window.
3. Whether PodDisruptionBudget does not allow eviction.
4. Whether the Pod sets `cluster-autoscaler.kubernetes.io/safe-to-evict=false`.
5. Whether there are kube-system non-DaemonSet Pods or non-controller management Pods on the node.

# # 4. Path C: two-level cascade

Traceability in chronological order:

1. Run path A first to determine whether HPA has increased the target replica or made the workload desired replicas larger than ready replicas.
2. If the HPA is not expanded, the conclusion converges to the Pod layer blocking, and the problem is no longer attributed to the node.
3. If HPA has been expanded and Pod Pending has been added, use these Pending Pods as the input of path B to check why CA has no supplementary nodes (**includes CA Pod log analysis**).
4. If it cannot be proven that the HPA has been expanded and there is no Pending Pod, the report is "insufficient linkage evidence" and the historical HPA Event, Deployment revision or indicator timeline that needs to be supplemented are listed.
5. In the cascading scenario, the CA Pod logs also include scheduling attempt records and cloud API call errors on the CA side, which can be used as key supplementary evidence for HPA→CA linkage.

# # 5. Manual tool sequence

When `huawei_autoscaling_diagnose` is unavailable or fails:1. `huawei_list_cce_hpas`
2. `huawei_list_cce_addons`
3. `huawei_list_cce_nodepools`
4. `huawei_get_cce_deployments` / `huawei_list_cce_statefulsets`
5. `huawei_get_cce_pods` (**Additionally pull `namespace=kube-system` to locate the CA component Pod**)
6. **`huawei_get_pod_logs`**: Locate the Pod whose name contains `autoscaler`/`cce-elastic`/`elastic-engine` under `kube-system` and pull its log (`tail_lines=200`). Look for `NoExpansionOptions`, `QuotaExceeded`, `subnet`, `permission denied`, `skipping node group`, `max node group size`, `scale up plan empty`, `not suitable for removal`, `safe-to-evict` and other signals in the log - this step is often the most critical step to confirm the root cause of the CA side.
7. `huawei_get_cce_events`
8. `huawei_get_cce_pod_metrics_topN` / `huawei_get_cce_node_metrics_topN`
9. If necessary, use `huawei_get_aom_metrics` to query custom PromQL.