---
id: huawei-cloud-cce-workload-failure-diagnoser
name: huawei-cloud-cce-workload-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE workload rollout and availability failures with hcloud CLI for CCE cluster discovery and kubeconfig acquisition, then kubectl for read-only Kubernetes evidence collection. Use this skill when the user mentions CCE Deployment, StatefulSet, DaemonSet, rollout stuck, replicas unavailable, Pod not ready, ImagePullBackOff, CrashLoopBackOff, probe failures, scheduling failures, PVC mount failures, workload events, or asks to troubleshoot a Huawei Cloud CCE workload without using the Python SDK dispatcher.
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, workload, diagnosis]
---

# Huawei Cloud CCE Workload Failure Diagnoser

This skill diagnoses CCE workload rollout and availability failures through the Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

**Execution model**: `hcloud CCE` -> short-lived kubeconfig -> `kubectl --kubeconfig=<file>` -> read-only workload evidence -> cause ranking and handoff recommendations.

Use CCE hcloud commands for cluster-level operations:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE CreateKubernetesClusterCert`

Use `kubectl` for Kubernetes resources after kubeconfig acquisition. Workloads, ReplicaSets, Pods, Events, logs, PVCs, Services, Ingresses, HPAs, and Nodes are Kubernetes resources and should be inspected with `kubectl --kubeconfig=<file>`.

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, `huawei_workload_*` actions, or bundled SDK scripts for this skill.

## When To Use

Use this skill for:

- Deployment rollout stuck, `ProgressDeadlineExceeded`, old replicas remaining, or new replicas not ready.
- StatefulSet or DaemonSet not updating, unavailable replicas, or stalled rollout.
- CCE workload status is abnormal but the user needs evidence before remediation.
- Pod-level symptoms surfaced from a workload, including `Pending`, `FailedScheduling`, `ImagePullBackOff`, `ErrImagePull`, `CrashLoopBackOff`, `OOMKilled`, `Evicted`, `FailedMount`, `Unhealthy`, or `ContainersNotReady`.
- Event, log, selector, ReplicaSet, PVC, HPA, Service, Ingress, or Node evidence needs to be correlated for a CCE workload.

Do not use this skill to mutate resources. Scaling, deleting, restarting, rollback, cordon, drain, or node operations must be handed off as recommendations only.

## Required Inputs

Collect these values before diagnosis:

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Include when hcloud operation requires it or multiple projects are possible |
| `cluster_id` | Preferred | If absent, find it with `ListClusters` |
| `namespace` | Yes | Kubernetes namespace |
| `kind` | Yes | `Deployment`, `StatefulSet`, or `DaemonSet` |
| `name` | Yes | Workload name |
| `selector` | Optional | Derive from workload if absent |

## Prerequisites

1. `hcloud` (Huawei Cloud KooCLI) is installed and available in `PATH`. Use the native binary for the runtime platform. Linux sandboxes should use the Linux KooCLI installer or tarball; macOS and Windows should use their corresponding packages. Skill commands should be written as `hcloud ...`, not with a platform-specific executable path.
2. `kubectl` is installed and compatible with the target Kubernetes minor version. Use the native binary for the runtime platform (`linux-amd64`, `linux-arm64`, `darwin-*`, or `windows-amd64`). Many agent sandboxes run on Linux even when the authoring workstation is Windows, so never hard-code a Windows-only `kubectl.exe` path in the skill workflow.
3. AK/SK credentials are configured in hcloud. Verify presence only with:

```bash
hcloud configure list
```

4. The caller has Huawei Cloud IAM permission to list/show CCE clusters and create kubeconfig certificates.
5. The generated kubeconfig user has Kubernetes RBAC permission to read the required namespace resources.

Never print AK, SK, security token, kubeconfig certificates, or Authorization headers in the final report. Redact secrets in logs.

## CCE hcloud Setup Flow

### 1. Confirm CLI Tools

```bash
hcloud version
hcloud configure list
kubectl version --client
```

If `kubectl` is missing, install or download the platform-native binary before continuing:

```bash
# Linux amd64 example
curl -LO "https://dl.k8s.io/release/v1.33.0/bin/linux/amd64/kubectl"
chmod +x ./kubectl
./kubectl version --client
```

On Windows, use `kubectl.exe`; on Linux and macOS, use `kubectl` without the `.exe` suffix.

If `hcloud` is missing, install or download the platform-native KooCLI binary before continuing:

```bash
# Linux/macOS example: official installer
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
bash ./hcloud_install.sh -y
hcloud version
```

On Windows, the extracted binary is `hcloud.exe`, but examples in this skill still use `hcloud` so the workflow remains platform-neutral.

### 2. Locate The CCE Cluster

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
```

