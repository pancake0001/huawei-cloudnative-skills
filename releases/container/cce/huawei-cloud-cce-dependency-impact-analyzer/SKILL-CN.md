---
name: huawei-cloud-cce-dependency-impact-analyzer
description: >
  使用 hcloud 和只读 kubectl-cce 证据分析华为云 CCE 依赖拓扑和影响面。 适用于用户需要确认故障影响了哪些工作负载、Pod、Service、Ingress、EndpointSlice、
  Node、入口或上下游路径，并需要传播路径、置信度限制或完整影响报告的场景。
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, dependency, impact]
---

# 华为云 CCE 依赖影响分析

## 概述

映射 CCE 服务拓扑并估算故障影响面，说明异常工作负载或 Pod 集合如何影响 Service、EndpointSlice、Ingress 入口和节点分布，同时区分静态可能路径与真实用户流量损失。

执行模型：

```text
hcloud CCE 查询集群 -> kubectl cce 拓扑快照 -> 目标匹配 -> 传播路径 -> 影响面报告 -> 诊断交接
```

不要使用 Python SDK dispatcher、旧 skill 执行动作、捆绑 SDK 脚本、kubeconfig 生成、直接 IAM HTTP 调用或 Huawei Cloud SDK import。

## 前置条件

1. `hcloud`、`kubectl` 和 kubectl-cce 均为当前平台可执行的原生二进制。
2. 凭据和项目上下文通过批准的受保护渠道提供。
3. IAM 允许只读发现 CCE 集群，Kubernetes RBAC 允许读取所需工作负载、Pod、Service、Ingress、EndpointSlice、Node 和 Event。
4. 访问 Kubernetes 前先读 `references/kubectl-cce.md`。工具或插件缺失时使用 `huawei-cloud-kubectl-cce-installer`；本 skill 不负责安装工具。
5. 不得打印凭据、Authorization header、插件认证信息、镜像仓库密钥、应用密钥，也不得输出对象数据中的敏感值。

## 相关 Skill

| Skill                                            | 使用场景                                                                |
| ------------------------------------------------ | ----------------------------------------------------------------------- |
| `huawei-cloud-cce-observability-context-builder` | 需要告警、日志、指标、Events 和时间线上下文确认真实影响                 |
| `huawei-cloud-cce-workload-failure-diagnoser`    | 目标工作负载不可用、发布卡住或 Pod 未 Ready                             |
| `huawei-cloud-cce-pod-failure-diagnoser`         | 单个 Pod 出现启动、镜像、调度、存储、探针或驱逐故障                     |
| `huawei-cloud-cce-node-failure-diagnoser`        | 影响集中在某个 Node 或可用区                                            |
| `huawei-cloud-cce-network-failure-diagnoser`     | Service、Ingress、EndpointSlice、DNS、策略、ELB 或 EIP 证据指向网络故障 |
| `huawei-cloud-cce-storage-failure-diagnoser`     | 涉及共享 PVC、PV、CSI、attach、mount 或存储后端依赖                     |
| `huawei-cloud-cce-change-impact-analyzer`        | 影响发生在发布、配置、路由、策略、Node 或基础设施变更之后               |
| `huawei-cloud-cce-root-cause-analyzer`           | 多个领域需要最终根因排序                                                |

## 参数确认

| 输入              | 必填 | 说明                                                |
| ----------------- | ---- | --------------------------------------------------- |
| `region`          | 是   | 请求上下文或 `HW_REGION_NAME`，否则要求用户输入                                   |
| `project_id`      | 是   | 显式传给 hcloud 和 kubectl-cce                      |
| `cluster_id`      | 推荐 | 没有时先用 hcloud 按名称定位                        |
| `namespace`       | 推荐 | 目标命名空间；仅在必要时使用全集群范围              |
| `target_name`     | 推荐 | 工作负载、Service、Pod、Ingress 或稳定 app label 值 |
| `label_selector`  | 可选 | 显式 selector 优先于名称前缀匹配                    |
| `failure_symptom` | 可选 | 用户可见故障或疑似受影响路径                        |
| `fault_time`      | 推荐 | 用于关联拓扑和可观测证据                            |

## 区域选择

优先使用当前请求或已建立任务上下文中的 `region`；未提供时读取 `HW_REGION_NAME`；两者都没有时停止执行并要求用户提供 `region` 或设置 `HW_REGION_NAME`，不得从 hcloud profile 推断区域。

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

