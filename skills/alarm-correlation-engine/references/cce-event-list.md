# CCE事件列表

来源：<https://support.huaweicloud.com/usermanual-cce/cce_10_0902.html>

使用规则：
- 创建事件告警时，优先使用 `中文事件描述##事件名称` 格式作为 `event_name`。
- 如果仅传事件名称（例如 `NodeHasDiskPressure`）或中文事件描述（例如 `节点磁盘空间不足`），工具会尝试自动映射到完整格式。

## 工作负载相关事件

| 类别 | 事件描述 | 事件名称 | 事件级别 |
|---|---|---|---|
| Pod | Pod内存不足OOM | PodOOMKilling | 重要 |
| Pod | 启动失败 | FailedStart | 重要 |
| Pod | 拉取镜像失败 | FailedPullImage | 重要 |
| Pod | 启动重试失败 | BackOffStart | 重要 |
| Pod | 调度失败 | FailedScheduling | 重要 |
| Pod | 拉取镜像重试失败 | BackOffPullImage | 重要 |
| Pod | 创建失败 | FailedCreate | 重要 |
| Pod | 状态异常 | Unhealthy | 次要 |
| Pod | 删除失败 | FailedDelete | 次要 |
| Pod | 未拉取镜像异常 | ErrImageNeverPull | 次要 |
| Pod | 扩容失败 | FailedScaleOut | 次要 |
| Pod | 待机失败 | FailedStandBy | 次要 |
| Pod | 更新配置失败 | FailedReconfig | 次要 |
| Pod | 激活失败 | FailedActive | 次要 |
| Pod | 回滚失败 | FailedRollback | 次要 |
| Pod | 更新失败 | FailedUpdate | 次要 |
| Pod | 缩容失败 | FailedScaleIn | 次要 |
| Pod | 重启失败 | FailedRestart | 次要 |
| Deployment | 标签选择器冲突 | SelectorOverlap | 次要 |
| Deployment | 副本集创建异常 | ReplicaSetCreateError | 次要 |
| Deployment | 部署回滚版本未发现 | DeploymentRollbackRevisionNotFound | 次要 |
| DaemonSet | 标签选择器异常 | SelectingAll | 次要 |
| Job | 太多活跃Pod | TooManyActivePods | 次要 |
| Job | 太多成功Pod | TooManySucceededPods | 次要 |
| CronJob | 查询失败 | FailedGet | 次要 |
| CronJob | 查询Pod列表失败 | FailedList | 次要 |
| CronJob | 未知Job | UnexpectedJob | 次要 |

## 网络相关事件

| 类别 | 事件描述 | 事件名称 | 事件级别 |
|---|---|---|---|
| Service | 创建负载均衡失败 | CreatingLoadBalancerFailed | 次要 |
| Service | 删除负载均衡失败 | DeletingLoadBalancerFailed | 次要 |
| Service | 更新负载均衡失败 | UpdateLoadBalancerFailed | 次要 |

## 节点相关事件

| 类别 | 事件描述 | 事件名称 | 事件级别 |
|---|---|---|---|
| Node | 节点重启 | Rebooted | 重要 |
| Node | 节点不可调度 | NodeNotSchedulable | 重要 |
| Node | 节点状态异常 | NodeNotReady | 重要 |
| Node | 节点创建失败 | NodeCreateFailed | 重要 |
| Node | 节点挂载或卸载EVS盘失败 | FailedToAttachDetach | 重要 |
| Node | 节点kubelet故障 | KUBELETIsDown | 次要 |
| Node | 节点内存空间不足 | NodeHasInsufficientMemory | 次要 |
| Node | 节点上发现未注册的网络设备 | UnregisterNetDevice | 次要 |
| Node | 网卡未发现 | NetworkCardNotFound | 次要 |
| Node | 节点kube-proxy故障 | KUBEPROXYIsDown | 次要 |
| Node | 节点磁盘空间已满 | NodeOutOfDisk | 次要 |
| Node | 节点任务夯住 | TaskHung | 次要 |
| Node | CIDR不可用 | CIDRNotAvailable | 次要 |
| Node | 节点的连接跟踪表已满 | ConntrackFull | 次要 |
| Node | 节点磁盘空间不足 | NodeHasDiskPressure | 次要 |
| Node | 节点纳管失败 | NodeInstallFailed | 次要 |
| Node | 节点操作系统内核故障 | KernelOops | 次要 |
| Node | 节点内存不足强杀进程 | OOMKilling | 次要 |
| Node | 节点docker故障 | DOCKERIsDown | 次要 |
| Node | CIDR分配失败 | CIDRAssignmentFailed | 次要 |
| Node | 节点docker夯住 | DockerHung | 次要 |
| Node | 节点文件系统只读 | FilesystemIsReadOnly | 次要 |
| Node | 节点ntp服务故障 | NTPIsDown | 次要 |
| Node | 节点卸载失败 | NodeUninstallFailed | 次要 |
| Node | 节点磁盘卸载夯住 | AUFSUmountHung | 次要 |
| Node | 节点cni插件故障 | CNIIsDown | 次要 |
| Namespace | 废弃节点清理 | DeleteNodeWithNoServer | 次要 |

