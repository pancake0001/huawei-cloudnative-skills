---
name: huawei-cloud-cce-storage-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE storage failures using hcloud for cluster and cloud-storage metadata plus read-only kubectl-cce evidence. Use this skill whenever
  the user mentions PVC Pending, provisioning or binding failures, EVS topology conflicts, FailedAttach, FailedMount, CSI errors, SFS or SFS Turbo NFS timeouts,
  OBS 403 or credential errors, runtime I/O, read-only filesystems, capacity or inode exhaustion, subPath issues, or PVC termination.
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, storage, diagnosis]
---

# Huawei Cloud CCE Storage Failure Diagnoser

## Overview

This skill diagnoses CCE/Kubernetes storage failures across provisioning, binding, scheduling, attach/mount, runtime I/O, capacity, permission, and teardown
stages.

### Application Routing

Use this skill when a user supplies `namespace + app_name` and reports a storage-related symptom: PVC Pending, a volume mount/attach failure, filesystem I/O
or read-only errors, capacity/inode exhaustion, or a workload that cannot schedule because of a PV constraint. Treat `app_name` as a named Deployment or
StatefulSet unless the user supplies `workload_type`. Read only that workload and its selector-matched Pods, then derive referenced PVCs from Pod volumes and
continue with the exact PVC/PV chain. Do not use this skill merely because an application is unhealthy without storage evidence; route general application
failures to the Pod or workload failure diagnoser instead.

Execution model:

```text
hcloud CCE/cloud storage discovery -> kubectl cce storage evidence -> optional CSI logs/cloud metrics -> cause ranking -> Markdown report
```

Do not use Python SDK dispatchers, legacy skill execution actions, old Huawei storage actions, bundled SDK scripts, kubeconfig generation, or Huawei Cloud SDK
imports.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` before
running Kubernetes commands.

## Prerequisites

1. `hcloud`, `kubectl`, and kubectl-cce are available as platform-native binaries.
2. Credentials and project context are provided through approved protected channels.
3. IAM and Kubernetes RBAC permit the required read-only cluster, storage, Event, Pod, Node, and CSI log queries.
4. If tooling is missing, use `huawei-cloud-kubectl-cce-installer`; this skill must not download or execute installers.
5. Never print credentials, tokens, headers, proxy details, storage secrets, or sensitive CSI log values.

## Related Skills

| Skill                                        | When To Use                                                                                   |
| -------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `huawei-cloud-cce-pod-failure-diagnoser`     | Pod is Pending, ContainerCreating, CrashLooping, or has FailedMount/FailedAttach events       |
| `huawei-cloud-cce-node-failure-diagnoser`    | Storage symptoms correlate with node pressure, taints, NotReady, kubelet, or per-node limits  |
| `huawei-cloud-cce-network-failure-diagnoser` | SFS/SFS Turbo/NFS or OBS access depends on network, security group, ACL, NAT, or DNS evidence |
| `huawei-cloud-cce-metric-analyzer`           | EVS/SFS/node filesystem capacity, I/O, or latency metrics are needed                          |
| `huawei-cloud-cce-root-cause-analyzer`       | Storage is one candidate in a multi-domain incident                                           |
| `huawei-cloud-cce-auto-remediation-runner`   | User-confirmed remediation preview/execution                                                  |

## Parameters

### Input Parameter Validation
This skill requires both `region` and `cluster_id` before diagnosis. It never performs a region-wide fallback. The supplied `cluster_id` must pass the following validation before any downstream query:
1. Check whether `cluster_id` is a standard UUID:
   - UUID: call `hcloud CCE ShowCluster` to verify it.
   - Otherwise: call `hcloud CCE ListClusters`, perform an exact and unique name match, convert it to a UUID, then call `ShowCluster` to verify it.
If a required `cluster_id` is missing, or any supplied `cluster_id` is invalid, unmatched, or ambiguous, stop the operation and require the user to provide the correct region and cluster ID. A supplied invalid `cluster_id` must never fall back to a global query; never guess or select a cluster. Storage diagnosis requires one explicit scope: `namespace` plus `app_name`, `namespace` plus `pvc_name`, or a specific `pv_name`. If none is supplied, stop and request the required scope; never enumerate PVCs, Pods, or PVs to choose on the user's behalf. For any other required resource identifier, first use the corresponding read-only query tool to list candidates when the user cannot provide an unambiguous value, then ask the user to choose; never select a candidate automatically.

### Input Parameters

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Request context or `HW_REGION_NAME`; otherwise ask the user. |
| `project_id` | Operation-specific | Resolve through hcloud or active credentials when needed; ask the user only when the target project cannot be determined. |
| `cluster_id` | Yes | Target CCE cluster UUID, or an exact cluster name resolved and verified through hcloud. |
| `namespace` | Required with app or PVC scope | Required with `app_name`, `pod_name`, or `pvc_name`; never use `-A`. |
| `app_name` | Optional | Application/workload name. Requires `namespace`; resolve only the named workload and its Pods. |
| `workload_type` | Optional | `deployment` or `statefulset`. Required only when `app_name` is ambiguous between workload kinds. |
| `pvc_name` | Optional | Specific PVC. |
| `pod_name` | Optional | Specific Pod with a mount or I/O symptom. |
| `pv_name` | Optional | Specific cluster-scoped PV. |
| `failure_symptom` | Recommended | `pvc_pending`, `failed_mount`, `failed_attach`, `capacity`, `readonly_fs`, `nfs_timeout`, `obs_403`, or `terminating`. |
| `volume_id` | Optional | EVS, SFS, SFS Turbo, or OBS identifier when known. |

## Region Selection

Use the region supplied by the current request or established task context. If it is absent, use `HW_REGION_NAME`. If neither source provides a region, stop and ask the user to provide `region` or set `HW_REGION_NAME`; never infer it from an hcloud profile.

## Explicit Credential Propagation

Accept `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token`. AK and SK must be supplied together; a token requires that pair. When
provided, append all supplied options to every `hcloud` and `kubectl cce` command, pass them unchanged to delegated skills, and do not use an hcloud profile
or authentication environment variables. Never print credential values.

## Core Commands And Evidence Collection

### 1. Verify Tools And Plugin

Read `references/kubectl-cce.md`, then verify platform-native tools and plugin discovery:

```bash
hcloud version
kubectl version --client
kubectl plugin list
```

If a tool or plugin is missing, stop and use `huawei-cloud-kubectl-cce-installer`. Do not download an installer or fall back to SDK or kubeconfig access.

### 2. Discover Cluster Context

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

### 3. Collect Kubernetes Storage Evidence

Collect the minimum evidence for the declared symptom. Require `namespace + app_name`, `namespace + pvc_name`, or `pv_name` before Kubernetes collection. For application scope, read the named Deployment/StatefulSet, then only its selector-matched Pods and referenced PVCs. Do not discover candidates by listing PVCs or Pods.
Never use `-A` or enumerate all cluster storage resources. Resolve identities in this order: named Pod/application -> PVC -> PV -> StorageClass -> VolumeAttachment.

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc <pvc-name> -n <namespace> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <pod-name> -n <namespace> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pv <pv-name> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get storageclass <storage-class-name> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector type=Warning --chunk-size=100 -o json
```

