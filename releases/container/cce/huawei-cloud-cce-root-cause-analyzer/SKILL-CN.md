---
name: huawei-cloud-cce-root-cause-analyzer
description: >
  使用 hcloud、kubectl-cce、可观测上下文包和相关诊断 Skill 分析华为云 CCE 跨域故障。 适用于同时涉及告警、工作负载发布、Pod Events 或日志、近期变更、服务拓扑、
  节点、网络、存储或指标，且需要根因排序、证据链、影响面、置信度、下一步措施 和恢复交接的场景。
version: 1.0.0
tags: [huawei-cloud, cce, root-cause, kubectl, diagnosis]
---

# 华为云 CCE 根因分析

## 概述

本 skill 负责把 CCE 多域证据收敛成可交付的根因结论和 Markdown 报告。它是编排与综合分析 skill：通过 `hcloud`、`kubectl cce`
和聚焦的只读诊断 skill 采集证据，再按时间吻合度、证据强度、影响范围、反证和可恢复性排序根因。

执行模型：

```text
可观测上下文包 -> hcloud CCE 查询集群 -> kubectl cce 采集当前 Kubernetes 证据 -> 可选 hcloud/AOM/LTS 证据 -> 域诊断 skill 下钻 -> 根因排序 -> Markdown 报告
```

不要使用 Python SDK dispatcher、旧 skill 执行动作、旧 Huawei 诊断 action、捆绑 SDK 脚本、kubeconfig 生成或 Huawei Cloud SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。执行 Kubernetes 命令前先读
`references/kubectl-cce.md`。

## 前置条件

1. `hcloud`、`kubectl` 和 kubectl-cce 均为当前平台可执行的原生二进制。
2. 凭据和项目上下文通过批准的受保护渠道提供。
3. IAM 和 Kubernetes RBAC 允许所选域 Skill 所需的只读证据采集。
4. 给出高置信度根因前，先构建或复用可观测上下文包。
5. 工具缺失时使用 `huawei-cloud-kubectl-cce-installer`，本技能不得下载或执行安装脚本。

## 证据依赖 Skill

按证据类型使用这些只读 skill 作为证据来源：

| Skill                                            | 作用                                                                                    |
| ------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `huawei-cloud-cce-observability-context-builder` | 第一轮告警、Events、日志、指标、拓扑、时间窗口和数据缺口上下文包                        |
| `huawei-cloud-cce-workload-failure-diagnoser`    | Deployment/StatefulSet/DaemonSet 发布漏斗、ReplicaSet、探针、镜像、启动命令、Ready 异常 |
| `huawei-cloud-cce-pod-failure-diagnoser`         | Pod CrashLoopBackOff、ImagePullBackOff、OOMKilled、Pending、Evicted、日志和事件         |
| `huawei-cloud-cce-node-failure-diagnoser`        | NodeNotReady、资源压力、污点、lease 超时、kubelet/runtime、节点级影响                   |
| `huawei-cloud-cce-network-failure-diagnoser`     | Service、EndpointSlice、DNS/CoreDNS、Ingress、NetworkPolicy、ELB/EIP/NAT/VPC 证据       |
| `huawei-cloud-cce-storage-failure-diagnoser`     | PVC/PV、StorageClass、CSI、attach/mount、存储供应异常                                   |
| `huawei-cloud-cce-dependency-impact-analyzer`    | Service/Ingress/Pod/Node 传播路径和影响面                                               |
| `huawei-cloud-cce-change-impact-analyzer`        | 近期发布、配置、路由、安全、节点和基础设施变更关联                                      |
| `huawei-cloud-cce-alarm-correlation-engine`      | AOM 当前/历史告警聚合、告警风暴和告警时间锚点                                           |
| `huawei-cloud-cce-kubernetes-event-analyzer`     | 当前和历史 Kubernetes Event 分析                                                        |
| `huawei-cloud-cce-metric-analyzer`               | 需要指标证据时查询 AOM/Prometheus 和云资源指标                                          |

**恢复交接目标**：`huawei-cloud-cce-auto-remediation-runner` 不是证据依赖。只有根因明确后，且用户要求预览或确认恢复动作时，才作为交接目标提及。

## 参数确认

| 输入                   | 必填     | 说明                                            |
| ---------------------- | -------- | ----------------------------------------------- |
| `region`               | 是       | 例如 `cn-north-4`                               |
| `project_id`           | 通常需要 | kubectl-cce 和多数 hcloud 操作需要              |
| `cluster_id`           | 推荐     | 没有时先用 `hcloud CCE ListClusters` 按名称定位 |
| `namespace`            | 可选     | 应用命名空间                                    |
| `target_name`          | 可选     | 工作负载、Service、Pod、Ingress 或业务对象      |
| `fault_time` / `hours` | 推荐     | 用于事件、告警、指标和变更关联                  |
| `symptoms`             | 推荐     | 用户可感知故障、已知告警和现象                  |
| `--cli-access-key`     | 可选     | 为本次诊断链显式指定 AK                         |
| `--cli-secret-key`     | 可选     | 显式指定 SK，必须与显式 AK 成对提供             |
| `--cli-security-token` | 可选     | STS token，只能与显式 AK/SK 一起使用            |