## 存储相关事件

| 类别 | 事件描述 | 事件名称 | 事件级别 |
|---|---|---|---|
| PV | 主机卸载块存储失败 | DetachVolumeFailed | 次要 |
| PV | 卷回收策略未知 | VolumeUnknownReclaimPolicy | 次要 |
| PV | 挂载数据卷失败 | SetUpAtVolumeFailed | 次要 |
| PV | 数据卷回收失败 | VolumeFailedRecycle | 次要 |
| PV | 等待主机挂载块存储失败 | WaitForAttachVolumeFailed | 次要 |
| PV | 数据卷删除失败 | VolumeFailedDelete | 次要 |
| PV | 挂载盘符失败 | MountDeviceFailed | 次要 |
| PV | 卸载数据卷失败 | TearDownAtVolumeFailed | 次要 |
| PV | 卸载盘符失败 | UnmountDeviceFailed | 次要 |
| PV | 主机挂载块存储失败 | AttachVolumeFailed | 次要 |
| PVC | 数据卷扩容失败 | VolumeResizeFailed | 次要 |
| PVC | 卷PVC丢失 | ClaimLost | 次要 |
| PVC | 创建卷失败 | ProvisioningFailed | 次要 |
| PVC | 创建卷清理失败 | ProvisioningCleanupFailed | 次要 |
| PVC | 卷误绑定 | ClaimMisbound | 次要 |

## 弹性伸缩相关事件

| 类别 | 事件描述 | 事件名称 | 事件级别 |
|---|---|---|---|
| Autoscaler | 扩容节点超时 | ScaleUpTimedOut | 重要 |
| Autoscaler | 节点池资源充足 | NodePoolAvailable | 重要 |
| Autoscaler | 缩容节点 | ScaleDown | 重要 |
| Autoscaler | 未触发节点扩容 | NotTriggerScaleUp | 重要 |
| Autoscaler | 删除未注册节点成功 | DeleteUnregistered | 重要 |
| Autoscaler | 缩容空闲节点成功 | ScaleDownEmpty | 重要 |
| Autoscaler | 缩容节点失败 | ScaleDownFailed | 重要 |
| Autoscaler | 节点池扩容节点失败 | FailedToScaleUpGroup | 重要 |
| Autoscaler | 节点池扩容节点成功 | ScaledUpGroup | 重要 |
| Autoscaler | 扩容节点失败 | ScaleUpFailed | 重要 |
| Autoscaler | 修复节点池节点个数成功 | FixNodeGroupSizeDone | 重要 |
| Autoscaler | 节点池退避重试中 | NodeGroupInBackOff | 重要 |
| Autoscaler | 修复节点池节点个数失败 | FixNodeGroupSizeError | 重要 |
| Autoscaler | 节点池资源售罄 | NodePoolSoldOut | 重要 |
| Autoscaler | 触发节点扩容 | TriggeredScaleUp | 重要 |
| Autoscaler | 节点池扩容节点启动 | StartScaledUpGroup | 重要 |
| Autoscaler | 删除未注册节点失败 | DeleteUnregisteredFailed | 重要 |
| HPA | HPA非法指标范围 | InvalidTargetRange | 重要 |
| HPA | HPA获取伸缩对象失败 | FailedGetScale | 重要 |
| HPA | HPA计算资源扩缩副本数失败 | FailedComputeMetricsReplicas | 重要 |
| HPA | HPA获取对象指标失败 | FailedGetObjectMetric | 重要 |
| HPA | HPA获取Pod资源指标失败 | FailedGetPodsMetric | 重要 |
| HPA | HPA获取集群资源指标失败 | FailedGetResourceMetric | 重要 |
| HPA | HPA获取容器资源指标失败 | FailedGetContainerResourceMetric | 重要 |
| HPA | HPA获取外部指标失败 | FailedGetExternalMetric | 重要 |
| HPA | HPA伸缩Pod失败 | FailedRescale | 重要 |
| HPA | Pod扩缩容成功 | SuccessfulRescale | 次要 |
| CronHPA | CronHPA伸缩失败 | ScaleFailed | 重要 |
| CronHPA | CronHPA查询关联HPA失败 | FailedGetHorizontalPodAutoscaler | 重要 |
| CronHPA | CronHPA查询伸缩对象失败 | FailedGetHpaScale | 重要 |
| CronHPA | CronHPA更新关联HPA失败 | UpdateHPAFailed | 重要 |
| CronHPA | 更新HPA策略成功 | UpdateHPASuccess | 次要 |
| CronHPA | 跳过更新HPA策略 | SkipUpdateHPA | 次要 |
| CronHPA | 跳过更新工作负载实例数 | SkipUpdateTarget | 次要 |
| CronHPA | 更新工作负载实例数成功 | UpdateTargetSuccess | 次要 |
| CustomedHPA | CustomedHPA解析冷却时间失败 | FailedSetPolicySettings | 重要 |
| CustomedHPA | CustomedHPA处理定时/指标规则失败 | FailedSubmitRule | 重要 |
| CustomedHPA | CustomedHPA计算资源扩缩副本数失败 | FailedComputeReplicas | 重要 |
| CustomedHPA | CustomedHPA伸缩Pod失败 | FailedScale | 重要 |
| CustomedHPA | CustomedHPA指标扩缩容成功 | MetricScaleSuccess | 次要 |
| CustomedHPA | CustomedHPA周期扩缩容成功 | CronScaleSuccess | 次要 |

