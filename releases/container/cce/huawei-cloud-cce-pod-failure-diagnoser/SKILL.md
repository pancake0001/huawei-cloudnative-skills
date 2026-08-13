---
id: huawei-cloud-cce-pod-failure-diagnoser
name: huawei-cloud-cce-pod-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE Pod failures with hcloud CLI for CCE cluster discovery and kubectl-cce plugin access, then `kubectl cce` for read-only Kubernetes evidence collection. Use this skill when the user mentions CCE Pod CrashLoopBackOff, ImagePullBackOff, ErrImagePull, OOMKilled, Pending, Evicted, restart storms, container logs, Pod Events, Pod metrics, or asks to troubleshoot a Huawei Cloud CCE Pod without using the Python SDK dispatcher.
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, pod, diagnosis]
---

# Huawei Cloud CCE Pod Failure Diagnoser

This skill diagnoses single-resource Pod failures in Huawei Cloud CCE clusters through the Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

**Execution model**: `hcloud CCE` cluster discovery -> `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` read-only Pod evidence -> cause ranking and handoff recommendations.

Use CCE hcloud commands for cluster-level metadata:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

Use `kubectl cce` for Kubernetes resources through kubectl-cce plugin access. Pods, Events, logs, Services, PVCs, Nodes, and metrics from metrics-server are Kubernetes resources and should be inspected with `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>`.

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, `huawei_pod_*` actions, or bundled SDK scripts for this skill.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` for the plugin access contract.

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

5. The caller has Huawei Cloud IAM permission to list/show CCE clusters and use kubectl-cce plugin access.
6. The kubectl-cce authenticated user has Kubernetes RBAC permission to read Pods, Events, logs, Services, PVCs, Nodes, and metrics in the target namespace.

Never print AK, SK, security token, kubectl-cce proxy credentials, or Authorization headers in the final report. Redact secrets in logs.

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

The kubectl-cce plugin normally talks to the CCE API Gateway endpoint `<cluster-id>.cce.<region>.myhuaweicloud.com`. If that endpoint is not valid for the current environment, set `CCE_ENDPOINT` or pass `--endpoint`. If plugin/API Gateway access fails, report it as an access gap with the error text; do not fall back to kubeconfig generation or SDK calls by default.

### 4. Configure kubectl-cce Plugin

Read `references/kubectl-cce.md` before running Kubernetes commands. Use the kubectl CCE plugin as the primary Kubernetes access path; do not generate kubeconfig, patch kubeconfig server fields, call the Kubernetes SDK, or fall back to SDK dispatcher actions.

If `kubectl` or `kubectl-cce` is missing, use `huawei-cloud-kubectl-cce-installer` to install or repair local prerequisites. This diagnoser verifies and uses the plugin; it does not own plugin installation policy.

Verify local tooling and plugin discovery:

```bash
kubectl version --client
kubectl plugin list
```

Configure plugin credentials through approved tool parameters, a protected shell environment, or an approved local credential provider without printing values. Pass cluster, region, and project ID explicitly in diagnostic commands:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

Use `CCE_ENDPOINT` or `--endpoint` only when the default `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is not valid for the current environment. If plugin access fails, report the sanitized installation, credential, API Gateway reachability, or Kubernetes RBAC gap; do not switch to kubeconfig generation or SDK calls.

The plugin intentionally blocks streaming commands such as `exec`, `attach`, and `port-forward`. `logs -f` and `watch` are not hardened, so use bounded `logs --tail` and normal `get` commands in diagnosis reports.

### 5. Verify Kubernetes Access

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get nodes
```

If RBAC denies a read, report the missing permission and continue only with evidence that can be collected safely.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence ordering and failure rules.

### First Sweep For Abnormal Pods

Before deep-diving, find abnormal Pods and restart-heavy Pods:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A --field-selector=status.phase!=Running -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,NODE:.spec.nodeName"
```

Use the field-selector output for obvious `Pending`/`Failed` Pods, and use the custom column output to catch Pods that are `Running` but not Ready or have abnormal restart counts.

### Find Candidate Pods

If the target Pod name is known:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <pod-name> -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <pod-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
```

If only a workload name is known, derive the selector from the workload and list Pods:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deployment <workload-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o yaml
```

For StatefulSet or DaemonSet, replace `deployment` with the correct workload kind.

### Collect Events

Prefer Pod-specific events, then namespace events sorted by time:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

When `events.k8s.io/v1` is available:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

Only cite Events that map to the target Pod, its owner, selected Pods, or the responsible Node/PVC.

### Collect Logs

For CrashLoopBackOff, OOMKilled, and frequent restarts, inspect previous logs first:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
```

For multi-container Pods, narrow the container when needed:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> -c <container-name> --previous --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> -c <container-name> --tail=200
```

Do not repeatedly request container logs for `ImagePullBackOff` when the image was never pulled. Use Events as primary evidence.

If a log command for an image-pull failure returns `container is waiting to start: trying and failing to pull image` or `previous terminated container ... not found`, treat that as supporting evidence that no container ever started, not as a kubectl failure.

### Collect Metrics And Node Context

Use metrics-server through kubectl when available:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod <pod-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod <pod-name> -n <namespace> --containers
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod -n <namespace> --sort-by=memory
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top node
```

If metrics-server is unavailable and `kubectl cce ... top` returns `Metrics API not available`, record it as a verification gap and avoid inventing resource trends. Do not switch to Python SDK, AOM SDK, or hand-written API calls to fill this gap inside this skill.

When Pending, Evicted, or node pressure appears:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
```

When storage appears:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pv
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

Use `references/output-schema.md` as the detailed schema. Put decision-critical information first; command traces and supporting evidence come after the reader already knows the conclusion.

The user-facing report should include, in this order:

- Executive summary: status, confidence, affected Pod/workload, and one-line conclusion.
- Root-cause analysis: top causes ranked with direct evidence and plain-language interpretation.
- Recommended next steps: immediate safe checks, candidate fix paths, and handoff owner/skill.
- Target: region, project, cluster, namespace, Pod/workload/selector.
- Pod lifecycle funnel with pass/fail layers.
- Negative evidence: why adjacent causes were ruled out, such as scheduling, node readiness, logs, metrics, OOM, storage, or probes.
- Current/previous log findings when available.
- Metrics and node/storage gaps when unavailable.
- Detailed evidence: relevant Events, status fields, owner/workload details, and selected command evidence.
- CLI path used: hcloud CCE operations and kubectl evidence commands.
- Explicit note that no mutating command was run.

After identifying the top cause, read `references/scenario-guides.md` and apply the matching scenario section. Do this for every concrete failure type, not only image pull failures. The scenario guide contains the expected interpretation, ruled-out causes, follow-up checks, candidate fixes, and handoff guidance for ImagePullBackOff, CrashLoopBackOff, OOMKilled, Pending, storage mount failures, eviction, probe failures, CNI/sandbox failures, and admission/quota failures.

## Safety Rules

Read `references/risk-rules.md` before making recommendations. This skill is read-only. Do not run:

- `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `drain`, or `taint`
- Any hcloud create/update/delete operation
- Any SDK dispatcher action

## Verification

Read `references/verification-method.md` for the CLI verification checklist. A valid implementation should pass these checks:

- `hcloud version`, `hcloud configure list`, and `kubectl version --client` work.
- `hcloud CCE ListClusters` and `ShowCluster` find the target cluster.
- `kubectl cce ...` can reach the cluster through the CCE API Gateway.
- `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` can read the target namespace.
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