If the user provides a cluster name instead of an ID, match it against the cluster list and record the cluster UUID.

### 3. Check Cluster Metadata

```bash
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Use this evidence to confirm the cluster is available, in the expected region/project, and reachable from the current network.

If `ShowClusterEndpoints` returns an empty `publicEndpoint` and the kubeconfig server is a private IP address, `kubectl` must run from a network that can reach the cluster private API server, such as a Huawei Cloud VPC host, VPN, Direct Connect, Cloud Desktop, or a sandbox with VPC connectivity. Do not treat this as an SDK/CLI conversion failure.

If `publicEndpoint` is present but `CreateKubernetesClusterCert` still returns a kubeconfig whose `clusters[].cluster.server` points to the private endpoint, create a temporary copy of the kubeconfig and replace only the `server` field with `publicEndpoint` before running `kubectl` from an external network. Record both the original server and the server actually used. Do not modify certificate, key, token, or user fields.

For recently awakened clusters or newly bound EIPs, KooCLI default timeout values may be too short. If `CreateKubernetesClusterCert` returns a KooCLI timeout, retry with explicit CLI timeouts, for example `--cli-connect-timeout=20 --cli-read-timeout=90 --cli-retry-count=2`.

### 4. Acquire A Short-Lived Kubeconfig

Use the shortest practical duration, normally 1 day.

```bash
mkdir -p ~/.kube/huawei-cce
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > ~/.kube/huawei-cce/<cluster-id>.kubeconfig
chmod 600 ~/.kube/huawei-cce/<cluster-id>.kubeconfig
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.kube\huawei-cce" | Out-Null
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > "$env:USERPROFILE\.kube\huawei-cce\<cluster-id>.kubeconfig"
```

The kubeconfig file format is platform-independent. KooCLI may emit JSON-formatted kubeconfig; `kubectl` accepts JSON or YAML kubeconfig. Only the path syntax and executable name differ between Linux/macOS and Windows.

### 5. Verify Kubernetes Access

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i get deployments -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -n <namespace>
```

If RBAC denies a read, report the missing permission and stop or continue with partial evidence.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence ordering and failure rules.

When many workloads across several namespaces are simultaneously unavailable, first check cluster-wide evidence before deep-diving a single workload:

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
kubectl --kubeconfig=<kubeconfig-file> get events -A --sort-by=.lastTimestamp
```

If all candidate nodes are `Ready=Unknown`, `NotReady`, tainted with `node.kubernetes.io/unreachable`, or tainted with `node.cloudprovider.kubernetes.io/shutdown`, rank the common node/scheduling blocker above individual workload symptoms.

### Deployment Evidence

```bash
kubectl --kubeconfig=<kubeconfig-file> get deployment <name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe deployment <name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> rollout status deployment/<name> -n <namespace> --timeout=30s
kubectl --kubeconfig=<kubeconfig-file> rollout history deployment/<name> -n <namespace>
```

Derive the selector from `spec.selector.matchLabels`, then inspect ReplicaSets and Pods:

```bash
kubectl --kubeconfig=<kubeconfig-file> get rs -n <namespace> --selector='<selector>' -o yaml
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o yaml
```

Filter ReplicaSets by ownerReference pointing to the Deployment UID. Treat the highest `deployment.kubernetes.io/revision` as the new version.

### StatefulSet Evidence

```bash
kubectl --kubeconfig=<kubeconfig-file> get statefulset <name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe statefulset <name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> rollout status statefulset/<name> -n <namespace> --timeout=30s
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
```

Compare `spec.replicas`, `status.currentReplicas`, `status.updatedReplicas`, `status.readyReplicas`, `status.availableReplicas`, and partition settings in `spec.updateStrategy`.

### DaemonSet Evidence

```bash
kubectl --kubeconfig=<kubeconfig-file> get daemonset <name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe daemonset <name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> rollout status daemonset/<name> -n <namespace> --timeout=30s
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
```

Compare `desiredNumberScheduled`, `currentNumberScheduled`, `updatedNumberScheduled`, `numberReady`, `numberAvailable`, `numberUnavailable`, and node scheduling constraints.

### Event Evidence

Collect workload, ReplicaSet, and Pod events. Prefer UID-related filtering when possible, and always avoid treating all namespace warnings as workload evidence.

```bash
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --field-selector involvedObject.name=<name> --sort-by=.lastTimestamp
```

When `events.k8s.io/v1` is available:

```bash
kubectl --kubeconfig=<kubeconfig-file> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

