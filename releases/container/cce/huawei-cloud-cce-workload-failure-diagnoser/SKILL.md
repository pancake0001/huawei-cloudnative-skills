---
name: huawei-cloud-cce-workload-failure-diagnoser
description: Diagnose CCE workload rollout failures with hcloud and read-only kubectl-cce. Use this skill whenever the user mentions unavailable replicas or a stalled Deployment, StatefulSet, or DaemonSet.
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, workload, diagnosis]
---

# Huawei Cloud CCE Workload Failure Diagnoser

## Overview

This skill diagnoses CCE workload rollout and availability failures through the Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

**Execution model**: `hcloud CCE` cluster discovery ->
`kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` read-only workload evidence -> cause ranking and handoff recommendations.

Use CCE hcloud commands for cluster-level metadata:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

Use `kubectl cce` for Kubernetes resources through kubectl-cce plugin access. Workloads, ReplicaSets, Pods, Events, logs, PVCs, Services, Ingresses, HPAs,
and Nodes are Kubernetes resources. Inspect them with `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>`.

Do not use Python SDK dispatchers, legacy skill execution actions, old Huawei workload actions, or bundled SDK scripts for this skill.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` for the plugin access contract.

## When To Use

Use this skill for:

- Deployment rollout stuck, `ProgressDeadlineExceeded`, old replicas remaining, or new replicas not ready.
- StatefulSet or DaemonSet not updating, unavailable replicas, or stalled rollout.
- CCE workload status is abnormal but the user needs evidence before remediation.
- Pod-level symptoms surfaced from a workload, including `Pending`, `FailedScheduling`, `ImagePullBackOff`, `ErrImagePull`, `CrashLoopBackOff`, `OOMKilled`,
  `Evicted`, `FailedMount`, `Unhealthy`, or `ContainersNotReady`.
- Event, log, selector, ReplicaSet, PVC, HPA, Service, Ingress, or Node evidence needs to be correlated for a CCE workload.

Do not use this skill to mutate resources. Scaling, deleting, restarting, rollback, cordon, drain, or node operations must be handed off as recommendations only.

## Parameters

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

1. `hcloud` (Huawei Cloud KooCLI) is installed and available in `PATH`. Use the native binary for the runtime platform. Linux sandboxes should use the Linux
   installer or tarball; macOS and Windows should use their corresponding packages. Write skill commands as `hcloud ...`, without a platform-specific path.
2. `kubectl` is installed and compatible with the target Kubernetes minor version. Use the native binary for the runtime platform (`linux-amd64`,
   `linux-arm64`, `darwin-*`, or `windows-amd64`). Agent sandboxes often run on Linux, so never hard-code a Windows-only `kubectl.exe` path.
3. AK/SK credentials are configured in hcloud. Verify presence only with:

```bash
hcloud configure list
```

1. The caller has Huawei Cloud IAM permission to list/show CCE clusters and use kubectl-cce plugin access.
2. The kubectl-cce authenticated user has Kubernetes RBAC permission to read the required namespace resources.

Never print AK, SK, security token, kubectl-cce proxy credentials, or Authorization headers in the final report. Redact secrets in logs.

## Core Commands And Setup

### 1. Confirm CLI Tools

```bash
hcloud version
hcloud configure list
kubectl version --client
```

If `kubectl`, `kubectl-cce`, or `hcloud` is missing, stop this diagnosis flow and
use `huawei-cloud-kubectl-cce-installer` or an approved platform-specific
installation procedure. This diagnoser must not download or execute installer
scripts. Pin an approved version, verify its published checksum or signature,
and then rerun the version checks above.

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

The kubectl-cce plugin normally talks to `<cluster-id>.cce.<region>.myhuaweicloud.com`. If that CCE API Gateway endpoint is invalid for the current environment,
set `CCE_ENDPOINT` or pass `--endpoint`. If access fails, report the error as an access gap; do not fall back to kubeconfig generation or SDK calls.

### 4. Configure kubectl-cce Plugin

Read `references/kubectl-cce.md` before running Kubernetes commands. Use the kubectl CCE plugin as the primary Kubernetes access path. Do not generate or patch
kubeconfig, call the Kubernetes SDK, or fall back to SDK dispatcher actions.

If `kubectl` or `kubectl-cce` is missing, use `huawei-cloud-kubectl-cce-installer` to install or repair local prerequisites. This diagnoser only verifies and uses
the plugin; it does not own plugin installation policy.

Verify local tooling and plugin discovery:

```bash
kubectl version --client
kubectl plugin list
```

Configure plugin credentials through approved tool parameters, a protected shell environment, or an approved local credential provider without printing values.
Pass cluster, region, and project ID explicitly in diagnostic commands:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

Use `CCE_ENDPOINT` or `--endpoint` only when the default `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is invalid. If plugin access fails, report the
sanitized installation, credential, API Gateway reachability, or Kubernetes RBAC gap; do not switch to kubeconfig generation or SDK calls.

