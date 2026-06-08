# Workflow

1. Record the failure time, region, cluster_id, namespace, workload, pod, and node given by the user.
2. If the time is unclear, default to the last hour and indicate the assumption in the output.
3. Call `huawei_list_aom_alarms` to summarize active + history alarms, and then use `huawei_analyze_aom_alarms` to remove duplicates and classify them.
4. Call `huawei_get_cce_events` to obtain Kubernetes Events, grouped by involved object and reason.
5. Call the Pod/Node TopN indicator tool to find resource peaks, abnormal nodes, and abnormal Pods.
6. When log evidence is needed, check `huawei_query_aom_logs` first, and then fill in the Pod local log.
7. Output the evidence timeline, exception summary, missing information, and diagnostic skills recommended for transfer.