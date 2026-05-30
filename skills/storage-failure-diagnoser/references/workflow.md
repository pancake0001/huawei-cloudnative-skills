# Workflow

## 可复用能力与缺口

当前仓库已经具备以下可复用能力：

- Kubernetes 对象：`huawei_get_cce_pvcs`、`huawei_get_cce_pvs`、`huawei_get_cce_pods`、`huawei_get_kubernetes_nodes`、`huawei_get_cce_events`、`huawei_get_pod_logs`。
- 华为云存储：`huawei_list_evs`、`huawei_get_evs_metrics`、`huawei_list_sfs`、`huawei_list_sfs_turbo`。
- 网络补证：`huawei_list_security_groups`、`huawei_list_vpc_acls`，可复用 network-failure-diagnoser 的安全组/ACL 思路。
- 日志与报告：已有 Pod 日志、AOM/LTS 日志、Markdown/HTML 报告型 diagnoser 的输出模式。
- 外部 huawei-cloud skill 也覆盖 ECS/EVS/VPC/ELB/EIP/SFS、CCE Pod/PVC/PV/Event、Pod 日志、AOM/LTS、网络诊断、工作负载诊断和完整报告生成；本 skill 复用其中只读工具与“先按步骤取证，再输出完整报告”的习惯。

本 skill 补齐的原子能力：

- `huawei_get_cce_storageclasses`：读取 StorageClass 的 provisioner、parameters、`volumeBindingMode`。
- `huawei_get_cce_volumeattachments`：读取 VolumeAttachment 的 `attached`、`attachError`、`detachError`。
- `huawei_get_cce_node_stats_summary`：经 API Server 代理读取节点 `/stats/summary`，解析 PVC `usedBytes/capacityBytes` 和 inode。
- `huawei_get_cce_everest_csi_logs`：读取 `kube-system` 中 Everest CSI driver/controller 日志片段，自动脱敏。
- `huawei_storage_failure_diagnose`：一次性编排 PVC/PV/SC/Pod/Node/Event/VolumeAttachment/CSI logs/stats，生成结构化 findings 和 Markdown 报告。

仍需人工或后续扩展的能力：

- 不执行 `kubectl exec`、节点 SSH、dmesg、本机 fsck 或主动 NFS/OBS 连通性探测。
- 不直接调用云侧 detach/force detach、修改 IAM 委托、扩容 PVC、删除 finalizer。
- ConfigMap/Secret 的 `resourceVersion` 没有天然更新时间；仅能用 `managedFields.time`、Pod 时间和 FailedMount 事件做旁证。

## 输入与主流程

最小输入为 `region`、`cluster_id`。建议补齐：

- `namespace`、`pvc_name`：PVC Pending、Terminating、容量耗尽时优先提供。
- `pod_name`：Pod Pending、ContainerCreating、Running 但 IO 异常时优先提供。
- `failure_symptom`：例如“PVC Pending”“FailedMount mount.nfs timeout”“OBS 403”“Read-only file system”“no space left on device”“PVC Terminating”。

主流程：

1. 调用 `huawei_storage_failure_diagnose`，默认 `include_stats=true`、`include_logs=true`、`include_cloud=false`。
2. 若需要云侧清单补证，设置 `include_cloud=true`，会按命中的存储类型读取 EVS/SFS/SFS Turbo 和安全组/ACL 只读信息。
3. 若主工具返回 `report_markdown`，最终输出以该 Markdown 为主体，不要丢弃证据矩阵。
4. 若主工具失败，按下面四阶段手工兜底。

## 一、供应期故障

准入：PVC `status=Pending`。

通用前置：

- 读取 StorageClass 的 `volumeBindingMode`。
- 若为 `WaitForFirstConsumer` 且无关联 Pod，输出“正常行为，等待 Pod 调度触发动态创建”，置信度高。

分支：

- EVS：PVC 事件命中 `FailedProvisioning` + `QuotaExceeded`，定位为 EVS 云硬盘配额不足。
- SFS/SFS Turbo：事件命中 `Subnet IP insufficiency`，或供应失败返回 `400/403` 且文本指向 subnet/mount/ip，定位为 VPC 子网可用 IP 或挂载点分配问题。
- OBS：事件命中 `BucketAlreadyExists` 或 `InvalidBucketName`，定位为桶名冲突或命名不合法。

