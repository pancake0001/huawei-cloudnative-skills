# Workflow

# # 1. Collection range

Prioritize using `huawei_analyze_cce_cost_optimization` as the combined action; only when you need to add details, review individual indicators, or manually generate specific HPA YAML, call the lower-level actions below.

1. Confirm the region, cluster_id, namespace range, business exclusion rules and statistics window.
2. Pods and workloads under `kube-system` are excluded by default; other namespaces are processed according to business loads unless otherwise excluded by the user.
3. Pull node, node pool, Pod, Deployment and indicator data.
4. Check both 24-hour and 7-day windows for all utilization class judgments.

# # 2. Idle resources and low utilization nodes

Calculate separately for each window:

- cluster_cpu_avg = Average CPU usage of all Ready nodes.
- cluster_mem_avg = Average memory usage of all Ready nodes.
- node_cpu_avg / node_mem_avg = Single node average usage.

Trigger tips:

- The average CPU or memory usage of the cluster is less than 30%, indicating that the overall resources may be excessive.
- Prompt when the CPU or memory usage of a single node is significantly lower than the cluster average. The default judgment is: 20 percentage points below the cluster average, or 60% below the cluster average.
- If the node low utilization only occurs for 24 hours and is not obvious for 7 days, it is marked as a short-term fluctuation; when both windows are hit, it is marked as a stable optimization opportunity.

Output suggestions:

- It is recommended to adjust the node pool min/max, enable scale down, optimize scheduling and load balancing.
- Immediate deletion of nodes is not directly recommended unless there is clear redundancy and the user requires an execution plan.

# # 3. Excessive Request

Only analyze non-kube-system workloads.

Compare each business workload separately:

- CPU request vs 24 hour and 7 day actual CPU p95/avg.
- Memory request vs 24 hours and 7 days actual memory p95/avg.

Trigger tips:

- request is greater than 2 times actual p95 and holds for both windows, marked as stable excess.
- request is 3 times larger than actual p95, marked as high priority optimization.
- It is only marked as an observation item when hit for 24 hours, and it is not recommended to change the request immediately.

If the request field is missing from the existing action return, the user is required to supplement the Deployment/Pod YAML or obtain it through subsequent tool extensions; do not directly give the request modification value based on the current usage of the Pod.

# # 4. Flexible strategy optimization

Check node pool autoscaling:

- Use `huawei_list_cce_nodepools` to check whether autoscaling is enabled, min/max, cooldown, and priority.
- If not configured, give the recommended node pool autoscaler strategy, including min/max, scale-down delay, resource threshold and applicable node pool.
- If configured, check whether the min/max is too tight, whether the scale down is too slow, and whether the priority meets the service level.

Check HPA:

- Use `huawei_list_cce_hpas` to query the existing HPA in the business namespace, and `kube-system` will not be analyzed by default.
- If there is no HPA, use `huawei_generate_cce_hpa_manifest` to generate `autoscaling/v2` HPA YAML recommendations based on business workload indicators.
- When you need to actually create or update an HPA, first call `huawei_configure_cce_hpa` without `confirm=true` to get a preview; applications with `confirm=true` are allowed only after the user explicitly confirms.
- HPA recommendations must be based on the reasonableness of the request; when the request is obviously excessive, it is recommended to calibrate the request first, and then configure the HPA.

# # 5. Output sequence

1. Overall conclusion: Are there clear cost optimization opportunities?
2. 24-hour and 7-day utilization summary.
3. Risk of low utilization nodes and cluster idleness.
4. Excessive request workload.
5. HPA/autoscaler current status and recommended configuration.
6. Risks, verification methods, and pre-execution confirmation list.