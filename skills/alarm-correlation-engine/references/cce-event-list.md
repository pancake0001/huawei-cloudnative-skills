# CCE event list

Source: <https://support.huaweicloud.com/usermanual-cce/cce_10_0902.html>

Usage rules:
- When creating an event alarm, give priority to using the `Chinese event description##event name` format as `event_name`.
- If only the event name (such as `NodeHasDiskPressure`) or Chinese event description (such as `Node Disk Space Insufficient`) is passed, the tool will try to automatically map to the full format.

# # Workload related events

| Category | Event description | Event name | Event level |
|---|---|---|---|
| Pod | Pod out of memory OOM | PodOOMKilling | Important |
| Pod | Failed to start | FailedStart | Important |
| Pod | Failed to pull image | FailedPullImage | Important |
| Pod | Startup retry failed | BackOffStart | Important |
| Pod | Scheduling failed | FailedScheduling | Important |
| Pod | Retry to pull image failed | BackOffPullImage | Important |
| Pod | Creation failed | FailedCreate | Important |
| Pod | Abnormal status | Unhealthy | Minor |
| Pod | Delete failed | FailedDelete | Minor |
| Pod | Image not pulled exception | ErrImageNeverPull | Minor |
| Pod | Expansion failed | FailedScaleOut | Minor |
| Pod | Standby Failed | FailedStandBy | Minor |
| Pod | Failed to update configuration | FailedReconfig | Minor |
| Pod | Activation failed | FailedActive | Minor |
| Pod | Rollback failed | FailedRollback | Minor |
| Pod | Update failed | FailedUpdate | Minor |
| Pod | Scaling failed | FailedScaleIn | Minor |
| Pod | Restart failed | FailedRestart | Minor |
| Deployment | Tag Selector Conflict | SelectorOverlap | Minor |
| Deployment | Replica set creation exception | ReplicaSetCreateError | Minor |
| Deployment | Deployment rollback version not found | DeploymentRollbackRevisionNotFound | Minor |
| DaemonSet | Tag selector exception | SelectingAll | Minor |
| Job | Too Many Active Pods | TooManyActivePods | Minor |
| Job | Too Many Successful Pods | TooManySucceededPods | Minor |
| CronJob | Query failed | FailedGet | Minor |
| CronJob | Failed to query Pod list | FailedList | Minor |
| CronJob | UnknownJob | UnexpectedJob | Secondary |

# # Network related events

| Category | Event description | Event name | Event level |
|---|---|---|---|
| Service | Creating Load Balancer Failed | CreatingLoadBalancerFailed | Minor |
| Service | Deleting load balancer failed | DeletingLoadBalancerFailed | Minor |
| Service | Update Load Balancer Failed | UpdateLoadBalancerFailed | Minor |

# # Node related events

| Category | Event description | Event name | Event level |
|---|---|---|---|
| Node | Node restart | Rebooted | Important |
| Node | Node is not schedulable | NodeNotSchedulable | Important |
| Node | Abnormal node status | NodeNotReady | Important |
| Node | Node creation failed | NodeCreateFailed | Important |
| Node | The node failed to mount or unmount the EVS disk | FailedToAttachDetach | Important |
| Node | Node kubelet failure | KUBELETIsDown | Minor |
| Node | Insufficient memory space in node | NodeHasInsufficientMemory | Minor |
| Node | An unregistered network device was found on the node | UnregisterNetDevice | Minor |
| Node | Network card not found | NetworkCardNotFound | Minor |
| Node | Node kube-proxy failure | KUBEPROXYIsDown | Minor |
| Node | Node disk space full | NodeOutOfDisk | Minor |
| Node | Node Task Hung | TaskHung | Secondary |
| Node | CIDR Not Available | CIDRNotAvailable | Minor |
| Node | The node's connection tracking table is full | ConntrackFull | Minor |
| Node | Insufficient disk space on node | NodeHasDiskPressure | Minor |
| Node | Node management failed | NodeInstallFailed | Minor |
| Node | Node operating system kernel failure | KernelOops | Minor |
| Node | Insufficient node memory to kill the process | OOMKilling | Minor |
| Node | Node docker failure | DOCKERIsDown | Minor |
| Node | CIDR allocation failed | CIDRAssignmentFailed | Minor |
| Node | Node docker ramming | DockerHung | Secondary |
| Node | Node Filesystem ReadOnly | FilesystemIsReadOnly | Secondary |
| Node | Node ntp service failure | NTPIsDown | Minor |
| Node | Node uninstall failed | NodeUninstallFailed | Minor |
| Node | Node disk unmount and hold | AUFSUmountHung | Minor |
| Node | Node cni plug-in failure | CNIIsDown | Minor |
| Namespace | Abandoned node cleanup | DeleteNodeWithNoServer | Minor |

