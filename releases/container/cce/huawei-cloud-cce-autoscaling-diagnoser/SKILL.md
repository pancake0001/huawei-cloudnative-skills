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

Use `hcloud` for cloud resources and cluster validation. Use `huawei-cloud-kubectl-cce-installer` for Kubernetes reads. Prometheus/AOM evidence requires the cluster monitoring integration.

Credential priority is explicit tool input, then local hcloud profile, then `HW_ACCESS_KEY`/`HW_SECRET_KEY`, with optional `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Use `--cli-access-key`, `--cli-secret-key`, and optionally `--cli-security-token` together for caller-supplied credentials; they are forwarded to `hcloud` and `kubectl cce`. Resolve `region` from input/context, then `HW_REGION_NAME`, or request it.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_autoscaling_diagnose` | Run end-to-end autoscaling diagnosis | R3 |
| `huawei_list_cce_hpas` | Inspect HPA objects | R3 |
| `huawei_list_cce_addons`, `huawei_get_cce_addon_detail` | Inspect autoscaling and metrics add-ons | R3 |
| `huawei_list_cce_nodepools`, `huawei_get_kubernetes_nodes` | Inspect node pool and node capacity evidence | R3 |
| `huawei_get_cce_pods`, `huawei_get_cce_deployments`, `huawei_list_cce_statefulsets`, `huawei_get_cce_events` | Inspect workload and scheduling evidence | R3 |
| `huawei_get_cce_pod_metrics_topN`, `huawei_get_cce_node_metrics_topN`, `huawei_get_aom_metrics` | Inspect metric evidence | R3 |

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `namespace` | No | Limit workload evidence to one namespace. |
| `workload_name`, `workload_type` | No | Narrow diagnosis to one workload. |
| `target`, `scale_direction`, `question` | No | State the suspected HPA/CA path and symptom. |
| `hours`, `top_n`, `event_limit` | No | Limit metric/event collection volume. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit permanent or temporary credentials. |

### Input Parameter Validation

Required parameters must be present before execution. `cluster_id` is validated before any diagnostic query: a UUID is checked with `hcloud CCE ShowCluster`; a non-UUID must exactly and uniquely match a name from `hcloud CCE ListClusters`, then the resolved UUID is checked. Missing, invalid, unmatched, or ambiguous values stop the operation. Never guess a cluster or broaden to another cluster.

## Core Commands

```bash
python3 scripts/huawei-cloud.py huawei_autoscaling_diagnose \
  region=<region> cluster_id=<cluster-id-or-name> namespace=<namespace>
```

## Workflow

1. Validate `region` and `cluster_id`.
2. Collect only evidence relevant to the requested HPA or node-autoscaling path.
3. Correlate HPA, pending/scheduling, node-pool, add-on, event, and metric evidence.
4. Return findings, confidence, data gaps, and non-mutating recommendations.

## Notes

- Kubernetes reads must use a specific namespace or named resource; do not use `-A` for whole-cluster collection.
- If `kubectl cce` reports an x509 upstream error, retry with `--cce-insecure-upstream-tls=true`.
- No active alarm does not prove the autoscaling path is healthy; inspect historical events and collected evidence as well.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
