# Workflow

This workflow uses CCE `hcloud` commands only for Huawei Cloud cluster access and `kubectl` for Kubernetes workload evidence.

## Evidence Order

1. Confirm `region`, `project_id`, `cluster_id`, `namespace`, `kind`, and `name`.
2. Use `hcloud CCE ListClusters` and `ShowCluster` to confirm the target cluster exists and is available.
3. Use `hcloud CCE CreateKubernetesClusterCert` to create a short-lived kubeconfig.
4. If the returned kubeconfig points to a private API server while `ShowClusterEndpoints.publicEndpoint` is available and the agent is outside the VPC, use a temporary kubeconfig copy whose server is the public endpoint.
5. Verify access with `kubectl --kubeconfig=<file> cluster-info` and `kubectl auth can-i`.
6. When several workloads are failing at once, inspect Nodes and cluster events first to detect a shared scheduling or node readiness blocker.
7. Read the workload YAML and describe output.
8. Record `metadata.uid`, `metadata.generation`, `status.observedGeneration`, selector, desired/current/updated/ready/available replicas, strategy, and conditions.
9. For Deployment, list ReplicaSets with the workload selector and keep only those whose ownerReference points to the Deployment UID.
10. For StatefulSet and DaemonSet, compare the workload status directly and identify selected Pods.
11. List Pods matching the workload selector and capture readiness, restart counts, node placement, container states, and ownerReferences.
12. Collect Events sorted by time, then keep only events related to the workload, owned ReplicaSets, or selected Pods.
13. For not-ready new-version Pods, inspect `describe pod`, current logs, previous logs, PVCs, node conditions, and service/endpoints only as needed.
14. Build the rollout funnel, rank Top3 causes, cite evidence, and recommend handoffs without running mutating commands.

## Rollout Funnel

### Deployment

1. Controller observed generation: `status.observedGeneration >= metadata.generation`.
2. Desired replicas exist: `spec.replicas` is known and not blocked by paused rollout.
3. New ReplicaSet exists: owned RS with highest `deployment.kubernetes.io/revision`.
4. New ReplicaSet scaled: new RS desired replicas align with rollout strategy.
5. New Pods created: selected Pods owned by the new RS exist.
6. New Pods ready: Pod Ready condition is true for enough Pods.
7. Workload available: `status.availableReplicas` reaches expectation and conditions are healthy.

### StatefulSet

1. Controller observed generation.
2. Update strategy and partition allow updates.
3. `status.updatedReplicas` reaches expected replicas.
4. Selected Pods are Running and Ready.
5. `status.readyReplicas` and `availableReplicas` reach expectation.

### DaemonSet

1. Controller observed generation.
2. Desired nodes are schedulable.
3. `updatedNumberScheduled` reaches `desiredNumberScheduled`.
4. `numberReady` and `numberAvailable` reach expectation.
5. No node selector, taint, toleration, or resource pressure evidence blocks placement.

## Failure Rules

### ControlPlaneNotObserved

- Signal: `status.observedGeneration` is lower than `metadata.generation`.
- Evidence: workload generation fields.
- Next checks: control-plane pressure, controller-manager delays, API throttling, and recent cluster events.
- Handoff: `huawei-cloud-cce-root-cause-analyzer`.

### ReplicaSetCreateBlocked

- Signal: Deployment new ReplicaSet is missing, not owned by the Deployment, or has zero Pods despite desired replicas.
- Evidence: Deployment conditions, ReplicaSet YAML/status, `FailedCreate` events.
- Stronger subtype: `QuotaOrAdmissionRejected` when events mention quota, LimitRange, admission, webhook, denied, forbidden, or policy.
- Handoff: `huawei-cloud-cce-auto-remediation-runner` only for approved remediation planning.

### RolloutBlocked

- Signal: updated/current replicas progress but ready/available replicas do not reach expectation.
- Evidence: workload conditions such as `Progressing=False`, `ProgressDeadlineExceeded`, `Available=False`, or stalled status counters.
- Next checks: new-version Pods, Pod conditions, events, logs, and service readiness.
- Handoff: `huawei-cloud-cce-pod-failure-diagnoser`.

### ProbeFailure

- Signal: Pod is Running but not Ready, and events contain `Unhealthy` startup/liveness/readiness probe failures.
- Evidence: Pod Ready/ContainersReady conditions, probe event message, container logs when available, workload probe config.
- Next checks: probe path, port, scheme, initial delay, thresholds, startup time, and dependency reachability.
- Handoff: `huawei-cloud-cce-pod-failure-diagnoser` or `huawei-cloud-cce-network-failure-diagnoser`.

### Pod Runtime Failures

- Signals: `Pending`, `FailedScheduling`, `FailedMount`, `ImagePullBackOff`, `ErrImagePull`, `CrashLoopBackOff`, `OOMKilled`, `Evicted`, frequent restarts, or `ContainersNotReady`.
- Evidence: `describe pod`, events, current logs, previous logs, PVC/PV state, node conditions, and optional `kubectl top`.
- Handoff: pod/node/storage/network skills based on the first concrete blocker.

### Shared Node Or Scheduling Blocker

- Signal: many workloads across namespaces are unavailable, Pods are Pending, and all candidate nodes are `Ready=Unknown`/`NotReady` or have untolerated taints such as `node.kubernetes.io/unreachable` or `node.cloudprovider.kubernetes.io/shutdown`.
- Evidence: `kubectl get nodes`, `describe node`, Pod `FailedScheduling` events, and workload unavailable counts.
- Next checks: whether the cluster was recently awakened, whether ECS worker nodes are still stopped/unreachable, node heartbeat recovery, and CCE node pool status.
- Handoff: `huawei-cloud-cce-node-failure-diagnoser` or remediation runner for explicit node recovery actions.

### ContainerCommandNotFound

- Signal: `CrashLoopBackOff` or container start failure evidence contains executable-not-found, permission denied, or invalid command path.
- Evidence: last termination message, exit code, `BackOff`/start events, workload `command` and `args`.
- Next checks: image tag, entrypoint/CMD, command override, image contents, and release artifact.
- Handoff: `huawei-cloud-cce-pod-failure-diagnoser`.

## Cross-Skill Handoff Mapping

| Diagnosis Direction | Target Skill | Reason |
| --- | --- | --- |
| Pod-level failures | `huawei-cloud-cce-pod-failure-diagnoser` | CrashLoop, ImagePull, OOM, Pending, probe, or log drilldown |
| Node pressure or scheduling | `huawei-cloud-cce-node-failure-diagnoser` | NotReady, DiskPressure, MemoryPressure, taints, capacity, scheduling |
| Service, Ingress, ELB, or dependency reachability | `huawei-cloud-cce-network-failure-diagnoser` | Service endpoints missing, readiness path fails, ingress/service mismatch |
| Storage mount or PVC/PV issues | `huawei-cloud-cce-storage-failure-diagnoser` | FailedMount, FailedAttachVolume, PVC Pending, storage class issues |
| Multi-domain root cause | `huawei-cloud-cce-root-cause-analyzer` | Evidence crosses workload, node, storage, network, and alarms |
| Remediation actions | `huawei-cloud-cce-auto-remediation-runner` | Scale, rollback, patch, delete, cordon, drain, reboot, or quota changes |
| Alarm correlation | `huawei-cloud-cce-alarm-correlation-engine` | AOM alarm correlation, deduplication, and severity grouping |