# # Store related events

| Category | Event description | Event name | Event level |
|---|---|---|---|
| PV | Host failed to detach block storage | DetachVolumeFailed | Minor |
| PV | Volume Reclaim Policy Unknown | VolumeUnknownReclaimPolicy | Minor |
| PV | Failed to mount data volume | SetUpAtVolumeFailed | Minor |
| PV | Data volume recycling failed | VolumeFailedRecycle | Minor |
| PV | Waiting for host to mount block storage failed | WaitForAttachVolumeFailed | Minor |
| PV | Data volume deletion failed | VolumeFailedDelete | Minor |
| PV | Mount drive letter failed | MountDeviceFailed | Minor |
| PV | Failed to dismount data volume | TearDownAtVolumeFailed | Minor |
| PV | Unmount drive letter failed | UnmountDeviceFailed | Minor |
| PV | Host failed to mount block storage | AttachVolumeFailed | Minor |
| PVC | Data volume expansion failed | VolumeResizeFailed | Minor |
| PVC | Volume PVC Lost | ClaimLost | Secondary |
| PVC | Volume creation failed | ProvisioningFailed | Minor |
| PVC | Creating volume cleanup failed | ProvisioningCleanupFailed | Minor |
| PVC | Volume Misbound | ClaimMisbound | Minor |

# # Auto-scaling related events| Category | Event description | Event name | Event level |
|---|---|---|---|
| Autoscaler | Expansion node timeout | ScaleUpTimedOut | Important |
| Autoscaler | Node pool resources are sufficient | NodePoolAvailable | Important |
| Autoscaler | Scale down node | ScaleDown | Important |
| Autoscaler | Node scaling is not triggered | NotTriggerScaleUp | Important |
| Autoscaler | Unregistered node deleted successfully | DeleteUnregistered | Important |
| Autoscaler | Scale down idle node successfully | ScaleDownEmpty | Important |
| Autoscaler | Scaling node failed | ScaleDownFailed | Important |
| Autoscaler | Node pool expansion node failed | FailedToScaleUpGroup | Important |
| Autoscaler | Node pool expansion node successful | ScaledUpGroup | Important |
| Autoscaler | Failed to expand node capacity | ScaleUpFailed | Important |
| Autoscaler | Fix the number of node pool nodes successfully | FixNodeGroupSizeDone | Important |
| Autoscaler | Node pool backoff retrying | NodeGroupInBackOff | Important |
| Autoscaler | Failed to fix the number of node pool nodes | FixNodeGroupSizeError | Important |
| Autoscaler | Node pool resources sold out | NodePoolSoldOut | Important |
| Autoscaler | Trigger node expansion | TriggeredScaleUp | Important |
| Autoscaler | Node pool expansion node startup | StartScaledUpGroup | Important |
| Autoscaler | Failed to delete unregistered nodes | DeleteUnregisteredFailed | Important |
| HPA | HPA illegal indicator range | InvalidTargetRange | Important |
| HPA | HPA failed to obtain the scaling object | FailedGetScale | Important |
| HPA | HPA compute resource scaling replicas failed | FailedComputeMetricsReplicas | Important |
| HPA | HPA failed to get object metrics | FailedGetObjectMetric | Important |
| HPA | HPA failed to obtain Pod resource metrics | FailedGetPodsMetric | Important |
| HPA | HPA failed to obtain cluster resource metrics | FailedGetResourceMetric | Important |
| HPA | HPA failed to get container resource metrics | FailedGetContainerResourceMetric | Important |
| HPA | HPA failed to get external metrics | FailedGetExternalMetric | Important |
| HPA | HPA scaling Pod failed | FailedRescale | Important |
| HPA | Pod expansion and contraction successful | SuccessfulRescale | Secondary |
| CronHPA | CronHPA scaling failed | ScaleFailed | Important |
| CronHPA | CronHPA query related HPA failed | FailedGetHorizontalPodAutoscaler | Important |
| CronHPA | CronHPA failed to query the scaling object | FailedGetHpaScale | Important |
| CronHPA | CronHPA failed to update associated HPA | UpdateHPAFailed | Important |
| CronHPA | Update HPA policy successful | UpdateHPASuccess | Minor |
| CronHPA | Skip update HPA policy | SkipUpdateHPA | Minor |
| CronHPA | Number of Skip Update Workload Instances | SkipUpdateTarget | Minor |
| CronHPA | Update workload instance count successful | UpdateTargetSuccess | Minor |
| CustomedHPA | CustomedHPA failed to parse the cooling time | FailedSetPolicySettings | Important |
| CustomedHPA | CustomedHPA failed to process timing/metric rules | FailedSubmitRule | Important |
| CustomedHPA | CustomedHPA failed to calculate the number of resource scaling replicas | FailedComputeReplicas | Important |
| CustomedHPA | CustomedHPA scaling Pod failed | FailedScale | Important |
| CustomedHPA | CustomedHPA indicator expansion and contraction success | MetricScaleSuccess | Minor |
| CustomedHPA | CustomedHPA cycle expansion and contraction successful | CronScaleSuccess | Minor |

