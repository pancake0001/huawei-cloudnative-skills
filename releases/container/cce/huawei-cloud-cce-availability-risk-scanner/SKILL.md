---
id: huawei-cloud-cce-availability-risk-scanner
name: huawei-cloud-cce-availability-risk-scanner
description: Scan Huawei Cloud CCE clusters for availability risks such as single replicas, missing PDBs, probe gaps, topology imbalance, gateway concentration, and resource overcommit. Trigger when users request an availability or resilience assessment.
tags: [cce, availability, risk-scanner, inspection]
---

# Huawei Cloud CCE Availability Risk Scanner

## Overview

Perform a read-only CCE availability assessment covering workload replica/PDB/probe posture, affinity and topology distribution, gateway concentration, core add-ons, and resource pressure. Results are findings and recommendations only; this skill does not change workloads, PDBs, affinity, probes, nodes, or cluster configuration.

## Dependencies And Authentication

Use `hcloud` for cloud resources and `huawei-cloud-kubectl-cce-installer` for Kubernetes reads. Prometheus/AOM checks require the cluster monitoring integration. Credentials use explicit CLI inputs first, then hcloud profile, then `HW_ACCESS_KEY`/`HW_SECRET_KEY` with optional `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Obtain `region` from input/context, then `HW_REGION_NAME`, or request it.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_scan_cce_availability_risk` | Run the complete availability scan | R3 |
| `huawei_get_kubernetes_nodes`, `huawei_list_cce_nodepools` | Inspect node and topology posture | R3 |
| `huawei_get_cce_pods`, `huawei_get_cce_deployments`, `huawei_list_cce_daemonsets`, `huawei_list_cce_statefulsets` | Inspect workload posture | R3 |
| `huawei_get_cce_services`, `huawei_get_cce_ingresses` | Inspect gateway exposure | R3 |
| `huawei_get_cce_node_metrics_topN`, `huawei_get_aom_metrics` | Inspect resource evidence | R3 |
| `huawei_list_cce_clusters` | List clusters for user selection only | R3 |

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `exclude_namespaces`, `gateway_keywords` | No | Scope workload and gateway assessment. |
| `metrics_hours`, `limit` | No | Bound metric and resource collection. |
| `cpu_limit_request_ratio`, `memory_limit_request_ratio` | No | Overcommit thresholds. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit credentials. |

### Input Parameter Validation

Validate all required parameters before execution. Validate `cluster_id` through `hcloud CCE ShowCluster` when it is a UUID; otherwise resolve one exact, unique `ListClusters` name match and validate its UUID. Missing, invalid, unmatched, or ambiguous values stop the scan. Never infer or automatically select a target cluster.

## Core Commands

```bash
python3 scripts/huawei-cloud.py huawei_scan_cce_availability_risk \
  region=<region> cluster_id=<cluster-id-or-name> metrics_hours=24
```

## Workflow

1. Validate the target cluster.
2. Gather scoped node, workload, gateway, and metric evidence.
3. Classify availability risks with supporting observations and data gaps.
4. Return recommendations only; send any change to its dedicated change-management skill.

## Notes

- Kubernetes reads require a specific namespace or named resource; do not use `-A`.
- Retry a `kubectl cce` x509 upstream failure with `--cce-insecure-upstream-tls=true`.
- A lack of active alarms is not a health verdict; historical and resource evidence remain relevant.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
