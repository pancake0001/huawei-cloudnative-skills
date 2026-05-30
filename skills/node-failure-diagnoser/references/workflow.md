# Workflow

## 可复用能力与缺口

- 已有可复用工具：`huawei_get_kubernetes_nodes` 查 Node Ready/压力条件，`huawei_get_cce_events` 查 Kubernetes Events，`huawei_get_cce_pods` 查 Pod phase/reason/lastState，`huawei_get_cce_node_metrics` 和 `huawei_get_cce_pod_metrics_topN` 查 AOM 指标，`huawei_node_diagnose`/`huawei_node_batch_diagnose` 查节点监控、NPD 与工作负载摘要。
- 外部 huawei-cloud skill 中同样强调 CCE 节点、Pod、Event、监控、巡检和诊断报告工具族，可直接沿用这些只读工具与“先列任务、再输出完整报告”的输出习惯。
- 原缺口：缺少 `kube-node-lease` 续约证据、缺少 Node 条件全量时间戳、缺少节点上 Pod 症状聚合、缺少把 NotReady/压力/CNI/kubelet 证据合成 Markdown 报告的确定性动作。
- 已补主工具：`huawei_node_failure_diagnose` 一次性输出结构化证据和 `report_markdown`。

## 主流程

1. 输入必须包含 `region`、`cluster_id`，以及 `node_name` 或 `node_ip`。
2. 调用 `huawei_node_failure_diagnose`，默认 `lease_timeout_seconds=40`、`event_limit=500`、`hours=1`、`include_metrics=true`。
3. 若主工具返回 `report_markdown`，直接以该 Markdown 为最终报告主体，只可补充用户关心的解释，不要丢弃证据表。
4. 若主工具失败，按下方手工兜底流程执行。

## 1. 控制面存活状态分流

采集：

- `v1.Node.status.conditions` 中的 `Ready`、`MemoryPressure`、`DiskPressure`、`PIDPressure`、`NetworkUnavailable`。
- `kube-node-lease/<node_name>` 的 `spec.renewTime`，计算当前时间与 renewTime 的差值。

判定：

- 情况 A：`Ready=Unknown` 且 Lease 续约延迟超过 40 秒。推论为控制面与节点失联。若没有 `SystemOOM`、`EvictionThresholdMet`、`FailedCreatePodSandBox/CNI`、`ContainerRuntimeNotReady` 等更强证据，结论应写为“控制面与节点失联（网络链路或 Kubelet/CRI 心跳中断，需节点侧验证）”，不要过早单押 kubelet 或网络。
- 情况 B：`Ready=False` 且 Lease 正常续约。推论为 kubelet 存活并主动报告节点或基础设施不健康。
- 情况 C：`Ready=True`。推论为基础通信正常，继续排查局部资源压力、CNI 和工作负载症状。
- 情况 D：其他组合。标记为证据不足，继续用 Event、Pod 和节点本地日志收敛。

## 2. 节点事件时序回溯

过滤 `involvedObject.kind=Node` 且 `involvedObject.name=<node_name>` 的 Event，并按 `lastTimestamp/eventTime/firstTimestamp` 倒序排列。

强信号：

- `SystemOOM`：内存压力强证据。
- `EvictionThresholdMet` 且 message 包含 `imagefs`、`nodefs`、`DiskPressure`、`ephemeral-storage`：磁盘压力强证据。
- `KubeletSetupFailed`、`ContainerRuntimeNotReady`、`PLEG`、runtime not ready：kubelet/CRI 异常强证据。
- `NodeNotReady`：NotReady 结果证据，必须继续找根因。

## 3. 负载侧症状下钻

查询 `spec.nodeName=<node_name>` 的所有 Pod，并聚合 `phase`、`reason`、`message`、容器 `state` 和 `lastState`。

判定：

- 磁盘压力：多个 Pod `phase=Failed`、`reason=Evicted`，message 指出 `DiskPressure`、`nodefs`、`imagefs` 或 `ephemeral-storage`。
- 内存压力：业务 Pod 的 `lastState.terminated.reason=OOMKilled`，尤其退出码 `137`；若同时有 `SystemOOM`，置信度为高。
- 网络异常：新 Pod 长期 `ContainerCreating`，对应 Pod Event 有 `FailedCreatePodSandBox`，message 包含 `CNI`、`network plugin returns error`、`timeout waiting for DHCP` 等。
- kubelet/CRI 异常：大量 Pod 变为 `Unknown`/`NodeLost`，或 `kube-system` 核心 DaemonSet（kube-proxy、CNI 插件、CSI 插件等）异常、频繁重启、`Unhealthy`。

## 4. 指标与云侧补证

- 用 `huawei_get_cce_node_metrics` 验证 CPU、内存、磁盘趋势，不把单点峰值直接当根因。
- 用 `huawei_get_cce_pod_metrics_topN node_ip=<node_ip>` 查节点上高内存/高 CPU Pod。
- NotReady 或网络候选较强时，追加安全组、网络 ACL、Master-Node 通信链路核对。
- 涉及内核漏洞、重启后生效类问题时，追加 HSS 主机和漏洞清单，但不要在本 skill 中执行修复。

## 5. 结论合成

优先级不是固定顺序，而是证据强度：

1. 强 Event + Pod 症状一致：高置信度，可直接落到内存、磁盘、网络或 kubelet/CRI 类别。
2. `Ready=Unknown` + Lease 超时：对“节点失联”本身为高置信度；对底层根因通常只能给中低置信度候选，除非有独立强证据。
3. 压力条件为 `Unknown` 且 reason 为 `NodeStatusUnknown`：只说明 kubelet 不再上报，不等价于 MemoryPressure/DiskPressure 正常或异常；报告应标为“不可判定”并说明缺少独立证据。
4. 只有 NotReady 或只有指标异常：中低置信度，需要本地日志验证。

结论必须包含：根因类别、置信度、关键证据、影响面、未确认风险、下一步验证。