Keep events whose involved object UID/name maps to the workload, owned ReplicaSets, or selected Pods.

### Pod Drilldown

For every new-version Pod that is not Ready, inspect state, events, logs, and resource pressure:

```bash
kubectl --kubeconfig=<kubeconfig-file> describe pod <pod-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl --kubeconfig=<kubeconfig-file> top pod <pod-name> -n <namespace>
```

If scheduling or node pressure appears:

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
```

If storage appears:

```bash
kubectl --kubeconfig=<kubeconfig-file> get pvc -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe pvc <pvc-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> get pv
```

If traffic or readiness path appears:

```bash
kubectl --kubeconfig=<kubeconfig-file> get svc,endpoints,ingress -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe svc <service-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe ingress <ingress-name> -n <namespace>
```

## Cause Ranking

Rank causes with direct evidence. Prefer the first failing layer in the rollout funnel:

1. Control plane has not observed the workload generation.
2. New version object was not created or has no Pods.
3. New-version Pods exist but are Pending or unscheduled.
4. New-version Pods start but are not Ready.
5. Workload status has insufficient ready/available replicas.
6. Cluster/node/storage/network symptoms explain the Pod or readiness failure.

Common cause labels:

| Cause | Evidence |
| --- | --- |
| `ControlPlaneNotObserved` | `observedGeneration < generation` |
| `ReplicaSetCreateBlocked` | Deployment new ReplicaSet missing or FailedCreate events |
| `QuotaOrAdmissionRejected` | Events mention quota, LimitRange, webhook, denied, forbidden, or admission |
| `SchedulingBlocked` | Pods Pending with `FailedScheduling` |
| `ImagePullFailure` | `ImagePullBackOff`, `ErrImagePull`, image auth/tag/DNS errors |
| `CrashLoopOrAppExit` | `CrashLoopBackOff`, non-zero exit code, previous logs |
| `ContainerCommandNotFound` | Startup error says executable not found or command cannot be run |
| `ProbeFailure` | `Unhealthy` events for startup/liveness/readiness probe |
| `OOMKilled` | Last termination reason or events show OOM |
| `StorageMountFailure` | `FailedMount`, `FailedAttachVolume`, PVC Pending |
| `NodePressureOrNotReady` | Node conditions show pressure/not ready or Pods evicted |
| `ServiceOrIngressMismatch` | Service selector/endpoints/Ingress do not match ready Pods |

## Report Format

Use `references/output-schema.md` as the detailed schema. The user-facing report should include:

- Target: region, project, cluster, namespace, kind, name.
- CLI path used: hcloud CCE operations and kubectl evidence commands.
- Summary status and confidence.
- Rollout funnel with pass/fail layers.
- Top causes ranked with direct evidence snippets.
- Handoff recommendations for pod, node, storage, network, root-cause, or remediation skills.
- Explicit note that no mutating command was run.
- Verification gaps, including RBAC denials, missing metrics-server, inaccessible logs, or unavailable hcloud/kubectl tools.

## Safety Rules

Read `references/risk-rules.md` before making recommendations. This skill is read-only. Do not run:

- `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `drain`, or `taint`
- Any hcloud create/update/delete operation except `CreateKubernetesClusterCert`
- Any SDK dispatcher action

## Verification

Read `references/verification-method.md` for the CLI verification checklist. A valid implementation should pass these checks:

- `hcloud version`, `hcloud configure list`, and `kubectl version --client` work.
- `hcloud CCE ListClusters` and `ShowCluster` find the target cluster.
- `CreateKubernetesClusterCert` creates a short-lived kubeconfig.
- `kubectl --kubeconfig=<file>` can read the target namespace.
- Repository/package search finds no SDK dispatcher entrypoints in this skill package.

## References

- `references/workflow.md` - evidence order and failure rules.
- `references/output-schema.md` - Markdown and JSON report structure.
- `references/risk-rules.md` - read-only boundaries and handoff rules.
- `references/verification-method.md` - environment and CLI verification.
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/