The plugin blocks streaming commands such as `exec`, `attach`, and `port-forward`. `logs -f` and `watch` are not hardened, so use bounded `logs --tail` and normal
`get` commands in diagnosis reports.

### 5. Verify Kubernetes Access

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get deployments -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
```

If RBAC denies a read, report the missing permission and stop or continue with partial evidence.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence ordering and failure rules.

When many workloads across several namespaces are simultaneously unavailable, first check cluster-wide evidence before deep-diving a single workload:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

If all candidate nodes are `Ready=Unknown`, `NotReady`, or tainted with node.kubernetes.io/unreachable or node.cloudprovider.kubernetes.io/shutdown, rank the
common node/scheduling blocker above individual workload symptoms.

### Deployment Evidence

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deployment <name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe deployment <name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status deployment/<name> -n <namespace> --timeout=30s
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout history deployment/<name> -n <namespace>
```

Derive the selector from `spec.selector.matchLabels`, then inspect ReplicaSets and Pods:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get rs -n <namespace> --selector='<selector>' -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o yaml
```

Filter ReplicaSets by ownerReference pointing to the Deployment UID. Treat the highest deployment.kubernetes.io/revision annotation as the new version.

### StatefulSet Evidence

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get statefulset <name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe statefulset <name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status statefulset/<name> -n <namespace> --timeout=30s
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
```

Compare `spec.replicas`, `status.currentReplicas`, `status.updatedReplicas`, `status.readyReplicas`, `status.availableReplicas`, and partition settings in `spec.updateStrategy`.

### DaemonSet Evidence

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get daemonset <name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe daemonset <name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status daemonset/<name> -n <namespace> --timeout=30s
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
```

Compare `desiredNumberScheduled`, `currentNumberScheduled`, `updatedNumberScheduled`, `numberReady`, `numberAvailable`, `numberUnavailable`, and node scheduling constraints.

### Event Evidence

Collect workload, ReplicaSet, and Pod events. Prefer UID-related filtering when possible, and always avoid treating all namespace warnings as workload evidence.

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector involvedObject.name=<name> --sort-by=.lastTimestamp
```

When the Kubernetes Events v1 API is available:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

Keep events whose involved object UID/name maps to the workload, owned ReplicaSets, or selected Pods.

### Pod Drilldown

For every new-version Pod that is not Ready, inspect state, events, logs, and resource pressure:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod <pod-name> -n <namespace>
```

If scheduling or node pressure appears:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
```

If storage appears:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pv
```

If traffic or readiness path appears:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,ingress -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe svc <service-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe ingress <ingress-name> -n <namespace>
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

## Output Format

Use `references/output-schema.md` as the detailed schema. The user-facing report should include:

- Target: region, project, cluster, namespace, kind, name.
- CLI path used: hcloud CCE operations and kubectl evidence commands.
- Summary status and confidence.
- Rollout funnel with pass/fail layers.
- Top causes ranked with direct evidence snippets.
- Handoff recommendations for pod, node, storage, network, root-cause, or remediation skills.
- Explicit note that no mutating command was run.
- Verification gaps, including RBAC denials, missing metrics-server, inaccessible logs, or unavailable hcloud/kubectl tools.

## Best Practices

- Start with the first failed rollout layer and rank hypotheses by direct evidence.
- Correlate workload generation, owned objects, selected Pods, and Events before assigning a cause.
- Keep logs and metrics bounded, and record unavailable evidence as a verification gap.
- Separate read-only diagnosis from remediation and name the handoff for every proposed change.

## Notes And Safety Rules

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
- `references/output-schema.md` - Markdown and JSON report structure.
- `references/risk-rules.md` - read-only boundaries and handoff rules.
- `references/verification-method.md` - environment and CLI verification.
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/
