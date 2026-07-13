---
id: huawei-cloud-cce-node-failure-diagnoser
name: huawei-cloud-cce-node-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE node failures with hcloud CLI for CCE cluster discovery, node metadata, and kubeconfig acquisition, then kubectl for read-only Kubernetes node evidence. Use this skill for CCE NodeNotReady, Ready=Unknown, kube-node-lease timeout, DiskPressure, MemoryPressure, PIDPressure, NetworkUnavailable, CNI/node network symptoms, kubelet or container runtime abnormalities, node problem detector events, eviction impact, and node-level workload impact. Do not use the Python SDK dispatcher.
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, node, diagnosis]
---

# Huawei Cloud CCE Node Failure Diagnoser

This skill diagnoses CCE/Kubernetes node failures through Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

Execution model:

```text
hcloud CCE -> short-lived kubeconfig -> kubectl --kubeconfig=<file> -> read-only node evidence -> ranked diagnosis report
```

Use CCE hcloud commands for cluster-level and CCE node metadata:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE ListNodes`
- `hcloud CCE ShowNode`
- `hcloud CCE CreateKubernetesClusterCert`

Use `kubectl` for Kubernetes node state, kube-node-lease, Events, Pods on the node, logs from affected Pods when needed, and metrics from metrics-server.

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, old `huawei_node_*` actions, or Huawei Cloud SDK imports for this skill.

## When To Use

Use this skill for:

- Node `NotReady`, `Ready=False`, `Ready=Unknown`, or stale kube-node-lease.
- `DiskPressure`, `MemoryPressure`, `PIDPressure`, `NetworkUnavailable`, CNI, CRI, kubelet, or node problem detector signals.
- Pod evictions, sandbox creation failures, image pull failures, or restart storms concentrated on one node.
- Node resource pressure, allocatable/request saturation, taints, scheduling disabled, or node-local workload impact.
- User asks to diagnose a CCE node without mutating the cluster.

Do not use this skill to modify node or workload state. Cordon, uncordon, drain, reboot, delete, taint, scale, or restart operations must be written as recommendations and handed off to a remediation skill after confirmation.

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Required by most hcloud CCE operations |
| `cluster_id` | Preferred | If absent, resolve by cluster name with `ListClusters` |
| `cluster_name` | Optional | Use only to locate `cluster_id` |
| `node_name` | Preferred | Kubernetes node name, often the internal IP in CCE |
| `node_ip` | Optional | Use to match `kubectl get nodes -o wide` or CCE node metadata |
| `namespace` | Optional | Needed when narrowing affected Pods or logs |

At least one of `node_name` or `node_ip` should be provided. If both are missing, first list nodes and ask the user which node or symptom to focus on.

## Prerequisites

1. `hcloud` is installed and available in `PATH`, or a platform-native binary has been located and validated with `hcloud version`.
2. `kubectl` is installed and compatible with the target Kubernetes version. Linux sandboxes must use a Linux kubectl binary; Windows workstations use `kubectl.exe`.
3. Credentials are available to hcloud through a profile, environment, or one-off CLI parameters. Verify only masked configuration with:

```bash
hcloud configure list
```

4. IAM allows CCE cluster/node read and kubeconfig certificate creation.
5. Kubernetes RBAC allows read access to nodes, leases, events, pods, pod logs, and metrics when available.

Never print AK, SK, security tokens, kubeconfig certificates, Authorization headers, or registry secrets.

## CCE hcloud Setup Flow

### 1. Confirm CLI Tools

```bash
hcloud version
hcloud configure list
kubectl version --client
```

If a tool is not in `PATH`, locate or install a platform-native binary and validate the exact binary before using it. Keep skill examples platform-neutral as `hcloud` and `kubectl`; only local debug notes may contain absolute executable paths.

### 2. Locate And Check The Cluster

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Confirm the cluster is in the expected region/project and is reachable from the current network. If only a private API endpoint is available, run kubectl from a VPC/VPN/Direct Connect/Cloud Desktop environment that can reach the private endpoint.

### 3. Optional CCE Node Metadata

Use these commands to correlate Kubernetes node names with CCE node IDs and cloud metadata:

```bash
hcloud CCE ListNodes --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowNode --cluster_id=<cluster-id> --node_id=<node-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Do not use CCE node update/delete/reset operations.

