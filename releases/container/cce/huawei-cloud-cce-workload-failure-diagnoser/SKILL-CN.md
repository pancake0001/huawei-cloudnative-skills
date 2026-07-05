---
id: huawei-cloud-cce-workload-failure-diagnoser
name: huawei-cloud-cce-workload-failure-diagnoser
description: >
  使用 hcloud CLI 进行华为云 CCE 集群发现和 kubeconfig 获取，再使用 kubectl 只读采集 Kubernetes 证据，诊断 CCE 工作负载发布和可用性故障。当用户提到 CCE Deployment、StatefulSet、DaemonSet、发布卡住、副本不可用、Pod 未就绪、ImagePullBackOff、CrashLoopBackOff、探针失败、调度失败、PVC 挂载失败、工作负载事件，或要求在不使用 Python SDK dispatcher 的情况下排查华为云 CCE 工作负载时，使用此 skill。
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, workload, diagnosis]
---

# 华为云 CCE 工作负载故障诊断

此 skill 通过华为云 `hcloud` CLI 和 Kubernetes `kubectl` 诊断 CCE 工作负载发布和可用性故障。

**执行模型**：`hcloud CCE` -> 短期 kubeconfig -> `kubectl --kubeconfig=<file>` -> 只读工作负载证据 -> 根因排序与移交建议。

集群级操作使用 CCE hcloud 命令：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE CreateKubernetesClusterCert`

获取 kubeconfig 后，使用 `kubectl` 查看 Kubernetes 资源。工作负载、ReplicaSet、Pod、Event、日志、PVC、Service、Ingress、HPA 和 Node 都属于 Kubernetes 资源，应通过 `kubectl --kubeconfig=<file>` 检查。

此 skill 不使用 Python SDK dispatcher 命令、`scripts/huawei-cloud.py`、`skill action=exec`、`huawei_workload_*` 动作或任何捆绑 SDK 脚本。

## 何时使用

此 skill 适用于：

- Deployment 发布卡住、`ProgressDeadlineExceeded`、旧副本残留或新副本未就绪。
- StatefulSet 或 DaemonSet 更新失败、副本不可用或发布停滞。
- CCE 工作负载状态异常，但用户需要先拿到证据再做修复。
- 工作负载下钻出的 Pod 级症状，包括 `Pending`、`FailedScheduling`、`ImagePullBackOff`、`ErrImagePull`、`CrashLoopBackOff`、`OOMKilled`、`Evicted`、`FailedMount`、`Unhealthy` 或 `ContainersNotReady`。
- 需要关联 Event、日志、selector、ReplicaSet、PVC、HPA、Service、Ingress 或 Node 证据来判断 CCE 工作负载问题。

不要用此 skill 修改资源。扩缩容、删除、重启、回滚、cordon、drain 或节点操作只能作为建议移交，不能直接执行。

## 必要输入

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
2. `kubectl` 已安装，并与目标 Kubernetes 小版本兼容。使用运行环境对应平台的原生二进制（`linux-amd64`、`linux-arm64`、`darwin-*` 或 `windows-amd64`）。很多 agent sandbox 即使作者工作站是 Windows，也会运行在 Linux 上，所以不要在 skill 流程中硬编码 Windows 专属 `kubectl.exe` 路径。
3. AK/SK 凭据已配置到 hcloud。只检查配置是否存在：

```bash
hcloud configure list
```

4. 调用方拥有华为云 IAM 权限，可以列出/查看 CCE 集群并创建 kubeconfig 证书。
5. 生成的 kubeconfig 用户拥有 Kubernetes RBAC 权限，可以读取目标命名空间中的必要资源。

最终报告中不要打印 AK、SK、安全令牌、kubeconfig 证书或 Authorization header。日志中必须脱敏密钥。

## CCE hcloud 设置流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
```

如果缺少 `kubectl`，先安装或下载运行平台对应的原生二进制：

```bash
# Linux amd64 示例
curl -LO "https://dl.k8s.io/release/v1.33.0/bin/linux/amd64/kubectl"
chmod +x ./kubectl
./kubectl version --client
```

