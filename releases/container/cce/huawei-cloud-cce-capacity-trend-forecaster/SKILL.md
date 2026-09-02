---
id: huawei-cloud-cce-capacity-trend-forecaster
name: huawei-cloud-cce-capacity-trend-forecaster
description: Analyze Huawei Cloud CCE capacity trends, forecast CPU, memory, and disk bottlenecks, and recommend non-mutating capacity actions. Trigger when users ask for capacity trends, forecasts, or planning.
tags: [cce, capacity, forecast, trend]
---

# Huawei Cloud CCE Capacity Trend Forecaster

## Overview

Analyze CCE CPU, memory, and disk trends across a selected time window; calculate p95 and slope, project bottleneck timing, and provide capacity/HPA recommendations. It is read-only: generated HPA manifests are previews and no configuration is applied.

## Dependencies And Authentication

Use `hcloud` for cloud resource discovery and cluster validation. Use `huawei-cloud-kubectl-cce-installer` for named or namespace-scoped Kubernetes reads. AOM Prometheus data requires the CCE monitoring integration and enough retained history for a meaningful forecast.

Explicit `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token` take precedence and are forwarded to CLI calls. Otherwise use hcloud profile then `HW_ACCESS_KEY`/`HW_SECRET_KEY`, optionally `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Resolve `region` from input/context, then `HW_REGION_NAME`, or ask the user.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_analyze_cce_capacity_trend` | Analyze trends and forecast capacity bottlenecks | R3 |
| `huawei_list_cce_clusters`, `huawei_get_kubernetes_nodes`, `huawei_list_cce_nodepools` | Collect cluster capacity inventory | R3 |
| `huawei_get_cce_deployments`, `huawei_list_cce_hpas` | Review workload autoscaling posture | R3 |
| `huawei_get_cce_node_metrics_topN`, `huawei_get_aom_metrics` | Query metric evidence | R3 |
| `huawei_generate_cce_hpa_manifest` | Generate a non-applying HPA preview | R3 |

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `hours`, `step_seconds`, `top_n` | No | Forecast window and data granularity. |
| `target_cpu_percent`, `target_memory_percent`, `bottleneck_percent`, `headroom_percent` | No | Forecast thresholds. |
| `exclude_namespaces`, `business_namespaces` | No | Workload scope. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit credentials. |

### Input Parameter Validation

All required parameters must be supplied. Before any query, validate a UUID `cluster_id` with `hcloud CCE ShowCluster`; otherwise exact-match a single cluster name with `hcloud CCE ListClusters` and verify the resolved UUID. Missing, invalid, unmatched, or ambiguous values stop execution; do not choose another cluster.

## Core Commands

```bash
python3 scripts/huawei-cloud.py huawei_analyze_cce_capacity_trend \
  region=<region> cluster_id=<cluster-id-or-name> hours=168
```

## Workflow

1. Validate region and cluster.
2. Collect scoped capacity inventory and time-series metrics.
3. Produce trend statistics, forecast confidence, bottleneck projections, and data-quality gaps.
4. Return recommendations and optional manifest previews without applying them.

## Notes

- Forecasts are estimates, not capacity guarantees; missing or short metric history lowers confidence.
- Kubernetes reads must specify a namespace or resource; avoid `-A`.
- Retry `kubectl cce` x509 upstream failures with `--cce-insecure-upstream-tls=true`.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
