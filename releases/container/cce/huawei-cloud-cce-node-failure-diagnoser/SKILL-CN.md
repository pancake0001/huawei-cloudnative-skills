---
name: huawei-cloud-cce-node-failure-diagnoser
description: 使用 hcloud 和只读 kubectl-cce 诊断 CCE 节点故障；用户提到 NodeNotReady、节点压力、lease 过期、kubelet、runtime、CNI、驱逐或节点级影响时使用本技能。
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, node, diagnosis]
---

# 华为云 CCE 节点故障诊断

## 概述

本技能通过华为云 `hcloud` CLI 和 Kubernetes `kubectl` 诊断 CCE/Kubernetes 节点故障。

执行模型：

```text
hcloud CCE 查询集群 -> kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> 只读采集节点证据 -> 排名诊断报告
```

CCE hcloud 只用于集群级和 CCE 节点元数据：

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE ListNodes`
- `hcloud CCE ShowNode`

Kubernetes 节点状态、kube-node-lease、Events、节点上的 Pods、必要时的 Pod 日志，以及 metrics-server 指标，都使用 `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 采集。

不要使用 Python SDK dispatcher、旧 skill 执行动作、旧 Huawei node action 或 Huawei Cloud SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。插件接入约束见 `references/kubectl-cce.md`。

## 使用场景

适用于：

- 节点 `NotReady`、`Ready=False`、`Ready=Unknown` 或 kube-node-lease 过期。
- `DiskPressure`、`MemoryPressure`、`PIDPressure`、`NetworkUnavailable`、CNI、CRI、kubelet 或 NPD 信号。
- Pod 驱逐、sandbox 创建失败、镜像拉取失败或重启集中发生在某个节点。
- 节点资源压力、allocatable/request 饱和、taints、不可调度状态或节点级影响面。
- 用户要求只读诊断 CCE 节点。

本技能不修改节点或工作负载状态。cordon、uncordon、drain、reboot、delete、taint、scale、restart 等动作只能作为建议输出，并在用户确认后交给 remediation skill。

## 参数确认

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `region` | 是 | 例如 `cn-north-4` |
| `project_id` | 通常需要 | 大多数 hcloud CCE 操作需要 |
| `cluster_id` | 推荐 | 如果没有，用集群名通过 `ListClusters` 解析 |
| `cluster_name` | 可选 | 仅用于定位 `cluster_id` |
| `node_name` | 推荐 | Kubernetes 节点名，CCE 中常见为内网 IP |
| `node_ip` | 可选 | 用于匹配 `kubectl cce ... get nodes -o wide` 或 CCE 节点元数据 |
| `namespace` | 可选 | 缩小受影响 Pod 或日志范围时使用 |

`node_name` 和 `node_ip` 至少提供一个。两者都没有时，先列出节点，让用户选择目标节点或症状范围。

## 前置条件

1. `hcloud` 已安装并在 `PATH` 中，或已找到平台原生二进制并用 `hcloud version` 验证。
2. `kubectl` 已安装并兼容目标 Kubernetes 版本。Linux sandbox 使用 Linux kubectl；Windows 工作站使用 `kubectl.exe`。
3. hcloud 已具备认证配置，或本次命令通过临时参数传入凭据。只用下面命令做脱敏验证：

```bash
hcloud configure list
```

1. IAM 允许读取 CCE 集群/节点并使用 kubectl-cce API Gateway 接入。
2. Kubernetes RBAC 允许读取 nodes、leases、events、pods、pod logs 和 metrics。

不要打印 AK、SK、security token、kubectl-cce 代理凭据、Authorization header 或镜像仓库密钥。

## 核心命令与准备流程

### 1. 确认 CLI 工具

```bash
hcloud version
hcloud configure list
kubectl version --client
```

如果工具缺失，停止当前诊断流程，改用 `huawei-cloud-kubectl-cce-installer`
或批准的平台安装流程。本诊断技能不得下载或执行安装脚本。安装时固定批准版本、
校验官方 checksum 或签名，再重新执行上述检查。

### 2. 定位并检查集群

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

确认集群在目标 region/project 中。kubectl-cce 插件默认访问 CCE API Gateway endpoint `<cluster-id>.cce.<region>.myhuaweicloud.com`；如果该 endpoint 不适用于当前环境，设置 `CCE_ENDPOINT` 或传入 `--endpoint`。

