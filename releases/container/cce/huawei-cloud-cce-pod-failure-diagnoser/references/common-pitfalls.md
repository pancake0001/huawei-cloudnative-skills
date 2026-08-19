# Common Pitfalls And Solutions

This document lists common traps when diagnosing CCE Pod failures with `hcloud CCE` and `kubectl`.

## Pitfall 1: Missing Targeting Parameter

**Symptom**: The diagnosis cannot identify a target Pod or returns an overly broad namespace scan.

**Root Cause**: No `pod_name`, `workload_name`, or `selector` was provided.

**Solution**: Always narrow the target:

```bash
# With pod_name
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <pod-name> -n <namespace> -o wide

# With workload_name, first derive the selector
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get deployment <workload-name> -n <namespace> -o yaml
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide

# With a known label selector
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='app=my-app' -o wide
```

## Pitfall 2: Wrong Namespace

**Symptom**: No Pods found, or the user-provided Pod name cannot be found.

**Root Cause**: The target Pod is in a different namespace.

**Solution**: Verify namespaces and scan by name carefully:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A | grep <pod-name-fragment>
```

On Windows PowerShell, use:

```powershell
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A | Select-String <pod-name-fragment>
```

## Pitfall 3: ImagePullBackOff With Log Requests

**Symptom**: Logs are empty, `kubectl cce ... logs` reports that the container is waiting, or previous logs report that no previous terminated container exists.

**Root Cause**: `ImagePullBackOff` means the image was not pulled, so no container exists to produce logs.

**Solution**: Use Events as primary evidence:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
```

Focus on image name, tag, pull secret, registry, DNS, timeout, unauthorized, or repository-not-found messages.

Expected log errors for this case include:

- `container "<name>" in pod "<pod>" is waiting to start: trying and failing to pull image`
- `previous terminated container "<name>" in pod "<pod>" not found`

Treat these as confirmation that the container never started; do not spend time retrying logs.

The final report should include a recommendation block, not only the Event text. At minimum, state:

- Whether the image is a short name or a fully qualified registry path.
- How the short name resolves. Example: `azxsdc:latest` resolves as `docker.io/library/azxsdc:latest`.
- Whether the Event points more strongly to a missing repo/tag, auth/pull-secret problem, DNS/network problem, mirror/proxy error, or rate limit.
- Which concrete field should be fixed first, usually the Deployment image string or imagePullSecret.
- A safe target format, such as `swr.<region>.myhuaweicloud.com/<namespace>/<repo>:<tag>`.

## Pitfall 4: OOMKilled Without Previous Logs

**Symptom**: Current logs only show a fresh startup and miss the crash evidence.

**Root Cause**: After OOMKilled or a crash, the restarted container's current logs may not contain the failure.

**Solution**: Read previous logs first, then correlate memory limits:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod <pod-name> -n <namespace> --containers
```

If metrics are unavailable, report the gap instead of inferring a memory trend.

## Pitfall 5: Pending Without FailedScheduling Events

**Symptom**: Pod is Pending but the diagnosis does not explain why.

**Root Cause**: The scheduler Event is the main source of truth for Pending Pods.

**Solution**:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
```

For `FailedMount` or `FailedAttachVolume`, inspect PVC/PV and consider handing off to storage diagnosis:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
```

## Pitfall 6: Evicted Without Node Pressure Evidence

**Symptom**: The Pod says `Evicted`, but the cause remains unclear.

**Root Cause**: Eviction is normally explained by node pressure or kubelet resource thresholds.

**Solution**:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top node
```

If node-level pressure is confirmed, hand off to `huawei-cloud-cce-node-failure-diagnoser`.

## Pitfall 7: Cluster Endpoint Not Reachable

**Symptom**: `kubectl cce ...` times out or cannot reach the CCE API Gateway.

**Root Cause**: The kubectl-cce plugin endpoint may be unreachable from the current runtime or a custom endpoint may be required.

