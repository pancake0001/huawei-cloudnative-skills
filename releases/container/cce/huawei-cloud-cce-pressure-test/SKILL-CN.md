---
id: huawei-cloud-cce-pressure-test
name: huawei-cloud-cce-pressure-test
description: >
  使用 hcloud CLI 获取华为云 CCE 集群信息，并通过 `kubectl cce` 插件命令做 Kubernetes 预检、路由、压测 Job、日志和指标采集，使用 k6 发起受控流量。用户提到 CCE
  压测、负载测试、压力测试、性能测试、k6、ELB 流量测试、全链路压测、弹性评估或流量生成时使用本技能。不要使用 Python SDK dispatcher。
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, k6, elb, pressure-test]
---

# 华为云 CCE 压测技能

本技能通过华为云 `hcloud` CLI、Kubernetes `kubectl` 和 k6，对 CCE 工作负载进行受控压测、观测和报告生成。

执行模型：

```text
hcloud CCE 查询集群 -> kubectl cce 预检/路由/客户端证据 -> k6 发流 -> kubectl cce 指标/日志/事件 -> 压测报告
```

集群发现使用 CCE hcloud 命令，Kubernetes 访问使用 kubectl-cce 插件：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

通过 kubectl-cce 插件接入后，Deployment、StatefulSet、DaemonSet、Pod、Service、EndpointSlice、Ingress、HPA、PDB、Event、Job 日志和 metrics-server 指标都用
`kubectl cce` 读取。

需要南北向云侧上下文时，可以只读使用以下 hcloud 命令：

- `hcloud ELB ListLoadBalancers/v3`
- `hcloud ELB ListListeners/v3`
- `hcloud ELB ListPools/v3`
- `hcloud ELB ListMembers/v3`
- `hcloud ELB ListHealthMonitors/v3`
- `hcloud VPC ListSubnets`
- `hcloud VPC ListSecurityGroups/v3`
- `hcloud VPC ListSecurityGroupRules/v3`
- `hcloud EIP ListPublicips/v3`
- `hcloud NAT ListNatGateways`

禁止使用 Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、旧的 `huawei_*pressure*` action 或华为云 SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。插件接入约束见 `references/kubectl-cce.md`。

## 适用场景

- CCE 工作负载压测、k6 测试、负载测试、压力测试和性能基线。
- k6 client -> ELB -> ingress controller -> Service -> Pod 的全链路验证。
- 发流前检查已有工作负载的路由、后端和可观测性状态。
- 基线阶段与扩容/HPA 阶段的弹性对比。
- 分析压测期间出现的延迟、4xx/5xx、连接错误、超时、资源饱和或 HPA 响应慢。
- 根据流量结果和 Kubernetes/云侧证据生成 Markdown 报告。

如果只是普通故障诊断、没有压测语境，应使用 Pod、工作负载、节点或网络诊断 skill。

## 必要输入

准备发流前先收集：

| 输入                     | 必填                 | 说明                                                       |
| ------------------------ | -------------------- | ---------------------------------------------------------- |
| `region`                 | 是                   | 例如 `cn-north-4`                                          |
| `project_id`             | 通常需要             | 多数 hcloud CCE 操作需要项目 ID                            |
| `cluster_id`             | 推荐                 | 没有时用集群名从 `ListClusters` 定位                       |
| `cluster_name`           | 可选                 | 仅用于定位 `cluster_id`                                    |
| `namespace`              | 通常需要             | 目标工作负载 namespace                                     |
| `workload_name`          | 通常需要             | Deployment、StatefulSet 或 DaemonSet 名称                  |
| `workload_kind`          | 可选                 | 未指定时默认 Deployment                                    |
| `target_url`             | 发流前必填           | 外部 URL、Ingress URL 或经批准创建的 Service URL           |
| `target_port`            | 可选                 | 容器或 Service 目标端口                                    |
| `host_header`            | 可选                 | Ingress 使用 Host 规则时需要                               |
| `traffic_model`          | 是                   | `smoke`、`keepalive`、`short`、`ramp` 或用户自定义 k6 脚本 |
| `vus`、`duration`、`rps` | 是                   | 先小流量冒烟，再按批准范围提升                             |
| `test_window`            | 生产或类生产目标必填 | 包含负责人和停止条件                                       |
| `output_dir`             | 推荐                 | 保存压测摘要、日志、证据和报告                             |

目标、负责人或流量边界不清楚时，必须先停下来确认，不能直接发流。

## 前置条件

1. `hcloud` 已安装并在 `PATH` 中，或已定位到当前平台原生二进制并用 `hcloud version` 验证。示例统一写 `hcloud`，不要写死某个操作系统的绝对路径。
2. `kubectl` 已安装并与目标 Kubernetes 小版本兼容。Linux sandbox 使用 Linux kubectl，Windows 工作站使用 `kubectl.exe`。skill 流程里不要写死 `kubectl.exe`。
3. 本地已安装 k6，或准备使用经过用户批准的集群内 k6 Job 镜像。公网镜像拉取不稳定时，应先把 k6 镜像同步到同区域 SWR。
4. AK/SK 已配置到 hcloud。只用下面命令检查脱敏配置：

   ```bash
   hcloud configure list
   ```

