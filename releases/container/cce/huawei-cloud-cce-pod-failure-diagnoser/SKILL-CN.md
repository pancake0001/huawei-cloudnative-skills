---
id: huawei-cloud-cce-pod-failure-diagnoser
name: huawei-cloud-cce-pod-failure-diagnoser
description: >
  使用 hcloud CLI 发现华为云 CCE 集群并获取 kubeconfig，再使用 kubectl 采集只读 Kubernetes 证据来诊断 Pod 故障。用户提到 CCE Pod CrashLoopBackOff、ImagePullBackOff、ErrImagePull、OOMKilled、Pending、Evicted、频繁重启、容器日志、Pod Events、Pod 指标，或要求不要使用 Python SDK dispatcher 排查华为云 CCE Pod 时使用本技能。
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, pod, diagnosis]
---

# 华为云 CCE Pod 故障诊断

本技能通过华为云 `hcloud` CLI 和 Kubernetes `kubectl` 诊断 CCE 集群中的单个 Pod 或一组 Pod 故障。

**执行模型**：`hcloud CCE` -> 短期 kubeconfig -> `kubectl --kubeconfig=<file>` -> 只读 Pod 证据 -> 原因排序与移交建议。

集群级操作使用 CCE hcloud 命令：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE CreateKubernetesClusterCert`

拿到 kubeconfig 后，Pods、Events、日志、Service、PVC、Node、metrics-server 指标等 Kubernetes 资源都用 `kubectl --kubeconfig=<file>` 读取。

禁止使用 Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、`huawei_pod_*` action 或本 skill 包内旧 SDK 脚本。

## 适用场景

- Pod `CrashLoopBackOff`、`Error`、`RunContainerError` 或频繁重启。
- Pod `ImagePullBackOff`、`ErrImagePull` 或镜像仓库认证/拉取失败。
- Pod `OOMKilled`、退出码 `137` 或内存限制压力。
- Pod `Pending`、`FailedScheduling`、`FailedMount`、`FailedAttachVolume` 或 sandbox 创建失败。
- Pod `Evicted`、节点 MemoryPressure/DiskPressure/ephemeral-storage 压力。
- 需要关联容器当前日志、previous 日志、Events、重启次数、探针失败和 Pod 资源使用情况。

本技能不执行变更操作。扩缩容、删除、重启、回滚、cordon、drain、taint、节点操作都只输出建议，并移交到对应恢复类 skill。

## 必要输入

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `region` | 是 | 例如 `cn-north-4` |
| `project_id` | 通常需要 | hcloud 操作需要项目 ID 或存在多项目时应提供 |
| `cluster_id` | 推荐 | 没有时先用 `ListClusters` 查找 |
| `namespace` | 是 | Kubernetes namespace |
| `pod_name` | 推荐 | 目标 Pod 名称 |
| `workload_name` | 可选 | 不知道 Pod 名时用工作负载推导 selector |
| `selector` | 可选 | 例如 `app=my-app` |

## 前置条件

1. `hcloud` 已安装并在 `PATH` 中。不同平台使用对应原生二进制，命令示例统一写 `hcloud ...`，不要硬编码 Windows 或 Linux 专属路径。
2. `kubectl` 已安装，并与目标 Kubernetes 小版本兼容。很多 agent sandbox 运行在 Linux，即使开发机是 Windows，也不要在流程里写死 `kubectl.exe`。
3. 如果 `hcloud` 或 `kubectl` 不在 `PATH` 中，先定位当前平台可执行的二进制，赋值给 shell 变量，并用 `version` 验证后再用。不要因为某个文件名叫 `kubectl.exe` 或 `hcloud.exe` 就假设它适配当前 OS。
4. AK/SK 已配置到 hcloud。只用下面命令检查配置，不打印密钥：

```bash
hcloud configure list
```

5. IAM 至少允许 list/show CCE 集群并创建 kubeconfig 证书。
6. kubeconfig 对应用户具备目标 namespace 中读取 Pod、Events、logs、Service、PVC、Node、metrics 的 RBAC 权限。

最终报告里不要输出 AK、SK、security token、kubeconfig 证书或 Authorization header。日志片段必须脱敏。

## CCE hcloud 准备流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
```

缺少 `kubectl` 时先安装当前运行平台的原生二进制：

