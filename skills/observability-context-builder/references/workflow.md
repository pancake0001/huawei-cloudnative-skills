# Workflow

1. 记录用户给出的故障时间、region、cluster_id、namespace、workload、pod、node。
2. 如果时间不明确，默认看最近 1 小时，并在输出中标明假设。
3. 调用 `huawei_list_aom_alarms` 汇总 active + history 告警，再用 `huawei_analyze_aom_alarms` 做去重和分级。
4. 调用 `huawei_get_cce_events` 获取 Kubernetes Events，按 involved object 和 reason 分组。
5. 调用 Pod/Node TopN 指标工具，找出资源峰值、异常节点和异常 Pod。
6. 需要日志证据时优先查 `huawei_query_aom_logs`，再补 Pod 近端日志。
7. 输出证据时间线、异常摘要、缺失信息和建议转交的诊断 skill。

