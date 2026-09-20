# Workflow

## 1. Gateway Phase

Perform dual routing first; do not directly enter HPA or CA details.

Semantic intent:

- Matches Pod, workload, Deployment, StatefulSet, replica, instance: `Target=WORKLOAD`.
- Matches Node, node, ECS, virtual machine, server, host: `Target=NODE`.
- Ambiguous descriptions such as "Why isn't autoscaling working": `Target=UNKNOWN`.

Capability discovery:

- `Has_HPA`: the internal HPA collector returns HPA total count or target-scope-matched HPA.
- `Has_CA`: internal CCE add-on and node-pool collectors identify CCE elastic engine/Cluster Autoscaler and node-pool autoscaling.

Routing matrix:

| Target | Has_HPA / Has_CA | Route |
| --- | --- | --- |
| WORKLOAD | Any | A: Workload autoscaling diagnosis |
| NODE | Any | B: Node autoscaling diagnosis |
| UNKNOWN | True / False | A: Workload autoscaling diagnosis |
| UNKNOWN | False / True | B: Node autoscaling diagnosis |
| UNKNOWN | True / True | C: Dual-layer cascade diagnosis |
| Any | False / False | BLOCKED: No autoscaling capability configured |

## 2. Path A: Pod-Layer HPA Closed Loop

Goal: Explain why replica count did not increase from N to N+1.

Check sequence:

1. Does HPA exist and does its scaleTargetRef point to the correct Deployment/StatefulSet?
   When `hpa_name` or `workload_name` is supplied, read the named HPA and target workload directly, then use the workload selector for Pod reads.
2. HPA status: `currentReplicas`, `desiredReplicas`, `minReplicas`, `maxReplicas`, conditions.
3. HPA Events: correlate Events on the HPA, scale target, and target Pods; inspect `FailedGetResourceMetric`, `FailedComputeMetricsReplicas`, `FailedGetScale`, `Selector`, and `missing request`.
4. Metric condition: parse Resource, Pods, Object, and External metrics. Compare current and target values when they are numerically comparable; if the ratio falls within HPA tolerance, flag as "condition not met".
5. Resource requests: CPU/Memory utilization-type HPA must check whether target Pod containers have corresponding `resources.requests`.
6. Metric components: verify the required `metrics.k8s.io`, `custom.metrics.k8s.io`, or `external.metrics.k8s.io` APIService and check metrics-server/AOM/Prometheus add-on visibility.
7. Upper limit and behavior: `maxReplicas`, `ScalingLimited`, disabled scale directions, stabilization windows, and behavior/stabilization/cooldown-related Events.

Typical root causes:

- HPA not configured or HPA not matching the target workload.
- Missing CPU/Memory request; HPA cannot calculate utilization.
- Metric missing or metrics/AOM/Prometheus pipeline broken.
- Current metric below threshold, or within default ~10% tolerance.
- `maxReplicas` reached.
- scaleTargetRef, selector, or labels mismatch.

## 3. Path B: Node-Layer CA Closed Loop

Goal: Explain why node count did not increase from M to M+1, or why scale-down was blocked by protection policies.

**Priority prerequisite step: Analyze CA component Pod logs.**

CA components (CCE cluster elastic engine/Cluster Autoscaler) run as Pods in the `kube-system` namespace. Their standard output logs are the **most direct, highest-confidence** evidence source for node scaling issues. Prioritize retrieving CA Pod logs before investigation:

- Locate Pods in `kube-system` with names containing `autoscaler`/`cce-elastic`/`elastic-engine`.
- Retrieve their standard-output logs with `tail_lines=200`.
- The Cluster Autoscaler diagnosis tool executes this log-analysis step automatically.

**CA Log Key Signal Quick Reference:**

