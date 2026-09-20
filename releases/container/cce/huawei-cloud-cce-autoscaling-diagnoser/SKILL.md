---
id: huawei-cloud-cce-autoscaling-diagnoser
name: huawei-cloud-cce-autoscaling-diagnoser
description: Diagnose Huawei Cloud CCE autoscaling failures for HPA, Cluster Autoscaler, pending Pods, node pools, metrics, quotas, and scheduling constraints. Trigger when users report HPA or node autoscaling failures.
tags: [cce, autoscaling, hpa, diagnosis]
---

# Huawei Cloud CCE Autoscaling Diagnoser

## Overview

Diagnose read-only evidence for workload and node autoscaling failures: HPA state, Cluster Autoscaler/add-on status, Pending Pods, scheduling events, node-pool limits, and available metrics. The skill never changes HPA, node pools, workloads, or cloud resources.

## Dependencies And Authentication

Use `hcloud` for CCE cloud resources and cluster validation. Use `huawei-cloud-kubectl-cce-installer` for Kubernetes reads. AOM Prometheus evidence remains an authenticated AOM query and requires the cluster monitoring integration.

Credential priority is explicit tool input, then local hcloud profile, then `HW_ACCESS_KEY`/`HW_SECRET_KEY`, with optional `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Use `--cli-access-key`, `--cli-secret-key`, and optionally `--cli-security-token` together for caller-supplied credentials; they are forwarded to `hcloud` and `kubectl cce`. `kubectl cce` must receive credentials through these CLI inputs or its supported `HW_*` environment variables; an hcloud profile alone may not satisfy the plugin. Resolve `region` from input/context, then `HW_REGION_NAME`, or request it.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_diagnose_cce_hpa_autoscaling` | Diagnose HPA metric, Condition, metric APIService, behavior policy, target workload, Request, replica-limit, and related-event failures | R3 |
| `huawei_diagnose_cce_cluster_autoscaler` | Diagnose Cluster Autoscaler, Pending Pod, scheduling, node-pool bounds, PDB/eviction blockers, and autoscaler-log failures | R3 |

HPA, add-on, node-pool, Pod, workload, Event, PDB, autoscaler-log, and AOM metric collection are internal evidence sources and are not exposed as standalone tools.

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `namespace` | Yes | Namespace containing the target workload, HPA, or Pending Pods. |
| `hpa_name` | HPA diagnosis only | Narrow HPA diagnosis to one HPA in the supplied namespace. When combined with `workload_name`, the HPA must target that workload. |
| `workload_name`, `workload_type` | HPA diagnosis only | Narrow diagnosis to the HPA targeting one workload. |
| `scale_direction`, `question` | No | For Cluster Autoscaler diagnosis, specify `scale_up` or `scale_down` and describe the symptom. |
| `hours` | No | Prometheus evidence window in hours. Default `1`; allowed range `1`-`24`. HPA usage evidence includes the latest, maximum, and average value in this window. |
| `event_limit` | No | Maximum Warning Events retained for the namespace. Default `200`; allowed range `1`-`500`. Event requests use server-side Warning filtering and bounded chunks. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit permanent or temporary credentials. |

### Input Parameter Validation

Required parameters must be present before execution. `cluster_id` is validated before any diagnostic query: a UUID is checked with `hcloud CCE ShowCluster`; a non-UUID must exactly and uniquely match a name from `hcloud CCE ListClusters`, then the resolved UUID is checked. Missing, invalid, unmatched, or ambiguous values stop the operation. Never guess a cluster or broaden to another cluster. Kubernetes reads require the supplied `namespace`; whole-cluster reads are not supported. `hours` must be `1`-`24`, `event_limit` must be `1`-`500`, and boolean parameters must be `true` or `false`.

## Core Commands

```bash
# HPA diagnosis
python3 scripts/huawei-cloud.py huawei_diagnose_cce_hpa_autoscaling \
  region=<region> cluster_id=<cluster-id-or-name> namespace=<namespace> \
  hpa_name=<hpa-name>

# Cluster Autoscaler and node-pool diagnosis
python3 scripts/huawei-cloud.py huawei_diagnose_cce_cluster_autoscaler \
  region=<region> cluster_id=<cluster-id-or-name> namespace=<namespace> \
  scale_direction=scale_up
```

## Workflow

1. Validate `region` and `cluster_id`.
2. The HPA tool executes only the HPA diagnostic path; the Cluster Autoscaler tool executes only the node-autoscaling diagnostic path.
3. Correlate HPA, pending/scheduling, node-pool, add-on, event, and metric evidence. HPA diagnosis includes only Normal events bound to the selected HPA (for example `SuccessfulRescale`) in addition to namespace Warning events. CPU and memory usage are aggregated by the target workload selector through `kube_pod_labels`; when that metric is unavailable, the tool falls back to the already collected target Pod set without issuing per-Pod metric requests.
4. Return findings, confidence, data gaps, and non-mutating recommendations.

## Notes

- Kubernetes reads must use a specific namespace or named resource; do not use `-A` for whole-cluster collection. When HPA diagnosis receives `hpa_name` or `workload_name`, it reads the named HPA and its target Deployment/StatefulSet, then reads Pods through that workload's selector instead of listing all namespace Pods. Cluster Autoscaler scale-up diagnosis first verifies that the AOM Prometheus Pod-phase metric exists, then queries Pending Pods and the standard CA unschedulable-Pod metric. Only when the Pod-phase metric is confirmed does it avoid a Pod list; otherwise it falls back to a server-filtered `status.phase=Pending` Pod query. Events are server-filtered with `type=Warning`; scale-down or an unspecified direction additionally reads scoped Pod/PDB state for eviction blockers.
- HPA diagnosis parses Resource, Pods, Object, and External metric entries; it verifies only the APIService required by the configured metric types and reports API access failures as data gaps or metric-path issues. For CPU/Memory utilization HPA, it also queries the target Pod set's aggregate usage divided by aggregate Request, rather than a TopN subset.
- HPA `spec.behavior` is evaluated for disabled scale directions and stabilization windows. A configured window is evidence for delayed scaling, not by itself a fault.
- If `kubectl cce` reports an x509 upstream error, retry with `--cce-insecure-upstream-tls=true`.
- No active alarm does not prove the autoscaling path is healthy; inspect historical events and collected evidence as well.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