## 二、调度与绑定期故障

准入：PVC `Bound`，关联 Pod `Pending/Unschedulable`。

EVS：

- 读取 PV `spec.nodeAffinity`，通常体现单 AZ。
- 读取 Pod `nodeSelector`、tolerations 和 FailedScheduling 事件。
- 查询 Ready 节点标签、污点和调度事件。
- 若出现 `volume node affinity conflict`、PV AZ 内无 Ready 节点、或 AZ 内节点全被不可容忍污点/资源不足阻断，输出“EVS 强单可用区属性导致 Pod 无法调度到存储所在 AZ”。

Local：

- 读取 PV `nodeAffinity` 绑定节点。
- 若该节点 `Ready=False/Unknown`，输出“本地存储所属宿主机宕机/离线”，置信度最高。

## 三、挂载期故障

准入：Pod 卡在 `ContainerCreating`，或事件包含 `FailedAttachVolume`/`FailedMount`。

EVS：

- 按 PV 和目标 Node 过滤 VolumeAttachment。
- VolumeAttachment 不存在：K8s 控制面尚未下发挂载指令。
- `attached=false` 且 `attachError` 命中 max/limit/exceed：ECS 单节点挂载盘数量上限。
- `attached=false` 且 `attachError` 命中 in-use/attached/lock/status：EVS 被残留节点占用或底层锁未释放。
- `attached=true` 但 FailedMount：云侧已挂载，进入宿主机内核/文件系统挂载失败分支。

SFS/SFS Turbo：

- `FailedMount` 文本包含 `mount.nfs` 和 `timed out`：疑似网络数据面阻断。
- 输出 SFS endpoint、NetworkPolicy 旁证，并提醒重点检查节点安全组、SFS 安全组、VPC ACL 和 2049 端口。

OBS：

- 读取 Everest CSI 日志，结合 PV/事件关键词。
- 命中 `403 Forbidden`、`SignatureDoesNotMatch`、`failed to save temporary ak sk file`、`obsfs: ak size is invalid`、`fuse_opt_parse fail`：定位 IAM 委托被改、AK/SK Secret 失效、Secret 字段/格式错误或桶权限异常。

权限异常：

- 事件出现 `permission denied`、`forbidden`、`access denied` 时，作为独立权限候选输出；OBS 403 优先走 OBS 凭证分支。

## 四、运行期与注销期异常

容量与 inode：

- 通过 `/stats/summary` 解析 PVC `usedBytes/capacityBytes` 和 `inodesUsed/inodes`。
- 容量使用率 > 95%：容量耗尽，置信度最高。
- inode 使用率 > 95%：inode 耗尽，小文件过多，置信度最高。

只读文件系统：

- 用户症状或事件包含 `Read-only file system`。
- 若同一节点有 `DiskPressure`、`KernelOops` 或类似事件，输出“宿主机触发 Linux 只读保护机制”，建议迁移工作负载并检查节点底层存储链路。

ConfigMap/Secret subPath：

- Pod 使用 ConfigMap/Secret `subPath` 挂载。
- 随后出现 `FailedMount`、`subPath`、`not a directory`、`stale file handle` 等事件，输出 subPath 挂载点保护/死锁类问题。

PVC 删除保护：

- PVC 有 `deletionTimestamp` 且 finalizers 包含 `kubernetes.io/pvc-protection`。
- 遍历所有 Pod，若仍引用该 PVC，输出“删除保护生效：请先删除残留 Pod”，置信度最高。

## 结论合成

结论按证据强度排序，而不是按阶段固定优先级：

1. 明确事件/状态字段直接指向云配额、桶名、VolumeAttachment、容量或 PVC protection：高置信度。
2. 调度事件与 PV nodeAffinity/节点标签一致：高置信度；只有资源不足文本时为中高置信度。
3. NFS timeout、只读文件系统、IO error：通常是中等置信度，需要云侧安全组/节点日志补证。
4. 没有明确命中时输出证据缺口，不把猜测写成结论。
