---
name: huawei-cloud-cce-node-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE node failures using hcloud for cluster and node metadata plus read-only kubectl-cce evidence. Use this skill whenever the user
  mentions NodeNotReady, Ready=Unknown, stale kube-node-lease, DiskPressure, MemoryPressure, PIDPressure, NetworkUnavailable, CNI, kubelet or runtime failures,
  eviction, or node-level workload impact.
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, node, diagnosis]
---

# Huawei Cloud CCE Node Failure Diagnoser

## Overview

This skill diagnoses CCE/Kubernetes node failures through Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

Execution model:

```text
hcloud CCE cluster discovery -> kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> read-only node evidence -> ranked diagnosis report
```

Use CCE hcloud commands for cluster-level and CCE node metadata. Use kubectl-cce for Kubernetes API access:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE ListNodes`
- `hcloud CCE ShowNode`

Use `kubectl cce` through the kubectl-cce plugin for Kubernetes node state, kube-node-lease, Events, Pods on the node, logs from affected Pods when needed, and
metrics from metrics-server.

Do not use Python SDK dispatchers, legacy skill execution actions, old Huawei node actions, or Huawei Cloud SDK imports for this skill.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` for the
plugin access contract.

## When To Use

Use this skill for:

- Node `NotReady`, `Ready=False`, `Ready=Unknown`, or stale kube-node-lease.
- `DiskPressure`, `MemoryPressure`, `PIDPressure`, `NetworkUnavailable`, CNI, CRI, kubelet, or node problem detector signals.
- Pod evictions, sandbox creation failures, image pull failures, or restart storms concentrated on one node.
- Node resource pressure, allocatable/request saturation, taints, scheduling disabled, or node-local workload impact.
- User asks to diagnose a CCE node without mutating the cluster.

Do not use this skill to modify node or workload state. Cordon, uncordon, drain, reboot, delete, taint, scale, or restart operations must be recommendations and
must be handed off to a remediation skill after confirmation.

## Parameters

| Input          | Required  | Notes                                                                 |
| -------------- | --------- | --------------------------------------------------------------------- |
| `region`       | Yes       | Request context or `HW_REGION_NAME`; otherwise ask the user                                                 |
| `project_id`   | Usually   | Required by most hcloud CCE operations                                |
| `cluster_id`   | Preferred | If absent, resolve by cluster name with `ListClusters`                |
| `cluster_name` | Optional  | Use only to locate `cluster_id`                                       |
| `node_name`    | Preferred | Kubernetes node name, often the internal IP in CCE                    |
| `node_ip`      | Optional  | Use to match `kubectl cce ... get nodes -o wide` or CCE node metadata |
| `namespace`    | Optional  | Needed when narrowing affected Pods or logs                           |

At least one of `node_name` or `node_ip` should be provided. If both are missing, first list nodes and ask the user which node or symptom to focus on.

## Region Selection

Use the region supplied by the current request or established task context. If it is absent, use `HW_REGION_NAME`. If neither source provides a region, stop and ask the user to provide `region` or set `HW_REGION_NAME`; never infer it from an hcloud profile.

## Explicit Credential Propagation

Accept `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token`. AK and SK must be supplied together; a token requires that pair. When
provided, append all supplied options to every `hcloud` and `kubectl cce` command, pass them unchanged to delegated skills, and do not use an hcloud profile
or authentication environment variables. Never print credential values.

## Prerequisites

1. `hcloud` is installed and available in `PATH`, or a platform-native binary has been located and validated with `hcloud version`.
2. `kubectl` is installed and compatible with the target Kubernetes version. Linux sandboxes must use a Linux kubectl binary; Windows workstations use
   `kubectl.exe`.
3. Credentials are available to hcloud through a profile, environment, or one-off CLI parameters. Verify only masked configuration with `hcloud configure list`.
4. IAM allows CCE cluster/node read and kubectl-cce API Gateway access.
5. Kubernetes RBAC allows read access to nodes, leases, events, pods, pod logs, and metrics when available.

Never print AK, SK, security tokens, kubectl-cce proxy credentials, Authorization headers, or registry secrets.

## Core Commands And Setup

### 1. Confirm CLI Tools

```bash
hcloud version
hcloud configure list
kubectl version --client
```

If a tool is missing, stop this diagnosis flow and use `huawei-cloud-kubectl-cce-installer` or an approved platform-specific procedure. This diagnoser must not
download or execute installer scripts. Pin an approved version, verify its published checksum or signature, and then rerun the checks.

### 2. Locate And Check The Cluster

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Confirm that the cluster is in the expected region/project and reachable from the current network. The plugin normally uses the CCE API Gateway endpoint
`<cluster-id>.cce.<region>.myhuaweicloud.com`. If it is invalid for the environment, set `CCE_ENDPOINT` or pass `--endpoint`. Report access failures and do not
fall back to kubeconfig generation or SDK calls.

### 3. Optional CCE Node Metadata

Use these commands to correlate Kubernetes node names with CCE node IDs and cloud metadata:

```bash
hcloud CCE ListNodes --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowNode --cluster_id=<cluster-id> --node_id=<node-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Do not use CCE node update/delete/reset operations.

### 4. Configure kubectl-cce Plugin

Read `references/kubectl-cce.md` before running Kubernetes commands. Use the kubectl CCE plugin as the primary Kubernetes access path. Do not generate or patch
kubeconfig, call the Kubernetes SDK, or fall back to SDK dispatcher actions.

If `kubectl` or `kubectl-cce` is missing, use `huawei-cloud-kubectl-cce-installer` to install or repair local prerequisites. This diagnoser only verifies and
uses the plugin; it does not own plugin installation policy.

Verify local tooling and plugin discovery:

```bash
kubectl version --client
kubectl plugin list
```

Configure plugin credentials through approved tool parameters, a protected shell environment, or an approved local credential provider without printing values.
Pass cluster, region, and project ID explicitly in diagnostic commands:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

Use `CCE_ENDPOINT` or `--endpoint` only when the default `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is invalid. If plugin access fails, report the
sanitized installation, credential, API Gateway reachability, or Kubernetes RBAC gap; do not switch to kubeconfig generation or SDK calls.