Keep at most 100 Warning Events and 200 CSI log lines by default. A cluster-scoped VolumeAttachment query is permitted only after a specific PV name is
resolved and must be filtered locally to that PV; if RBAC or API filtering cannot narrow the result, record a data gap instead of broadening collection.

### 4. Collect CSI Evidence

Identify the backend from the StorageClass provisioner first, then query only its corresponding CSI controller/node Pods in `kube-system`. CCE versions may
use different labels, so a bounded `kube-system` discovery query is allowed. Keep logs bounded and sanitize endpoint, credential, Secret, and mount details:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system --show-labels
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <csi-pod-name> -n kube-system -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <csi-pod-name> -n kube-system -c <csi-container-name> --tail=200
```

### 5. Collect Cloud-Side Evidence

Extract the backend identity from PV `spec.csi.volumeHandle`, CSI `volumeAttributes`, and StorageClass parameters first. Use hcloud for EVS/SFS/SFS
Turbo/OBS/VPC/security-group/ACL context only after that identity is known. If extraction is ambiguous, record a data gap; never guess a cloud resource.

## Diagnosis Workflow

1. PVC Pending/provisioning: inspect PVC conditions/events, StorageClass provisioner/parameters, access mode, volumeBindingMode, quota/capacity, and CSI
   provisioner logs.
2. Binding/topology: compare PVC, PV node affinity, Pod nodeSelector/affinity, selected node, StorageClass allowed topologies, and available zones.
3. FailedAttach/VolumeAttachment: inspect VolumeAttachment status, attachError/detachError, target node, EVS volume state, residual attachments, and per-node
   disk limits.
4. FailedMount/ContainerCreating: inspect Pod events, kubelet mount messages, Secret/ConfigMap references, filesystem type, NFS endpoint/DNS, and CSI logs.
5. Runtime I/O/capacity: inspect Pod restart/events/log hints, PVC capacity, node filesystem pressure, inode/capacity evidence, and metrics if available.
6. SFS/SFS Turbo/NFS: correlate mount timeout with DNS, route, security group, ACL, and network diagnoser evidence.
7. OBS/IAM/credential: inspect Events and CSI logs for 403, delegation, AK/SK Secret, bucket, endpoint, and policy errors without printing secrets.
8. Terminating/finalizer: inspect deletionTimestamp, finalizers, bound Pods, VolumeAttachment, and protection state. Recommend remediation only; do not remove
   finalizers.

## Output Format

The Markdown report must start with:

1. `## Summary`: likely storage root cause, affected PVC/Pod/Node, impact, confidence.
2. `## Root Cause Analysis`: ranked causes with evidence and counter-evidence.
3. `## Next Actions`: verification, mitigation, and remediation handoff.
4. `## Evidence`: PVC/PV/StorageClass/VolumeAttachment/Pod/Node/Event/CSI/cloud evidence.
5. `## Data Gaps`: missing RBAC, missing CSI logs, missing cloud volume ID, unavailable metrics, or unknown StorageClass backend.

## Best Practices

- Diagnose storage in lifecycle order: provisioning, binding, scheduling, attach, mount, runtime, and teardown.
- Correlate PVC, PV, StorageClass, VolumeAttachment, Pod, Node, CSI, and cloud volume identities.
- Keep CSI logs bounded and redact credentials, endpoints, and sensitive mount details.
- Treat missing cloud identifiers, RBAC, logs, or metrics as explicit data gaps.

## Notes And Safety Rules

Do not mutate resources. Do not run `exec`, node SSH, packet capture, stress tests, `fsck`, finalizer removal, force detach, or storage expansion from this
skill.

## Verification

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]storage|huawei[-_]get[-_]cce|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

Expected result: no executable SDK dispatcher entrypoints or bare Kubernetes access paths remain. Markdown hits should be prohibitions or verification checks
only.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: staged storage diagnosis workflow.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/risk-rules.md`: read-only boundaries and high-risk handoff rules.