5. IAM 至少允许 CCE 集群读取和使用 kubectl-cce API Gateway 接入。只有需要云侧网络证据时才需要 ELB/VPC/EIP/NAT 只读权限。
6. Kubernetes
   RBAC 允许读取工作负载、Service、EndpointSlice、Ingress、HPA、Event、Pod、Pod 日志、Job 日志和指标。写权限只在用户批准路由、客户端 Job 或扩缩容变更时需要。

不要在报告、命令输出、manifest 或日志中打印 AK、SK、security token、kubectl-cce 代理凭据、Authorization header、镜像仓库密钥或应用密钥。

## CCE hcloud 准备流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
k6 version
```

本地没有 k6 时，只有在用户批准 Job manifest 和目标地址后，才使用集群内 k6
Job。缺少 hcloud 或 kubectl 时，先安装或定位当前平台原生二进制，并验证实际使用的二进制。

### 2. 定位并检查集群

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

确认集群属于预期 region/project。kubectl-cce 插件默认访问 CCE API Gateway endpoint
`<cluster-id>.cce.<region>.myhuaweicloud.com`。如果该 endpoint 不适用于当前环境，设置 `CCE_ENDPOINT` 或传入 `--endpoint`。如果插件/API
Gateway 访问失败，在报告中记录错误和访问缺口；不要默认退回 kubeconfig 生成或 SDK 调用。

### 3. 配置 kubectl-cce 插件

执行 Kubernetes 命令前先阅读 `references/kubectl-cce.md`。本 skill 以 kubectl CCE 插件作为主要 Kubernetes 访问路径；不要生成 kubeconfig、不要改写 kubeconfig
server 字段、不要调用 Kubernetes SDK，也不要退回 SDK dispatcher 动作。

如果缺少 `kubectl` 或 `kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`
安装或修复本地前置工具。本诊断 skill 只负责验证和使用插件，不负责定义插件安装策略。

先验证本地工具和插件发现：

```bash
kubectl version --client
kubectl plugin list
```

通过受批准的工具参数、受保护的 shell 环境或本地凭据提供方配置插件认证，不要打印凭据值。诊断命令中显式传入集群、区域和项目 ID：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

仅当默认 `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint 不适用于当前环境时，才设置 `CCE_ENDPOINT` 或传入
`--endpoint`。如果插件访问失败，在报告中记录脱敏后的安装、凭据、API Gateway 可达性或 Kubernetes RBAC 缺口；不要切换到 kubeconfig 生成或 SDK 调用。

插件会阻断 `exec`、`attach`、`port-forward` 等流式命令；`logs -f` 和 `watch` 未强化，诊断报告中使用有限 `logs --tail` 和普通 `get` 命令。

### 4. 验证 Kubernetes 访问

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get deployments -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list jobs -n <client-namespace>
```

只有用户批准变更后，才检查对应写权限：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i create jobs -n <client-namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i create services -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i patch services -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i patch ingress -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i update deployments/scale -n <namespace>
```

RBAC 拒绝读取时，在报告中写明缺少的 verb/resource，并只继续采集允许读取的证据。RBAC 拒绝变更时，不能切换到 SDK 或手写 API 绕过。

## 压测流程

执行压测前阅读 `references/workflow.md`。标准流程：

1. 明确目标、负责人、流量模型、限制和停止条件。
2. 配置 kubectl-cce 插件凭据并验证 Kubernetes 访问。
3. 用 `kubectl cce` 做只读预检。
4. 选择发流模式：本地 k6 访问外部 URL，或经批准的集群内 k6 Job。
5. 对所有创建、patch、扩缩容或发流命令先展示 manifest/命令。
6. 先跑低流量冒烟。
7. 再跑经批准的 baseline 或 ramp 阶段。
8. 采集 k6 摘要、Job 日志、Events、HPA 状态、Pod 指标和可选 ELB/VPC 证据。
9. 生成报告，把总结、根因/瓶颈分析和下一步措施放在最前面。
10. 做弹性评估时，对比 baseline 与扩容/HPA 阶段，并明确数据缺口。

## 只读预检

