# Workflow

## Evidence Order

1. Scope: confirm `region`, `cluster_id`, `namespace`, `kind`, and `name`.
2. Workload snapshot: read `metadata.uid`, `metadata.generation`, `status.observedGeneration`, selector, desired/current/updated/ready/available replicas, strategy, and conditions.
3. Pods: list `v1/Pod` in the namespace with `labelSelector` from `spec.selector.matchLabels`.
4. Deployment only: list `apps/v1/ReplicaSet` with the same selector, then keep RS objects whose ownerReference points to the Deployment UID.
5. Events: list namespace events with `fieldSelector=involvedObject.namespace=<namespace>`, then keep only events whose `involvedObject.uid` is in Workload UID, RS UIDs, or Pod UIDs. Sort newest first.
6. Generation check: if `observedGeneration < generation`, stop at control-plane-not-observed and recommend control plane pressure or throttling checks.
7. Version lock: for Deployment, choose the owned ReplicaSet with highest `deployment.kubernetes.io/revision` as NewRS; for StatefulSet/DaemonSet, use the workload itself and compare `updatedReplicas`.
8. Rollout funnel: compare desired -> current/updated -> NewRS created -> NewRS Pods Ready -> workload available.
9. Pod runtime diagnosis: if NewRS or new-version Pods exist but are not Ready, reuse Pod diagnosis for Pending, ImagePullBackOff, CrashLoopBackOff, OOMKilled, Evicted, and PodNotReady.
10. Output: rank Top3 causes, cite evidence, list handoff skills, and keep remediation as recommendations only.

## Failure Rules

### ControlPlaneNotObserved

- Signal: `status.observedGeneration` is lower than `metadata.generation`.
- Evidence: workload generation fields.
- Next checks: apiserver/controller-manager throttling, cluster component pressure, AOM alarms, recent control plane issues.

### ReplicaSetCreateBlocked

- Signal: Deployment NewRS has desired replicas but zero current replicas, or NewRS has no owned Pods.
- Evidence: NewRS spec/status, RS Warning events.
- Stronger subtype: `QuotaOrAdmissionRejected` when FailedCreate mentions quota, LimitRange, admission, webhook, denied, or forbidden.

### RolloutBlocked / ReplicasUnavailable

- Signal: `updatedReplicas`, `readyReplicas`, or `availableReplicas` are below expected replicas.
- Evidence: workload status and funnel layer that first fails.
- Next checks: abnormal new-version Pods, progress deadline, minReadySeconds, and workload conditions.

### ProbeFailure

- Signal: Pod is Running but not Ready and Events contain `Unhealthy` for startup, liveness, or readiness probe.
- Evidence: Pod Ready/ContainersReady conditions, Unhealthy events, current/previous logs when available.
- Next checks: probe path, port, scheme, initial delay, thresholds, app startup time, and dependency reachability.

### Pod Runtime Failures

- Signals: Pending, FailedScheduling, FailedMount, ImagePullBackOff, CrashLoopBackOff, OOMKilled, Evicted, frequent restarts.
- Evidence: use `pod-failure-diagnoser` output rather than re-implementing runtime logic here.

### ContainerCommandNotFound

- Signal: CrashLoopBackOff/StartError evidence contains `exec: "...": executable file not found in $PATH` or similar command-not-found startup error.
- Evidence: last termination message, exit code, FailedStart/BackOff events.
- Next checks: Deployment `command`/`args`, image ENTRYPOINT/CMD, image tag correctness, and whether the executable exists inside the image.
