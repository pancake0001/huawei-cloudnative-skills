---
id: huawei-cloud-cce-dependency-impact-analyzer
name: huawei-cloud-cce-dependency-impact-analyzer
description: >
  使用 hcloud CLI 做集群发现，并通过 kubectl-cce 插件命令只读采集 Pod、Service、Ingress、EndpointSlice 和 Node 证据，分析华为云 CCE 服务拓扑影响面。适用于依赖影响分析、影响面、传播路径、受影响入口、上下游影响或完整 Markdown 影响报告场景。不要使用 Python SDK dispatcher action。
tags: [cce, dependency, impact, cascade, hcloud, kubectl-cce]
---

# 华为云 CCE 依赖影响分析

本 skill 用于分析 CCE 故障的服务拓扑和影响面，说明一个异常工作负载或 Pod 集合如何通过 Service、EndpointSlice、Ingress 和节点分布传播影响。

执行模型：

```text
hcloud CCE 查询集群 -> kubectl cce 拓扑快照 -> 目标匹配 -> 传播路径 -> 影响面报告 -> 诊断交接
```

不要使用 Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、`huawei_dependency_impact_*`、`huawei_get_cce_*`、捆绑 SDK 脚本、kubeconfig 生成或 Huawei Cloud SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。执行 Kubernetes 命令前先读 `references/kubectl-cce.md`。

## 相关 Skill

| Skill | 使用场景 |
| --- | --- |
| `huawei-cloud-cce-workload-failure-diagnoser` | 目标工作负载不可用、发布卡住或 Pod 未 Ready |
| `huawei-cloud-cce-pod-failure-diagnoser` | 单个 Pod 出现 CrashLoopBackOff、ImagePullBackOff、OOMKilled、Pending 或 Evicted |
| `huawei-cloud-cce-network-failure-diagnoser` | Service、Ingress、EndpointSlice、DNS、NetworkPolicy、ELB 或 EIP 证据指向网络故障 |
| `huawei-cloud-cce-change-impact-analyzer` | 故障发生在发布、配置、路由、策略、节点或基础设施变更之后 |
| `huawei-cloud-cce-root-cause-analyzer` | 需要跨域根因排序 |
| `huawei-cloud-cce-auto-remediation-runner` | 根因明确后的恢复预览和确认执行 |

## 必要输入

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `region` | 是 | 例如 `cn-north-4` |
| `project_id` | 通常需要 | kubectl-cce 需要 |
| `cluster_id` | 推荐 | 没有时先用 hcloud 按名称定位 |
| `namespace` | 推荐 | 目标命名空间；不明确时用全集群扫描 |
| `target_name` | 推荐 | 工作负载、Service、Pod 或 app label 值 |
| `label_selector` | 可选 | 如果用户提供，优先级高于名称前缀匹配 |
| `failure_symptom` | 可选 | Service 不通、Ingress 失败、Pod 不可用、节点集中等 |

## 采集方式

1. 查询并确认集群：

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

2. 通过 kubectl-cce 采集拓扑。命名空间明确时用 `-n <namespace>`，否则用 `-A` 并在报告里控制输出规模：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods,svc,ingress,endpoints,endpointslices -n <namespace> -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

如果 Kubernetes 版本或 RBAC 不支持 `endpointslices`，退回 `endpoints` 并记录数据缺口。

## 分析流程

1. 明确 region、cluster、namespace、目标对象、selector 和故障现象。
2. 目标匹配：优先 `label_selector`，其次 ownerReference、Pod 前缀、app label 或 Service selector。
3. 上游映射：找 selector 匹配目标 Pod 的 Service，标记 selector 不匹配和无 ready endpoint 的 Service。
4. 入口映射：找指向这些 Service 的 Ingress rule/default backend，输出 host、path、backend Service 和 ingress class/controller。
5. 节点分布：把受影响 Pod 映射到 Node，关注单节点集中、NotReady/压力节点和可用区集中。
6. 传播路径：外部流量按 `Ingress -> Service -> EndpointSlice/Endpoints -> Pods -> Nodes`，集群内流量按 `Service DNS -> EndpointSlice/Endpoints -> Pods -> Nodes`。
7. 影响面评分：综合 Pod Ready、受影响 Service/Ingress 数量、endpoint 可用性、节点集中度和用户可见现象。
8. 交接：根因级证据交给 workload/pod/node/network/change diagnoser，本 skill 聚焦影响面和拓扑。

## 输出要求

Markdown 报告必须从以下内容开始：

1. `## 总结`：受影响入口、后端、估计影响面和置信度。
2. `## 影响路径`：从 Ingress/Service 到 Pod/Node 的路径表。
3. `## 下一步措施`：最有效的验证和域诊断交接。
4. `## 证据`：Pod Ready、Service selector、EndpointSlice/Endpoints、Ingress backend、节点分布和 Events。
5. `## 置信度限制`：命名空间缺失、RBAC 拒绝、EndpointSlice 缺失、无访问日志或未知上游消费者。

只有静态拓扑时，不要直接声称真实用户流量受影响；需要日志、指标、告警或用户现象支撑。

## 验证

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_dependency_impact|huawei_get_cce_|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

期望结果：没有可执行 SDK dispatcher 入口，也没有裸 Kubernetes 访问路径。Markdown 中只能作为禁用项或验证项出现。

## References

- `references/kubectl-cce.md`：插件接入约束。
- `references/workflow.md`：拓扑和影响面分析流程。
- `references/output-schema.md`：结构化输出和 Markdown 布局。
- `references/risk-rules.md`：只读边界和置信度限制。
