---
name: huawei-cloud-cce-change-impact-analyzer
description: >
  使用 hcloud、只读 kubectl-cce 和可观测证据分析近期华为云 CCE 变更是否导致或放大故障。 适用于工作负载发布、ConfigMap 或 Secret
  元数据、Service、Ingress、Gateway、 NetworkPolicy、RBAC、Node、节点池或云网络变更，并需要时间线关联、影响面、 风险评分或完整影响报告的场景。
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, change-impact, analysis]
---

# 华为云 CCE 变更影响分析

## 概述

把“故障前发生过什么变更”转成有证据支撑的因果归因。关联当前拓扑、Kubernetes
Events、历史证据、AOM 告警、指标、日志和只读云资源元数据，对可能导致或放大CCE 故障的变更进行排序。

执行模型：

```text
hcloud CCE 查询集群 -> kubectl cce 当前状态 -> 历史证据交接 -> 变更分类 -> 时间线关联 -> 影响面 -> 报告
```

不要使用 Python SDK dispatcher、旧 skill 执行动作、捆绑 SDK 脚本、kubeconfig 生成、直接 IAM HTTP 调用或 Huawei Cloud SDK import。

## 前置条件

1. `hcloud`、`kubectl` 和 kubectl-cce 均为当前平台可执行的原生二进制。
2. 凭据和项目上下文通过批准的受保护渠道提供。
3. IAM 和 Kubernetes RBAC 允许所需集群、拓扑、Event、工作负载、策略和元数据只读查询。
4. 访问 Kubernetes 前先读 `references/kubectl-cce.md`。工具或插件缺失时使用 `huawei-cloud-kubectl-cce-installer`；本 skill 不负责安装工具。
5. 已提供故障时间或有界故障窗口，否则必须明确记录为置信度限制。
6. 不得打印凭据、Authorization header、插件认证信息、Secret 值、ConfigMap 敏感值、镜像仓库凭据或应用密钥。

## 相关 Skill

| Skill                                            | 使用场景                                                                                 |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| `huawei-cloud-cce-observability-context-builder` | 先构建共享范围、时间线、告警、Event、日志、指标和数据缺口上下文                          |
| `huawei-cloud-cce-kubernetes-event-analyzer`     | 需要超出当前 Event 窗口的历史或当前 Kubernetes Events                                    |
| `huawei-cloud-cce-alarm-correlation-engine`      | 需要 AOM 当前/历史告警、告警风暴或告警时间锚点                                           |
| `huawei-cloud-cce-metric-analyzer`               | 需要指标证明变更后发生性能退化                                                           |
| `huawei-cloud-cce-workload-failure-diagnoser`    | 可疑变更涉及镜像、命令、探针、资源、环境变量、selector 或 volume                         |
| `huawei-cloud-cce-network-failure-diagnoser`     | 可疑变更涉及 Service、Ingress、Gateway、NetworkPolicy、ELB、EIP、NAT、安全组、ACL 或路由 |
| `huawei-cloud-cce-node-failure-diagnoser`        | 可疑变更涉及节点污点、cordon/drain、节点池、升级、压力或 NotReady                        |
| `huawei-cloud-cce-storage-failure-diagnoser`     | 可疑变更涉及 PVC、StorageClass、CSI、拓扑、挂载或存储后端                                |
| `huawei-cloud-cce-dependency-impact-analyzer`    | 需要映射影响面和服务拓扑                                                                 |
| `huawei-cloud-cce-root-cause-analyzer`           | 变更发现需要和其他根因候选一起排序                                                       |

## 参数确认

| 输入                                | 必填 | 说明                                                            |
| ----------------------------------- | ---- | --------------------------------------------------------------- |
| `region`                            | 是   | 例如 `cn-north-4`                                               |
| `project_id`                        | 是   | 显式传给 hcloud 和 kubectl-cce                                  |
| `cluster_id`                        | 推荐 | 没有时先用 hcloud 按名称定位                                    |
| `namespace`                         | 可选 | 优先按命名空间采集；核心系统和网络变更保留全集群视角            |
| `target_name`                       | 可选 | 工作负载、Service、Pod、Ingress、Gateway、Node 或稳定 app label |
| `fault_time`                        | 推荐 | 时间先后排序锚点                                                |
| `hours` / `start_time` / `end_time` | 推荐 | 使用尽可能窄的有效故障窗口                                      |
| `known_changes`                     | 可选 | 用户提供的发布、配置、策略或基础设施变更记录                    |
| `log_group_id` / `log_stream_id`    | 可选 | 仅在批准的日志发现无法定位来源时使用                            |

## 核心命令

### 1. 验证工具和插件

```bash
hcloud version
hcloud configure list
kubectl version --client
kubectl plugin list
```

工具或插件缺失时停止当前流程，使用 `huawei-cloud-kubectl-cce-installer`；不得下载安装器，也不得回退到 SDK 或 kubeconfig 接入。

### 2. 发现集群上下文

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

### 3. 采集当前工作负载和拓扑状态

命名空间明确时优先按 namespace 采集。仅对集群级变更使用 `-A`，并控制证据规模。

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,pods,svc,ingress,endpoints,endpointslices,networkpolicy -n <namespace> -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

