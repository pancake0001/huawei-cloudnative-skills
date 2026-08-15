---
name: huawei-cloud-cce-storage-failure-diagnoser
description: >
  使用 hcloud 获取华为云 CCE 集群和云存储元数据，并通过只读 kubectl-cce 证据诊断存储故障。 适用于 PVC Pending、供应或绑定失败、EVS
  拓扑冲突、FailedAttach、FailedMount、 CSI 错误、SFS/SFS Turbo NFS 超时、OBS 403 或凭据错误、运行期 I/O、只读文件系统、 容量或 inode 耗尽、subPath 问题或 PVC
  删除异常。
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, storage, diagnosis]
---

# 华为云 CCE 存储故障诊断

## 概述

本 skill 诊断 CCE/Kubernetes 存储故障，覆盖供应、绑定、调度、attach/mount、运行期 I/O、容量、权限和删除保护。

执行模型：

```text
hcloud CCE/云侧存储查询 -> kubectl cce 存储证据 -> 可选 CSI 日志/云侧指标 -> 根因排序 -> Markdown 报告
```

不要使用 Python SDK dispatcher、旧 skill 执行动作、旧 Huawei storage action、捆绑 SDK 脚本、kubeconfig 生成或 Huawei Cloud SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。执行 Kubernetes 命令前先读
`references/kubectl-cce.md`。

## 前置条件

1. `hcloud`、`kubectl` 和 kubectl-cce 均为当前平台可执行的原生二进制。
2. 凭据和项目上下文通过批准的受保护渠道提供。
3. IAM 和 Kubernetes RBAC 允许所需的集群、存储、Event、Pod、Node 和 CSI 日志只读查询。
4. 工具缺失时使用 `huawei-cloud-kubectl-cce-installer`，本技能不得下载或执行安装脚本。
5. 不得打印凭据、token、header、代理信息、存储密钥或 CSI 日志中的敏感值。

## 相关 Skill

| Skill                                        | 使用场景                                                                      |
| -------------------------------------------- | ----------------------------------------------------------------------------- |
| `huawei-cloud-cce-pod-failure-diagnoser`     | Pod Pending、ContainerCreating、CrashLooping 或 FailedMount/FailedAttach 事件 |
| `huawei-cloud-cce-node-failure-diagnoser`    | 存储症状与节点压力、污点、NotReady、kubelet 或单节点限制有关                  |
| `huawei-cloud-cce-network-failure-diagnoser` | SFS/SFS Turbo/NFS 或 OBS 访问涉及网络、安全组、ACL、NAT 或 DNS                |
| `huawei-cloud-cce-metric-analyzer`           | 需要 EVS/SFS/节点文件系统容量、I/O 或延迟指标                                 |
| `huawei-cloud-cce-root-cause-analyzer`       | 存储只是跨域故障的候选之一                                                    |
| `huawei-cloud-cce-auto-remediation-runner`   | 用户确认后的恢复预览和执行                                                    |

## 参数确认

| 输入              | 必填     | 说明                                                                                                               |
| ----------------- | -------- | ------------------------------------------------------------------------------------------------------------------ |
| `region`          | 是       | 例如 `cn-north-4`                                                                                                  |
| `project_id`      | 通常需要 | kubectl-cce 和云资源 hcloud 命令需要                                                                               |
| `cluster_id`      | 推荐     | 没有时先用 hcloud 按名称定位                                                                                       |
| `namespace`       | 推荐     | PVC/Pod 场景需要                                                                                                   |
| `pvc_name`        | 可选     | 指定 PVC                                                                                                           |
| `pod_name`        | 可选     | 有挂载或 I/O 异常的 Pod                                                                                            |
| `failure_symptom` | 推荐     | `pvc_pending`、`failed_mount`、`failed_attach`、`capacity`、`readonly_fs`、`nfs_timeout`、`obs_403`、`terminating` |
| `volume_id`       | 可选     | 已知 EVS/SFS/SFS Turbo/OBS 标识                                                                                    |

## 核心命令与证据采集

### 1. 验证工具和插件

先读 `references/kubectl-cce.md`，再验证当前平台的原生工具和插件发现：

