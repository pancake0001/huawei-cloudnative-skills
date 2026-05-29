# Workflow

1. 读取用户给出的告警名称、资源、时间窗口和严重级别。
2. 默认使用最近 1 小时；如果用户描述过去故障，按用户时间扩大窗口。
3. 调用 `huawei_list_aom_alarms`，不要只查 active_alert。
4. 调用 `huawei_analyze_aom_alarms` 形成去重、突发、关注、常态分组。
5. 如果告警与通知或静默有关，读取规则、动作规则、静默规则。
6. 按资源、namespace、node、workload、alarm type 归并。
7. 输出需要继续诊断的 Pod、Node、Network 或 Workload 对象。

