# Scenario Guides

Use this file after the top cause is identified. The main skill report format stays generic; this reference provides scenario-specific interpretation, next checks, and candidate fix paths.

For every diagnosed scenario, include these report parts:

- **Interpretation**: what the signal means in plain language.
- **Likely subtype**: the concrete failure class, if evidence supports one.
- **Ruled-out causes**: adjacent causes that are less likely and why.
- **Next checks**: specific checks that confirm or refute the hypothesis.
- **Candidate fix paths**: safe remediation options, without executing them.
- **Handoff**: the next skill or owner when the fix is outside this read-only diagnoser.

## ImagePullBackOff / ErrImagePull

Signals:

- Container waiting reason is `ImagePullBackOff` or `ErrImagePull`.
- Events include `FailedPullImage`, `BackOffPullImage`, failed pull, unauthorized, denied, not found, timeout, DNS, mirror, or manifest errors.

Interpretation:

- The Pod has been scheduled, but the container image cannot be pulled, so the container never starts.
- Short image names are resolved by the runtime. For example, `azxsdc:latest` is normally treated as `docker.io/library/azxsdc:latest`.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| `not found`, `manifest unknown`, `repository does not exist`, 404 | Repository or tag missing |
| `unauthorized`, `authentication required`, `denied`, 401/403 | Registry auth or pull secret |
| `no such host`, DNS timeout, connection timeout | DNS or network path |
| 429 or rate-limit text | Registry rate limit |
| mirror/proxy URL plus 400/5xx | Mirror or proxy behavior, often triggered by invalid image path/tag |

Ruled-out examples:

- Scheduling is unlikely when `PodScheduled=True` and `nodeName` is set.
- OOM and probes are unlikely when the container never started.
- Logs are not expected; current or previous log errors can confirm the container was never created.

Next checks:

- Confirm the intended registry, namespace, repository, and tag.
- Check whether the image should be fully qualified, such as `swr.<region>.myhuaweicloud.com/<namespace>/<repo>:<tag>` or `docker.io/<org>/<repo>:<tag>`.
- Confirm `imagePullSecrets` exists and applies to the target namespace for private images.
- Inspect the owner Deployment/StatefulSet/DaemonSet image field and release pipeline template.

Candidate fix paths:

- Replace the image with a full valid image reference and redeploy through the normal workload release workflow.
- Fix or recreate the image pull secret if the Event points to auth.
- Fix node egress/DNS or registry mirror configuration if the Event points to network/mirror issues.

Handoff:

- Workload/release owner for image field changes.
- SWR/image-management skill for private SWR repository, tag, or pull-secret checks.
- Network skill if DNS or registry connectivity is the main signal.

## CrashLoopBackOff / App Exit

Signals:

- Container waiting reason is `CrashLoopBackOff`.
- Restart count increases.
- Last state is terminated with non-zero exit code, `Error`, or application-specific reason.
- Events show back-off restarting failed container.

Interpretation:

- The image was pulled and the container started, but the process repeatedly exits or is killed.
- Previous logs and termination state are usually more valuable than current logs.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| Exit code 1/2 and stack trace | Application startup error |
| `exec format error` | Wrong CPU architecture image |
| `executable file not found`, permission denied | Bad command/args or file permissions |
| Dependency connection refused/timeouts | Downstream dependency unavailable |
| Probe events before restarts | Probe-induced restart or startup too slow |

Ruled-out examples:

- Image pull is unlikely if image ID exists and previous logs are available.
- Scheduling is unlikely if the Pod repeatedly starts on a node.

Next checks:

- Read `--previous` logs first, then current logs.
- Capture exit code, reason, start/finish time, command, args, env, ConfigMap/Secret mounts, and recent rollout/config changes.
- Check whether restart timing aligns with liveness/startup probe failures.

Candidate fix paths:

- Fix application config, command, args, dependency endpoint, or image architecture.
- Adjust startup/liveness probe thresholds if direct evidence shows the app needs more startup time.
- Redeploy through normal workload workflow.

Handoff:

- Workload owner for app/config/image changes.
- Network/root-cause skill if dependency failures span services.

## OOMKilled

Signals:

- Last terminated reason is `OOMKilled`.
- Exit code is `137`.
- Events or container state indicate memory kill.

Interpretation:

- The container exceeded its memory cgroup limit, or node memory pressure contributed to termination.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| Limit is low and app uses near limit | Container memory limit too low |
| Memory grows over time | Memory leak or unbounded cache |
| JVM or runtime max heap exceeds limit | Runtime memory setting mismatch |
| Node MemoryPressure | Node-level memory pressure |

Ruled-out examples:

- Image pull is ruled out if the container started and terminated.
- Scheduling is less likely if the Pod is running/restarting on a node.

Next checks:

- Compare memory requests/limits with app/runtime settings.
- Use `kubectl top pod --containers` and `kubectl top node` when metrics-server is available.
- Check previous logs around termination and recent traffic/batch events.
- Inspect node `MemoryPressure`.

Candidate fix paths:

- Tune app memory, cache, JVM/runtime settings, or workload memory limits through the remediation workflow.
- Investigate memory leak if usage grows over time.
- Hand off node pressure to node diagnosis.

Handoff:

- Auto-remediation runner for limit changes after confirmation.
- Node diagnoser for node pressure.

## Pending / FailedScheduling

Signals:

- Pod phase is `Pending`.
- Condition `PodScheduled=False`.
- Events include `FailedScheduling`.

Interpretation:

- The scheduler cannot place the Pod on any node.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| Insufficient cpu/memory/pods | Cluster/node capacity shortage |
| Untolerated taint | Missing toleration |
| Node affinity/selector mismatch | Placement constraint too strict |
| Pod anti-affinity | Anti-affinity blocks placement |
| Quota or LimitRange text | Namespace policy or quota |

Ruled-out examples:

- Image pull is not reached until scheduling succeeds.
- Container logs are not expected before scheduling and start.

Next checks:

- Read the full `FailedScheduling` Event message.
- Inspect nodes, taints, allocatable resources, requests, affinity, tolerations, namespace ResourceQuota, and LimitRange.

Candidate fix paths:

- Adjust requests, affinity/tolerations, quota, or scale node capacity through the appropriate workflow.

Handoff:

- Node/autoscaling diagnoser for capacity or taints.
- Auto-remediation runner for scaling after confirmation.

## StorageMountFailure

Signals:

- Events include `FailedMount`, `FailedAttachVolume`, `FailedMapVolume`, or PVC timeout.
- Pod stays Pending or container cannot start due to volume setup.

Interpretation:

- The Pod scheduling path may be complete, but required storage cannot attach, mount, or become bound.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| PVC Pending | Provisioning/storage class issue |
| Attach timeout | Cloud volume attach issue |
| Mount permission or path error | Node mount/filesystem issue |
| Secret/configmap volume missing | Referenced object missing |

Ruled-out examples:

- Image pull is less likely if Events point to volume setup before image pull.
- App logs may be unavailable because the container has not started.

Next checks:

- Inspect PVC, PV, StorageClass, volume attachments, referenced Secret/ConfigMap, and node Events.

Candidate fix paths:

- Fix PVC/StorageClass/reference configuration or cloud volume state through storage remediation.

Handoff:

- Storage failure diagnoser.

## Evicted / Node Pressure

Signals:

- Pod reason/message contains `Evicted`.
- Node has MemoryPressure, DiskPressure, PIDPressure, or related pressure Events.
- Events mention ephemeral-storage or resource pressure.

Interpretation:

- Kubelet evicted the Pod to protect node stability.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| MemoryPressure | Node memory pressure |
| DiskPressure or ephemeral-storage text | Node disk or ephemeral storage pressure |
| QoS BestEffort/Burstable | Lower eviction priority |
| Node NotReady/unreachable | Node health issue |

Ruled-out examples:

- App crash is less likely if Pod reason is Evicted and kubelet cites pressure.
- Image pull is unrelated if the Pod had already been running.

Next checks:

- Inspect node conditions, allocated resources, Pod QoS, ephemeral-storage requests/limits, and node Events.

Candidate fix paths:

- Add requests/limits, reduce disk usage, move workload, or remediate node pressure through the right workflow.

Handoff:

- Node failure diagnoser.
- Auto-remediation runner for confirmed workload resource changes.

## ProbeFailure

Signals:

- Pod is Running but not Ready.
- Events include `Unhealthy` for readiness, liveness, or startup probe.

Interpretation:

- The container process may run, but Kubernetes health checks fail.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| Readiness fails only | Traffic should not be sent; app not ready |
| Liveness fails and restarts | Probe may be killing the app |
| Startup probe fails | Startup window too short |
| HTTP status mismatch | Wrong path, port, scheme, or auth |

Ruled-out examples:

- Image pull and scheduling are already successful.
- OOM is less likely unless termination state also shows OOMKilled.

Next checks:

- Inspect probe config, Events, container ports, Service endpoints, app logs, and startup timing.

Candidate fix paths:

- Fix probe path/port/scheme, increase thresholds, or fix the app dependency causing health check failure.

Handoff:

- Workload owner for probe/app changes.
- Network skill if probe depends on service connectivity.

## SandboxOrCNIBlocked

Signals:

- Events include `FailedCreatePodSandBox`, CNI errors, IP allocation errors, or runtime sandbox setup failures.

Interpretation:

- Scheduling succeeded, but kubelet/container runtime cannot create the Pod sandbox or network.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| IP allocation exhausted | CNI/IP pool exhaustion |
| CNI plugin not ready | CNI daemon issue |
| Runtime sandbox errors | containerd/runtime issue |
| Node-specific repeated failures | Node-local failure |

Ruled-out examples:

- App logs are unavailable because the container never starts.
- Image pull may not be reached if sandbox creation fails first.

Next checks:

- Inspect Pod Events, node conditions, CNI daemon Pods, affected node pattern, and cluster network/IP pool capacity.

Candidate fix paths:

- Fix CNI daemon, IP pool, or node runtime through network/node remediation.

Handoff:

- Network failure diagnoser.
- Node failure diagnoser.

## QuotaOrAdmissionRejected

Signals:

- Events mention ResourceQuota, LimitRange, admission webhook, forbidden, denied, or policy.

Interpretation:

- Kubernetes admission or namespace policy rejected or constrained the Pod.

Subtype hints:

| Evidence | Likely subtype |
| --- | --- |
| `exceeded quota` | ResourceQuota |
| missing requests/limits | LimitRange |
| webhook denied | Admission policy/webhook |
| forbidden by policy | Security or governance policy |

Ruled-out examples:

- Node capacity may be irrelevant if admission rejected the Pod before scheduling.
- Logs are unavailable because the container never starts.

Next checks:

- Inspect ResourceQuota, LimitRange, validating/mutating webhook messages, namespace labels, and policy owner.

Candidate fix paths:

- Adjust resource requests/limits, namespace quota, or admission policy through the owning workflow.

Handoff:

- Platform/admin owner.
- Auto-remediation runner only when a concrete safe change is confirmed.