Windows 使用 `kubectl.exe`；Linux 和 macOS 使用不带 `.exe` 后缀的 `kubectl`。

如果缺少 `hcloud`，先安装或下载运行平台对应的 KooCLI 原生二进制：

```bash
# Linux/macOS 示例：官方安装脚本
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
bash ./hcloud_install.sh -y
hcloud version
```

在 Windows 上解压得到的二进制是 `hcloud.exe`，但此 skill 中的示例仍统一写作 `hcloud`，以保持流程的平台中性。

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

如果 `ShowClusterEndpoints` 返回空的 `publicEndpoint`，且 kubeconfig server 是私网 IP 地址，则 `kubectl` 必须在能够访问集群私网 API Server 的网络中运行，例如华为云 VPC 主机、VPN、专线、云桌面，或具备 VPC 连通性的 sandbox。不要把这种情况误判为 SDK/CLI 改造失败。

如果 `publicEndpoint` 已存在，但 `CreateKubernetesClusterCert` 返回的 kubeconfig 中 `clusters[].cluster.server` 仍指向私网 endpoint，则在外部网络运行 `kubectl` 前，创建 kubeconfig 临时副本，并只把 `server` 字段替换为 `publicEndpoint`。记录原始 server 和实际使用的 server。不要修改证书、密钥、token 或 user 字段。

对于刚唤醒的集群或刚绑定 EIP 的集群，KooCLI 默认超时时间可能偏短。如果 `CreateKubernetesClusterCert` 返回 KooCLI timeout，可使用显式超时重试，例如 `--cli-connect-timeout=20 --cli-read-timeout=90 --cli-retry-count=2`。

### 4. 获取短期 kubeconfig

使用尽可能短的有效期，通常为 1 天。

```bash
mkdir -p ~/.kube/huawei-cce
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > ~/.kube/huawei-cce/<cluster-id>.kubeconfig
chmod 600 ~/.kube/huawei-cce/<cluster-id>.kubeconfig
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.kube\huawei-cce" | Out-Null
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > "$env:USERPROFILE\.kube\huawei-cce\<cluster-id>.kubeconfig"
```

kubeconfig 文件格式与平台无关。KooCLI 可能输出 JSON 格式 kubeconfig；`kubectl` 可以接受 JSON 或 YAML kubeconfig。Linux/macOS 和 Windows 的差异主要是路径语法和可执行文件名称。

### 5. 验证 Kubernetes 访问

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i get deployments -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -n <namespace>
```

如果 RBAC 拒绝某个读操作，报告缺失权限，并停止或基于部分证据继续诊断。

## 诊断流程

阅读 `references/workflow.md` 获取详细证据顺序和故障规则。

当多个命名空间中的大量工作负载同时不可用时，先检查集群级共性证据，再下钻单个工作负载：

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
kubectl --kubeconfig=<kubeconfig-file> get events -A --sort-by=.lastTimestamp
```

如果所有候选节点都是 `Ready=Unknown`、`NotReady`，或带有 `node.kubernetes.io/unreachable`、`node.cloudprovider.kubernetes.io/shutdown` taint，则应将共性的节点/调度阻塞排在单个工作负载症状之前。

### Deployment 证据

```bash
kubectl --kubeconfig=<kubeconfig-file> get deployment <name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe deployment <name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> rollout status deployment/<name> -n <namespace> --timeout=30s
kubectl --kubeconfig=<kubeconfig-file> rollout history deployment/<name> -n <namespace>
```

从 `spec.selector.matchLabels` 推导 selector，然后检查 ReplicaSet 和 Pod：

```bash
kubectl --kubeconfig=<kubeconfig-file> get rs -n <namespace> --selector='<selector>' -o yaml
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o yaml
```

按 ownerReference 过滤 ReplicaSet，只保留指向 Deployment UID 的对象。将 `deployment.kubernetes.io/revision` 最大的 ReplicaSet 视为新版本。

