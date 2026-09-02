---
id: huawei-cloud-cce-daily-cluster-inspector
name: huawei-cloud-cce-daily-cluster-inspector
description: Run read-only Huawei Cloud CCE daily health checks, quick checks, inspections, and evidence summaries. Trigger when users request cluster inspection or health verification.
tags: [cce, inspection, health-check, daily]
---

# Huawei Cloud CCE Daily Cluster Inspector

## Overview

Perform periodic, low-risk CCE health inspections. Start with a quick check and gather deeper read-only evidence only when observations warrant it. The skill never remediates, scales, drains, restarts, or changes cluster resources.

## Dependencies And Authentication

Use `hcloud` for cluster and cloud evidence. Use `huawei-cloud-kubectl-cce-installer` for Kubernetes resources, with namespace- or resource-scoped reads. AOM and Prometheus checks require the monitoring integration. Explicit CLI credentials take precedence, then hcloud profile, then `HW_ACCESS_KEY`/`HW_SECRET_KEY` with optional `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Resolve region from input/context, then `HW_REGION_NAME`, or ask the user.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_cce_quick_check`, `huawei_cce_auto_inspection`, `huawei_cce_deep_diagnosis` | Run staged health inspection | R3 |
| `huawei_cce_cluster_inspection`, `huawei_cce_cluster_inspection_parallel` | Run detailed inspection | R3 |
| `huawei_pod_status_inspection`, `huawei_node_status_inspection`, `huawei_node_resource_inspection` | Inspect resource health | R3 |
| `huawei_event_inspection`, `huawei_aom_alarm_inspection`, `huawei_elb_monitoring_inspection` | Inspect event and monitoring evidence | R3 |
| `huawei_aggregate_inspection_results`, `huawei_export_inspection_report` | Produce local inspection reports | R3 |

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `thresholds`, `hours`, `top_n` | No | Inspection scope and thresholds. |
| `namespace`, `business_labels`, `elb_ids` | No | Limit evidence collection. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit credentials. |

### Input Parameter Validation

Validate required parameters before execution. A UUID `cluster_id` is verified with `hcloud CCE ShowCluster`; a name must exactly and uniquely resolve through `hcloud CCE ListClusters`, then its UUID is verified. Missing, invalid, unmatched, or ambiguous values stop inspection. Never infer or substitute a cluster.

## Core Commands

```bash
python3 scripts/huawei-cloud.py huawei_cce_quick_check \
  region=<region> cluster_id=<cluster-id-or-name>
```

## Workflow

1. Validate region and cluster.
2. Run a quick check first.
3. Collect deeper evidence only for observed anomalies.
4. Report findings, historical context, data gaps, and recommended handoff; do not remediate.

## Notes

- Do not conclude the cluster is healthy solely because no active alarm exists; include event/history evidence.
- Kubernetes reads must specify a namespace or named resource; do not use `-A`.
- Retry a `kubectl cce` x509 upstream failure with `--cce-insecure-upstream-tls=true`.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
