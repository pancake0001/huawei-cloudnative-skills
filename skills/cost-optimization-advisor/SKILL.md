---
name: cost-optimization-advisor
description: Use this skill for Huawei Cloud CCE cost optimization analysis, including idle resources, oversized CPU or memory requests, low-utilization nodes, 24-hour and 7-day utilization trends, HPA recommendations, and node autoscaler policy optimization.
---

# cost-optimization-advisor

You are responsible for analyzing cost optimization opportunities for CCE clusters. By default, only read-only analysis and configuration recommendations are made, and HPA, autoscaler, node pool or workload are not directly modified.

# # Processing steps

1. Collect region, cluster_id, namespace range and business exclusion rules; `kube-system` is excluded by default.
2. Analyze the node CPU/memory usage in two windows of 24 hours and 7 days respectively.
3. Mark low utilization nodes: significantly lower than the average cluster node usage, or the cluster average CPU/memory is lower than 30%.
4. Analyze the difference between requests and actual usage of non-kube-system workloads and identify excessive requests.
5. Check the node pool autoscaling information and use `huawei_list_cce_hpas` to check the business namespace HPA.
6. If HPA is required, first use `huawei_generate_cce_hpa_manifest` or `huawei_configure_cce_hpa` without `confirm=true` to generate a preview; configuration is allowed only after the user explicitly confirms.
7. Output optimization suggestions, expected impacts, risks and configuration strategies; when real configuration is required, the confirmation process must be followed.

# # References

- Thresholds, windows and analysis steps read `references/workflow.md`.
- For scaling, HPA/autoscaler configuration and security boundaries read `references/risk-rules.md`.
- Output cost optimization report as per `references/output-schema.md`.

# # Recommended action

Combination analysis: Prioritize using `huawei_analyze_cce_cost_optimization` to complete resource inventory, 24h/7d node utilization, business Pod usage/request, HPA/autoscaler status and report output in one go.

Resource list: `huawei_list_cce_nodes`, `huawei_list_cce_nodepools`, `huawei_get_cce_pods`, `huawei_get_cce_deployments`, `huawei_list_cce_hpas`.

Indicator analysis: `huawei_get_cce_node_metrics_topN`, `huawei_get_cce_node_metrics`, `huawei_get_cce_pod_metrics_topN`, `huawei_get_cce_pod_metrics`, `huawei_get_aom_metrics`.

Elastic policy: `huawei_generate_cce_hpa_manifest`, `huawei_configure_cce_hpa`. `huawei_configure_cce_hpa` only returns a preview by default, and `confirm=true` can be set only after the user explicitly confirms it.

Chart: `huawei_generate_monitor_dashboard`.

# # Risk constraints

This skill does not automatically scale down, modify requests, or automatically install or update HPA/autoscaler. YAML, parameter suggestions and execution plans can be generated; the real configuration must be explicitly confirmed by the user before calling the execution action with `confirm=true`.