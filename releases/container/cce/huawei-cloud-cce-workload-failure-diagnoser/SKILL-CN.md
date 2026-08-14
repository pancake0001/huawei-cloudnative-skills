---
name: huawei-cloud-cce-workload-failure-diagnoser
description: >
  使用 hcloud 发现华为云 CCE 集群，并通过只读 kubectl-cce 证据诊断 Deployment、
  StatefulSet 和 DaemonSet 发布或可用性故障。适用于发布卡住、副本不可用、
  Pod 未 Ready、ImagePullBackOff、CrashLoopBackOff、探针或调度失败、
  PVC 挂载失败或工作负载 Events。
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, workload, diagnosis]
---

# 华为云 CCE 工作负载故障诊断

## 概述

此 skill 通过华为云 `hcloud` CLI 和 Kubernetes `kubectl` 诊断 CCE 工作负载发布和可用性故障。

**执行模型**：`hcloud CCE` 查询集群 -> `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 只读采集工作负载证据 -> 根因排序与移交建议。

集群级操作使用 CCE hcloud 命令：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

通过 kubectl-cce 插件接入后，使用 `kubectl cce` 查看 Kubernetes 资源。工作负载、ReplicaSet、Pod、Event、日志、PVC、Service、Ingress、HPA 和 Node
都属于 Kubernetes 资源，应通过 `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 检查。

此 skill 不使用 Python SDK dispatcher、旧 skill 执行动作、旧 Huawei workload 动作或捆绑 SDK 脚本。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。插件接入约束见 `references/kubectl-cce.md`。

## 何时使用

此 skill 适用于：

- Deployment 发布卡住、`ProgressDeadlineExceeded`、旧副本残留或新副本未就绪。
- StatefulSet 或 DaemonSet 更新失败、副本不可用或发布停滞。
- CCE 工作负载状态异常，但用户需要先拿到证据再做修复。
- 工作负载下钻出的 Pod 级症状，包括 `Pending`、`FailedScheduling`、`ImagePullBackOff`、`ErrImagePull`、`CrashLoopBackOff`、`OOMKilled`、`Evicted`、`FailedMount`、`Unhealthy` 或 `ContainersNotReady`。
- 需要关联 Event、日志、selector、ReplicaSet、PVC、HPA、Service、Ingress 或 Node 证据来判断 CCE 工作负载问题。

不要用此 skill 修改资源。扩缩容、删除、重启、回滚、cordon、drain 或节点操作只能作为建议移交，不能直接执行。

## 参数确认

诊断前先收集这些值：

| 输入 | 是否必需 | 说明 |
| --- | --- | --- |
| `region` | 是 | 例如：`cn-north-4` |
| `project_id` | 通常需要 | 当 hcloud 操作要求项目 ID，或存在多个项目时传入 |
| `cluster_id` | 优先提供 | 如果没有，先用 `ListClusters` 查找 |
| `namespace` | 是 | Kubernetes 命名空间 |
| `kind` | 是 | `Deployment`、`StatefulSet` 或 `DaemonSet` |
| `name` | 是 | 工作负载名称 |
| `selector` | 可选 | 未提供时从工作负载中推导 |

## 前置条件

1. `hcloud`（华为云 KooCLI）已安装并可在 `PATH` 中访问。使用运行环境对应平台的原生二进制。Linux sandbox 应使用 Linux 版 KooCLI 安装脚本或 tar 包；macOS 和 Windows 使用对应安装包。skill 命令应写成 `hcloud ...`，不要写平台专属的可执行文件路径。
2. `kubectl` 已安装，并与目标 Kubernetes 小版本兼容。使用运行环境对应平台的原生二进制（`linux-amd64`、`linux-arm64`、`darwin-*` 或
   `windows-amd64`）。很多 agent sandbox 会运行在 Linux 上，所以不要在 skill 流程中硬编码 Windows 专属 `kubectl.exe` 路径。
3. AK/SK 凭据已配置到 hcloud。只用 `hcloud configure list` 检查配置是否存在，不打印密钥。
4. 调用方拥有华为云 IAM 权限，可以列出/查看 CCE 集群并使用 kubectl-cce API Gateway 接入。
5. kubectl-cce 认证用户拥有 Kubernetes RBAC 权限，可以读取目标命名空间中的必要资源。

最终报告中不要打印 AK、SK、安全令牌、kubectl-cce 代理凭据或 Authorization header。日志中必须脱敏密钥。

