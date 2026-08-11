---
id: huawei-cloud-cce-storage-failure-diagnoser
name: huawei-cloud-cce-storage-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE storage failures with hcloud CLI for cluster/cloud storage metadata and kubectl-cce plugin commands for read-only PVC, PV, StorageClass, Pod, Node, Event, VolumeAttachment, and CSI log evidence. Use this skill for PVC Pending, provisioning failures, PV/PVC binding issues, EVS topology conflicts, VolumeAttachment attach failures, FailedMount, SFS/SFS Turbo NFS timeout, OBS 403 or credential errors, runtime IO errors, read-only filesystem, capacity or inode exhaustion, subPath mount deadlocks, PVC Terminating protection, and Markdown storage diagnosis reports. Do not use Python SDK dispatcher actions.
tags: [cce, storage-diagnosis, evs, pvc, fault-diagnosis, hcloud, kubectl-cce]
---

# Huawei Cloud CCE Storage Failure Diagnoser

This skill diagnoses CCE/Kubernetes storage failures across provisioning, binding, scheduling, attach/mount, runtime I/O, capacity, permission, and teardown stages.

Execution model:

```text
hcloud CCE/cloud storage discovery -> kubectl cce storage evidence -> optional CSI logs/cloud metrics -> cause ranking -> Markdown report
```

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, `huawei_storage_*`, `huawei_get_cce_*`, bundled SDK scripts, kubeconfig generation, or Huawei Cloud SDK imports.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` before running Kubernetes commands.

## Related Skills

| Skill | When To Use |
| --- | --- |
| `huawei-cloud-cce-pod-failure-diagnoser` | Pod is Pending, ContainerCreating, CrashLooping, or has FailedMount/FailedAttach events |
| `huawei-cloud-cce-node-failure-diagnoser` | Storage symptoms correlate with node pressure, taints, NotReady, kubelet, or per-node limits |
| `huawei-cloud-cce-network-failure-diagnoser` | SFS/SFS Turbo/NFS or OBS access depends on network, security group, ACL, NAT, or DNS evidence |
| `huawei-cloud-cce-metric-analyzer` | EVS/SFS/node filesystem capacity, I/O, or latency metrics are needed |
| `huawei-cloud-cce-root-cause-analyzer` | Storage is one candidate in a multi-domain incident |
| `huawei-cloud-cce-auto-remediation-runner` | User-confirmed remediation preview/execution |

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Required by kubectl-cce and hcloud cloud-resource commands |
| `cluster_id` | Preferred | Resolve by name with hcloud if absent |
| `namespace` | Recommended | Needed for PVC/Pod scope |
| `pvc_name` | Optional | Specific PVC |
| `pod_name` | Optional | Specific Pod with mount or I/O symptom |
| `failure_symptom` | Recommended | `pvc_pending`, `failed_mount`, `failed_attach`, `capacity`, `readonly_fs`, `nfs_timeout`, `obs_403`, `terminating` |
| `volume_id` | Optional | EVS/SFS/SFS Turbo/OBS identifier when known |

## Collection

1. Discover cluster context:

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

2. Collect Kubernetes storage evidence through kubectl-cce:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc,pv,storageclass,volumeattachments -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

3. Collect CSI evidence when RBAC allows. Keep logs bounded and sanitized:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system -l app=everest-csi-driver -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs -n kube-system -l app=everest-csi-driver --tail=200
```

4. Collect cloud-side read-only evidence only when identifiers are known or safely derived. Use hcloud for EVS/SFS/SFS Turbo/OBS/VPC/security-group/ACL context and metric skills for time-series evidence. If an operation name or identifier is uncertain, run help or record a data gap.

## Diagnosis Workflow

1. PVC Pending/provisioning: inspect PVC conditions/events, StorageClass provisioner/parameters, access mode, volumeBindingMode, quota/capacity, and CSI provisioner logs.
2. Binding/topology: compare PVC, PV node affinity, Pod nodeSelector/affinity, selected node, StorageClass allowed topologies, and available zones.
3. FailedAttach/VolumeAttachment: inspect VolumeAttachment status, attachError/detachError, target node, EVS volume state, residual attachments, and per-node disk limits.
4. FailedMount/ContainerCreating: inspect Pod events, kubelet mount messages, Secret/ConfigMap references, filesystem type, NFS endpoint/DNS, and CSI logs.
5. Runtime I/O/capacity: inspect Pod restart/events/log hints, PVC capacity, node filesystem pressure, inode/capacity evidence, and metrics if available.
6. SFS/SFS Turbo/NFS: correlate mount timeout with DNS, route, security group, ACL, and network diagnoser evidence.
7. OBS/IAM/credential: inspect Events and CSI logs for 403, delegation, AK/SK Secret, bucket, endpoint, and policy errors without printing secrets.
8. Terminating/finalizer: inspect deletionTimestamp, finalizers, bound Pods, VolumeAttachment, and protection state. Recommend remediation only; do not remove finalizers.

## Output Requirements

The Markdown report must start with:

1. `## Summary`: likely storage root cause, affected PVC/Pod/Node, impact, confidence.
2. `## Root Cause Analysis`: ranked causes with evidence and counter-evidence.
3. `## Next Actions`: verification, mitigation, and remediation handoff.
4. `## Evidence`: PVC/PV/StorageClass/VolumeAttachment/Pod/Node/Event/CSI/cloud evidence.
5. `## Data Gaps`: missing RBAC, missing CSI logs, missing cloud volume ID, unavailable metrics, or unknown StorageClass backend.

Do not mutate resources. Do not run `exec`, node SSH, packet capture, stress tests, `fsck`, finalizer removal, force detach, or storage expansion from this skill.

## Verification

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_storage|huawei_get_cce_|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

Expected result: no executable SDK dispatcher entrypoints or bare Kubernetes access paths remain. Markdown hits should be prohibitions or verification checks only.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: staged storage diagnosis workflow.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/risk-rules.md`: read-only boundaries and high-risk handoff rules.
