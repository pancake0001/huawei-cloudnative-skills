# Workflow

1. 建立故障时间线：用户感知时间、告警触发时间、Kubernetes 事件时间、发布/配置变更时间。
2. 首选调用 `huawei_root_cause_analyze`；如果需要下钻，再分别调用 rollout、dependency、change、network、node/pod diagnoser。
3. Workload 发布漏斗优先级最高：generation/observedGeneration、ReplicaSet、Pod Ready、事件、日志、command/args、探针、镜像。
4. 依赖影响面用 Service selector、Ingress backend、Pod Ready 和 Node 分布判断传播路径。
5. 变更影响面用审计日志、K8s 历史事件、AOM 告警和当前拓扑验证“变更后出现故障”的因果链。
6. 对每条根因候选记录支持证据、反证、数据缺口和恢复交接。
7. 按影响范围、时间吻合度、证据强度、可恢复性排序。
8. 输出 Top3 根因、验证步骤、影响面和恢复建议。
9. 对低置信度结论明确标注需要补充的数据。