读取保留的控制器 revision 证据，不改变工作负载：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout history <deployment|statefulset|daemonset>/<workload-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get rs -n <namespace> -o json
```

### 4. 安全采集配置和安全元数据

只采集 ConfigMap 和 Secret metadata，不从集群读取 `data`、`binaryData` 或 `stringData`。

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get configmap,secret -n <namespace> -o custom-columns='KIND:.kind,NAMESPACE:.metadata.namespace,NAME:.metadata.name,RESOURCE_VERSION:.metadata.resourceVersion,CREATED_AT:.metadata.creationTimestamp'
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get role,rolebinding,serviceaccount -n <namespace> -o json
```

怀疑 Gateway API 或集群级 RBAC 变更时，只采集相关对象；CRD 不存在或 RBAC 被拒绝时记录为数据缺口：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get gateway,httproute -n <namespace> -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get clusterrole,clusterrolebinding -o json
```

当前 resourceVersion、创建时间、managed fields 和保留的 ReplicaSet 本身不能证明变更时间、操作者、历史值或因果关系。

### 5. 采集历史和可观测证据

使用可观测上下文构建器以及 Event、alarm、metric 或 log 专项 skill 获取历史证据。优先使用批准的审计/CTS/LTS 记录或用户提供的脱敏 before/after
manifest。历史来源不存在时记录数据缺口，不得编造变更时间线，也不得推断 Secret 内容。

### 6. 采集云侧当前状态

只有资源标识已知或可安全推导时才使用只读 hcloud
operation。节点池、ELB、EIP、NAT、VPC、安全组和 ACL 证据交给 Node 或 Network 专项 skill，并关联其命令轨迹。本地 KooCLI operation 形态不同时先运行
`hcloud <service> <operation> --help`。没有 CTS/审计证据时，云侧当前状态不能当作云侧变更历史。

## 分析流程

1. 明确故障窗口、故障时间、受影响对象、用户现象和已知变更记录。
2. 从保留的 workload revision、当前 Events、批准的审计/LTS/CTS 记录、告警、日志、指标和用户提供的变更证据中建立候选。
3. 每个候选记录来源、时间、可用的操作者、对象、变更字段摘要，以及是否存在可靠的 before/after 值。
4. 忽略 controller status 更新、Lease/Event 噪声、HPA 单纯副本调整、Pod binding、status subresource 写入和平台托管 RBAC，除非其他证据把它们与故障关联。
5. 将候选分为工作负载、配置、网络、安全、存储或基础设施变更。分类证据不得包含 Secret 值。
6. 把每个候选映射到当前 Pod、Service、Ingress/Gateway、Node、命名空间、存储对象和上下游依赖路径。
7. 按时间先后、拓扑重合、变更后响应信号、专项诊断确认和反证排序。数值评分仅用于相对比较，不能作为因果证明。
8. 输出 Top N 变更风险、证据、反证、数据缺口、置信度和最有区分度的下一步验证。

## 输出格式

Markdown 报告必须从以下内容开始：

1. `## 总结`：最可疑变更、影响范围、置信度、证据充分性，以及因果已确认还是仅怀疑。
2. `## 变更影响分析`：排序变更、时间、来源、变更字段摘要、受影响对象、证据、反证、分数和置信度。
3. `## 下一步措施`：价值最高的验证、专项诊断交接和必要的批准恢复交接。
4. `## 证据时间线`：变更、Event、告警、指标/日志、诊断和用户现象的统一时间线。
5. `## 影响面`：受影响工作负载、Pod、Service、Ingress/Gateway、Node、命名空间、存储对象和依赖路径。
6. `## 数据缺口`：审计/LTS/CTS 历史不可用、before/after 缺失、RBAC 拒绝、revision 缺失、操作者未知或云侧历史缺口。
7. `## 附录`：有界命令轨迹、证据来源和脱敏采集错误。

不能只因对象发生过更新就断定“变更导致故障”。必须同时具备时间先后关系，以及至少一个匹配的响应信号或专项诊断结论。

## 最佳实践

- 排序变更前先建立共享故障时间线。
- 区分当前状态、保留 revision、审计历史和用户陈述。
- 优先输出字段级摘要和 hash，不输出敏感配置值。
- 保留反证和发生在故障之后的候选。
- 使用专项域诊断确认变更字段与故障特征是否一致。

## 注意事项与安全规则

- 仅使用只读 hcloud 和 kubectl-cce 操作。
- 不执行 rollback、apply、create、patch、edit、delete、scale、restart、drain、reboot、rollout undo、exec、attach、port-forward、抓包或主动流量生成。
- 禁止读取或输出 Kubernetes Secret 值。默认不读取 ConfigMap data，只使用 metadata 或用户提供的脱敏 before/after 证据。
- 不生成 kubeconfig，不调用云或 Kubernetes SDK。
- 需要恢复时，在用户明确确认后交给批准的恢复流程。

## 验证

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]change[-_]impact|huawei[-_]query|huawei[-_]get[-_]cce|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
git diff --check
```

期望结果：没有可执行 SDK dispatcher 入口、裸 Kubernetes 访问路径、变更命令或 Secret 值采集。Markdown 命中只能是禁用项或验证文本。

## 参考文档

- `references/kubectl-cce.md`：插件接入约束。
- `references/workflow.md`：变更候选、关联、评分和交接流程。
- `references/capability-map.md`：证据来源、隐私控制和已知缺口。
- `references/output-schema.md`：结构化输出和 Markdown 布局。
- `references/risk-rules.md`：只读边界和恢复交接规则。
