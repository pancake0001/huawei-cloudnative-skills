---
id: huawei-cloud-cce-cost-optimization-advisor
name: huawei-cloud-cce-cost-optimization-advisor
description: Analyze Huawei Cloud CCE cost optimization opportunities from utilization, oversized requests, idle nodes, and autoscaling posture. Trigger when users request cost or resource-efficiency advice.
tags: [cce, cost-optimization, utilization, autoscaling]
---

# Huawei Cloud CCE Cost Optimization Advisor

## Overview

Provide read-only CCE cost-efficiency findings from node utilization, workload requests, HPA coverage, and node-pool autoscaling posture. Recommendations and generated manifests are advisory only: the skill does not modify HPA, node pools, workloads, or cloud resources.

## Dependencies And Authentication

Use `hcloud` for cloud discovery and cluster validation; use `huawei-cloud-kubectl-cce-installer` for scoped Kubernetes reads. AOM Prometheus data requires the monitoring integration. Explicit CLI credentials take precedence; otherwise use hcloud profile then `HW_ACCESS_KEY`/`HW_SECRET_KEY`, with optional `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Resolve `region` from input/context, then `HW_REGION_NAME`, or ask for it.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_analyze_cce_cost_optimization` | Analyze cost-efficiency opportunities | R3 |
| `huawei_list_cce_clusters`, `huawei_list_cce_nodes`, `huawei_get_kubernetes_nodes`, `huawei_list_cce_nodepools` | Collect node and pool inventory | R3 |
| `huawei_get_cce_pods`, `huawei_get_cce_deployments`, `huawei_list_cce_hpas` | Collect workload request and autoscaling posture | R3 |
| `huawei_get_cce_node_metrics_topN`, `huawei_get_cce_node_metrics`, `huawei_get_cce_pod_metrics_topN`, `huawei_get_cce_pod_metrics`, `huawei_get_aom_metrics` | Query usage evidence | R3 |
| `huawei_generate_cce_hpa_manifest`, `huawei_generate_monitor_dashboard` | Generate local advisory artifacts | R3 |

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `short_hours`, `long_hours`, `top_n` | No | Utilization analysis windows and result size. |
| `exclude_namespaces`, `business_namespaces` | No | Workload scope. |
| `hpa_*` | No | Values used only in a generated HPA recommendation. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit credentials. |

### Input Parameter Validation

Required `region` and `cluster_id` must be supplied. Validate UUIDs with `hcloud CCE ShowCluster`; otherwise resolve exactly one name using `hcloud CCE ListClusters` and then verify its UUID. Invalid, unmatched, ambiguous, or missing input stops the operation. Never broaden the analysis to another cluster.

## Core Commands

```bash
python3 scripts/huawei-cloud.py huawei_analyze_cce_cost_optimization \
  region=<region> cluster_id=<cluster-id-or-name> short_hours=24 long_hours=168
```

## Workflow

1. Validate the target cluster.
2. Collect only scoped inventory and metric evidence.
3. Identify utilization/request patterns and explain confidence or missing data.
4. Return advisory optimization options without applying changes.

## Notes

- Findings are utilization signals, not billing invoices or guaranteed savings.
- Kubernetes reads require a namespace or named resource; do not use `-A`.
- Retry `kubectl cce` x509 upstream failures with `--cce-insecure-upstream-tls=true`.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