| Signal | Meaning | Severity |
| --- | --- | --- |
| `No expansion options` | CA has no available expansion options, usually because node pool specs/AZ/subnet do not meet the schedulable Pod requirements | critical |
| `max node group size reached` | Node group has reached max_nodes limit | critical |
| `Scale-up: final scale-up plan is empty` | Final expansion plan is empty; all node groups were skipped | critical |
| `Quota exceeded` / `quota limit` | Cloud resource (ECS/EVS/EIP) quota insufficient | critical |
| `subnet ip exhausted` / `no available ip` | VPC subnet available IP exhausted | critical |
| `iam` / `permission denied` / `agency` / `forbidden` | IAM agency or permission abnormality | critical |
| `Failed to refresh` / `cannot connect` | CA cannot connect to cloud API or control plane | high |
| `skipping node group` | CA skipped a node group; the log will state the reason | high |
| `pod ... is unschedulable` | CA identified an unschedulable Pod | info |
| `ScaleDown: no candidates` | No candidate nodes for scale-down | info |
| `node ... is not suitable for removal` | Node does not meet scale-down conditions | high |
| `not safe to evict` / `safe-to-evict=false` | PDB or annotation protection blocking eviction | high |

Scale-up check sequence:

1. **Prioritize CA Pod log review**: `huawei_diagnose_cce_cluster_autoscaler` automatically retrieves and analyzes them. CA logs often directly expose the root cause.
2. Is CCE cluster elastic engine/Cluster Autoscaler installed, and is the version below 1.13.8?
3. Are node pools/scaling groups autoscaling-enabled with min/max configured, and has any pool already reached its maximum?
4. Do Pending Pods exist, especially `FailedScheduling` with `Insufficient cpu/memory/pods/ephemeral-storage`?
5. Has the node pool reached `max_nodes`?
6. Is Pending caused by affinity, anti-affinity, nodeSelector, or taint/toleration mismatch? This may not be solvable by simply adding nodes.
7. Cloud resource signals: VPC subnet IP exhaustion, ECS/EVS/EIP quota insufficient, IAM agency permission abnormality (CA logs usually contain explicit error messages).

Scale-down check sequence:

1. **Prioritize CA Pod log review**: Scale-down signals such as `not suitable for removal`, `not safe to evict`, `no candidates` are explicitly recorded in CA logs.
2. Are node requests below the scale-down threshold and continuously meeting the cooldown window?
3. Does a PodDisruptionBudget with `disruptionsAllowed=0` select the affected Pods?
4. Do Pods have `cluster-autoscaler.kubernetes.io/safe-to-evict=false` annotation?
5. Are there kube-system non-DaemonSet Pods or non-controller-managed Pods on the node?

## 4. Path C: Dual-Layer Cascade

Trace chronologically:

1. Run Path A first; determine whether HPA has increased target replicas or made workload desired replicas greater than ready replicas.
2. If HPA did not scale up, converge the conclusion to Pod-layer blocking; do not continue attributing the issue to nodes.
3. If HPA has scaled up and new Pods are Pending, treat those Pending Pods as input for Path B and check why CA did not add nodes (**including CA Pod log analysis**).
4. If HPA scaling cannot be proven and there are no Pending Pods, report as "insufficient cascade evidence" and list the historical HPA Events, Deployment revisions, or metric timelines that need to be collected.
5. In cascade scenarios, CA Pod logs simultaneously contain CA-side scheduling attempt records and cloud API call errors, which can serve as key supplementary evidence for the HPA→CA linkage.

## 5. Evidence Collection Boundary

The composite diagnosis owns its evidence collection. It gathers scoped HPA, add-on, node-pool, workload, Pod, Event, autoscaler-log, and AOM metric data internally; these collectors are not standalone public actions. Cluster Autoscaler scale-up first verifies `kube_pod_status_phase` is present in AOM Prometheus, then queries Pending Pods and `cluster_autoscaler_unschedulable_pods_count`. If the Pod-phase metric is unavailable, it falls back to a server-side `status.phase=Pending` Pod query. Events are filtered to Warning; PDB and non-Pending Pod reads occur only when scale-down checks are required. If collection fails, return the affected `data_gaps` and use the appropriate specialized CCE skill for deeper follow-up.