The plugin blocks streaming commands such as `exec`, `attach`, and `port-forward`. `logs -f` and `watch` are not hardened, so use bounded `logs --tail` and
normal `get` commands in diagnosis reports.

### 5. Verify Kubernetes Read Access

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get nodes
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list leases -n kube-node-lease
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -A
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -A
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -A
```

If RBAC denies a read, report the missing verb/resource and continue only with allowed evidence.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence order and failure rules.

Start with the cluster and node baseline:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get lease <node-name> -n kube-node-lease -o yaml
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --field-selector involvedObject.kind=Node,involvedObject.name=<node-name> --sort-by=.lastTimestamp
```

Then inspect workload impact on the node:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A --field-selector spec.nodeName=<node-name> -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A --field-selector spec.nodeName=<node-name> -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,REASON:.status.reason,NODE:.spec.nodeName"
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

Use metrics-server when available:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top node <node-name>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -A --sort-by=memory
```

If `kubectl cce ... top` returns `Metrics API not available`, record it as a verification gap and avoid inventing resource trends.

## Cause Ranking

Rank causes by direct evidence and the first failing layer:

1. Cluster/API Gateway/plugin/RBAC reachability gap.
2. Node liveness and kube-node-lease staleness.
3. Node conditions: Ready, pressure, NetworkUnavailable, kubelet/CRI/CNI/NPD conditions.
4. Taints, unschedulable state, and scheduling impact.
5. Pod symptoms concentrated on the node: Evicted, ContainerStatusUnknown, FailedCreatePodSandBox, volume mount failures, restart storms.
6. Resource saturation using allocatable/request summary and metrics when available.

Common cause labels:

| Cause                         | Evidence                                                                         |
| ----------------------------- | -------------------------------------------------------------------------------- |
| `ControlPlaneDisconnected`    | Ready=Unknown, stale lease, NodeStatusUnknown conditions                         |
| `NodeNotReady`                | Ready=False with kubelet/node problem Events                                     |
| `MemoryPressure`              | MemoryPressure=True, evictions, memory metrics or allocatable pressure           |
| `DiskPressure`                | DiskPressure=True, ephemeral-storage evictions, disk problem conditions          |
| `PIDPressure`                 | PIDPressure=True or PID problem Events                                           |
| `NetworkUnavailableOrCNI`     | NetworkUnavailable=True, CNIProblem, FailedCreatePodSandBox concentrated on node |
| `KubeletOrRuntimeProblem`     | KUBELETProblem, CRIProblem, containerd/kubelet restart signals                   |
| `SchedulingDisabledOrTainted` | unschedulable node or taints causing scheduling impact                           |
| `HealthyOrNoNodeFault`        | Node Ready, lease fresh, no pressure/problem signals                             |

## Output Format

Use `references/output-schema.md` as the detailed schema. Put decision-critical information first; command traces and raw condition tables come after the
conclusion and next steps.

The user-facing report should include, in this order:

- Executive summary: node health status, confidence, root category, and one-line conclusion.
- Root-cause analysis: top causes ranked with direct evidence and interpretation.
- Recommended next steps: safe checks, candidate fix paths, and handoff owner/skill.
- Target: region, project, cluster, node name/IP, and optional namespace/workload scope.
- Node lifecycle/liveness funnel.
- Workload impact: Pods on node, evicted/failed/not-ready Pods, and concentrated symptoms.
- Negative evidence: adjacent causes that were checked and are less likely.
- Node condition table and kube-node-lease finding.
- Metrics and verification gaps.
- CLI path used: hcloud CCE operations and kubectl-cce evidence commands.
- Explicit statement that no mutating command was run.

## Best Practices

- Start with node liveness and lease freshness before interpreting downstream Pod symptoms.
- Correlate Kubernetes node names, CCE node IDs, conditions, Events, and affected Pods.
- Treat unavailable metrics or logs as verification gaps instead of inferring trends.
- Keep diagnosis read-only and hand off every node or workload mutation.

## Notes And Safety Rules

Read `references/risk-rules.md` before making recommendations. This skill is read-only. Do not run:

- `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `uncordon`, `drain`, or `taint`
- CCE node reset/delete/update operations
- ECS reboot/stop/delete operations
- Any SDK dispatcher action

## Verification

Read `references/verification-method.md` for the CLI verification checklist. A valid implementation should pass these checks:

- `hcloud version`, `hcloud configure list`, and `kubectl version --client` work.
- `hcloud CCE ListClusters` and `ShowCluster` work, and `kubectl cce ...` can reach the cluster through the CCE API Gateway.
- `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id>` can read nodes, leases, events, and pods.
- Repository/package search finds no SDK dispatcher entrypoints in this skill package.

## References

- `references/workflow.md` - node evidence order and failure rules.
- `references/common-pitfalls.md` - node diagnosis traps and CLI examples.
- `references/output-schema.md` - Markdown and JSON report structure.
- `references/risk-rules.md` - read-only boundaries and handoff rules.
- `references/verification-method.md` - environment and CLI verification.
- `references/iam-policies.md` - IAM and Kubernetes RBAC requirements.
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.
