# Configure Node Fault Detection Policy / Configure Node Fault Detection Policy
**Update time: 2026-03-30 GMT+08:00**
**Source: Huawei Cloud official document https://support.huaweicloud.com/usermanual-cce/cce_10_0659.html**

The node fault detection function relies on the [CCE Node Fault Detection] (https://support.huaweicloud.com/usermanual-cce/cce_10_0132.html) plug-in. This plug-in instance will run on each node to monitor fault events on the node. This article introduces how to enable the node fault detection capability.

---

# # Enable node failure detection

- Log in to the [CCE console](https://console.huaweicloud.com/cce2.0/?#/cce/cluster/list), click the cluster name to enter the cluster.
- Select "Node Management" on the left and switch to the "Node" tab.
- Click "Fault Detection Strategy" to view the current fault detection items. For the list of NPD check items, please see [NPD Check Items] (#npd Check Items). If there is no "Fault Detection Strategy" button, it means that the CCE node fault detection plug-in is not installed in the cluster or the plug-in is running abnormally. After the plug-in is installed and the plug-in is running normally, the fault detection policy function can be used normally.
- When the current node check result is abnormal, "Indicator Abnormal" will be prompted in the node status.
- You can click "Indicator Abnormality" and follow the repair suggestions to repair it.

---

# # Custom check item configuration

- Log in to the [CCE console](https://console.huaweicloud.com/cce2.0/?#/cce/cluster/list), click the cluster name to enter the cluster.
- Select "Node Management" on the left, switch to the "Node" tab, and click "Fault Detection Strategy".
- View the current inspection item configuration in the jumped page, click "Edit" in the inspection item operation column, and customize the inspection item configuration. Currently, the following configurations are supported:
  - **Enable/Disable**: Customize the opening or closing of a certain check item.- **Target node**: The check item runs on all nodes by default. You can customize the node labels to filter the nodes that meet the conditions according to your own scenario needs. If you set multiple filter conditions, the target node must meet all conditions at the same time. If no filter conditions are set, the default is all nodes. For example, the Spot instance interruption and recycling check only runs on the Spot instance nodes, and you can filter the Spot instance nodes through the specified node label `cce.io/is-spot`.
  - **Check Cycle**: The time interval for check triggering. The CCE node fault detection plug-in provides a default check cycle, which can match common fault scenarios. You can customize the check cycle according to your own scenario needs.
  - **Trigger Threshold**: The CCE node fault detection plug-in provides a default threshold that can match common fault scenarios. You can customize the fault threshold according to your own scenario needs. Different check items have different fault thresholds, such as the number of failures, resource usage percentage, etc., please adjust according to the actual situation. For example, in the "Connection Tracking Table Exhaustion" check item, the trigger threshold of the resource usage percentage can be adjusted from 90% to 80%.
  - **Fault response strategy**: After a fault occurs, you can customize and modify the fault response strategy according to your own scenario needs. The current fault response strategy is as follows:

| Failure response strategy | Effect |
|-------------|------|
| Prompt exception | Report Kubernetes events. |
| Disable scheduling | Report Kubernetes events and add the NoSchedule taint to the node. |
| Evict node load | Report Kubernetes events and add NoExecute taint to the node. This operation will evict the load on the node and may cause business discontinuity, please choose carefully. |

---

# # NPD check items

The current check items are only supported by plug-ins of version 1.16.0 and above.

The inspection items of NPD are mainly divided into **event type inspection items** and **status type inspection items**.

# # #Event type check items
For event check items, when a problem occurs, NPD will report an event to APIServer. The event types are divided into Normal (normal event) and Warning (abnormal event).

| Troubleshooting items | Function description | Monitoring objects/matching rules |
|-----------|----------|------------------|| OOMKilling | Monitor kernel logs, check OOM events and report them<br>Typical scenario: The memory used by the process in the container exceeds the Limit, triggers OOM and terminates the process | Monitoring object: `/dev/kmsg`<br>Matching rules: `"Killed process \\d+ (.+) total-vm:\\d+kB, anon-rss:\\d+kB, file-rss:\\d+kB.*"` |
| TaskHung | Monitor the kernel log, check the taskHung event and report it<br>Typical scenario: disk card IO causes the process to get stuck | Monitoring object: `/dev/kmsg`<br>Matching rule: `"task \\S+:\\w+ blocked for more than \\w+ seconds\\."` |
| ReadonlyFilesystem | Monitor the kernel log and check whether there is a Remount root filesystem read-only error in the system kernel<br>Typical scenario: The user mistakenly unmounts the node data disk from the ECS side, and the application still continues to write operations to the corresponding mount point of the data disk, triggering the kernel to generate an IO error and remount the disk as a read-only disk.<br>⚠️ Description: The node container stores Rootfs as Device When using the Mapper type, data disk uninstallation will cause thinpool exceptions, affecting NPD operation, and NPD will be unable to detect node failures. | Monitoring object: `/dev/kmsg`<br> Matching rule: `"Remounting filesystem read-only"` |

# # # Status class check items
For status check items, when a problem occurs, NPD will report an event to the API Server and modify the node status simultaneously. It can be used in conjunction with [Node-problem-controller fault isolation] (https://support.huaweicloud.com/usermanual-cce/cce_10_0132.html#cce_10_0132__section1471610580474) to isolate the node.

## # # System component check
| Troubleshooting items | Function description | Remarks |
|-----------|----------|------|| CNIProblem | Check the running status of CNI components (container network components) | - |
| CRIProblem | Check the running status of node CRI components (container runtime components) Docker and Containerd | Check object: Docker or Containerd |
| FrequentKubeletRestart | Check whether the key component Kubelet restarts frequently by regularly reviewing system logs<br>Default threshold: 4 restarts within 4 minutes | Monitoring object: logs in the `/run/log/journal` directory<br>⚠️ Ubuntu and Huawei Cloud EulerOS 2.0 operating systems do not support this check item due to incompatible log formats |
| FrequentDockerRestart | Check whether Docker restarts frequently when the container is running by regularly reviewing system logs | Same as above |
| FrequentContainerdRestart | Check whether Containerd restarts frequently when the container is running by regularly tracing back the system log | Same as above |
| KubeletProblem | Check the running status of key component Kubelet | - |
| KubeProxyProblem | Check the running status of the key component KubeProxy | - |
| PodIdentityAgentProblem | Check the running status of the key component PodIdentityAgent (this check item takes effect when the plug-in version is 1.19.50 and above) | ⚠️ If the cluster version does not support Pod Identity function (supported by v1.28.15-r80, v1.29.15-r40, v1.30.14-r40, v1.31.14-r0, v1.32.9-r0, v1.33.7-r0, v1.34.2-r0 and above), PodIdentity in NPD Alarm configurations for Agent exceptions do not take effect.<br>The PodIdentityAgent component on the node is used to exchange temporary credentials for accessing cloud services (such as EVS) based on the delegation configured by the user to the plug-in or load. Abnormalities will cause abnormal access to cloud services, which may affect the business of the entire cluster and require eviction of the workload on the node. |

## # # System indicators| Fault check items | Function description | Threshold/calculation method |
|-----------|----------|---------------|
| ConntrackFullProblem | Check if the connection tracking table is exhausted | Default threshold: 90%<br>Usage: `nf_conntrack_count`<br>Maximum value: `nf_conntrack_max` |
| DiskProblem | Check the disk usage of node system disks and CCE data disks (including CRI logical disks and Kubelet logical disks) | Default threshold: 90%<br>Data source: `df -h`<br>⚠️ Currently, it is not supported to check other data disks except node system disks and CCE data disks |
| FDProblem | Check whether the number of key system resource FD file handles is exhausted | Default threshold: 90%<br>Usage: 1st value in `/proc/sys/fs/file-nr`<br>Maximum value: 3rd value in `/proc/sys/fs/file-nr` |
| MemoryProblem | Check whether the system key resource Memory memory resource is exhausted | Default threshold: 80%<br>Usage: `MemTotal-MemAvailable` in `/proc/meminfo`<br>Maximum value: `MemTotal` in `/proc/meminfo` |
| PIDProblem | Check whether the system key resource PID process resource is exhausted | Default threshold: 90%<br>Usage: the denominator of the fourth value in `/proc/loadavg`, indicating the total number of runnable processes<br>Maximum value: the smaller value of `/proc/sys/kernel/pid_max` and `/proc/sys/kernel/threads-max` |

## # # Storage check
| Fault check items | Function description | Check logic/threshold |
|-----------|----------|---------------|| DiskReadonly | Check the availability of key disks by regularly performing test write operations on node system disks and CCE data disks (including CRI logical disks and Kubelet logical disks) | Detection path:<br>- `/mnt/paas/kubernetes/kubelet/`<br>- `/var/lib/docker/`<br>- `/var/lib/containerd/`<br>- `/var/paas/sys/log/kubernetes`<br>A temporary file `npd-disk-write-ping` will be generated in the detection path |
| EmptyDirVolumeGroupStatusError | Check whether the temporary volume storage pool on the node is normal<br>Fault impact: Pods that rely on the storage pool cannot write the corresponding temporary volume normally. The temporary volume was remounted by the kernel as a read-only file system due to IO errors. <br>Typical scenario: The user configures two data disks as temporary volume storage pools when creating a node. The user mistakenly deletes some data disks, causing the storage pool to become abnormal. | Check period: 30 seconds<br>Data source: `vgs -o vg_name, vg_attr`<br>Detection principle: Check whether the VG (storage pool) has a p state, which indicates that some PVs (data disks) are lost. |
| LocalPvVolumeGroupStatusError | Check whether the persistent volume storage pool on the node is normal<br>Fault impact: Pods that rely on the storage pool cannot write the corresponding persistent volume normally. The persistent volume was remounted by the kernel as a read-only file system due to IO errors. <br>Typical scenario: The user configures two data disks as persistent volume storage pools when creating a node, and the user deletes some data disks by mistake. | - |
| MountPointProblem | Check whether the mount point on the node is abnormal<br>Exception definition: The mount point is inaccessible (cd)<br>Typical scenario: The node mounts nfs (network file system, common obsfs, s3fs, etc.). When the connection is abnormal due to network or peer nfs server exceptions, all processes accessing the mount point are stuck. For example, in the cluster upgrade scenario, kubelet scans all mount points when restarting. When this abnormal mount point is scanned, it will get stuck, causing the upgrade to fail. | Equivalence check command:<br>`for dir in \`df -h | grep -v "Mounted on" | awk "{print \\$NF}"\`;do cd $dir; done && echo "ok"` |
| DiskHung | Check whether all disks on the node have card IO, that is, IO read and write unresponsive<br>Card IO definition: The system does not respond after issuing IO requests to the disk, and some processes are stuck in the D state<br>Typical scenarios: The disk cannot respond due to operating system hard drive abnormalities or serious underlying network failures | Check objects: all data disks<br>Data source: `/proc/diskstat` Equivalent query command: `iostat -xmt 1`<br>Threshold (needs to be met at the same time):<br>-Average utilization (ioutil)>=0.99<br>-Average IO queue length (avgqu-sz)>=1<br>-Average IO transmission volume<br>⚠️ Some operating systems have no data changes during card IO. At this time, the CPU IO time occupancy rate (iowait) is > 0.8. |
| DiskSlow | Check whether slow IO exists on all disks on the node, that is, IO reading and writing are responsive but the response is slow<br>Typical scenario: Cloud disks cause slow IO due to network fluctuations. | Check object: all data disks<br>Data source: `/proc/diskstat` Equivalent query command `iostat -xmt 1`<br>Default threshold: average IO delay, await >=5000ms<br>⚠️ This check item is invalid in the card IO scenario because the IO request does not respond and the await data will not be refreshed. |

## # # Other checks
| Fault check items | Function description | Thresholds/Remarks |
|-----------|----------|----------|
| NTPProblem | Check whether the node clock synchronization service ntpd or chronyd is running normally and whether the system time drifts | Default clock offset threshold: 8000ms |
| ProcessD | Check whether the D process exists on the node | Default threshold: 10 abnormal processes exist three times in a row<br>Data source: `/proc/{PID}/stat`, `ps aux`<br>⚠️ Exception scenario: ProcessD ignores the resident D process heartbeat and update that the SDI card driver under the BMS node depends on |
| ProcessZ | Check whether the Z process exists on the node | - |
| RDMA network card abnormality | Check the RDMA network card status on the node | Default threshold: 1 RDMA network card abnormality exists once in a row<br>Data source: Command: `rdma link show`<br>⚠️ NPD has added an abnormality detection function for RDMA network cards in version 1.19.37 and above, and will mark the RDMAProblem status on the node. Since this status is actively written to the node object by NPD, if you roll back to an old version that does not support this function, NPD no longer has the ability to clean up this status, so the marked status will be retained. |
| ResolvConfFileProblem | Check whether the ResolvConf configuration file is missing/abnormal<br>Exception definition: Does not contain any upstream domain name resolution server (nameserver). | Check object: `/etc/resolv.conf` |
| ScheduledEvent | Check whether there is a live migration planned event on the node. Live migration planning events are usually triggered by hardware failures and are an automatic fault repair method at the IaaS layer. <br>Typical scenario: The underlying host is abnormal, such as fan damage, disk bad sectors, etc., causing the virtual machine on it to trigger live migration. | Data source: `http://169.254.169.254/meta-data/latest/events/scheduled`<br>This check item is an Alpha feature and is not enabled by default. |
| SpotPriceNodeReclaimNotification | Check whether the spot instance node has been preempted and is in an interrupted recycling state | Default check period: 120 seconds<br>Default failure response strategy: evict node load |

---

# # Comparison of Kubelet built-in check items
The kubelet component has the following built-in check items, but there are deficiencies. You can make up for them by upgrading the cluster or installing NPD:

| Troubleshooting items | Function description | Disadvantages |
|-----------|----------|------|
| PIDPressure | Check whether the PID is sufficient<br>Period: 10 seconds<br>Threshold: 90% | For community 1.23.1 and previous versions, this check item becomes invalid when the pid usage is greater than 65535. For details, see [issue 107107](https://github.com/kubernetes/kubernetes/issues/107107). For community version 1.24 and earlier, this check item does not consider thread-max. |
| MemoryPressure | Check whether the container's allocable space (allocable) memory is sufficient<br>Period: 10 seconds<br>Threshold: Maximum value -100MiB<br>Maximum value (Allocable): total node memory - node reserved memory | This detection item does not check memory exhaustion from the overall memory dimension of the node, and only focuses on the container part (Allocable). |
| DiskPressure | Check the disk usage and inodes usage of kubelet disk and docker disk<br>Period: 10 seconds<br>Threshold: 90% | - |