## 核心命令与准备流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
```

如果缺少 `kubectl`、`kubectl-cce` 或 `hcloud`，停止当前诊断流程，改用
`huawei-cloud-kubectl-cce-installer` 或批准的平台安装流程。本诊断技能不得下载或
执行安装脚本。安装时固定批准版本、校验官方 checksum 或签名，再重新执行上述版本检查。

### 2. 定位 CCE 集群

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
```

如果用户提供的是集群名而不是集群 ID，从集群列表中匹配目标集群并记录集群 UUID。

### 3. 检查集群元数据

```bash
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

使用这些证据确认集群处于可用状态、位于预期 region/project，并且当前网络可以访问。

kubectl-cce 插件默认访问 CCE API Gateway endpoint `<cluster-id>.cce.<region>.myhuaweicloud.com`。如果该 endpoint 不适用于当前环境，设置
`CCE_ENDPOINT` 或传入 `--endpoint`。如果插件/API Gateway 访问失败，在报告中记录错误和访问缺口；不要退回 kubeconfig 生成或 SDK 调用。

### 4. 配置 kubectl-cce 插件

执行 Kubernetes 命令前先阅读 `references/kubectl-cce.md`。本 skill 以 kubectl CCE 插件作为主要 Kubernetes 访问路径；不要生成 kubeconfig、不要改写 kubeconfig server 字段、不要调用 Kubernetes SDK，也不要退回 SDK dispatcher 动作。

如果缺少 `kubectl` 或 `kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer` 安装或修复本地前置工具。本诊断 skill 只负责验证和使用插件，不负责定义插件安装策略。

先验证本地工具和插件发现：

```bash
kubectl version --client
kubectl plugin list
```

通过受批准的工具参数、受保护的 shell 环境或本地凭据提供方配置插件认证，不要打印凭据值。诊断命令中显式传入集群、区域和项目 ID：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

仅当默认 `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint 不适用于当前环境时，才设置 `CCE_ENDPOINT` 或传入 `--endpoint`。如果插件访问失败，在报告中记录脱敏后的安装、凭据、API Gateway 可达性或 Kubernetes RBAC 缺口；不要切换到 kubeconfig 生成或 SDK 调用。

插件会阻断 `exec`、`attach`、`port-forward` 等流式命令；`logs -f` 和 `watch` 未强化，诊断报告中使用有限 `logs --tail` 和普通 `get` 命令。

### 5. 验证 Kubernetes 访问

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get deployments -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
```

如果 RBAC 拒绝某个读操作，报告缺失权限，并停止或基于部分证据继续诊断。

## 诊断流程

阅读 `references/workflow.md` 获取详细证据顺序和故障规则。

当多个命名空间中的大量工作负载同时不可用时，先检查集群级共性证据，再下钻单个工作负载：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

如果所有候选节点都是 `Ready=Unknown`、`NotReady`，或带有 `node.kubernetes.io/unreachable`、`node.cloudprovider.kubernetes.io/shutdown` taint，则应将共性的节点/调度阻塞排在单个工作负载症状之前。

### Deployment 证据

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deployment <name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe deployment <name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status deployment/<name> -n <namespace> --timeout=30s
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout history deployment/<name> -n <namespace>
```

从 `spec.selector.matchLabels` 推导 selector，然后检查 ReplicaSet 和 Pod：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get rs -n <namespace> --selector='<selector>' -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o yaml
```

按 ownerReference 过滤 ReplicaSet，只保留指向 Deployment UID 的对象。将 `deployment.kubernetes.io/revision` 最大的 ReplicaSet 视为新版本。

### StatefulSet 证据

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get statefulset <name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe statefulset <name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status statefulset/<name> -n <namespace> --timeout=30s
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
```

对比 `spec.replicas`、`status.currentReplicas`、`status.updatedReplicas`、`status.readyReplicas`、`status.availableReplicas`，以及 `spec.updateStrategy` 中的 partition 设置。

### DaemonSet 证据

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get daemonset <name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe daemonset <name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status daemonset/<name> -n <namespace> --timeout=30s
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> --selector='<selector>' -o wide
```

对比 `desiredNumberScheduled`、`currentNumberScheduled`、`updatedNumberScheduled`、`numberReady`、`numberAvailable`、`numberUnavailable` 和节点调度约束。

### Event 证据

采集工作负载、ReplicaSet 和 Pod 事件。尽量使用 UID 相关过滤，并始终避免把命名空间下所有 Warning 事件都当作目标工作负载证据。

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector involvedObject.name=<name> --sort-by=.lastTimestamp
```

Kubernetes Events v1 API 可用时：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

