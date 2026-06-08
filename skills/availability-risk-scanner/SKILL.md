---
name: availability-risk-scanner
description: Use this skill for Huawei Cloud CCE availability risk scanning, including master HA and utilization, node and workload AZ balance, single replicas, missing PodDisruptionBudgets, health probes, unreasonable affinity or nodepool pinning, core addon anti-affinity, gateway workload distribution, and request/limit overcommit.
---

# availability-risk-scanner

You are responsible for scanning CCE clusters for availability risks. By default, perform only read-only checks, report output, and remediation planning. Do not directly modify workloads, PDBs, affinity rules, probes, node pools, or cluster configuration.

# Processing Steps

1. Collect `region`, `cluster_id`, excluded namespaces, and gateway keywords. Exclude ordinary application risks in `kube-system` by default, but still inspect core add-ons such as CoreDNS and nginx-ingress.
2. Prefer `huawei_scan_cce_availability_risk` for the combined scan. Pass `output_dir` when an audit trail is needed.
3. Check control plane visibility, master HA, master CPU/memory metrics, node AZ distribution, and node pool distribution.
4. Check Deployment, StatefulSet, and DaemonSet replicas, PDBs, Pod distribution, health probes, affinity, anti-affinity, topology spread, and resource requests/limits.
5. Pay special attention to gateway workloads such as nginx, gateway, ingress, proxy, kong, apisix, and traefik.
6. Output the report, risk levels, remediation recommendations, and an authorized execution plan. Real remediation requires explicit customer authorization first.

# # References

- Read `references/workflow.md` for the scan process, judgment rules, and manual review points.
- Read `references/risk-rules.md` for remediation authorization, safety boundaries, and prohibited actions.
- Read `references/output-schema.md` for the output structure.

# Recommended Action

Combined scan: `huawei_scan_cce_availability_risk`.

Supplemental queries: `huawei_get_kubernetes_nodes`, `huawei_get_cce_pods`, `huawei_get_cce_deployments`, `huawei_get_cce_services`, `huawei_get_cce_ingresses`, `huawei_list_cce_nodepools`, `huawei_list_cce_daemonsets`, `huawei_list_cce_statefulsets`, `huawei_get_cce_node_metrics_topN`.

# Risk Boundaries

This skill does not automatically scale replicas, create PDBs, modify probes, adjust affinity, migrate nodes, or scale node pools. It may generate remediation plans, YAML recommendations, and validation checklists. Remediation execution requires explicit user authorization and must be handed off to a write-capable action or a manual change process.
