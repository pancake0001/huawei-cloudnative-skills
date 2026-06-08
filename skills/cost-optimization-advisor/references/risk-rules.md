# RiskRules

- Allows automated execution of R1 read-only queries for: Nodes, Node Pools, Pods, Deployments, Metrics, AOM PromQL, Report Generation.
- It is prohibited to automatically shrink the node pool, delete nodes, modify workload requests, install HPA, update HPA, and start and stop the autoscaler.
- Generating HPA YAML, autoscaler parameters and execution plans is allowed; `huawei_configure_cce_hpa` without `confirm=true` will only preview.
- Applying HPA/autoscaler configuration must be explicitly confirmed by the user, and `confirm=true` is allowed after confirmation.
- Do not analyze the excessive request problem of `kube-system`; system components are only used as node utilization background.
- Do not directly recommend scaling down based on a single 24-hour low utilization; you need to also refer to the 7-day window.
- Data gaps must be marked in the report if the metric is missing, the request is missing, or the HPA status is not visible.
- Cost optimization recommendations must include rollback strategies and validation metrics.