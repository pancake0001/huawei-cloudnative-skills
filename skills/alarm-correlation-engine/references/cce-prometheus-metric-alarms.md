# CCE 告警中心 Prometheus 指标告警参考


> 本文档只收录“告警类型=指标类”的规则，用于后续创建 Prometheus 指标告警时直接参考。

## 使用约束

- 集群版本：`v1.17` 及以上
- 基础依赖：云原生监控插件（指标上报至 AOM Prometheus）
- `problem_gauge` 类规则额外依赖：节点故障检测插件（NPD）

## 1) 负载规则集（指标类）

| 告警项 | 告警说明 | PromQL |
|---|---|---|
| Pod状态异常 | 检查 Pod 状态是否异常 | `sum(min_over_time(kube_pod_status_phase{phase=~"Pending\|Unknown\|Failed"}[10m]) and count_over_time(kube_pod_status_phase{phase=~"Pending\|Unknown\|Failed"}[10m]) > 18 ) by (namespace,pod,phase,cluster_name,cluster) > 0` |
| Pod频繁重启 | 检查 Pod 是否频繁重启 | `increase(kube_pod_container_status_restarts_total[5m]) > 3` |
| Deployment副本数不匹配 | 检查无状态负载副本是否匹配 | `(kube_deployment_spec_replicas != kube_deployment_status_replicas_available) and (changes(kube_deployment_status_replicas_updated[5m]) == 0)` |
| Statefulset副本数不匹配 | 检查有状态负载副本是否匹配 | `(kube_statefulset_status_replicas_ready != kube_statefulset_status_replicas) and (changes(kube_statefulset_status_replicas_updated[5m]) == 0)` |
| 容器CPU使用率大于80% | 检查容器 CPU 使用率是否大于 80% | `100 * (sum(rate(container_cpu_usage_seconds_total{image!="",container!="POD"}[1m])) by (cluster_name,pod,node,namespace,container,cluster) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (cluster_name,pod,node,namespace,container,cluster)) > 80` |
| 容器内存使用率大于80% | 检查容器内存使用率是否大于 80% | `(sum(container_memory_working_set_bytes{image!="",container!="POD"}) by (cluster_name,node,container,pod,namespace,cluster) / sum(container_spec_memory_limit_bytes > 0) by (cluster_name,node,container,pod,namespace,cluster) * 100) > 80` |
| 容器状态异常 | 检查容器状态是否异常 | `sum by (namespace,pod,container,cluster_name,cluster) (kube_pod_container_status_waiting_reason) > 0` |

## 2) 节点资源规则集（指标类）

