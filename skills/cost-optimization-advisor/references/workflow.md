# Workflow

## 1. 采集范围

优先使用 `huawei_analyze_cce_cost_optimization` 作为组合 action；只有需要补充明细、复核单项指标或手工生成特定 HPA YAML 时，再调用下方低层 action。

1. 确认 region、cluster_id、namespace 范围、业务排除规则和统计窗口。
2. 默认排除 `kube-system` 下的 Pod 和工作负载；其他命名空间按业务负载处理，除非用户另行排除。
3. 拉取节点、节点池、Pod、Deployment 和指标数据。
4. 对所有利用率类判断同时检查 24 小时和 7 天两个窗口。

## 2. 空闲资源和低利用率节点

对每个窗口分别计算：

- cluster_cpu_avg = 全部 Ready 节点 CPU 平均使用率。
- cluster_mem_avg = 全部 Ready 节点内存平均使用率。
- node_cpu_avg / node_mem_avg = 单节点平均使用率。

触发提示：

- 集群平均 CPU 或内存使用率低于 30%，提示整体资源可能过量。
- 单节点 CPU 或内存使用率明显低于集群平均值时提示。默认判定为：低于集群平均 20 个百分点，或低于集群平均的 60%。
- 如果节点低利用率只在 24 小时出现而 7 天不明显，标记为短期波动；两个窗口都命中时标记为稳定优化机会。

输出建议：

- 优先建议调整节点池 min/max、开启 scale down、优化调度和负载均衡。
- 不直接建议立即删除节点，除非有明确冗余且用户要求执行计划。

## 3. 过量 Request

只分析非 `kube-system` 工作负载。

对每个业务工作负载分别比较：

- CPU request vs 24 小时和 7 天实际 CPU p95/avg。
- Memory request vs 24 小时和 7 天实际 memory p95/avg。

触发提示：

- request 大于实际 p95 的 2 倍，且两个窗口都成立，标记为稳定过量。
- request 大于实际 p95 的 3 倍，标记为高优先级优化。
- 仅 24 小时命中时标记为观察项，不建议立即改 request。

如果现有 action 返回中缺少 request 字段，要求用户补充 Deployment/Pod YAML 或通过后续工具扩展获取；不要凭 Pod 当前使用率直接给出 request 修改值。

## 4. 弹性策略优化

检查节点池 autoscaling：

- 使用 `huawei_list_cce_nodepools` 查看 autoscaling 是否开启、min/max、cooldown、priority。
- 如果未配置，给出建议的节点池 autoscaler 策略，包括 min/max、scale-down delay、资源阈值和适用节点池。
- 如果已配置，检查 min/max 是否过紧、scale down 是否过慢、优先级是否符合业务等级。

检查 HPA：

- 使用 `huawei_list_cce_hpas` 查询业务命名空间已有 HPA，默认不分析 `kube-system`。
- 如没有 HPA，基于业务工作负载指标用 `huawei_generate_cce_hpa_manifest` 生成 `autoscaling/v2` HPA YAML 建议。
- 需要实际创建或更新 HPA 时，先调用不带 `confirm=true` 的 `huawei_configure_cce_hpa` 获取预览；用户明确确认后才允许带 `confirm=true` 应用。
- HPA 建议必须基于 request 合理性；request 明显过量时，先建议校准 request，再配置 HPA。

## 5. 输出顺序

1. 总体结论：是否存在明确成本优化机会。
2. 24 小时和 7 天利用率摘要。
3. 低利用率节点和集群空闲风险。
4. 过量 request 工作负载。
5. HPA/autoscaler 当前状态和建议配置。
6. 风险、验证方式、执行前确认清单。
