# Workflow

This workflow is read-only and uses only `hcloud CCE` plus `kubectl`.

## Evidence Order

1. Scope: confirm `region`, `project_id`, `cluster_id`, `namespace`, and one of `pod_name`, `workload_name`, or `selector`.
2. CLI setup: verify `hcloud`, masked hcloud credentials, `kubectl`, cluster metadata, endpoint reachability, kubeconfig acquisition, and read RBAC.
3. First sweep: list all Pods, non-Running Pods, readiness, restart counts, and nodes before choosing the target Pod.
4. Pod snapshot: read phase/status, reason/message, node, owner references, QoS, conditions, container states, last states, restart counts, image, and resource requests/limits.
5. Events: correlate Pod events by involved object; preserve reason, message, count, source, and last timestamp.
6. Logs: for CrashLoopBackOff, OOMKilled, and frequent restarts, inspect `--previous` logs first, then current logs. ImagePullBackOff normally has no container log.
7. Metrics: for OOMKilled/Evicted/resource suspicion, use `kubectl top` for Pod, container, and node data when metrics-server is available.
8. Related objects: for Pending and mount failures, inspect Nodes, PVCs, PVs, quotas, LimitRanges, and relevant workload selectors.
9. Output: classify failure type, cite evidence, rank Top3 causes, list read-only next checks, and hand off any mutation to `huawei-cloud-cce-auto-remediation-runner`.

## Baseline Commands

```bash
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <kubeconfig-file>

kubectl --kubeconfig=<kubeconfig-file> get pods -A -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector=status.phase!=Running -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,NODE:.spec.nodeName"
kubectl --kubeconfig=<kubeconfig-file> get pod <pod-name> -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> describe pod <pod-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --tail=200
```

## Failure Rules

### CrashLoopBackOff

- Signals: waiting reason `CrashLoopBackOff`, BackOff restarting events, high `restart_count`, terminated last state.
- Evidence: `describe pod`, previous logs, exit code, last termination reason, liveness/startup probe events, ConfigMap/Secret change timing.
- Common causes: application crash, missing config, bad command/args, failed dependency, probe too aggressive, resource shortage during startup.

### ImagePullBackOff / ErrImagePull

- Signals: waiting reason `ImagePullBackOff` or `ErrImagePull`, Events such as `FailedPullImage`, `BackOffPullImage`, failed pull, or back-off pulling image.
- Evidence: image string, imagePullSecrets, Event message, repository/tag/auth/network hints.
- Common causes: wrong image/tag, missing secret, SWR/registry permission, repository deleted, node egress or DNS issue, registry rate limit.
- Important: do not keep requesting container logs when the image was never pulled. Errors like `container is waiting to start: trying and failing to pull image` and `previous terminated container ... not found` are expected supporting evidence.

### OOMKilled

- Signals: last terminated reason `OOMKilled`, exit code `137`, restart after memory pressure.
- Evidence: last state, memory limit/request, `kubectl top pod --containers`, node memory pressure, traffic or batch job timing.
- Common causes: memory limit too low, memory leak, cache growth, sudden traffic, JVM/runtime memory settings inconsistent with container limit.

### Pending

- Signals: phase `Pending`, `PodScheduled=False`, `FailedScheduling`, `FailedMount`, `FailedAttachVolume`, `FailedCreatePodSandBox`.
- Evidence: scheduler Event message, node allocatable resources, taints/tolerations, affinity/nodeSelector, namespace quota, PVC/PV state.
- Common causes: insufficient resources, strict affinity, missing toleration, quota, PVC pending, mount timeout, CNI/sandbox creation issue.

### Evicted

- Signals: Pod reason/message contains `Evicted`, phase `Failed`, eviction Events.
- Evidence: eviction message, node pressure condition, QoS class, requests/limits, ephemeral-storage usage.
- Common causes: MemoryPressure, DiskPressure, ephemeral-storage exhaustion, node NotReady, planned node maintenance.

### Probe Failure

- Signals: Events mention readiness/liveness/startup probe failures, Pod is Running but not Ready.
- Evidence: probe path, port, timeout, period, failureThreshold, container logs, Service endpoints.
- Common causes: app startup slower than probe window, wrong probe path/port, dependency unavailable, TLS/auth mismatch, resource starvation.

### Sandbox Or CNI Failure

- Signals: `FailedCreatePodSandBox`, CNI/IP allocation errors, runtime sandbox errors.
- Evidence: Events, node condition, CNI daemon Pod status, node logs if available through a node-diagnosis handoff.
- Common causes: CNI component issue, IP pool exhaustion, node runtime issue, network plugin misconfiguration.

## Scenario-Specific Report Guidance

After matching a failure rule above, read `scenario-guides.md` for the corresponding scenario. Use it to fill in interpretation, negative evidence, next checks, candidate fixes, and handoff guidance in the final report.