### 3. 可选 CCE 节点元数据

用于把 Kubernetes 节点名和 CCE 节点 ID、云侧元数据关联起来：

```bash
hcloud CCE ListNodes --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowNode --cluster_id=<cluster-id> --node_id=<node-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

不要执行 CCE 节点 update/delete/reset 类操作。

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

### 5. 验证 Kubernetes 只读权限

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get nodes
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list leases -n kube-node-lease
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -A
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -A
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -A
```

若 RBAC 拒绝某项读取，在报告中记录缺失权限，只继续采集允许读取的证据。

## 诊断流程

详细证据顺序和故障规则见 `references/workflow.md`。

节点基线：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe node <node-name>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get lease <node-name> -n kube-node-lease -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --field-selector involvedObject.kind=Node,involvedObject.name=<node-name> --sort-by=.lastTimestamp
```

节点影响面：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A --field-selector spec.nodeName=<node-name> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A --field-selector spec.nodeName=<node-name> -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,PHASE:.status.phase,REASON:.status.reason,NODE:.spec.nodeName"
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

指标可用时：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top node <node-name>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -A --sort-by=memory
```

`kubectl cce ... top` 返回 `Metrics API not available` 时，把它记录为验证缺口，不要编造资源趋势。

## 原因排序

按直接证据和最先失败的层级排序：

1. 集群/API Gateway、kubectl-cce 插件或 RBAC 缺口。
2. 节点活性和 kube-node-lease 是否过期。
3. 节点 conditions：Ready、pressure、NetworkUnavailable、kubelet/CRI/CNI/NPD。
4. taints、不可调度状态和调度影响。
5. 节点上集中的 Pod 症状：Evicted、ContainerStatusUnknown、FailedCreatePodSandBox、挂载失败、重启风暴。
6. allocatable/request 汇总和 metrics 指标显示的资源饱和。

## 输出格式

按 `references/output-schema.md` 输出用户报告。报告要先给结论和行动建议，再放命令轨迹和原始条件表。

报告至少按这个顺序包含：

- 执行摘要：节点健康状态、置信度、根因分类和一句话结论。
- 根因分析：Top causes，附直接证据和解释。
- 下一步措施：安全检查、候选修复路径、移交对象或 skill。
- 目标范围：region、project、cluster、node name/IP、可选 namespace/workload。
- 节点活性漏斗。
- 节点工作负载影响面。
- 反向证据：相邻原因为什么不优先。
- Node condition 表和 kube-node-lease 结论。
- 指标缺口和验证缺口。
- CLI 路径：hcloud CCE 操作和 kubectl 证据命令。
- 明确说明没有执行任何变更命令。

## 最佳实践

- 先检查节点存活状态和 lease 新鲜度，再解释下游 Pod 症状。
- 关联 Kubernetes 节点名、CCE 节点 ID、conditions、Events 和受影响 Pod。
- 指标或日志不可用时记录验证缺口，不推断不存在的趋势。
- 保持只读诊断，所有节点或工作负载变更都必须移交。

## 注意事项与安全边界

执行建议前先读 `references/risk-rules.md`。本技能只读，不运行：

- `kubectl cce ... apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout undo`、`cordon`、`uncordon`、`drain`、`taint`
- CCE 节点 reset/delete/update
- ECS reboot/stop/delete
- 任意 SDK dispatcher action

## 验证

见 `references/verification-method.md`。有效实现应满足：

- `hcloud version`、`hcloud configure list`、`kubectl version --client` 可用。
- `hcloud CCE ListClusters`、`ShowCluster` 可用，`kubectl cce ...` 能读取目标集群。
- `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` 能读取 nodes、leases、events、pods。
- 技能包中没有 SDK dispatcher 入口残留。

## 参考文档

- `references/workflow.md` - 节点证据顺序和故障规则。
- `references/common-pitfalls.md` - 节点诊断常见坑和 CLI 示例。
- `references/output-schema.md` - Markdown 和 JSON 报告结构。
- `references/risk-rules.md` - 只读边界和移交规则。
- `references/verification-method.md` - 环境和 CLI 验证。
- `references/iam-policies.md` - IAM 与 Kubernetes RBAC 要求。
