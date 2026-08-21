---
name: huawei-cloud-cce-pod-failure-diagnoser
description: >
  使用 hcloud 和只读 kubectl-cce 证据诊断华为云 CCE Pod 故障。 适用于 CrashLoopBackOff、ImagePullBackOff、ErrImagePull、OOMKilled、Pending、
  FailedScheduling、FailedMount、FailedAttachVolume、探针失败、sandbox 或 CNI 失败、 频繁重启、Error、RunContainerError 或 Evicted 等场景。
version: 1.0.1
tags: [huawei-cloud, cce, kubectl, pod, diagnosis]
---

# 华为云 CCE Pod 故障诊断

## 概述

本技能通过华为云 `hcloud` CLI 和 Kubernetes `kubectl` 诊断 CCE 集群中的单个 Pod 或一组 Pod 故障。

**执行模型**：`hcloud CCE` 查询集群 -> `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id>`
只读采集 Pod 证据 -> 原因排序与移交建议。

集群级操作使用 CCE hcloud 命令：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

通过 kubectl-cce 插件接入后，Pods、Events、日志、Service、PVC、Node、metrics-server 指标等 Kubernetes 资源都用
`kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id>` 读取。

禁止使用 Python SDK dispatcher、旧 skill 执行动作、旧 Huawei Pod action 或本 skill 包内 SDK 脚本。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。插件接入约束见 `references/kubectl-cce.md`。

## 适用场景

- Pod `CrashLoopBackOff`、`Error`、`RunContainerError` 或频繁重启。
- Pod `ImagePullBackOff`、`ErrImagePull` 或镜像仓库认证/拉取失败。
- Pod `OOMKilled`、退出码 `137` 或内存限制压力。
- Pod `Pending`、`FailedScheduling`、`FailedMount`、`FailedAttachVolume` 或 sandbox 创建失败。
- Pod `Evicted`、节点 MemoryPressure/DiskPressure/ephemeral-storage 压力。
- 需要关联容器当前日志、previous 日志、Events、重启次数、探针失败和 Pod 资源使用情况。

本技能不执行变更操作。扩缩容、删除、重启、回滚、cordon、drain、taint、节点操作都只输出建议，并移交到对应恢复类 skill。

## 参数确认

| 输入            | 必填     | 说明                                        |
| --------------- | -------- | ------------------------------------------- |
| `region`        | 是       | 请求上下文或 `HW_REGION_NAME`，否则要求用户输入                           |
| `project_id`    | 通常需要 | hcloud 操作需要项目 ID 或存在多项目时应提供 |
| `cluster_id`    | 推荐     | 没有时先用 `ListClusters` 查找              |
| `namespace`     | 是       | Kubernetes namespace                        |
| `pod_name`      | 推荐     | 目标 Pod 名称                               |
| `workload_name` | 可选     | 不知道 Pod 名时用工作负载推导 selector      |
| `selector`      | 可选     | 例如 `app=my-app`                           |

## 区域选择

优先使用当前请求或已建立任务上下文中的 `region`；未提供时读取 `HW_REGION_NAME`；两者都没有时停止执行并要求用户提供 `region` 或设置 `HW_REGION_NAME`，不得从 hcloud profile 推断区域。

## 前置条件

1. `hcloud` 已安装并在 `PATH` 中。不同平台使用对应原生二进制，命令示例统一写 `hcloud ...`，不要硬编码 Windows 或 Linux 专属路径。
2. `kubectl` 已安装，并与目标 Kubernetes 小版本兼容。很多 agent sandbox 运行在 Linux，即使开发机是 Windows，也不要在流程里写死 `kubectl.exe`。
3. 如果 `hcloud` 或 `kubectl` 不在 `PATH` 中，先定位当前平台可执行的二进制，赋值给 shell 变量，并用 `version` 验证后再用。不要因为某个文件名叫 `kubectl.exe` 或
   `hcloud.exe` 就假设它适配当前 OS。
4. AK/SK 已配置到 hcloud。只用 `hcloud configure list` 检查配置，不打印密钥。
5. IAM 至少允许 list/show CCE 集群并使用 kubectl-cce API Gateway 接入。
6. kubectl-cce 认证用户具备目标 namespace 中读取 Pod、Events、logs、Service、PVC、Node、metrics 的 RBAC 权限。

最终报告里不要输出 AK、SK、security token、kubectl-cce 代理凭据或 Authorization header。日志片段必须脱敏。

