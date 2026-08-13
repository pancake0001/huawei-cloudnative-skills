---
name: root-cause-analyzer
description: Use this skill when a Huawei Cloud CCE incident spans alarms, workload rollout, Pod events/logs, recent changes, service topology, nodes, network, storage, or metrics, and the user needs a complete Markdown root-cause report with summary, evidence chain, impact scope, Top3 causes, confidence, and remediation handoff. Start from an observability context package when possible. Use hcloud CLI and kubectl-cce; do not use Python SDK dispatcher actions.
---

# root-cause-analyzer

你负责把 CCE 多域证据收敛成根因结论。默认输出完整 Markdown 报告，且把 `总结`、`根因分析`、`下一步措施` 放在报告前面。

## 执行方式

1. 使用 `hcloud` 做 CCE 集群发现和只读云侧元数据查询。
2. 使用 `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 采集 Kubernetes 当前证据。
3. 缺少 `kubectl` 或 `kubectl-cce` 时，先使用 `huawei-cloud-kubectl-cce-installer`。
4. 不使用 `scripts/huawei-cloud.py`、`skill action=exec`、`huawei_*` action、Python SDK、kubeconfig 生成或手写 IAM/API。

## 证据依赖 Skill

- `huawei-cloud-cce-workload-failure-diagnoser`：发布、ReplicaSet、探针、镜像、启动命令、Ready 异常。
- `huawei-cloud-cce-pod-failure-diagnoser`：CrashLoopBackOff、ImagePullBackOff、OOMKilled、Pending、Evicted、日志和事件。
- `huawei-cloud-cce-node-failure-diagnoser`：NodeNotReady、资源压力、污点、kubelet/runtime 和节点影响。
- `huawei-cloud-cce-network-failure-diagnoser`：Service、DNS、Ingress、EndpointSlice、NetworkPolicy、ELB/EIP/NAT/VPC。
- `huawei-cloud-cce-storage-failure-diagnoser`：PVC/PV、CSI、attach/mount、存储供应异常。
- `huawei-cloud-cce-dependency-impact-analyzer`：Service/Ingress/Pod/Node 传播路径和影响面。
- `huawei-cloud-cce-change-impact-analyzer`：近期发布、配置、路由、安全、节点和云侧变更关联。
- `huawei-cloud-cce-observability-context-builder`：第一轮告警、Events、日志、指标、拓扑、时间窗口和数据缺口上下文包。
- `huawei-cloud-cce-alarm-correlation-engine`、`huawei-cloud-cce-kubernetes-event-analyzer`、`huawei-cloud-cce-metric-analyzer`：告警、事件和指标补证。

`huawei-cloud-cce-auto-remediation-runner` 不是证据依赖，只在根因明确且用户要求恢复预览或确认执行时作为交接目标。

## 处理步骤

1. 明确故障现象、时间窗口、影响业务、region、project_id、cluster_id、namespace 和目标对象。
2. 优先用 `huawei-cloud-cce-observability-context-builder` 构建上下文包；用户已提供等价证据时可直接复用。
3. 通过 `kubectl cce` 采集 Pods、Workloads、Services、Ingresses、EndpointSlices、Nodes、PVC/PV、Events 等只读证据。
4. 根据信号调用或参考对应域诊断 skill，不在本 skill 里重复完整域诊断。
5. 建立时间线：用户感知时间、告警时间、Event 时间、发布/变更时间、恢复动作时间。
6. 生成 Top3 根因，逐条附直接证据、反证、数据缺口、影响面、置信度和验证步骤。
7. 恢复动作只作为建议，交给 `huawei-cloud-cce-auto-remediation-runner`。

## References

- 插件接入读 `references/kubectl-cce.md`。
- 证据链和根因排序读 `references/workflow.md`。
- 风险边界读 `references/risk-rules.md`。
- 报告结构按 `references/output-schema.md`。