| 告警项 | 告警说明 | PromQL |
|---|---|---|
| Kube持久卷使用率高 | 检查节点持久卷使用率是否过高 | `(kubelet_volume_stats_available_bytes{job="kubelet"} / kubelet_volume_stats_capacity_bytes{job="kubelet"}) < 0.03 and kubelet_volume_stats_used_bytes{job="kubelet"} > 0` |
| Kube持久卷声明状态异常 | 检查 PVC 状态是否异常 | `kube_persistentvolumeclaim_status_phase{phase=~"Failed\|Pending\|Lost"} > 0` |
| Kube持久卷状态异常 | 检查 PV 状态是否异常 | `kube_persistentvolume_status_phase{phase=~"Failed\|Pending"} > 0` |
| 节点CPU使用率超过80% | 检查节点 CPU 使用率是否大于 80% | `100 - (avg by(node,cluster_name,cluster) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100) > 80` |
| 节点内存可用率不足10% | 检查节点可用内存是否不足 10% | `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100 < 10` |
| 节点磁盘可用率不足10% | 检查节点可用磁盘是否不足 10% | `avg((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes) by (device,node,cluster_name,cluster) < 10` |
| 节点EmptyDir存储池异常 | 检查临时卷存储池是否异常 | `problem_gauge{type="EmptyDirVolumeGroupStatusError"} >= 1` |
| 节点内存资源不足 | 检查节点整体内存是否充足 | `problem_gauge{type="MemoryProblem"} >= 1` |
| 节点持久卷存储池异常 | 检查持久卷存储池是否异常 | `problem_gauge{type="LocalPvVolumeGroupStatusError"} >= 1` |
| 节点挂载点异常 | 检查挂载点是否异常 | `problem_gauge{type="MountPointProblem"} >= 1` |
| 节点文件句柄数不足 | 检查 FD 资源是否充足 | `problem_gauge{type="FDProblem"} >= 1` |
| 节点磁盘卡IO | 检查磁盘卡 IO 故障 | `problem_gauge{type="DiskHung"} >= 1` |
| 节点磁盘只读 | 检查磁盘是否只读 | `problem_gauge{type="DiskReadonly"} >= 1` |
| 节点磁盘异常 | 检查系统盘/数据盘异常 | `problem_gauge{type="DiskProblem"} >= 1` |
| 节点磁盘慢IO | 检查磁盘慢 IO 故障 | `problem_gauge{type="DiskSlow"} >= 1` |
| 节点进程资源不足 | 检查 PID 资源是否充足 | `problem_gauge{type="PIDProblem"} >= 1` |
| 节点连接跟踪表不足 | 检查 conntrack 表是否充足 | `problem_gauge{type="ConntrackFullProblem"} >= 1` |

## 3) 节点状态规则集（指标类）

| 告警项 | 告警说明 | PromQL |
|---|---|---|
| ResolvConf配置文件异常 | 检查 ResolvConf 配置异常 | `problem_gauge{type="ResolvConfFileProblem"} >= 1` |
| 节点CNI组件异常 | 检查 CNI 组件状态 | `problem_gauge{type="CNIProblem"} >= 1` |
| 节点CRI组件异常 | 检查 Docker/Containerd 运行状态 | `problem_gauge{type="CRIProblem"} >= 1` |
| 节点Kube-proxy故障 | 检查 kube-proxy 运行状态 | `problem_gauge{type="KUBEPROXYProblem"} >= 1` |
| 节点Kubelet异常 | 检查 kubelet 状态 | `problem_gauge{type="KUBELETProblem"} >= 1` |
| 节点存在计划事件 | 检查主机计划事件 | `problem_gauge{type="ScheduledEvent"} >= 1` |
| Node状态抖动 | 检查 Ready 状态频繁波动 | `sum(changes(kube_node_status_condition{status="true",condition="Ready"}[15m])) by (cluster_name,node,cluster) > 2` |
| 节点Containerd频繁重启 | 检查 Containerd 频繁重启 | `problem_gauge{type="FrequentContainerdRestart"} >= 1` |
| 节点进程D异常 | 检查 D 进程异常 | `problem_gauge{type="ProcessD"} >= 1` |
| 节点进程Z异常 | 检查 Z 进程异常 | `problem_gauge{type="ProcessZ"} >= 1` |
| 节点CRI频繁重启 | 检查 CRI 频繁重启 | `problem_gauge{type="FrequentCRIRestart"} >= 1` |
| 节点Docker频繁重启 | 检查 Docker 频繁重启 | `problem_gauge{type="FrequentDockerRestart"} >= 1` |
| 节点Kubelet频繁重启 | 检查 Kubelet 频繁重启 | `problem_gauge{type="FrequentKubeletRestart"} >= 1` |
| 节点NTP服务故障 | 检查 ntpd/chronyd 服务状态 | `problem_gauge{type="NTPProblem"} >= 1` |

## 配置建议（用于后续工具实现）

- 推荐默认阈值周期：`period=60`, `evaluation_periods=3`
- 规则命名建议：`{cluster_name}-{rule_short_name}`
- 默认企业项目：`all_granted_eps`（仅在显式传参时使用指定企业项目）
- 如果表达式使用 `problem_gauge`，创建前先检查 NPD 插件状态

