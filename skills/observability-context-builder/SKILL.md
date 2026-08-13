---
name: observability-context-builder
description: Use this skill when a Huawei Cloud CCE issue needs a read-only observability context package from hcloud, kubectl-cce, AOM alarms, metrics, LTS/log context, Pod logs, and Kubernetes Events before root-cause diagnosis. Use hcloud CLI and kubectl-cce; do not use Python SDK dispatcher actions, generated kubeconfig, or mutation commands.
---

# observability-context-builder

你负责把 CCE 现网可观测信号整理成可诊断的上下文包。这个 skill 是 `root-cause-analyzer` 的前置上下文构建步骤：收集范围、时间窗口、当前 Kubernetes 状态、Events、告警、指标、日志、数据缺口和推荐交接，不直接下最终根因结论，不执行恢复动作。

## 执行方式

1. 使用 `hcloud` 查询 CCE 集群、节点、AOM/LTS/CES 等只读云侧上下文。
2. 使用 `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 查询 Kubernetes 当前状态、Events、Pod 日志和 Metrics API。
3. 需要深挖告警、指标、事件或日志时，调用或参考对应只读 skill：alarm、metric、event、log analyzer。
4. 不使用 `scripts/huawei-cloud.py`、`skill action=exec`、`huawei_*` action、Python SDK、Kubernetes SDK、kubeconfig 生成或手写 IAM/API。

## 处理步骤

1. 明确故障现象、时间窗口、region、project_id、cluster_id、namespace、workload、pod、node、service、ingress。
2. 用 `hcloud CCE ListClusters` / `ShowCluster` / `ListNodes` 确认集群身份和基础状态。
3. 用 `kubectl cce` 采集 Pods、Workloads、Services、Ingresses、EndpointSlices、Nodes、PVC/PV、Events 等只读快照。
4. 对目标 Pod/Workload 补充 describe、bounded logs、previous logs 和 `top`，失败时记录数据缺口。
5. 汇总告警、指标、事件、日志和云侧元数据，按时间线归并。
6. 输出上下文包，并推荐下一步交给 root-cause、pod、workload、node、network、storage、alarm、event、metric 或 log skill。

## References

- 插件接入读 `references/kubectl-cce.md`。
- 完整取证步骤读 `references/workflow.md`。
- 风险边界读 `references/risk-rules.md`。
- 输出结构按 `references/output-schema.md`。
