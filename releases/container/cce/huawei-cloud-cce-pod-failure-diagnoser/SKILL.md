---
id: huawei-cloud-cce-pod-failure-diagnoser
name: huawei-cloud-cce-pod-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE Pod failures with hcloud CLI for CCE cluster discovery and kubeconfig acquisition, then kubectl for read-only Kubernetes evidence collection. Use this skill when the user mentions CCE Pod CrashLoopBackOff, ImagePullBackOff, ErrImagePull, OOMKilled, Pending, Evicted, restart storms, container logs, Pod Events, Pod metrics, or asks to troubleshoot a Huawei Cloud CCE Pod without using the Python SDK dispatcher.
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, pod, diagnosis]
---

# Huawei Cloud CCE Pod Failure Diagnoser

This skill diagnoses single-resource Pod failures in Huawei Cloud CCE clusters through the Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

**Execution model**: `hcloud CCE` -> short-lived kubeconfig -> `kubectl --kubeconfig=<file>` -> read-only Pod evidence -> cause ranking and handoff recommendations.

Use CCE hcloud commands for cluster-level operations:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE CreateKubernetesClusterCert`

Use `kubectl` for Kubernetes resources after kubeconfig acquisition. Pods, Events, logs, Services, PVCs, Nodes, and metrics from metrics-server are Kubernetes resources and should be inspected with `kubectl --kubeconfig=<file>`.

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, `huawei_pod_*` actions, or bundled SDK scripts for this skill.

## When To Use

Use this skill for:

- Pod `CrashLoopBackOff`, `Error`, `RunContainerError`, or frequent restarts.
- Pod `ImagePullBackOff`, `ErrImagePull`, or registry authentication/pull failures.
- Pod `OOMKilled`, exit code `137`, or suspected memory limit pressure.
- Pod `Pending`, `FailedScheduling`, `FailedMount`, `FailedAttachVolume`, or sandbox creation failures.
- Pod `Evicted`, node pressure, disk pressure, memory pressure, or ephemeral-storage pressure.
- Container logs, previous logs, Events, restart counts, readiness/liveness/startup probe failures, or Pod resource usage evidence.

Do not use this skill to mutate resources. Scaling, deleting, restarting, rollback, cordon, drain, taint, or node operations must be handed off as recommendations only.

## Required Inputs

Collect these values before diagnosis:

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Include when hcloud operation requires it or multiple projects are possible |
| `cluster_id` | Preferred | If absent, find it with `ListClusters` |
| `namespace` | Yes | Kubernetes namespace |
| `pod_name` | Preferred | Target Pod name |
| `workload_name` | Optional | Use to derive the Pod selector when Pod name is unknown |
| `selector` | Optional | Kubernetes label selector, for example `app=my-app` |

## Prerequisites

1. `hcloud` (Huawei Cloud KooCLI) is installed and available in `PATH`. Use the native binary for the runtime platform. Linux sandboxes should use the Linux KooCLI installer or tarball; macOS and Windows should use their corresponding packages. Skill commands should be written as `hcloud ...`, not with a platform-specific executable path.
2. `kubectl` is installed and compatible with the target Kubernetes minor version. Use the native binary for the runtime platform (`linux-amd64`, `linux-arm64`, `darwin-*`, or `windows-amd64`). Many agent sandboxes run on Linux even when the authoring workstation is Windows, so never hard-code a Windows-only `kubectl.exe` path in the skill workflow.
3. If either tool is not in `PATH`, locate a platform-native binary, assign it to a shell variable, and validate it with `version` before using it. Do not assume a file named `kubectl.exe` or `hcloud.exe` is valid for the current OS just because it exists.
4. AK/SK credentials are configured in hcloud. Verify presence only with:

```bash
hcloud configure list
```

5. The caller has Huawei Cloud IAM permission to list/show CCE clusters and create kubeconfig certificates.
6. The generated kubeconfig user has Kubernetes RBAC permission to read Pods, Events, logs, Services, PVCs, Nodes, and metrics in the target namespace.

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

The kubeconfig file format is platform-independent. KooCLI may emit JSON-formatted kubeconfig; `kubectl` accepts JSON or YAML kubeconfig. Only path syntax and executable name differ between Linux/macOS and Windows.

### 5. Verify Kubernetes Access

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get nodes
```

If RBAC denies a read, report the missing permission and continue only with evidence that can be collected safely.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence ordering and failure rules.

### First Sweep For Abnormal Pods

Before deep-diving, find abnormal Pods and restart-heavy Pods:

```bash
kubectl --kubeconfig=<kubeconfig-file> get pods -A -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector=status.phase!=Running -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,NODE:.spec.nodeName"
```

Use the field-selector output for obvious `Pending`/`Failed` Pods, and use the custom column output to catch Pods that are `Running` but not Ready or have abnormal restart counts.

### Find Candidate Pods

If the target Pod name is known:

```bash
kubectl --kubeconfig=<kubeconfig-file> get pod <pod-name> -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pod <pod-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe pod <pod-name> -n <namespace>
```

If only a workload name is known, derive the selector from the workload and list Pods:

```bash
kubectl --kubeconfig=<kubeconfig-file> get deployment <workload-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o yaml
```