### 3. 采集命名空间拓扑

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespace <namespace> -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,pods,svc,ingress,endpoints,endpointslices -n <namespace> -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

仅当命名空间未知或故障为集群级时使用 `-A`，并限制报告中的输出规模。Kubernetes 版本或 RBAC 不支持 EndpointSlice 时，使用 Endpoints 并记录数据缺口。

### 4. 补充佐证

需要证明真实流量或历史影响时，使用可观测上下文构建器或告警、事件、指标、日志类专项 skill。静态对象关系只能证明可能的传播路径。

### 5. 记录采集缺口

记录被拒绝的资源、范围、脱敏错误、使用的回退方式和对置信度的影响。不得通过 kubeconfig 或 SDK 绕过 kubectl-cce。

## 分析流程

1. 确认 region、project、cluster、namespace、目标对象、selector、故障现象和故障时间。
2. 优先使用 `label_selector` 匹配目标，其次使用工作负载 owner、Service selector、Pod 名称或稳定 label。沿 Pod -> ReplicaSet ->
   Deployment 以及 StatefulSet/DaemonSet 等价 owner 链向上关联。
3. 查找 selector 匹配目标 Pod label 的 Service。对 selectorless 或 `ExternalName`
   Service，检查类型及关联 Endpoints/EndpointSlices，不得直接判定为 selector 错误。
4. 查找引用目标 Service 的 Ingress rule 和 default backend，输出 host、path、后端 Service/port、ingress class 和 controller。
5. 将目标 Pod 和 endpoint Pod 映射到 Node 和可用区，关注单 Node 集中、NotReady 或压力节点以及可用区集中。
6. 外部路径按 `Ingress -> Service -> EndpointSlice/Endpoints -> Pods -> Nodes`，集群内路径按 `Service DNS -> EndpointSlice/Endpoints -> Pods -> Nodes` 建模。
7. 综合 Pod Ready、暴露入口、ready endpoint 比例、Node/可用区集中度，以及告警、日志、指标、Events 或用户现象进行影响评分。
8. 根因级证据交给 workload、Pod、Node、network、storage、change 或 root-cause 专项 skill。本 skill 负责拓扑和影响分析，不执行恢复。

## 输出格式

Markdown 报告必须从以下内容开始：

1. `## 总结`：受影响入口/后端、估计影响面、置信度，以及影响是已观测还是仅可能。
2. `## 影响路径`：从 Ingress 或 Service 到工作负载、Pod 和 Node 的路径表。
3. `## 下一步措施`：价值最高的验证和专项诊断交接。
4. `## 证据`：工作负载 owner、Pod Ready、Service selector/type、EndpointSlice/Endpoints、Ingress backend、Node 分布和 Events。
5. `## 置信度限制`：范围缺失、RBAC 拒绝、EndpointSlice 不可用、无流量证据、上游消费者未知或拓扑过期。
6. `## 附录`：有界命令轨迹和脱敏采集错误。

只有静态拓扑时，不得声称真实用户流量已受影响；必须由日志、指标、告警、批准测试路径产生的合成检查或明确用户现象支撑。

## 最佳实践

- 区分可能传播路径和已观测影响。
- 优先使用稳定 selector 和 ownerReference，不依赖名称前缀。
- 把 selectorless 和 `ExternalName` Service 当作特殊类型，不自动判错。
- 限制全集群快照规模，并记录快照时间。
- 评估置信度时保留反证和未知上游消费者。

## 注意事项与安全规则

- 仅使用只读 hcloud 和 kubectl-cce 操作。
- 不执行 apply、create、patch、edit、delete、scale、rollout undo、restart、exec、attach、port-forward、抓包、压测或主动流量生成。
- 不生成 kubeconfig，不调用云或 Kubernetes SDK。
- 不在证据和报告中暴露凭据、Secret 值、ConfigMap 敏感值或应用数据。
- 需要恢复时，在用户明确确认后交给批准的恢复流程。

## 验证

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]dependency[-_]impact|huawei[-_]get[-_]cce|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
git diff --check
```

期望结果：没有可执行 SDK dispatcher 入口、裸 Kubernetes 访问路径或变更命令。Markdown 命中只能是禁用项或验证文本。

## 参考文档

- `references/kubectl-cce.md`：插件接入约束。
- `references/workflow.md`：拓扑匹配、传播和交接流程。
- `references/output-schema.md`：结构化输出和 Markdown 布局。
- `references/risk-rules.md`：只读边界和置信度限制。