### 4. Acquire A Short-Lived Kubeconfig

```bash
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <temp-kubeconfig-file>
chmod 600 <temp-kubeconfig-file>
```

KooCLI may output JSON-formatted kubeconfig. `kubectl` accepts JSON or YAML kubeconfig. Store it outside the repository and delete it after the diagnosis when no longer needed.

If the cluster was recently awakened or an EIP was just bound, retry certificate creation with explicit timeouts:

```bash
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json --cli-connect-timeout=20 --cli-read-timeout=90 --cli-retry-count=2 > <temp-kubeconfig-file>
```

### 5. Verify Kubernetes Read Access

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i get nodes
kubectl --kubeconfig=<kubeconfig-file> auth can-i list leases -n kube-node-lease
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -A
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -A
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -A
```

If RBAC denies a read, report the missing verb/resource and continue only with allowed evidence.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence order and failure rules.

Start with the cluster and node baseline:

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
kubectl --kubeconfig=<kubeconfig-file> get lease <node-name> -n kube-node-lease -o yaml
kubectl --kubeconfig=<kubeconfig-file> get events -A --field-selector involvedObject.kind=Node,involvedObject.name=<node-name> --sort-by=.lastTimestamp
```

Then inspect workload impact on the node:

```bash
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector spec.nodeName=<node-name> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector spec.nodeName=<node-name> -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,REASON:.status.reason,NODE:.spec.nodeName"
kubectl --kubeconfig=<kubeconfig-file> get events -A --sort-by=.lastTimestamp
```

Use metrics-server when available:

```bash
kubectl --kubeconfig=<kubeconfig-file> top node <node-name>
kubectl --kubeconfig=<kubeconfig-file> top pods -A --sort-by=memory
```

If `kubectl top` returns `Metrics API not available`, record it as a verification gap and avoid inventing resource trends.

## Cause Ranking

Rank causes by direct evidence and the first failing layer:

1. Cluster/API reachability or kubeconfig/RBAC gap.
2. Node liveness and kube-node-lease staleness.
3. Node conditions: Ready, pressure, NetworkUnavailable, kubelet/CRI/CNI/NPD conditions.
4. Taints, unschedulable state, and scheduling impact.
5. Pod symptoms concentrated on the node: Evicted, ContainerStatusUnknown, FailedCreatePodSandBox, volume mount failures, restart storms.
6. Resource saturation using allocatable/request summary and metrics when available.

Common cause labels:

| Cause | Evidence |
| --- | --- |
| `ControlPlaneDisconnected` | Ready=Unknown, stale lease, NodeStatusUnknown conditions |
| `NodeNotReady` | Ready=False with kubelet/node problem Events |
| `MemoryPressure` | MemoryPressure=True, evictions, memory metrics or allocatable pressure |
| `DiskPressure` | DiskPressure=True, ephemeral-storage evictions, disk problem conditions |
| `PIDPressure` | PIDPressure=True or PID problem Events |
| `NetworkUnavailableOrCNI` | NetworkUnavailable=True, CNIProblem, FailedCreatePodSandBox concentrated on node |
| `KubeletOrRuntimeProblem` | KUBELETProblem, CRIProblem, containerd/kubelet restart signals |
| `SchedulingDisabledOrTainted` | unschedulable node or taints causing scheduling impact |
| `HealthyOrNoNodeFault` | Node Ready, lease fresh, no pressure/problem signals |

## Report Format

Use `references/output-schema.md` as the detailed schema. Put decision-critical information first; command traces and raw condition tables come after the conclusion and next steps.

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
- CLI path used: hcloud CCE operations and kubectl evidence commands.
- Explicit statement that no mutating command was run.

## Safety Rules

Read `references/risk-rules.md` before making recommendations. This skill is read-only. Do not run:

- `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, `cordon`, `uncordon`, `drain`, or `taint`
- CCE node reset/delete/update operations
- ECS reboot/stop/delete operations
- Any SDK dispatcher action

## Verification

Read `references/verification-method.md` for the CLI verification checklist. A valid implementation should pass these checks:

- `hcloud version`, `hcloud configure list`, and `kubectl version --client` work.
- `hcloud CCE ListClusters`, `ShowCluster`, and `CreateKubernetesClusterCert` work.
- `kubectl --kubeconfig=<file>` can read nodes, leases, events, and pods.
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
