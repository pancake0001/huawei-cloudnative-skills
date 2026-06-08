# CCE Alarm Center Prometheus Indicator Alarm Reference


> This document only contains the rules of "alarm type = indicator class", which can be used for direct reference when creating Prometheus indicator alarms later.

# # Use constraints

- Cluster version: `v1.17` and above
- Basic dependency: cloud native monitoring plug-in (indicators are reported to AOM Prometheus)
- `problem_gauge` class rules additional dependency: Node Failure Detection Plug-in (NPD)

# # 1) Load rule set (indicator class)

| Alarm item | Alarm description | PromQL |
|---|---|---|
| Pod status is abnormal | Check whether the Pod status is abnormal | `sum(min_over_time(kube_pod_status_phase{phase=~"Pending\|Unknown\|Failed"}[10m]) and count_over_time(kube_pod_status_phase{phase=~"Pending\|Unknown\|Failed"}[10m]) > 18 ) by (namespace,pod,phase,cluster_name,cluster) > 0` |
| Pod restarts frequently | Check whether Pod restarts frequently | `increase(kube_pod_container_status_restarts_total[5m]) > 3` |
| The number of Deployment replicas does not match | Check whether the stateless load replicas match | `(kube_deployment_spec_replicas != kube_deployment_status_replicas_available) and (changes(kube_deployment_status_replicas_updated[5m]) == 0)` |
| The number of Statefulset replicas does not match | Check whether the stateful load replicas match | `(kube_statefulset_status_replicas_ready != kube_statefulset_status_replicas) and (changes(kube_statefulset_status_replicas_updated[5m]) == 0)` |
| Container CPU usage is greater than 80% | Check whether container CPU usage is greater than 80% | `100 * (sum(rate(container_cpu_usage_seconds_total{image!="",container!="POD"}[1m])) by (cluster_name,pod,node,namespace,container,cluster) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (cluster_name,pod,node,namespace,container,cluster)) > 80` |
| Container memory usage is greater than 80% | Check whether container memory usage is greater than 80% | `(sum(container_memory_working_set_bytes{image!="",container!="POD"}) by (cluster_name,node,container,pod,namespace,cluster) / sum(container_spec_memory_limit_bytes > 0) by (cluster_name,node,container,pod,namespace,cluster) * 100) > 80` |
| The container status is abnormal | Check whether the container status is abnormal | `sum by (namespace,pod,container,cluster_name,cluster) (kube_pod_container_status_waiting_reason) > 0` |

# # 2) Node resource rule set (indicator class)

| Alarm item | Alarm description | PromQL |
|---|---|---|
| Kube persistent volume usage is high | Check whether the node persistent volume usage is too high | `(kubelet_volume_stats_available_bytes{job="kubelet"} / kubelet_volume_stats_capacity_bytes{job="kubelet"}) < 0.03 and kubelet_volume_stats_used_bytes{job="kubelet"} > 0` |
| Kube persistent volume claim status is abnormal | Check whether the PVC status is abnormal | `kube_persistentvolumeclaim_status_phase{phase=~"Failed\|Pending\|Lost"} > 0` |
| Kube persistent volume status is abnormal | Check whether the PV status is abnormal | `kube_persistentvolume_status_phase{phase=~"Failed\|Pending"} > 0` |
| Node CPU usage exceeds 80% | Check whether node CPU usage is greater than 80% | `100 - (avg by(node,cluster_name,cluster) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100) > 80` |
| The node memory availability is less than 10% | Check whether the node's available memory is less than 10% | `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100 < 10` |
| The node disk availability is less than 10% | Check whether the node's available disk is less than 10% | `avg((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes) by (device,node,cluster_name,cluster) < 10` |
| The node EmptyDir storage pool is abnormal | Check whether the temporary volume storage pool is abnormal | `problem_gauge{type="EmptyDirVolumeGroupStatusError"} >= 1` |
| Insufficient node memory resources | Check whether the overall memory of the node is sufficient | `problem_gauge{type="MemoryProblem"} >= 1` |
| Node persistent volume storage pool exception | Check whether the persistent volume storage pool is abnormal | `problem_gauge{type="LocalPvVolumeGroupStatusError"} >= 1` |
| The node mount point is abnormal | Check whether the mount point is abnormal | `problem_gauge{type="MountPointProblem"} >= 1` |
| Insufficient number of node file handles | Check whether FD resources are sufficient | `problem_gauge{type="FDProblem"} >= 1` |
| Node disk card IO | Check disk card IO failure | `problem_gauge{type="DiskHung"} >= 1` |
| Node disk read-only | Check whether the disk is read-only | `problem_gauge{type="DiskReadonly"} >= 1` |
| Node disk abnormality | Check system disk/data disk abnormality | `problem_gauge{type="DiskProblem"} >= 1` |
| Node disk slow IO | Check disk slow IO failure | `problem_gauge{type="DiskSlow"} >= 1` |
| Insufficient node process resources | Check whether PID resources are sufficient | `problem_gauge{type="PIDProblem"} >= 1` |
| The node connection tracking table is insufficient | Check whether the conntrack table is sufficient | `problem_gauge{type="ConntrackFullProblem"} >= 1` |

# # 3) Node status rule set (indicator class)| Alarm item | Alarm description | PromQL |
|---|---|---|
| ResolvConf configuration file exception | Check ResolvConf configuration exception | `problem_gauge{type="ResolvConfFileProblem"} >= 1` |
| Node CNI component exception | Check CNI component status | `problem_gauge{type="CNIProblem"} >= 1` |
| Node CRI component exception | Check Docker/Containerd running status | `problem_gauge{type="CRIProblem"} >= 1` |
| Node Kube-proxy failure | Check kube-proxy running status | `problem_gauge{type="KUBEPROXYProblem"} >= 1` |
| Node Kubelet exception | Check kubelet status | `problem_gauge{type="KUBELETProblem"} >= 1` |
| There are scheduled events on the node | Check the host scheduled events | `problem_gauge{type="ScheduledEvent"} >= 1` |
| Node status jitter | Check Ready status for frequent fluctuations | `sum(changes(kube_node_status_condition{status="true",condition="Ready"}[15m])) by (cluster_name,node,cluster) > 2` |
| Node Containerd restarts frequently | Check Containerd restarts frequently | `problem_gauge{type="FrequentContainerdRestart"} >= 1` |
| Node process D exception | Check D process exception | `problem_gauge{type="ProcessD"} >= 1` |
| Node process Z exception | Check Z process exception | `problem_gauge{type="ProcessZ"} >= 1` |
| Node CRI restarts frequently | Check CRI restarts frequently | `problem_gauge{type="FrequentCRIRestart"} >= 1` |
| Node Docker restarts frequently | Check Docker restarts frequently | `problem_gauge{type="FrequentDockerRestart"} >= 1` |
| Node Kubelet restarts frequently | Check Kubelet frequently restarts | `problem_gauge{type="FrequentKubeletRestart"} >= 1` |
| Node NTP service failure | Check ntpd/chronyd service status | `problem_gauge{type="NTPProblem"} >= 1` |

# # Configuration suggestions (for subsequent tool implementation)

- Recommended default threshold periods: `period=60`, `evaluation_periods=3`
- Rule naming suggestions: `{cluster_name}-{rule_short_name}`
-Default enterprise project: `all_granted_eps` (only use the specified enterprise project when passing parameters explicitly)
- If expression uses `problem_gauge`, check NPD plugin status before creating