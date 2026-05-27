# 配置节点故障检测策略 / Configure Node Fault Detection Policy
**更新时间：2026-03-30 GMT+08:00**
**来源：华为云官方文档 https://support.huaweicloud.com/usermanual-cce/cce_10_0659.html**

节点故障检查功能依赖[CCE节点故障检测](https://support.huaweicloud.com/usermanual-cce/cce_10_0132.html)插件，该插件实例会运行在每个节点上，对节点上的故障事件进行监控。本文介绍如何开启节点故障检测能力。

---

## 开启节点故障检测

- 登录[CCE控制台](https://console.huaweicloud.com/cce2.0/?#/cce/cluster/list)，单击集群名称进入集群。
- 在左侧选择“节点管理”，切换至“节点”页签。
- 单击“故障检测策略”，可查看当前故障检测项。关于NPD检查项列表请参见[NPD检查项](#npd检查项)。如果不存在“故障检测策略”按钮，则说明集群中未安装CCE节点故障检测插件或插件运行状态异常，已安装插件且插件运行正常后，可正常使用故障检测策略功能。
- 当前节点检查结果异常时，将在节点状态处提示“指标异常”。
- 您可单击“指标异常”，按照修复建议提示修复。

---

## 自定义检查项配置

- 登录[CCE控制台](https://console.huaweicloud.com/cce2.0/?#/cce/cluster/list)，单击集群名称进入集群。
- 在左侧选择“节点管理”，切换至“节点”页签，单击“故障检测策略”。
- 在跳转的页面中查看当前检查项配置，单击检查项操作列的“编辑”，自定义检查项配置。 当前支持以下配置：
  - **启用/停用**：自定义某个检查项的开启或关闭。
  - **目标节点**：检查项默认运行在全部节点，您可根据自身场景需求，通过节点标签自定义筛选满足条件的节点。如果设置多个筛选条件，则目标节点需同时满足所有条件，若不设置筛选条件，则默认为全部节点。例如竞价实例中断回收检查只运行在竞价实例节点，可通过指定的节点标签`cce.io/is-spot`筛选竞价实例节点。
  - **检查周期**：检查触发的时间间隔，CCE节点故障检测插件提供默认检查周期，能够匹配常见的故障场景，您可根据自身场景需求自定义修改检查周期。
  - **触发阈值**：CCE节点故障检测插件提供默认阈值，能够匹配常见的故障场景，您可根据自身场景需求自定义修改故障阈值。不同的检查项的故障阈值不同，例如失败次数、资源占用百分比等，请根据实际进行调整。例如“连接跟踪表耗尽”检查项中，可将资源占用百分比的触发阈值由90%调整至80%。
  - **故障应对策略**：故障产生后，您可根据自身场景需求自定义修改故障应对策略，当前故障应对策略如下：

| 故障应对策略 | 效果 |
|-------------|------|
| 提示异常 | 上报Kubernetes事件。 |
| 禁止调度 | 上报Kubernetes事件，并为节点添加NoSchedule污点。 |
| 驱逐节点负载 | 上报Kubernetes事件，并为节点添加NoExecute污点。该操作会驱逐节点上的负载，可能导致业务不连续，请谨慎选择。 |

---

## NPD检查项

当前检查项仅1.16.0及以上版本的插件支持。

NPD的检查项主要分为**事件类检查项**和**状态类检查项**。

### 事件类检查项
对于事件类检查项，当问题发生时，NPD会向APIServer上报一条事件，事件类型分为Normal（正常事件）和Warning（异常事件）

| 故障检查项 | 功能说明 | 监听对象/匹配规则 |
|-----------|---------|------------------|
| OOMKilling | 监听内核日志，检查OOM事件发生并上报<br>典型场景：容器内进程使用的内存超过了Limit，触发OOM并终止该进程 | 监听对象：`/dev/kmsg`<br>匹配规则：`"Killed process \\d+ (.+) total-vm:\\d+kB, anon-rss:\\d+kB, file-rss:\\d+kB.*"` |
| TaskHung | 监听内核日志，检查taskHung事件发生并上报<br>典型场景：磁盘卡IO导致进程卡住 | 监听对象：`/dev/kmsg`<br>匹配规则：`"task \\S+:\\w+ blocked for more than \\w+ seconds\\."` |
| ReadonlyFilesystem | 监听内核日志，检查系统内核是否有Remount root filesystem read-only错误<br>典型场景：用户从ECS侧误操作卸载节点数据盘，且应用程序对该数据盘的对应挂载点仍有持续写操作，触发内核产生IO错误将磁盘重挂载为只读磁盘。<br>⚠️ 说明：节点容器存储Rootfs为Device Mapper类型时，数据盘卸载会导致thinpool异常，影响NPD运行，NPD将无法检测节点故障。 | 监听对象：`/dev/kmsg`<br>匹配规则：`"Remounting filesystem read-only"` |

### 状态类检查项
对于状态类检查项，当问题发生时，NPD会向APIServer上报一条事件，并同步修改节点状态，可配合[Node-problem-controller故障隔离](https://support.huaweicloud.com/usermanual-cce/cce_10_0132.html#cce_10_0132__section1471610580474)对节点进行隔离。

#### 系统组件检查
| 故障检查项 | 功能说明 | 备注 |
|-----------|---------|------|
| CNIProblem | 检查CNI组件（容器网络组件）运行状态 | - |
| CRIProblem | 检查节点CRI组件（容器运行时组件）Docker和Containerd的运行状态 | 检查对象：Docker或Containerd |
| FrequentKubeletRestart | 通过定期回溯系统日志，检查关键组件Kubelet是否频繁重启<br>默认阈值：4分钟内重启4次 | 监听对象：`/run/log/journal`目录下的日志<br>⚠️ Ubuntu和Huawei Cloud EulerOS 2.0操作系统由于日志格式不兼容，暂不支持该检查项 |
| FrequentDockerRestart | 通过定期回溯系统日志，检查容器运行时Docker是否频繁重启 | 同上 |
| FrequentContainerdRestart | 通过定期回溯系统日志，检查容器运行时Containerd是否频繁重启 | 同上 |
| KubeletProblem | 检查关键组件Kubelet的运行状态 | - |
| KubeProxyProblem | 检查关键组件KubeProxy的运行状态 | - |
| PodIdentityAgentProblem | 检查关键组件PodIdentityAgent的运行状态（该检查项在插件版本为1.19.50及以上时生效） | ⚠️ 如果集群版本不支持Pod Identity功能（v1.28.15-r80、v1.29.15-r40、v1.30.14-r40、v1.31.14-r0、v1.32.9-r0、v1.33.7-r0、v1.34.2-r0及以上版本支持），NPD中针对PodIdentityAgent异常的告警配置不生效。<br>节点上PodIdentityAgent组件用来根据用户配置给插件或者负载的委托换取临时凭据访问云服务（如EVS），异常后会导致访问云服务功能异常，可能会影响整个集群的业务，需要驱逐该节点上的工作负载。 |

#### 系统指标
| 故障检查项 | 功能说明 | 阈值/计算方式 |
|-----------|---------|--------------|
| ConntrackFullProblem | 检查连接跟踪表是否耗尽 | 默认阈值：90%<br>使用量：`nf_conntrack_count`<br>最大值：`nf_conntrack_max` |
| DiskProblem | 检查节点系统盘、CCE数据盘（包含CRI逻辑盘与Kubelet逻辑盘）的磁盘使用情况 | 默认阈值：90%<br>数据来源：`df -h`<br>⚠️ 当前暂不支持检查除节点系统盘、CCE数据盘外的其他数据盘 |
| FDProblem | 检查系统关键资源FD文件句柄数是否耗尽 | 默认阈值：90%<br>使用量：`/proc/sys/fs/file-nr`中第1个值<br>最大值：`/proc/sys/fs/file-nr`中第3个值 |
| MemoryProblem | 检查系统关键资源Memory内存资源是否耗尽 | 默认阈值：80%<br>使用量：`/proc/meminfo`中`MemTotal-MemAvailable`<br>最大值：`/proc/meminfo`中`MemTotal` |
| PIDProblem | 检查系统关键资源PID进程资源是否耗尽 | 默认阈值：90%<br>使用量：`/proc/loadavg`中第4个值的分母，表示可运行的进程总数<br>最大值：`/proc/sys/kernel/pid_max`和`/proc/sys/kernel/threads-max`两者的较小值 |

#### 存储检查
| 故障检查项 | 功能说明 | 检查逻辑/阈值 |
|-----------|---------|--------------|
| DiskReadonly | 通过定期对节点系统盘、CCE数据盘（包含CRI逻辑盘与Kubelet逻辑盘）进行测试性写操作，检查关键磁盘的可用性 | 检测路径：<br>- `/mnt/paas/kubernetes/kubelet/`<br>- `/var/lib/docker/`<br>- `/var/lib/containerd/`<br>- `/var/paas/sys/log/kubernetes`<br>检测路径下会产生临时文件`npd-disk-write-ping` |
| EmptyDirVolumeGroupStatusError | 检查节点上临时卷存储池是否正常<br>故障影响：依赖存储池的Pod无法正常写对应临时卷。临时卷由于IO错误被内核重挂载成只读文件系统。<br>典型场景：用户在创建节点时配置两个数据盘作为临时卷存储池，用户误操作删除了部分数据盘导致存储池异常。 | 检查周期：30秒<br>数据来源： `vgs -o vg_name, vg_attr`<br>检测原理：检查VG（存储池）是否存在p状态，该状态表征部分PV（数据盘）丢失。 |
| LocalPvVolumeGroupStatusError | 检查节点上持久卷存储池是否正常<br>故障影响：依赖存储池的Pod无法正常写对应持久卷。持久卷由于IO错误被内核重挂载成只读文件系统。<br>典型场景：用户在创建节点时配置两个数据盘作为持久卷存储池，用户误操作删除了部分数据盘。 | - |
| MountPointProblem | 检查节点上的挂载点是否异常<br>异常定义：该挂载点不可访问（cd）<br>典型场景：节点挂载了nfs（网络文件系统，常见有obsfs、s3fs等），当由于网络或对端nfs服务器异常等原因导致连接异常时，所有访问该挂载点的进程均卡死。例如集群升级场景kubelet重启时扫描所有挂载点，当扫描到此异常挂载点会卡死，导致升级失败。 | 等效检查命令：<br>`for dir in \`df -h | grep -v "Mounted on" | awk "{print \\$NF}"\`;do cd $dir; done && echo "ok"` |
| DiskHung | 检查节点上所有磁盘是否存在卡IO，即IO读写无响应<br>卡IO定义：系统对磁盘的IO请求下发后未有响应，部分进程卡在D状态<br>典型场景：操作系统硬盘驱动异常或底层网络严重故障导致磁盘无法响应 | 检查对象：所有数据盘<br>数据来源： `/proc/diskstat` 等效查询命令： `iostat -xmt 1`<br>阈值（需同时满足）：<br>- 平均利用率（ioutil）>=0.99<br>- 平均IO队列长度（avgqu-sz）>=1<br>- 平均IO传输量<br>⚠️ 部分操作系统卡IO时无数据变化，此时计算CPU IO时间占用率（iowait） > 0.8。 |
| DiskSlow | 检查节点上所有磁盘是否存在慢IO，即IO读写有响应但响应缓慢<br>典型场景：云硬盘由于网络波动导致慢IO。 | 检查对象：所有数据盘<br>数据来源： `/proc/diskstat` 等效查询命令 `iostat -xmt 1`<br>默认阈值： 平均IO时延，await >=5000ms<br>⚠️ 卡IO场景下该检查项失效，原因为IO请求未有响应，await数据不会刷新。 |

#### 其他检查
| 故障检查项 | 功能说明 | 阈值/备注 |
|-----------|---------|----------|
| NTPProblem | 检查节点时钟同步服务ntpd或chronyd是否正常运行，系统时间是否漂移 | 默认时钟偏移阈值：8000ms |
| ProcessD | 检查节点是否存在D进程 | 默认阈值：连续3次存在10个异常进程<br>数据来源：`/proc/{PID}/stat`、`ps aux`<br>⚠️ 例外场景：ProcessD忽略BMS节点下的SDI卡驱动依赖的常驻D进程heartbeat、update |
| ProcessZ | 检查节点是否存在Z进程 | - |
| RDMA网卡异常 | 检查节点上RDMA网卡状态 | 默认阈值：连续1次存在1个RDMA网卡异常<br>数据来源：命令：`rdma link show`<br>⚠️ NPD在1.19.37及以上版本中新增了对RDMA网卡的异常检测功能，并会在节点上标注RDMAProblem状态。由于该状态由NPD主动写入节点对象，若回退到不支持此功能的旧版本，NPD不再具备清理该状态的能力，因此已标注的状态将保留。 |
| ResolvConfFileProblem | 检查ResolvConf配置文件是否丢失/异常<br>异常定义：不包含任何上游域名解析服务器（nameserver）。 | 检查对象：`/etc/resolv.conf` |
| ScheduledEvent | 检查节点是否存在热迁移计划事件。热迁移计划事件通常由硬件故障触发，是IaaS层的一种自动故障修复手段。<br>典型场景：底层宿主机异常，例如风扇损坏、磁盘坏道等，导致其上虚机触发热迁移。 | 数据来源：`http://169.254.169.254/meta-data/latest/events/scheduled`<br>该检查项为Alpha特性，默认不开启。 |
| SpotPriceNodeReclaimNotification | 检查竞价实例节点是否被抢占而处于中断回收状态 | 默认检查周期：120秒<br>默认故障应对策略：驱逐节点负载 |

---

## Kubelet内置检查项对比
kubelet组件内置如下检查项，但是存在不足，您可通过集群升级或安装NPD进行补足：

| 故障检查项 | 功能说明 | 缺点 |
|-----------|---------|------|
| PIDPressure | 检查PID是否充足<br>周期：10秒<br>阈值：90% | 社区1.23.1及以前版本，该检查项在pid使用量大于65535时失效，详见[issue 107107](https://github.com/kubernetes/kubernetes/issues/107107)。社区1.24及以前版本，该检查项未考虑thread-max。 |
| MemoryPressure | 检查容器可分配空间（allocable）内存是否充足<br>周期：10秒<br>阈值：最大值-100MiB<br>最大值（Allocable）：节点总内存-节点预留内存 | 该检测项没有从节点整体内存维度检查内存耗尽情况，只关注了容器部分(Allocable)。 |
| DiskPressure | 检查kubelet盘和docker盘的磁盘使用量及inodes使用量<br>周期：10秒<br>阈值：90% | - |