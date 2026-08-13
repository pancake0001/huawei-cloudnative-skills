---
id: huawei-cloud-cce-storage-failure-diagnoser
name: huawei-cloud-cce-storage-failure-diagnoser
description: >
  使用 hcloud CLI 查询集群和云侧存储元数据，并通过 kubectl-cce 插件命令只读采集 PVC、PV、StorageClass、Pod、Node、Event、VolumeAttachment 和 CSI 日志证据，诊断华为云 CCE 存储故障。适用于 PVC Pending、供应失败、PV/PVC 绑定异常、EVS 拓扑冲突、VolumeAttachment attach 失败、FailedMount、SFS/SFS Turbo NFS 超时、OBS 403 或凭据错误、运行期 IO、只读文件系统、容量或 inode 耗尽、subPath 挂载卡死、PVC Terminating 保护和 Markdown 存储诊断报告。不要使用 Python SDK dispatcher action。
tags: [cce, storage-diagnosis, evs, pvc, fault-diagnosis, hcloud, kubectl-cce]
---

# 华为云 CCE 存储故障诊断

本 skill 诊断 CCE/Kubernetes 存储故障，覆盖供应、绑定、调度、attach/mount、运行期 I/O、容量、权限和删除保护。

执行模型：

```text
hcloud CCE/云侧存储查询 -> kubectl cce 存储证据 -> 可选 CSI 日志/云侧指标 -> 根因排序 -> Markdown 报告
```

不要使用 Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、`huawei_storage_*`、`huawei_get_cce_*`、捆绑 SDK 脚本、kubeconfig 生成或 Huawei Cloud SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。执行 Kubernetes 命令前先读 `references/kubectl-cce.md`。

## 相关 Skill

| Skill | 使用场景 |
| --- | --- |
| `huawei-cloud-cce-pod-failure-diagnoser` | Pod Pending、ContainerCreating、CrashLooping 或 FailedMount/FailedAttach 事件 |
| `huawei-cloud-cce-node-failure-diagnoser` | 存储症状与节点压力、污点、NotReady、kubelet 或单节点限制有关 |
| `huawei-cloud-cce-network-failure-diagnoser` | SFS/SFS Turbo/NFS 或 OBS 访问涉及网络、安全组、ACL、NAT 或 DNS |
| `huawei-cloud-cce-metric-analyzer` | 需要 EVS/SFS/节点文件系统容量、I/O 或延迟指标 |
| `huawei-cloud-cce-root-cause-analyzer` | 存储只是跨域故障的候选之一 |
| `huawei-cloud-cce-auto-remediation-runner` | 用户确认后的恢复预览和执行 |

## 必要输入

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `region` | 是 | 例如 `cn-north-4` |
| `project_id` | 通常需要 | kubectl-cce 和云资源 hcloud 命令需要 |
| `cluster_id` | 推荐 | 没有时先用 hcloud 按名称定位 |
| `namespace` | 推荐 | PVC/Pod 场景需要 |
| `pvc_name` | 可选 | 指定 PVC |
| `pod_name` | 可选 | 有挂载或 I/O 异常的 Pod |
| `failure_symptom` | 推荐 | `pvc_pending`、`failed_mount`、`failed_attach`、`capacity`、`readonly_fs`、`nfs_timeout`、`obs_403`、`terminating` |
| `volume_id` | 可选 | 已知 EVS/SFS/SFS Turbo/OBS 标识 |

## 采集方式

1. 查询集群：

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

2. 通过 kubectl-cce 采集 Kubernetes 存储证据：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pvc,pv,storageclass,volumeattachments -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pvc <pvc-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

3. RBAC 允许时采集 CSI 证据，日志必须限量并脱敏：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system -l app=everest-csi-driver -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs -n kube-system -l app=everest-csi-driver --tail=200
```

4. 云侧只读证据只在标识明确或可安全关联时采集。EVS/SFS/SFS Turbo/OBS/VPC/安全组/ACL 用 hcloud；时间序列指标交给 metric analyzer。不确定 operation 或标识时先查 help 或写成数据缺口。

## 诊断流程

1. PVC Pending/供应失败：看 PVC conditions/events、StorageClass provisioner/parameters、access mode、volumeBindingMode、配额/容量和 CSI provisioner 日志。
2. 绑定/拓扑：比较 PVC、PV nodeAffinity、Pod nodeSelector/affinity、selected node、StorageClass allowedTopologies 和可用区。
3. FailedAttach/VolumeAttachment：看 VolumeAttachment status、attachError/detachError、目标节点、EVS volume 状态、残留挂载和单节点磁盘限制。
4. FailedMount/ContainerCreating：看 Pod Events、kubelet mount 消息、Secret/ConfigMap 引用、filesystem type、NFS endpoint/DNS 和 CSI 日志。
5. 运行期 I/O/容量：看 Pod 重启/事件/日志线索、PVC 容量、节点文件系统压力、inode/capacity 证据和可用指标。
6. SFS/SFS Turbo/NFS：把 mount timeout 与 DNS、路由、安全组、ACL 和 network diagnoser 证据关联。
7. OBS/IAM/凭据：看 Events 和 CSI 日志中的 403、委托、AK/SK Secret、bucket、endpoint、policy 错误，不输出密钥。
8. Terminating/finalizer：看 deletionTimestamp、finalizers、绑定 Pod、VolumeAttachment 和保护状态，只输出恢复建议，不移除 finalizer。

## 输出要求

Markdown 报告必须从以下内容开始：

1. `## 总结`：最可能存储根因、受影响 PVC/Pod/Node、影响和置信度。
2. `## 根因分析`：排序根因、证据和反证。
3. `## 下一步措施`：验证、缓解和恢复交接。
4. `## 证据`：PVC/PV/StorageClass/VolumeAttachment/Pod/Node/Event/CSI/云侧证据。
5. `## 数据缺口`：RBAC 缺失、CSI 日志缺失、云卷 ID 缺失、指标不可用或 StorageClass 后端未知。

本 skill 不修改资源，不执行 `exec`、节点 SSH、抓包、压测、`fsck`、finalizer 移除、强制 detach 或扩容。

## 验证

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_storage|huawei_get_cce_|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

期望结果：没有可执行 SDK dispatcher 入口，也没有裸 Kubernetes 访问路径。Markdown 中只能作为禁用项或验证项出现。

## References

- `references/kubectl-cce.md`：插件接入约束。
- `references/workflow.md`：分阶段存储诊断流程。
- `references/output-schema.md`：结构化输出和 Markdown 布局。
- `references/risk-rules.md`：只读边界和高风险动作交接。