只保留 involved object UID/name 能映射到工作负载、所属 ReplicaSet 或选中 Pod 的事件。

### Pod 下钻

对每个未 Ready 的新版本 Pod，检查状态、事件、日志和资源压力：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pod <pod-name> -n <namespace>
```

如果出现调度或节点压力迹象：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
```

如果出现存储迹象：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pv
```

如果出现流量或 readiness 路径问题：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,ingress -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe svc <service-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe ingress <ingress-name> -n <namespace>
```

## 根因排序

基于直接证据排序根因。优先采用发布漏斗中第一个失败层：

1. 控制面尚未观察到工作负载 generation。
2. 新版本对象未创建，或没有 Pod。
3. 新版本 Pod 已存在，但处于 Pending 或无法调度。
4. 新版本 Pod 已启动，但未 Ready。
5. 工作负载 ready/available 副本不足。
6. 集群、节点、存储或网络症状解释了 Pod 或 readiness 失败。

常见根因标签：

| 根因 | 证据 |
| --- | --- |
| `ControlPlaneNotObserved` | `observedGeneration < generation` |
| `ReplicaSetCreateBlocked` | Deployment 新 ReplicaSet 缺失或存在 FailedCreate 事件 |
| `QuotaOrAdmissionRejected` | 事件中出现 quota、LimitRange、webhook、denied、forbidden 或 admission |
| `SchedulingBlocked` | Pod Pending 且存在 `FailedScheduling` |
| `ImagePullFailure` | `ImagePullBackOff`、`ErrImagePull`、镜像认证/标签/DNS 错误 |
| `CrashLoopOrAppExit` | `CrashLoopBackOff`、非零退出码、previous logs |
| `ContainerCommandNotFound` | 启动错误显示可执行文件不存在或命令无法执行 |
| `ProbeFailure` | startup/liveness/readiness probe 的 `Unhealthy` 事件 |
| `OOMKilled` | 上次终止原因或事件显示 OOM |
| `StorageMountFailure` | `FailedMount`、`FailedAttachVolume`、PVC Pending |
| `NodePressureOrNotReady` | Node condition 显示压力/NotReady，或 Pod 被驱逐 |
| `ServiceOrIngressMismatch` | Service selector/endpoints/Ingress 与 Ready Pod 不匹配 |

## 输出格式

使用 `references/output-schema.md` 作为详细 schema。面向用户的报告应包含：

- 目标：region、project、cluster、namespace、kind、name。
- CLI 路径：使用过的 hcloud CCE 操作和 kubectl-cce 证据命令。
- 摘要状态和置信度。
- 发布漏斗及各层通过/失败情况。
- Top causes 排序，并附直接证据片段。
- 对 Pod、Node、Storage、Network、Root Cause 或 Remediation skill 的移交建议。
- 明确说明未执行任何变更命令。
- 验证缺口，包括 RBAC 拒绝、缺少 metrics-server、日志不可访问，或 hcloud/kubectl 工具不可用。

## 最佳实践

- 从发布漏斗最先失败的层级开始，依据直接证据排序候选根因。
- 关联工作负载 generation、所属对象、选中 Pod 和 Events 后再下结论。
- 限制日志和指标采集范围，将缺失证据明确记录为验证缺口。
- 将只读诊断和变更修复分离，为每项拟议变更注明移交对象。

## 注意事项与安全规则

提出建议前阅读 `references/risk-rules.md`。此 skill 只做只读诊断。不要运行：

- `kubectl cce ... apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout undo`、`cordon`、`drain` 或 `taint`
- 任何 hcloud create/update/delete 操作
- 任何 SDK dispatcher 动作

## 验证

阅读 `references/verification-method.md` 获取 CLI 验证清单。有效实现应通过这些检查：

- `hcloud version`、`hcloud configure list` 和 `kubectl version --client` 可用。
- `hcloud CCE ListClusters` 和 `ShowCluster` 能找到目标集群。
- `kubectl cce ...` 能通过 CCE API Gateway 读取目标集群。
- `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 能读取目标命名空间。
- 仓库/包内搜索不到 SDK dispatcher 入口。

## 参考文档

- `references/workflow.md` - 证据顺序和故障规则。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 只读边界和移交规则。
- `references/verification-method.md` - 环境和 CLI 验证。
- 华为云 KooCLI 文档：https://support.huaweicloud.com/hcli/
- 华为云 CCE 文档：https://support.huaweicloud.com/cce/
- Kubernetes kubectl 参考：https://kubernetes.io/docs/reference/kubectl/