## 核心命令与准备流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
```

如果缺少 `kubectl`、`kubectl-cce` 或 `hcloud`，停止当前诊断流程，改用 `huawei-cloud-kubectl-cce-installer`
或批准的平台安装流程。本诊断技能不得下载或执行安装脚本。安装流程必须选择当前平台的原生二进制、固定批准版本、校验官方发布的 checksum 或签名，然后重新执行上述版本检查。

### 2. 查找 CCE 集群

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
```

用户只提供集群名时，从列表中匹配并记录集群 UUID。

### 3. 检查集群元数据和访问端点

```bash
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

确认集群属于正确 region/project，状态可用，并判断当前网络能否访问 API Server。

kubectl-cce 插件默认访问 CCE API Gateway endpoint `<cluster-id>.cce.<region>.myhuaweicloud.com`。如果该 endpoint 不适用于当前环境，设置 `CCE_ENDPOINT` 或传入
`--endpoint`。如果插件/API Gateway 访问失败，在报告中记录错误和访问缺口；不要默认退回 kubeconfig 生成或 SDK 调用。

### 4. 配置 kubectl-cce 插件

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
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

仅当默认 `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint 不适用于当前环境时，才设置 `CCE_ENDPOINT` 或传入
`--endpoint`。如果插件访问失败，在报告中记录脱敏后的安装、凭据、API Gateway 可达性或 Kubernetes RBAC 缺口；不要切换到 kubeconfig 生成或 SDK 调用。

插件会阻断 `exec`、`attach`、`port-forward` 等流式命令；`logs -f` 和 `watch` 未强化，诊断报告中使用有限 `logs --tail` 和普通 `get` 命令。

### 5. 验证 Kubernetes 只读权限

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get nodes
```

如果 RBAC 拒绝某项读取，在报告里列为缺口，只继续采集允许读取的证据。

## 诊断流程

详细证据顺序和分类规则见 `references/workflow.md`。

### 先扫异常 Pod

深挖前先找异常 Pod 和重启较多的 Pod：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A --field-selector=status.phase!=Running -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,NODE:.spec.nodeName"
```

`field-selector` 适合发现明显的 `Pending`/`Failed` Pod；custom-columns 用来发现 `Running` 但未 Ready 或重启数异常的 Pod。

### 查找目标 Pod

已知 Pod 名时：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <pod-name> -n <namespace> -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <pod-name> -n <namespace> -o yaml
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
```

只知道工作负载名时，先从工作负载推导 selector：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get deployment <workload-name> -n <namespace> -o yaml
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o yaml
```

StatefulSet 或 DaemonSet 替换为对应资源类型。

### 采集 Events

优先 Pod 相关事件，再看 namespace 时间线：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

Kubernetes Events v1 API 可用时：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

只引用能映射到目标 Pod、owner、同 selector Pod、相关 Node/PVC 的 Events。

### 采集日志

CrashLoopBackOff、OOMKilled、频繁重启优先看 previous 日志：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
```

多容器 Pod 必要时指定容器：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> -c <container-name> --previous --tail=200
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> -c <container-name> --tail=200
```

`ImagePullBackOff` 通常没有容器日志，不要反复查日志，优先看 Events。

如果镜像拉取失败时日志命令返回 `container is waiting to start: trying and failing to pull image` 或
`previous terminated container ... not found`，这说明容器从未启动，是支持镜像拉取失败的证据，不是 kubectl 故障。

### 采集指标和节点上下文

metrics-server 可用时：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod <pod-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod <pod-name> -n <namespace> --containers
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod -n <namespace> --sort-by=memory
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top node
```

metrics-server 不可用且 `kubectl cce ... top` 返回 `Metrics API not available` 时，把指标缺失写进验证缺口，不要编造趋势。本技能内不要切换到 Python SDK、AOM
SDK 或手写 API 来补这个缺口。

Pending、Evicted 或节点压力相关时：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
```