目标不明确时，先做只读广域快照，并在报告里说明还需要确认哪些对象，不能直接给高置信度结论。

## 显式凭证透传

用户提供 `--cli-access-key` 和 `--cli-secret-key` 时，向每个选中的证据依赖 skill 以及所有 `hcloud`、`kubectl cce` 命令原样透传该 AK/SK 和可选的
`--cli-security-token`。该次诊断链不得使用 hcloud profile 或认证环境变量。AK/SK 不成对、仅提供 token 均必须拒绝；不得输出凭证值。

## 核心命令与证据采集

### 1. 构建或复用上下文

优先使用 `huawei-cloud-cce-observability-context-builder`
构建可观测上下文包；如果用户已经提供等价的告警、Events、日志、指标、范围、时间线和数据缺口，可以直接复用。

### 2. 验证工具

验证 `hcloud`、`kubectl` 和 `kubectl-cce`。缺插件时使用 `huawei-cloud-kubectl-cce-installer`。

```bash
hcloud version
kubectl version --client
kubectl plugin list
```

### 3. 发现集群元数据

使用只读 hcloud 命令：

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

### 4. 采集当前 Kubernetes 证据

通过插件采集，并且必须显式传入集群、区域和项目：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,svc,ingress,endpoints,endpointslices -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes,pv,pvc,storageclass -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

### 5. 补充专项证据

信号跨域时调用或参考对应依赖 skill 的报告，不在本 skill 里重复完整域诊断逻辑。

### 6. 补充历史证据

当前 Kubernetes 状态不足时，用告警、事件、指标、日志类 skill 补充 AOM/LTS/历史证据。

### 7. 记录数据缺口

所有采集失败都要记录命令类别、对象范围、脱敏错误和对置信度的影响。

## 根因分析流程

1. 建立故障时间线：用户感知时间、告警时间、Kubernetes Event 时间、发布/变更时间、恢复动作时间。
2. 明确影响面：目标工作负载/Pod/Service/Ingress/Node、命名空间、入口和依赖路径。
3. 按证据下钻：
   - 发布、副本、探针、启动命令、镜像、CrashLoop、NotReady -> workload 和 pod diagnoser；
   - 节点压力、NotReady、污点、kubelet/runtime、调度分布 -> node diagnoser；
   - Service、DNS、Ingress、EndpointSlice、NetworkPolicy、ELB/EIP/NAT/VPC -> network diagnoser；
   - PVC/PV/CSI/attach/mount -> storage diagnoser；
   - 服务拓扑和上下游影响 -> dependency-impact analyzer；
   - 近期发布、配置、网络、安全、节点或云侧变更 -> change-impact analyzer。
4. 将发现转成根因候选，每条都必须包含支持证据、反证、数据缺口、影响范围、置信度和验证步骤。
5. 按时间吻合度、直接证据、影响面、已知故障特征、反证和可恢复性排序 Top3。
6. 恢复动作只输出建议或交接说明；需要变更时交给 `huawei-cloud-cce-auto-remediation-runner`，并要求用户显式确认。

## 输出格式

Markdown 报告必须把关键信息放前面：

1. `## 总结`：故障概述、首要根因、影响范围、置信度和报告时间。
2. `## 根因分析`：Top3 根因、直接证据、反证、置信度，以及低排名原因为什么可能性更低。
3. `## 下一步措施`：立即验证、缓解建议、负责人交接和恢复 skill 交接。
4. `## 证据时间线`：用户现象、告警、Event、发布/变更、指标/日志证据按时间排序。
5. `## 排查步骤`：使用的命令/skill、脱敏错误和数据缺口。
6. `## 影响面`：受影响工作负载、Pod、Service、Ingress、Node、命名空间和上下游依赖。
7. `## 附录`：原始证据摘要、命令类别和限制。

有证据时不能只写“镜像拉取失败”“节点异常”“网络问题”“变更导致故障”。必须说明具体失败特征、为什么映射到该根因、缺什么证据、下一步怎么验证。

## 最佳实践

- 比较域级假设前，先建立共享时间线和对象范围。
- 依据直接证据和反证排序根因，不按症状出现次数排序。
- 采集器失败时保留数据缺口并降低置信度。
- 域级细节留在对应 diagnoser，本技能负责综合分析。

## 注意事项与安全规则

- 仅使用只读 `hcloud` 和 `kubectl cce` 操作。
- 不生成 kubeconfig，不调用云或 Kubernetes SDK。
- 不执行恢复、发布、节点、网络或存储变更。
- 脱敏凭据、token、header、代理信息、镜像仓库密钥和日志敏感值。

## 验证

改造后用以下扫描确认没有旧执行入口：

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]root[-_]cause|huawei[-_].*[-_]diagnose|huawei[-_].*[-_]analyze|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

期望结果：没有可执行 SDK dispatcher 入口，也没有裸 Kubernetes 访问路径。Markdown 中只能作为禁用项或验证项出现。

## 参考文档

- `references/kubectl-cce.md`：插件接入约束。
- `references/workflow.md`：证据链和根因排序。
- `references/output-schema.md`：结构化输出和 Markdown 布局。
- `references/risk-rules.md`：只读边界和交接规则。