```bash
hcloud version
kubectl version --client
kubectl plugin list
```

工具或插件缺失时停止当前流程，使用 `huawei-cloud-kubectl-cce-installer`；不得下载安装器，也不得回退到 SDK 或 kubeconfig 接入。

### 2. 查询集群

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

### 3. 采集 Kubernetes 存储证据

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc,pv,storageclass,volumeattachments -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

### 4. 采集 CSI 证据

RBAC 允许时采集 CSI 证据。不同 CCE 版本的 CSI label 可能不同，先发现实际 Pod 名称和 label，再选择目标；日志必须限量并脱敏：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system --show-labels
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pod <csi-pod-name> -n kube-system -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <csi-pod-name> -n kube-system -c <csi-container-name> --tail=200
```

### 5. 采集云侧证据

云侧只读证据只在标识明确或可安全关联时采集。EVS/SFS/SFS Turbo/OBS/VPC/安全组/ACL 使用 hcloud；时间序列指标交给 metric
analyzer。不确定 operation 或标识时先查 help，否则记录为数据缺口。

## 诊断流程

1. PVC Pending/供应失败：看 PVC conditions/events、StorageClass provisioner/parameters、access mode、volumeBindingMode、配额/容量和 CSI provisioner 日志。
2. 绑定/拓扑：比较 PVC、PV nodeAffinity、Pod nodeSelector/affinity、selected node、StorageClass allowedTopologies 和可用区。
3. FailedAttach/VolumeAttachment：看 VolumeAttachment status、attachError/detachError、目标节点、EVS volume 状态、残留挂载和单节点磁盘限制。
4. FailedMount/ContainerCreating：看 Pod Events、kubelet mount 消息、Secret/ConfigMap 引用、filesystem type、NFS endpoint/DNS 和 CSI 日志。
5. 运行期 I/O/容量：看 Pod 重启/事件/日志线索、PVC 容量、节点文件系统压力、inode/capacity 证据和可用指标。
6. SFS/SFS Turbo/NFS：把 mount timeout 与 DNS、路由、安全组、ACL 和 network diagnoser 证据关联。
7. OBS/IAM/凭据：看 Events 和 CSI 日志中的 403、委托、AK/SK Secret、bucket、endpoint、policy 错误，不输出密钥。
8. Terminating/finalizer：看 deletionTimestamp、finalizers、绑定 Pod、VolumeAttachment 和保护状态，只输出恢复建议，不移除 finalizer。

## 输出格式

Markdown 报告必须从以下内容开始：

1. `## 总结`：最可能存储根因、受影响 PVC/Pod/Node、影响和置信度。
2. `## 根因分析`：排序根因、证据和反证。
3. `## 下一步措施`：验证、缓解和恢复交接。
4. `## 证据`：PVC/PV/StorageClass/VolumeAttachment/Pod/Node/Event/CSI/云侧证据。
5. `## 数据缺口`：RBAC 缺失、CSI 日志缺失、云卷 ID 缺失、指标不可用或 StorageClass 后端未知。

## 最佳实践

- 按供应、绑定、调度、attach、mount、运行期和删除顺序诊断存储生命周期。
- 关联 PVC、PV、StorageClass、VolumeAttachment、Pod、Node、CSI 和云卷标识。
- 限制 CSI 日志范围，并脱敏凭据、endpoint 和敏感挂载信息。
- 云侧标识、RBAC、日志或指标缺失时，明确记录为数据缺口。

## 注意事项与安全规则

本 skill 不修改资源，不执行 `exec`、节点 SSH、抓包、压测、`fsck`、finalizer 移除、强制 detach 或扩容。

## 验证

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]storage|huawei[-_]get[-_]cce|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

期望结果：没有可执行 SDK dispatcher 入口，也没有裸 Kubernetes 访问路径。Markdown 中只能作为禁用项或验证项出现。

## 参考文档

- `references/kubectl-cce.md`：插件接入约束。
- `references/workflow.md`：分阶段存储诊断流程。
- `references/output-schema.md`：结构化输出和 Markdown 布局。
- `references/risk-rules.md`：只读边界和高风险动作交接。
