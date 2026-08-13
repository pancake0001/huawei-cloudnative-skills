---
id: huawei-cloud-cce-observability-context-builder
name: huawei-cloud-cce-observability-context-builder
description: |
  使用 hcloud CLI 和 kubectl-cce 为华为云 CCE 故障构建只读可观测上下文包。适用于根因分析前收集当前 Kubernetes 状态、Events、有界 Pod 日志、AOM 告警、指标、LTS/日志上下文、拓扑线索、时间窗口、证据缺口和下一步诊断交接。不要使用 Python SDK dispatcher action、生成 kubeconfig 或执行变更命令。
tags: [cce, observability, context, alarms, metrics, logs, events, hcloud, kubectl-cce, root-cause]
---

# 华为云 CCE 可观测上下文构建

本 skill 负责在根因分析前收集“现网可观测上下文”。它不直接给最终根因结论，而是把告警、事件、指标、日志、资源范围、时间窗口和数据缺口整理成上下文包，供 `huawei-cloud-cce-root-cause-analyzer` 和各专项诊断 skill 使用。

执行路径：

```text
范围和时间窗口 -> hcloud CCE/AOM/LTS 上下文 -> kubectl cce Events/logs/topology -> 信号时间线 -> 根因分析交接
```

不要使用 `scripts/huawei-cloud.py`、`skill action=exec`、`huawei_*` dispatcher action、Huawei Cloud SDK import、Kubernetes SDK、kubeconfig 生成或任何变更命令。

## 相关 Skill

| Skill | 作用 |
| ----- | ---- |
| `huawei-cloud-cce-root-cause-analyzer` | 上下文包的主要消费方 |
| `huawei-cloud-cce-alarm-correlation-engine` | 告警占主导时做 AOM 告警聚合 |
| `huawei-cloud-cce-kubernetes-event-analyzer` | Event 占主导时做事件深挖 |
| `huawei-cloud-cce-metric-analyzer` | 指标占主导时做 AOM/CES 指标深挖 |
| `huawei-cloud-cce-log-analyzer` | 日志占主导时做日志模式分析 |
| `huawei-cloud-cce-pod-failure-diagnoser` | Pod 级后续诊断 |
| `huawei-cloud-cce-workload-failure-diagnoser` | 工作负载发布和 Ready 后续诊断 |
| `huawei-cloud-cce-node-failure-diagnoser` | 节点压力和节点 Ready 后续诊断 |
| `huawei-cloud-cce-network-failure-diagnoser` | Service、DNS、Ingress、ELB/EIP/NAT 后续诊断 |
| `huawei-cloud-cce-storage-failure-diagnoser` | PVC/PV/CSI 后续诊断 |

## 输入

| 输入 | 必填 | 说明 |
| ---- | ---- | ---- |
| `region` | 是 | 例如 `cn-north-4` |
| `project_id` | 推荐 | AK/SK 和 `kubectl cce` 稳定执行通常需要 |
| `cluster_id` | 推荐 | 没有时按集群名精确解析 |
| `namespace` | 可选 | 限定应用命名空间 |
| `workload`、`pod`、`node`、`service`、`ingress` | 可选 | 目标对象线索 |
| `fault_time`、`start_time`、`end_time`、`hours` | 推荐 | 不明确时默认最近 1 小时 |
| `symptoms` | 推荐 | 用户可感知故障、告警文本或受影响业务 |

目标不明确时，先采集集群/命名空间级上下文，并把歧义写入数据缺口。

## 访问方式

### 集群和资源清单

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud CCE ShowCluster --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
hcloud CCE ListNodes --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
```

### 当前 Kubernetes 上下文

执行 Kubernetes 命令前先读 [references/kubectl-cce.md](references/kubectl-cce.md)。

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,svc,ingress,endpoints,endpointslices -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes,pv,pvc,storageclass -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
```

`top`、logs、previous logs 可能因为 Metrics API、RBAC、容器重启历史或插件限制失败。失败要写成数据缺口，不要改用 kubeconfig。

### 告警、指标和日志上下文

- 告警聚合交给 `huawei-cloud-cce-alarm-correlation-engine`。
- 指标趋势交给 `huawei-cloud-cce-metric-analyzer`。
- 日志深挖交给 `huawei-cloud-cce-log-analyzer`，或在本地 hcloud 支持时使用 LTS 只读查询。
- AOM/LTS 源不可用时，记录来源、时间窗口、缺失权限或缺失配置对置信度的影响。

不要在本 skill 中手写 IAM 签名或直接请求云 API。

## 工作流

1. 确认故障现象、时间窗口、region、project_id、cluster、namespace 和目标对象。
2. 用 `hcloud CCE` 解析集群身份和基础状态。
3. 用 `kubectl cce` 收集当前 Pods、Workloads、Services/Ingress、Endpoints/EndpointSlices、Nodes、PVC/PV、Events 和必要的有界日志。
4. 通过只读专项 skill 补充告警、指标、事件和日志。
5. 将信号按时间线归一化，保留来源、时间、对象、严重级别、消息和置信度。
6. 只输出上下文摘要和下一步建议，不在这里过度下最终根因。
7. 输出 Markdown 上下文包。

## 输出要求

输出顺序：

1. `## 总结`
2. `## 范围`
3. `## 高信号发现`
4. `## 时间线`
5. `## 分来源证据`
6. `## 数据缺口`
7. `## 建议交接`
8. `## 使用命令`

## 风险边界

- 只读。
- 使用 `hcloud` 和 `kubectl cce`。
- 不生成 kubeconfig。
- 不使用 SDK 或旧 dispatcher action。
- 不执行无界日志流或交互命令。
- 日志里命中疑似密钥时只描述位置并脱敏，不复制原值。

## References

| 文档 | 说明 |
| ---- | ---- |
| [Workflow](references/workflow.md) | 上下文采集顺序 |
| [Risk Rules](references/risk-rules.md) | 只读安全规则 |
| [Output Schema](references/output-schema.md) | 上下文包报告格式 |
| [kubectl-cce Usage](references/kubectl-cce.md) | 插件接入和命令约束 |
