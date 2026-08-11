# Workflow

1. 明确 region、project_id、cluster_id、namespace、目标对象、故障现象、fault_time 和分析窗口。
2. 优先构建或复用 `observability-context-builder` 上下文包：告警、Events、日志、指标、拓扑、时间线和数据缺口。
3. 读取 `references/kubectl-cce.md`，校验 `hcloud`、`kubectl`、`kubectl-cce`，用 hcloud 定位目标集群。
4. 使用 `kubectl cce` 只读采集 Pods、Workloads、ReplicaSets、Services、Ingresses、Endpoints/EndpointSlices、Nodes、Events、PVC/PV/StorageClass 和相关 NetworkPolicies。
5. 建立时间线：用户现象、告警、Event、发布/变更、指标/日志、恢复尝试。
6. 按证据调用或参考 workload、pod、node、network、storage、dependency-impact、change-impact、observability-context、alarm、event、metric 等依赖 skill。
7. 将各域发现归一成根因候选：域、标题、支持证据、反证、数据缺口、影响面、置信度和下一步验证。
8. 按时间吻合度、直接证据、故障特征、影响面、反证和可恢复性排序 Top3。
9. 报告前置 `总结`、`根因分析`、`下一步措施`，命令细节和原始证据放后面。