```bash
# Linux amd64 示例
curl -LO "https://dl.k8s.io/release/v1.33.0/bin/linux/amd64/kubectl"
chmod +x ./kubectl
./kubectl version --client
```

Windows 使用 `kubectl.exe`；Linux/macOS 使用 `kubectl`。

缺少 `hcloud` 时安装当前平台的 KooCLI：

```bash
# Linux/macOS 示例
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
bash ./hcloud_install.sh -y
hcloud version
```

Windows 解压后是 `hcloud.exe`，但技能示例仍写 `hcloud`，保持跨平台。

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

如果 `ShowClusterEndpoints` 没有 `publicEndpoint`，而 kubeconfig 指向私网 IP，`kubectl` 必须从能访问集群私网 API Server 的环境运行，例如 VPC 主机、VPN、专线、云桌面或具备 VPC 连通性的 sandbox。这不是 SDK/CLI 改造失败。

如果存在 `publicEndpoint`，但 `CreateKubernetesClusterCert` 返回的 kubeconfig 仍指向私网地址，可复制一个临时 kubeconfig，只替换 `clusters[].cluster.server` 为公网端点。记录原始 server 和实际使用 server，不要改 certificate、key、token 或 user 字段。

刚唤醒集群或刚绑定 EIP 时，KooCLI 默认超时可能偏短。`CreateKubernetesClusterCert` 超时时可加 `--cli-connect-timeout=20 --cli-read-timeout=90 --cli-retry-count=2` 重试。

### 4. 获取短期 kubeconfig

使用尽量短的有效期，通常 1 天。

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

kubeconfig 文件格式跨平台通用。KooCLI 可能输出 JSON 格式 kubeconfig，`kubectl` 可以接受 JSON 或 YAML kubeconfig。

### 5. 验证 Kubernetes 只读权限

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get pods/log -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i get nodes
```

如果 RBAC 拒绝某项读取，在报告里列为缺口，只继续采集允许读取的证据。

## 诊断流程

详细证据顺序和分类规则见 `references/workflow.md`。

### 先扫异常 Pod

深挖前先找异常 Pod 和重启较多的 Pod：

```bash
kubectl --kubeconfig=<kubeconfig-file> get pods -A -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector=status.phase!=Running -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,NODE:.spec.nodeName"
```

`field-selector` 适合发现明显的 `Pending`/`Failed` Pod；custom-columns 用来发现 `Running` 但未 Ready 或重启数异常的 Pod。

### 查找目标 Pod

已知 Pod 名时：

```bash
kubectl --kubeconfig=<kubeconfig-file> get pod <pod-name> -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pod <pod-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe pod <pod-name> -n <namespace>
```

只知道工作负载名时，先从工作负载推导 selector：

```bash
kubectl --kubeconfig=<kubeconfig-file> get deployment <workload-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> --selector='<selector>' -o yaml
```

StatefulSet 或 DaemonSet 替换为对应资源类型。

### 采集 Events

优先 Pod 相关事件，再看 namespace 时间线：

```bash
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --field-selector involvedObject.name=<pod-name> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
```

可用 `events.k8s.io/v1` 时：

```bash
kubectl --kubeconfig=<kubeconfig-file> get events.events.k8s.io -n <namespace> --sort-by=.eventTime -o yaml
```

只引用能映射到目标 Pod、owner、同 selector Pod、相关 Node/PVC 的 Events。

### 采集日志

CrashLoopBackOff、OOMKilled、频繁重启优先看 previous 日志：

```bash
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> --all-containers --tail=200
```

多容器 Pod 必要时指定容器：

```bash
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> -c <container-name> --previous --tail=200
kubectl --kubeconfig=<kubeconfig-file> logs <pod-name> -n <namespace> -c <container-name> --tail=200
```

`ImagePullBackOff` 通常没有容器日志，不要反复查日志，优先看 Events。

如果镜像拉取失败时日志命令返回 `container is waiting to start: trying and failing to pull image` 或 `previous terminated container ... not found`，这说明容器从未启动，是支持镜像拉取失败的证据，不是 kubectl 故障。

### 采集指标和节点上下文

metrics-server 可用时：

```bash
kubectl --kubeconfig=<kubeconfig-file> top pod <pod-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> top pod <pod-name> -n <namespace> --containers
kubectl --kubeconfig=<kubeconfig-file> top pod -n <namespace> --sort-by=memory
kubectl --kubeconfig=<kubeconfig-file> top node
```

metrics-server 不可用且 `kubectl top` 返回 `Metrics API not available` 时，把指标缺失写进验证缺口，不要编造趋势。本技能内不要切换到 Python SDK、AOM SDK 或手写 API 来补这个缺口。

Pending、Evicted 或节点压力相关时：

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
```

