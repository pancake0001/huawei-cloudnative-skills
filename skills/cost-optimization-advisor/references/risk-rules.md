# Risk Rules

- 允许自动执行 R1 只读查询：节点、节点池、Pod、Deployment、指标、AOM PromQL、报告生成。
- 禁止自动缩容节点池、删除节点、修改工作负载 request、安装 HPA、更新 HPA、启停 autoscaler。
- 生成 HPA YAML、autoscaler 参数和执行计划是允许的；`huawei_configure_cce_hpa` 不带 `confirm=true` 时只做预览。
- 应用 HPA/autoscaler 配置必须由用户明确确认，确认后才允许携带 `confirm=true`。
- 不分析 `kube-system` 的 request 过量问题；系统组件只作为节点利用率背景。
- 不基于单一 24 小时低利用率直接建议执行缩容；需要同时参考 7 天窗口。
- 如果指标缺失、request 缺失或 HPA 状态不可见，必须在报告中标记数据缺口。
- 成本优化建议必须包含回滚策略和验证指标。