For StatefulSet or DaemonSet, replace `deployment` with the correct workload kind.

### Collect Events

Prefer Pod-specific events, then namespace events sorted by time:

```bash
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
```

When `events.k8s.io/v1` is available:

```bash
kubectl --kubeconfig=<kubeconfig-file> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

Only cite Events that map to the target Pod, its owner, selected Pods, or the responsible Node/PVC.

### Collect Logs

For CrashLoopBackOff, OOMKilled, and frequent restarts, inspect previous logs first:

```bash
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --tail=200
```

For multi-container Pods, narrow the container when needed:

```bash
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> -c <container-name> --previous --tail=200
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> -c <container-name> --tail=200
```

Do not repeatedly request container logs for `ImagePullBackOff` when the image was never pulled. Use Events as primary evidence.

If a log command for an image-pull failure returns `container is waiting to start: trying and failing to pull image` or `previous terminated container ... not found`, treat that as supporting evidence that no container ever started, not as a kubectl failure.

### Collect Metrics And Node Context

Use metrics-server through kubectl when available:

```bash
kubectl --kubeconfig=<kubeconfig-file> top pod <pod-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> top pod <pod-name> -n <namespace> --containers
kubectl --kubeconfig=<kubeconfig-file> top pod -n <namespace> --sort-by=memory
kubectl --kubeconfig=<kubeconfig-file> top node
```

If metrics-server is unavailable and `kubectl top` returns `Metrics API not available`, record it as a verification gap and avoid inventing resource trends. Do not switch to Python SDK, AOM SDK, or hand-written API calls to fill this gap inside this skill.

When Pending, Evicted, or node pressure appears:

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
```

When storage appears:

```bash
kubectl --kubeconfig=<kubeconfig-file> get pvc -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe pvc <pvc-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> get pv
```

## Cause Ranking

Rank causes with direct evidence. Prefer the first failing layer in the Pod lifecycle:

1. Pod was not admitted or sandbox/network setup failed.
2. Pod exists but cannot schedule.
3. Pod scheduled but volumes cannot attach or mount.
4. Image cannot be pulled.
5. Container starts and exits or crashes.
6. Container runs but readiness/liveness/startup probes fail.
7. Node pressure or eviction explains the Pod failure.

Common cause labels:

| Cause | Evidence |
| --- | --- |
| `CrashLoopOrAppExit` | `CrashLoopBackOff`, non-zero exit code, previous logs |
| `ContainerCommandNotFound` | Startup error says executable not found or command cannot be run |
| `ImagePullFailure` | `ImagePullBackOff`, `ErrImagePull`, image auth/tag/DNS errors |
| `OOMKilled` | Last termination reason, exit code 137, memory limits or metrics |
| `SchedulingBlocked` | Pod Pending with `FailedScheduling` |
| `StorageMountFailure` | `FailedMount`, `FailedAttachVolume`, PVC Pending |
| `ProbeFailure` | `Unhealthy` Events for startup/liveness/readiness probe |
| `NodePressureOrEviction` | Evicted Pod, node pressure conditions, taints, or NotReady |
| `QuotaOrAdmissionRejected` | Events mention quota, LimitRange, webhook, denied, or forbidden |
| `SandboxOrCNIBlocked` | `FailedCreatePodSandBox`, CNI, IP allocation, or runtime sandbox errors |

## Report Format

Use `references/output-schema.md` as the detailed schema. The user-facing report should include:

- Target: region, project, cluster, namespace, Pod/workload/selector.
- CLI path used: hcloud CCE operations and kubectl evidence commands.
- Summary status and confidence.
- Pod lifecycle funnel with pass/fail layers.
- Top causes ranked with direct evidence snippets.
- Root-cause interpretation: explain what the failing message means in plain language, including how image names, registry defaults, scheduler state, node pressure, or storage state affect the conclusion.
- Negative evidence: briefly state why likely adjacent causes were ruled out, such as scheduling, node readiness, logs, metrics, OOM, storage, or probes.
- Current/previous log findings when available.
- Metrics and node/storage gaps when unavailable.
- Follow-up analysis recommendations: include concrete next checks, what result would confirm or refute the hypothesis, and which owner/system should be checked.
- Candidate fix paths: describe safe remediation options without executing them, and state when to hand off to workload, node, storage, network, root-cause, or remediation skills.
- Explicit note that no mutating command was run.

After identifying the top cause, read `references/scenario-guides.md` and apply the matching scenario section. Do this for every concrete failure type, not only image pull failures. The scenario guide contains the expected interpretation, ruled-out causes, follow-up checks, candidate fixes, and handoff guidance for ImagePullBackOff, CrashLoopBackOff, OOMKilled, Pending, storage mount failures, eviction, probe failures, CNI/sandbox failures, and admission/quota failures.

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
- `references/scenario-guides.md` - scenario-specific interpretation, next checks, candidate fixes, and handoff guidance.
- `references/common-pitfalls.md` - troubleshooting traps and CLI examples.
- `references/output-schema.md` - Markdown and JSON report structure.
- `references/risk-rules.md` - read-only boundaries and handoff rules.
- `references/verification-method.md` - environment and CLI verification.
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/