存储相关时：

```bash
kubectl --kubeconfig=<kubeconfig-file> get pvc -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe pvc <pvc-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> get pv
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

| 原因 | 证据 |
| --- | --- |
| `CrashLoopOrAppExit` | `CrashLoopBackOff`、非零退出码、previous 日志 |
| `ContainerCommandNotFound` | 启动错误显示命令不存在或无法执行 |
| `ImagePullFailure` | `ImagePullBackOff`、`ErrImagePull`、镜像认证/标签/DNS 错误 |
| `OOMKilled` | last state、退出码 137、内存限制或指标 |
| `SchedulingBlocked` | Pod Pending 且有 `FailedScheduling` |
| `StorageMountFailure` | `FailedMount`、`FailedAttachVolume`、PVC Pending |
| `ProbeFailure` | startup/liveness/readiness probe 的 `Unhealthy` Events |
| `NodePressureOrEviction` | Evicted、节点压力条件、taints、NotReady |
| `QuotaOrAdmissionRejected` | Events 提到 quota、LimitRange、webhook、denied、forbidden |
| `SandboxOrCNIBlocked` | `FailedCreatePodSandBox`、CNI、IP 分配或 runtime sandbox 错误 |

## 报告格式

用户侧报告应包含：

- 目标：region、project、cluster、namespace、Pod/workload/selector。
- CLI 路径：使用过的 hcloud CCE 和 kubectl 证据命令。
- 摘要状态和置信度。
- Pod 生命周期漏斗的通过/失败层。
- Top causes，附直接证据片段。
- 根因解释：用人能看懂的话解释失败信息意味着什么，包括镜像名解析、默认 registry、调度状态、节点压力、存储状态等如何影响结论。
- 反向证据：简要说明为什么排除了相邻原因，例如调度、节点 NotReady、日志、指标、OOM、存储、探针等。
- 当前日志和 previous 日志发现。
- 指标、节点、存储等缺口。
- 深入分析建议：给出下一步具体检查项、什么结果能确认或推翻当前假设、应该检查哪个系统或配置。
- 候选修复路径：只描述安全修复方案，不直接执行；需要变更时说明移交到 workload、node、storage、network、root-cause 或 remediation skill。
- 明确说明没有执行变更命令。

识别 Top Cause 后，读取 `references/scenario-guides.md` 并套用对应场景。这个规则适用于所有明确故障类型，不只适用于镜像拉取失败。场景指南覆盖 ImagePullBackOff、CrashLoopBackOff、OOMKilled、Pending、存储挂载、Evicted、探针失败、CNI/sandbox、Admission/Quota 等场景，并给出每类的解释、反向证据、下一步检查、候选修复和移交建议。

详细结构见 `references/output-schema.md`。

## 安全边界

诊断前阅读 `references/risk-rules.md`。本技能只读，禁止执行：

- `kubectl apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout undo`、`cordon`、`drain`、`taint`
- 除 `CreateKubernetesClusterCert` 以外的任何 hcloud create/update/delete 操作
- 任何 SDK dispatcher action

## 验证

按 `references/verification-method.md` 检查：

- `hcloud version`、`hcloud configure list`、`kubectl version --client` 可用。
- `hcloud CCE ListClusters` 和 `ShowCluster` 能定位目标集群。
- `CreateKubernetesClusterCert` 能生成短期 kubeconfig。
- `kubectl --kubeconfig=<file>` 能读取目标 namespace。
- 本 skill 包中没有 SDK dispatcher 入口或 SDK 脚本残留。

## References

- `references/workflow.md` - 证据顺序和故障分类规则。
- `references/scenario-guides.md` - 各故障场景的解释、下一步检查、候选修复和移交建议。
- `references/common-pitfalls.md` - 常见误区和 CLI 示例。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 只读边界和移交规则。
- `references/verification-method.md` - 环境和 CLI 验证。
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/
