# Workflow

1. 记录用户现象、故障时间、region、project_id、cluster_id、namespace 和目标对象。
2. 用 `hcloud CCE ListClusters`、`ShowCluster`、`ListNodes` 解析集群上下文。
3. 验证 `kubectl cce`，采集 namespaces、Pods、Workloads、Services、Ingresses、Endpoints、EndpointSlices、Nodes、PVC/PV、StorageClasses、Events。
4. 对目标对象采集 describe、bounded logs、previous logs、`top pods`、`top nodes`。
5. 需要时补充专项只读证据：alarm、metric、event、log analyzer。
6. 将所有证据归一到一条时间线，保留来源、时间、对象、严重级别、信号和置信度。
7. 输出上下文包和推荐交接。

## 交接规则

| 主信号 | 交接 |
| ------ | ---- |
| 镜像、重启、OOM、调度、探针、容器日志 | pod 或 workload diagnoser |
| NodeNotReady、节点压力、污点、runtime/kubelet | node diagnoser |
| Service、EndpointSlice、DNS、Ingress、ELB、EIP、NAT | network diagnoser |
| PVC/PV/CSI attach 或 mount | storage diagnoser |
| 多域信号或信号冲突 | root-cause analyzer |
| 告警为主 | alarm correlation engine |
| 指标为主 | metric analyzer |
| 历史 Event 为主 | kubernetes event analyzer |
| 日志模式为主 | log analyzer |