先看 Kubernetes 对象和健康状态：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,svc,endpoints,endpointslice,ingress,hpa,pdb -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top nodes
```

`kubectl cce ... top` 不可用时，记录为指标缺口，不要编造资源趋势。

南北向流量需要云侧上下文且有相关 ID 时，可只读检查 ELB：

```bash
hcloud ELB ListLoadBalancers/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListListeners/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListPools/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
```

API 版本过滤参数不确定时，先运行 `hcloud <service> <operation> --help`。

## 发流方式

### 本地 k6

当前运行环境能访问 `target_url` 时优先使用本地 k6，这样不需要创建 Kubernetes 资源。

```bash
k6 run --vus <vus> --duration <duration> <script.js>
```

记录目标 URL、Host header、VUs、duration、threshold 和脚本路径。脚本里不能写入凭据或 bearer token。

### 集群内 k6 Job

目标是集群内地址，或当前环境无法访问目标时，可使用集群内 Job。Job 会创建 Kubernetes 资源并产生流量，必须先展示 manifest 并获得用户明确批准。

ConfigMap 和 Job 模板见 `references/manifest-templates.md`。批准后才执行：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> apply -f <approved-k6-manifest.yaml>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> wait --for=condition=complete job/<job-name> -n <client-namespace> --timeout=<timeout>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs job/<job-name> -n <client-namespace> --all-containers
```

Job 出现 `ImagePullBackOff` 或 `ErrImagePull` 时，以 Pod Events 为主证据，建议把 k6 镜像同步到同区域 SWR。

## 路由和扩缩容变更

Service、Ingress、样例工作负载、ELB 创建、工作负载扩缩容、HPA 调整和清理都不是自动动作。先展示准确 YAML 或命令，说明风险与回滚，再在用户明确批准后执行。

Kubernetes 路由 manifest 模板见 `references/manifest-templates.md`。

手动扩缩容弹性测试只在批准后执行：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> scale deployment/<workload-name> -n <namespace> --replicas=<replicas>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status deployment/<workload-name> -n <namespace> --timeout=180s
```

创建收费 ELB 前必须评审子网、AZ、规格、公网/私网暴露和成本影响。优先复用已有 ingress-controller ELB。

## 分析和场景指南

按直接证据和最先失败的层级排序：

1. 目标可达性、DNS/TLS/Host header。
2. Kubernetes 路由：Ingress -> Service -> EndpointSlice -> Ready Pod。
3. k6 客户端健康、镜像拉取和日志。
4. 应用响应码、超时和延迟。
5. Pod CPU/内存/重启/探针/资源压力。
6. HPA 指标和扩容时延。
7. 节点和集群容量。
8. ELB/listener/pool/member 健康与云网络限制。

识别 Top finding 后，阅读 `references/scenario-guides.md` 并套用对应场景。报告不能只写“压测失败”或“镜像拉取失败”，每个重要发现都要给出具体下一步检查和候选修复。

## 报告格式

详细结构见 `references/output-schema.md`。报告要把关键信息放在前面，命令轨迹和支撑表格放在结论之后。

用户侧报告按以下顺序输出：

- 执行摘要：测试状态、置信度、目标、流量阶段和一句话结论。
- 根因或瓶颈分析：按证据排序的 Top findings，并解释含义。
- 下一步措施：安全检查、候选修复、回滚/停止动作和移交对象。
- 测试范围：region、project、cluster、namespace、workload、URL、流量模型、时间窗口和批准记录。
- 流量结果：请求数、RPS、成功率、延迟分位、threshold 和 k6 错误。
- 路由和工作负载健康：Ingress、Service、EndpointSlice、Pod、Event、HPA、指标。
- 云侧证据：如已采集，列出 ELB/listener/pool/member/VPC/EIP/NAT 上下文。
- 反向证据和验证缺口。
- CLI 路径：使用过的 hcloud CCE、kubectl、k6 命令或 Job manifest。
- 明确说明哪些变更或发流动作已被批准并执行。

## 安全边界

应用 manifest 或发流前阅读 `references/risk-rules.md`。本技能可以执行只读检查和生成报告，但不能自动执行：

- `kubectl cce ... apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout restart`、`rollout undo`
- 对真实目标执行本地 `k6 run` 或集群内 k6 Job 发流
- hcloud create/update/delete 操作，包括创建 ELB
- HPA、节点池、NAT、安全组或 EIP 变更
- 任何 SDK dispatcher action

## 验证

CLI 验证清单见 `references/verification-method.md`。有效实现应满足：

- `hcloud version`、`hcloud configure list`、`kubectl version --client` 可用，并且本地 `k6 version` 或已批准的集群内 Job 镜像验证可用。
- `hcloud CCE ListClusters`、`ShowCluster`、`ShowClusterEndpoints` 可用，`kubectl cce ...` 能读取目标集群。
- `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 能读取目标 namespace 和工作负载。
- 大流量前先执行冒烟压测。
- 本 skill 包中搜索不到 SDK dispatcher 入口。

## 参考文档

- `references/workflow.md` - 分阶段压测流程和证据顺序。
- `references/manifest-templates.md` - 本地 k6、集群内 k6 Job、Service、Ingress 模板。
- `references/scenario-guides.md` - 场景化分析和下一步建议。
- `references/common-pitfalls.md` - 压测常见陷阱和 CLI 示例。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 发流、变更和收费资源边界。
- `references/verification-method.md` - 环境和 CLI 验证。
- `references/iam-policies.md` - IAM 和 Kubernetes RBAC 要求。
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/