## 集群控制面事件

| 事件描述 | 事件名称 | 事件级别 |
|---|---|---|
| 内部故障 | Internal error | 重要 |
| 外部依赖异常 | External dependency error | 重要 |
| 初始化执行线程失败 | Failed to initialize process thread | 重要 |
| 更新数据库失败 | Failed to update database | 重要 |
| 节点池触发创建节点失败 | Failed to create node by nodepool | 重要 |
| 节点池触发删除节点失败 | Failed to delete node by nodepool | 重要 |
| 创建包周期节点失败 | Failed to create yearly/monthly subscription node | 重要 |
| 解除资源租户访问控制节点镜像的授权失败 | Failed to cancel the authorization of accessing the image of the master. | 重要 |
| 创建虚拟IP失败 | Failed to create the virtual IP for the master | 重要 |
| 删除节点虚拟机失败 | Failed to delete the node VM | 重要 |
| 删除节点安全组失败 | Failed to delete the security group of node | 重要 |
| 删除控制节点安全组失败 | Failed to delete the security group of master | 重要 |
| 删除控制节点网卡安全组失败 | Failed to delete the security group of port | 重要 |
| 删除集群ENI/SubENI安全组失败 | Failed to delete the security group of eni or subeni | 重要 |
| 解绑控制节点网卡失败 | Failed to detach the port of master | 重要 |
| 删除控制节点网卡失败 | Failed to delete the port of master | 重要 |
| 删除控制节点虚拟机失败 | Failed to delete the master VM | 重要 |
| 删除控制节点密钥对失败 | Failed to delete the key pair of master | 重要 |
| 删除控制节点subnet失败 | Failed to delete the subnet of master | 重要 |
| 删除控制节点VPC失败 | Failed to delete the VPC of master | 重要 |
| 删除集群证书失败 | Failed to delete certificate of cluster | 重要 |
| 删除控制节点云服务器组失败 | Failed to delete the server group of master | 重要 |
| 删除虚拟IP失败 | Failed to delete the virtual IP for the master | 重要 |
| 获取控制节点浮动IP失败 | Failed to get floating IP of the master | 重要 |
| 获取集群规格信息失败 | Failed to get cluster flavor | 重要 |
| 获取集群endpoint失败 | Failed to get cluster endpoint | 重要 |
| 获取Kubernetes集群连接失败 | Failed to get kubernetes connection | 重要 |
| 更新集群Secret失败 | Failed to update secret | 重要 |
| 处理用户操作超时 | Operation timed out | 重要 |
| 连接Kubernetes集群超时 | Connecting to Kubernetes cluster timed out | 重要 |
| 检查组件状态失败或组件状态异常 | Failed to check component status or components are abnormal | 重要 |
| 无法在Kubernetes集群中找到该节点 | The node is not found in kubernetes cluster | 重要 |
| 节点在Kubernetes集群中状态异常 | The status of node is not ready in kubernetes cluster | 重要 |
| 无法在ECS服务中找到该节点对应的虚拟机 | Can't find corresponding vm of this node in ECS | 重要 |
| 升级控制节点失败 | Failed to upgrade the master | 重要 |
| 升级节点失败 | Failed to upgrade the node | 重要 |
| 变更控制节点规格失败 | Failed to change flavor of the master | 重要 |
| 变更控制节点规格超时 | Change flavor of the master timeout | 重要 |
| 创建包周期节点校验不通过 | Failed to pass verification while creating yearly/monthly subscription node | 重要 |
| 安装节点失败 | Failed to install the node | 重要 |
| 清理VPC中集群容器网络路由表条目失败 | Failed to clean routes of cluster container network in VPC | 重要 |
| 集群状态不可用 | Cluster status is Unavailable | 重要 |
| 集群状态故障 | Cluster status is Error | 重要 |
| 集群状态长时间不更新 | Cluster status is not updated for a long time | 重要 |
| 集群升级超时后更新控制节点状态失败 | Failed to update master status after upgrading cluster timeout | 重要 |
| 集群升级超时后更新运行中的任务失败 | Failed to update running jobs after upgrading cluster timeout | 重要 |
| 更新集群状态失败 | Failed to update cluster status | 重要 |
| 更新节点状态失败 | Failed to update node status | 重要 |
| 纳管节点超时后移除数据库中的节点记录失败 | Failed to remove the static node from database | 重要 |
| 节点处理超时后更新节点状态为异常失败 | Failed to update node status to abnormal after node processing timeout | 重要 |
| 更新集群访问地址失败 | Failed to update the cluster endpoint | 重要 |
| 删除不可用的Kubernetes连接失败 | Failed to delete the unavailable connection of the Kubernetes cluster | 重要 |
| 同步集群证书失败 | Failed to sync the cluster cert | 重要 |