**Solution**:

```bash
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Use the default CCE API Gateway endpoint first. If that endpoint is not valid for the environment, set `CCE_ENDPOINT` or pass `--endpoint`, then rerun the same
`kubectl cce ...` command.

## Pitfall 8: kubectl-cce Gateway Timeout On Recently Awakened Cluster

**Symptom**: `kubectl cce ...` times out after a cluster wakeup or endpoint change.

**Root Cause**: The cluster API or CCE control plane is still becoming reachable, or the selected CCE API Gateway endpoint is not reachable from the runtime.

**Solution**:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
```

If the default endpoint is not valid, retry with `--endpoint <cce-api-gateway-endpoint>` or set `CCE_ENDPOINT`.

## Pitfall 9: Metrics API Unavailable

**Symptom**: `kubectl cce ... top` fails or returns no metrics.

**Root Cause**: metrics-server is not installed, not ready, or RBAC denies metrics access.

**Solution**:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get apiservices | grep metrics
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system | grep metrics
```

On PowerShell:

```powershell
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get apiservices | Select-String metrics
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system | Select-String metrics
```

If metrics remain unavailable, mark metrics as a gap and continue with Events/logs/status.

Do not switch to Huawei Cloud SDK, AOM SDK, curl IAM, or hand-written signed API calls inside this skill just to fetch metrics. This skill's cloud access path
is `hcloud CCE` plus `kubectl`.

## Pitfall 10: Frequent Restart False Positive

**Symptom**: A Pod is reported as a restart storm even though restarts are old or expected.

**Root Cause**: `restartCount` is cumulative for the container lifetime and does not show time distribution by itself.

**Solution**:

- Compare restart count with `lastState.terminated.finishedAt` and recent Events.
- Treat 0-2 historical restarts as low signal unless there are recent BackOff Events.
- Use previous logs only when the container actually has a previous terminated instance.

## Pitfall 11: Tool Exists But Is Not Executable On This OS

**Symptom**: A local `kubectl.exe` or `hcloud.exe` path exists, but running it fails with a platform error.

**Root Cause**: The binary does not match the current OS or architecture.

**Solution**: Validate the exact binary before using it:

```bash
hcloud version
kubectl version --client
```

If using explicit local paths, run the version command through that exact path. If it fails, locate or download the platform-native binary. Do not continue with
an unvalidated binary.

## Pitfall 12: KooCLI Help Syntax

**Symptom**: `hcloud CCE ListClusters help` returns a parameter format error.

**Root Cause**: KooCLI expects help as an option.

**Solution**:

```bash
hcloud CCE ListClusters --help
```

## Error And Gap Reference

| Signal                            | Likely Meaning                                   | Recommended Action                                              |
| --------------------------------- | ------------------------------------------------ | --------------------------------------------------------------- |
| `Forbidden`                       | Kubernetes RBAC denies read                      | Report missing verb/resource and continue with partial evidence |
| `NotFound`                        | Wrong namespace/name or deleted Pod              | Re-check namespace and owner workload                           |
| `Unable to connect to the server` | Endpoint/network issue                           | Check `ShowClusterEndpoints` and current network reachability   |
| `ImagePullBackOff`                | Image pull/auth/DNS/tag issue                    | Use Events; do not rely on logs                                 |
| `CrashLoopBackOff`                | Container exits repeatedly                       | Use previous logs, exit code, probe Events                      |
| `OOMKilled`                       | Container exceeded memory limit or node pressure | Check limits, previous logs, metrics if available               |
| `FailedScheduling`                | Scheduler could not place Pod                    | Check Event message, nodes, taints, affinity, quota             |
| `FailedMount`                     | Storage attach/mount issue                       | Check PVC/PV and storage skill handoff                          |
| `Metrics API not available`       | metrics-server absent or blocked                 | Record metric gap and avoid trend claims                        |