### StatefulSet 证据

```bash
kubectl --kubeconfig=<kubeconfig-file> get statefulset <name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe statefulset <name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> rollout status statefulset/<name> -n <namespace> --timeout=30s
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
```

对比 `spec.replicas`、`status.currentReplicas`、`status.updatedReplicas`、`status.readyReplicas`、`status.availableReplicas`，以及 `spec.updateStrategy` 中的 partition 设置。

### DaemonSet 证据

```bash
kubectl --kubeconfig=<kubeconfig-file> get daemonset <name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe daemonset <name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> rollout status daemonset/<name> -n <namespace> --timeout=30s
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
```

对比 `desiredNumberScheduled`、`currentNumberScheduled`、`updatedNumberScheduled`、`numberReady`、`numberAvailable`、`numberUnavailable` 和节点调度约束。

### Event 证据

采集工作负载、ReplicaSet 和 Pod 事件。尽量使用 UID 相关过滤，并始终避免把命名空间下所有 Warning 事件都当作目标工作负载证据。

```bash
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --field-selector involvedObject.name=<name> --sort-by=.lastTimestamp
```

如果可用 `events.k8s.io/v1`：

```bash
kubectl --kubeconfig=<kubeconfig-file> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

只保留 involved object UID/name 能映射到工作负载、所属 ReplicaSet 或选中 Pod 的事件。

### Pod 下钻

对每个未 Ready 的新版本 Pod，检查状态、事件、日志和资源压力：

```bash
kubectl --kubeconfig=<kubeconfig-file> describe pod <pod-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl --kubeconfig=<kubeconfig-file> top pod <pod-name> -n <namespace>
```

如果出现调度或节点压力迹象：

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
```

如果出现存储迹象：

```bash
kubectl --kubeconfig=<kubeconfig-file> get pvc -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe pvc <pvc-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> get pv
```

如果出现流量或 readiness 路径问题：

```bash
kubectl --kubeconfig=<kubeconfig-file> get svc,endpoints,ingress -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe svc <service-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe ingress <ingress-name> -n <namespace>
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

## 报告格式

使用 `references/output-schema.md` 作为详细 schema。面向用户的报告应包含：

- 目标：region、project、cluster、namespace、kind、name。
- CLI 路径：使用过的 hcloud CCE 操作和 kubectl 证据命令。
- 摘要状态和置信度。
- 发布漏斗及各层通过/失败情况。
- Top causes 排序，并附直接证据片段。
- 对 Pod、Node、Storage、Network、Root Cause 或 Remediation skill 的移交建议。
- 明确说明未执行任何变更命令。
- 验证缺口，包括 RBAC 拒绝、缺少 metrics-server、日志不可访问，或 hcloud/kubectl 工具不可用。

## 安全规则

提出建议前阅读 `references/risk-rules.md`。此 skill 只做只读诊断。不要运行：

- `kubectl apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout undo`、`cordon`、`drain` 或 `taint`
- 除 `CreateKubernetesClusterCert` 外的任何 hcloud create/update/delete 操作
- 任何 SDK dispatcher 动作

## 验证

阅读 `references/verification-method.md` 获取 CLI 验证清单。有效实现应通过这些检查：

- `hcloud version`、`hcloud configure list` 和 `kubectl version --client` 可用。
- `hcloud CCE ListClusters` 和 `ShowCluster` 能找到目标集群。
- `CreateKubernetesClusterCert` 能创建短期 kubeconfig。
- `kubectl --kubeconfig=<file>` 能读取目标命名空间。
- 仓库/包内搜索不到 SDK dispatcher 入口。

## 参考

- `references/workflow.md` - 证据顺序和故障规则。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 只读边界和移交规则。
- `references/verification-method.md` - 环境和 CLI 验证。
- 华为云 KooCLI 文档：https://support.huaweicloud.com/hcli/
- 华为云 CCE 文档：https://support.huaweicloud.com/cce/
- Kubernetes kubectl 参考：https://kubernetes.io/docs/reference/kubectl/
