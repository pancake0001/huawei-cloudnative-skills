# Risk Rules

## 只读边界

`change-impact-analyzer` 只允许执行只读查询和报告生成：

- 可以查询审计日志、K8s 事件、AOM 告警、Pod/Service/Ingress/Node/ConfigMap/Secret/NodePool/Security Group/VPC ACL 当前状态。
- 可以调用 Workload、Network、Node 诊断 action 做只读下钻。
- 可以把 `report_markdown` 写到用户指定的 `output_file`。

## 禁止动作

禁止在本 skill 内执行：

- 回滚或重新发布工作负载。
- 修改 Deployment/StatefulSet/DaemonSet、ConfigMap、Secret、Service、Ingress、Gateway。
- 修改 NetworkPolicy、RBAC、Security Group、VPC ACL。
- 扩缩容工作负载或节点池。
- cordon、uncordon、drain、delete、reboot 节点或 ECS。
- 修改 HSS 漏洞状态。

## 恢复动作交接

当报告指向明确恢复动作时：

1. 在报告中写明建议动作、风险和验证标准。
2. 不带 `confirm=true` 执行任何变更。
3. 转交 `auto-remediation-runner` 生成预览。
4. 用户明确确认后，才允许恢复 skill 执行动作。
5. 变更后再次运行 `huawei_change_impact_analyze` 或对应 diagnoser 做验证。

## 结论置信度

- `high`：审计变更、故障时间邻近、事件/告警响应、拓扑影响面四类证据至少命中三类。
- `medium`：命中审计变更和至少一类响应信号，或命中全局核心变更但响应信号不足。
- `low`：只有对象写操作或当前快照，缺少时间/响应/拓扑证据。

低置信度结论必须在报告中写出数据缺口，不要把推测写成事实。
