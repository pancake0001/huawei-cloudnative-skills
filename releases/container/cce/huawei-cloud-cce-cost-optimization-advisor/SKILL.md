---
id: huawei-cloud-cce-cost-optimization-advisor
name: huawei-cloud-cce-cost-optimization-advisor
description: Analyze Huawei Cloud CCE resource-cost allocation: cluster and node-pool capacity, allocated Requests, redundancy reserve, namespace cost share, actual usage, and autoscaling posture. Trigger when users request cost or resource-efficiency advice.
tags: [cce, cost-optimization, utilization, autoscaling]
---

# Huawei Cloud CCE Cost Optimization Advisor

## Overview

Provide a read-only CCE resource-cost view from cluster and node-pool CPU, memory, and GPU capacity; node-bound Pod Requests; redundancy reserve; allocation rate; and namespace-level allocation, actual usage, and Request adequacy. Capacity is the resource-cost baseline, allocated Requests represent in-use resource cost, and unallocated capacity is intentional redundancy for failures and bursts; the skill does not treat these capacity values as currency charges. The combined analysis uses AOM Prometheus metrics first, so it does not enumerate every Pod or workload through the Kubernetes API. Recommendations and generated manifests are advisory only: the skill does not modify HPA, node pools, workloads, or cloud resources.

## Dependencies And Authentication

Use `hcloud` for cloud discovery and cluster validation; use `huawei-cloud-kubectl-cce-installer` for scoped Kubernetes reads. AOM Prometheus data requires the monitoring integration. Explicit CLI credentials take precedence; otherwise use hcloud profile then `HW_ACCESS_KEY`/`HW_SECRET_KEY`, with optional `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Resolve `region` from input/context, then `HW_REGION_NAME`, or ask for it.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_analyze_cce_cost_optimization` | Run the combined cluster capacity, Requests allocation, namespace usage, elasticity, trend, and cost-efficiency analysis | R3 |
| `huawei_generate_cce_cost_optimization_report` | Run the analysis and generate an HTML and/or Markdown cost-optimization report with cluster and namespace resource trends | R3 |
| `huawei_generate_cce_hpa_manifest` | Generate a local advisory HPA YAML artifact | R3 |

CCE, AOM, hcloud, and scoped Kubernetes data collection are internal implementation details of the combined analysis and are not exposed as standalone tools.

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `analysis_days`, `analysis_date`, `top_n` | No | Number of completed calendar days to analyze (`1`-`7`, default `1`), one exact calendar day in `YYYY-MM-DD` form, and namespace result limit. The range always ends at today `00:00` in `Asia/Shanghai`; `analysis_date` is only valid with `analysis_days=1`. |
| `exclude_namespaces` | No | Comma-separated namespaces excluded from namespace allocation and usage analysis. Default: none; system namespaces are displayed for visibility. |
| `output_file`, `output_format` | No | Local report path and output type for `huawei_generate_cce_cost_optimization_report`. `output_format` is `html` (default), `markdown`, or `both`. HTML reports embed interactive trend charts; Markdown reports present self-contained summary tables plus six-hour cluster and namespace trend tables. Without `output_file`, files are written under `/tmp`. |
| `hpa_*` | No | Values used only in a generated HPA recommendation. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit credentials. |

### Input Parameter Validation

Required `region` and `cluster_id` must be supplied. Validate UUIDs with `hcloud CCE ShowCluster`; otherwise resolve exactly one name using `hcloud CCE ListClusters` and then verify its UUID. Invalid, unmatched, ambiguous, or missing input stops the operation. Never broaden the analysis to another cluster.

## Core Commands

```bash
python3 scripts/huawei-cloud.py huawei_analyze_cce_cost_optimization \
  region=<region> cluster_id=<cluster-id-or-name> analysis_days=7 top_n=20

# Generate a Markdown report
python3 scripts/huawei-cloud.py huawei_generate_cce_cost_optimization_report \
  region=<region> cluster_id=<cluster-id-or-name> output_format=markdown \
  output_file=/tmp/cce-cost-report.md
```

## Workflow

1. Validate the target cluster.
2. Use the cluster's AOM Prometheus instance to collect completed calendar days in `Asia/Shanghai` (default: the previous day; optional: the preceding `2`-`7` days, all ending at today `00:00:00`): allocatable capacity and Pod Requests start/end/minimum/maximum/average/change trends, namespace Requests trends, namespace actual usage, cluster usage trends, and HPA metric coverage. Trends return start, minimum, maximum, and end key points rather than every five-minute sample. Do not base capacity conclusions on a final-sample snapshot.
3. Use hcloud to collect node-pool autoscaling configuration and current node counts.
4. At each aligned Prometheus sampling point, use node-bound Requests to calculate cluster and node-pool allocation rate and free reserve. For each namespace, show allocated Requests and actual usage as a percentage of total allocatable capacity, then assess actual usage against Requests. A non-system namespace whose usage exceeds Requests is under-requested and should be reviewed for a Request increase; a namespace that remains well below Requests is over-requested and can be reviewed for a reduction. Report declared and Pending Pod Requests separately.
5. Return advisory optimization options without applying changes. Potential savings are capacity estimates, not billing estimates.

## Notes

- AOM Prometheus must receive CCE monitoring data; missing metric families are returned as data gaps.
- Allocation, namespace cost share, Request adequacy, and rightsizing findings are all derived from Pod `requests`. If workloads omit `requests` or configure them unrealistically, the resulting allocation and optimization assessment is correspondingly inaccurate and must be treated as a data-quality limitation.
- GPU analysis discovers allocatable resource names that contain `gpu`, then analyzes their bound/Pending Requests, reserve, and allocation trends. Actual GPU usage requires AOM collection of `cce_gpu_*` or `xgpu_*` metrics; a non-GPU cluster is not treated as a data gap.
- `kube-system` and `monitoring` are system namespaces. Their allocation and usage may be reported for visibility, but they never receive oversized-request findings, rightsizing estimates, or cost-reduction recommendations.
- Findings are utilization signals, not billing invoices or guaranteed savings.
- Kubernetes reads require a namespace or named resource; do not use `-A`.
- Retry `kubectl cce` x509 upstream failures with `--cce-insecure-upstream-tls=true`.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