存储相关时：

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pv
```

## 原因排序

按 Pod 生命周期中最先失败的层级排序：

1. Pod 未通过准入或 sandbox/network 创建失败。
2. Pod 存在但无法调度。
3. Pod 已调度但卷无法 attach/mount。
4. 镜像无法拉取。
5. 容器启动后退出或崩溃。
6. 容器运行但 startup/liveness/readiness 探针失败。
7. 节点压力或驱逐解释 Pod 故障。

常见原因标签：

| 原因                       | 证据                                                          |
| -------------------------- | ------------------------------------------------------------- |
| `CrashLoopOrAppExit`       | `CrashLoopBackOff`、非零退出码、previous 日志                 |
| `ContainerCommandNotFound` | 启动错误显示命令不存在或无法执行                              |
| `ImagePullFailure`         | `ImagePullBackOff`、`ErrImagePull`、镜像认证/标签/DNS 错误    |
| `OOMKilled`                | last state、退出码 137、内存限制或指标                        |
| `SchedulingBlocked`        | Pod Pending 且有 `FailedScheduling`                           |
| `StorageMountFailure`      | `FailedMount`、`FailedAttachVolume`、PVC Pending              |
| `ProbeFailure`             | startup/liveness/readiness probe 的 `Unhealthy` Events        |
| `NodePressureOrEviction`   | Evicted、节点压力条件、taints、NotReady                       |
| `QuotaOrAdmissionRejected` | Events 提到 quota、LimitRange、webhook、denied、forbidden     |
| `SandboxOrCNIBlocked`      | `FailedCreatePodSandBox`、CNI、IP 分配或 runtime sandbox 错误 |

## 输出格式

用户侧报告要把决策信息放前面；命令轨迹和支撑证据放在读者已经看到结论之后。

报告应按这个顺序输出：

- 执行摘要：状态、置信度、受影响 Pod/workload 和一句话结论。
- 根因分析：Top causes，附直接证据和人能看懂的解释。
- 下一步措施：立即可做的安全检查、候选修复路径、移交对象或 skill。
- 目标：region、project、cluster、namespace、Pod/workload/selector。
- Pod 生命周期漏斗的通过/失败层。
- 反向证据：为什么排除了相邻原因，例如调度、节点 NotReady、日志、指标、OOM、存储、探针等。
- 当前日志和 previous 日志发现。
- 指标、节点、存储等缺口。
- 详细证据：相关 Events、状态字段、owner/workload 信息和关键命令证据。
- CLI 路径：使用过的 hcloud CCE 和 kubectl-cce 证据命令。
- 明确说明没有执行变更命令。

识别 Top Cause 后，读取 `references/scenario-guides.md`
并套用对应场景。这个规则适用于所有明确故障类型，不只适用于镜像拉取失败。场景指南覆盖 ImagePullBackOff、CrashLoopBackOff、OOMKilled、Pending、存储挂载、Evicted、探针失败、CNI/sandbox、Admission/Quota 等场景，并给出每类的解释、反向证据、下一步检查、候选修复和移交建议。

详细结构见 `references/output-schema.md`。

## 最佳实践

- 从 Pod 生命周期最先失败的层级开始，依据直接证据排序候选根因。
- 将 Events、日志和指标采集限制在目标范围和相关时间窗口内。
- 明确记录反向证据和验证缺口，不推测无法获得的数据。
- 命令示例始终使用参数占位符，并脱敏凭据、令牌、请求头和镜像仓库密钥。
- 将只读诊断与变更修复分离，为每项拟议变更注明移交对象。

## 注意事项与安全边界

诊断前阅读 `references/risk-rules.md`。本技能只读，禁止执行：

- `kubectl cce ... apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout undo`、`cordon`、`drain`、`taint`
- 任何 hcloud create/update/delete 操作
- 任何 SDK dispatcher action

## 验证

按 `references/verification-method.md` 检查：

- `hcloud version`、`hcloud configure list`、`kubectl version --client` 可用。
- `hcloud CCE ListClusters` 和 `ShowCluster` 能定位目标集群。
- `kubectl cce ...` 能通过 CCE API Gateway 读取目标集群。
- `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id>` 能读取目标 namespace。
- 本 skill 包中没有 SDK dispatcher 入口或 SDK 脚本残留。

## 参考文档

- `references/workflow.md` - 证据顺序和故障分类规则。
- `references/scenario-guides.md` - 各故障场景的解释、下一步检查、候选修复和移交建议。
- `references/common-pitfalls.md` - 常见误区和 CLI 示例。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 只读边界和移交规则。
- `references/verification-method.md` - 环境和 CLI 验证。
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/


## x509 TLS 重试

当 `kubectl cce` 返回 `x509` 证书校验错误时，使用完全相同的命令，并在 `cce` 后追加 `--cce-insecure-upstream-tls=true` 重试。例如：`kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`。仅在出现该 TLS 校验错误时使用此参数。


## 集群 ID 输入

`cluster_id` 应传入标准 UUID。若输入值不是标准 UUID，先调用集群资源列表查询，并按集群名称做精确匹配；仅在唯一匹配时将名称转换为对应 UUID。未匹配或匹配到多个集群时，必须要求用户提供 UUID，不得猜测或任意选择集群。
