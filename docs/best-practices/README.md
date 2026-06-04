# 最佳实践合集

本目录用于沉淀华为云云原生运维 Skill 的最佳实践案例，覆盖 CCE 工作负载诊断、Pod/Node 故障恢复、容量与弹性治理、可用性风险识别、自动化恢复等典型场景。

## CCE工作负载故障诊断

| 最佳实践 | 场景 | 关键能力 |
| --- | --- | --- |
| [使用AICLI对CCE工作负载进行故障诊断与恢复](aicli-cce-workload-diagnosis-recovery.md) | Deployment 更新后新版本 Pod 未就绪，Rollout 卡住，需要定位根因并快速恢复业务。 | 工作负载故障诊断、Readiness 探针分析、版本历史分析、恢复预览、确认执行、恢复验证 |
| [使用OpenClaw诊断应用CPU上涨并扩容](openclaw-cce-cpu-diagnosis-scaling.md) | 应用 CPU 使用率异常升高，需要汇聚指标、日志和事件定位根因，并通过受控扩容恢复业务。 | 可观测上下文汇聚、Pod 运行状态分析、根因分析、扩容预览、确认执行、效果验证 |

## CCE集群运维与弹性

| 最佳实践 | 场景 | 关键能力 |
| --- | --- | --- |
| [使用OpenClaw进行CCE集群定期巡检](openclaw-cce-periodic-inspection.md) | 生产集群需要周期性健康检查、报告归档和异常通知。 | 定时巡检、告警/指标/事件汇聚、报告生成、邮件通知 |
| [使用AI CLI配置、查询和治理CCE AOM告警](aicli-cce-aom-alarm-configuration-query.md) | 集群上线或治理时，需要批量配置AOM告警规则，并进行活跃告警、历史告警、通知规则和静默规则查询。 | 告警规则一键创建、通知规则自动创建、SMN主题绑定、活跃告警查询、历史告警归并、规则启停删除、二次确认 |
| [基于AICLI和Skill实现CCE到CCI 2.0 Bursting](aicli-cce-cci-bursting.md) | CCE 集群突发流量或资源不足时，将符合条件的 Pod 弹性调度到 CCI 2.0。 | 预检查、VPCEP 创建、bursting 插件配置、虚拟节点验证、冒烟测试 |

## 编写规范

- 每个最佳实践应包含应用场景、前提条件、操作步骤、诊断结论、预期结果、约束限制和后续建议。
- 涉及截图时，请将图片放在 `assets/<case-name>/` 目录下，并使用相对路径引用。
- 不要在文档中写入 AK/SK、Token、证书、真实 project_id 等敏感信息。
- 恢复类操作必须体现预览和用户确认流程，避免误导用户直接执行高风险变更。