# # Cluster control plane events| Event description | Event name | Event level |
|---|---|---|
| Internal error | Internal error | Important |
| External dependency error | External dependency error | Important |
| Failed to initialize process thread | Failed to initialize process thread | Important |
| Failed to update database | Failed to update database | Important |
| Failed to create node by nodepool | Failed to create node by nodepool | Important |
| Failed to delete node by nodepool | Failed to delete node by nodepool | Important |
| Failed to create yearly/monthly subscription node | Failed to create yearly/monthly subscription node | Important |
| Failed to cancel the authorization of accessing the image of the master. | Failed to cancel the authorization of accessing the image of the master. | Important |
| Failed to create the virtual IP for the master | Failed to create the virtual IP for the master | Important |
| Failed to delete the node VM | Failed to delete the node VM | Important |
| Failed to delete the security group of node | Failed to delete the security group of node | Important |
| Failed to delete the security group of master | Failed to delete the security group of master | Important |
| Failed to delete the security group of control node network card | Failed to delete the security group of port | Important |
| Failed to delete the security group of eni or subeni | Failed to delete the security group of eni or subeni | Important |
| Failed to detach the port of master | Failed to detach the port of master | Important |
| Failed to delete the port of master | Failed to delete the port of master | Important |
| Failed to delete the master VM | Failed to delete the master VM | Important |
| Failed to delete the key pair of master | Failed to delete the key pair of master | Important |
| Failed to delete the subnet of master | Failed to delete the subnet of master | Important |
| Failed to delete the VPC of master | Failed to delete the VPC of master | Important |
| Failed to delete certificate of cluster | Failed to delete certificate of cluster | Important |
| Failed to delete the server group of master | Failed to delete the server group of master | Important |
| Failed to delete the virtual IP for the master | Failed to delete the virtual IP for the master | Important |
| Failed to get floating IP of the master | Failed to get floating IP of the master | Important |
| Failed to get cluster flavor information | Failed to get cluster flavor | Important |
| Failed to get cluster endpoint | Failed to get cluster endpoint | Important |
| Failed to get kubernetes cluster connection | Failed to get kubernetes connection | Important |
| Failed to update cluster Secret | Failed to update secret | Important |
| Handling user operation timeout | Operation timed out | Important |
| Connecting to Kubernetes cluster timed out | Important |
| Failed to check component status or components are abnormal | Failed to check component status or components are abnormal | Important |
| The node is not found in kubernetes cluster | The node is not found in kubernetes cluster | Important |
| The status of node is not ready in kubernetes cluster | The status of node is not ready in kubernetes cluster | Important |
| Can't find corresponding vm of this node in ECS | Important |
| Failed to upgrade the master node | Failed to upgrade the master | Important |
| Failed to upgrade the node | Failed to upgrade the node | Important |
| Failed to change flavor of the master | Failed to change flavor of the master | Important |
| Change flavor of the master timeout | Change flavor of the master timeout | Important |
| Failed to pass verification while creating yearly/monthly subscription node | Important |
| Failed to install the node | Failed to install the node | Important |
| Failed to clean routes of cluster container network in VPC | Failed to clean routes of cluster container network in VPC | Important |
| Cluster status is Unavailable | Cluster status is Unavailable | Important |
| Cluster status is Error | Cluster status is Error | Important |
| Cluster status is not updated for a long time | Cluster status is not updated for a long time | Important |
| Failed to update master status after upgrading cluster timeout | Failed to update master status after upgrading cluster timeout | Important |
| Failed to update running jobs after upgrading cluster timeout | Failed to update running jobs after upgrading cluster timeout | Important |
| Failed to update cluster status | Failed to update cluster status | Important |
| Failed to update node status | Failed to update node status | Important |
| Failed to remove the static node from database | Failed to remove the static node from database | Important |
| Failed to update node status to abnormal after node processing timeout | Failed to update node status to abnormal after node processing timeout | Important |
| Failed to update the cluster access address | Failed to update the cluster endpoint | Important |
| Failed to delete the unavailable connection of the Kubernetes cluster | Failed to delete the unavailable connection of the Kubernetes cluster | Important |
| Failed to sync the cluster cert | Failed to sync the cluster cert | Important |