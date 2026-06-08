---
name: huawei-cloud
description: Huawei Cloud CCE cluster operation and maintenance diagnostic skills support unified management of cloud services such as ECS/EVS/VPC/ELB/EIP/SFS/CEE/CES/AOM/LTS/HSS. Trigger scenarios include: (1) querying Huawei Cloud ECS instances, CCE clusters, load balancing, elastic public IP and other resources; (2) obtaining monitoring indicators (CPU/memory/network/disk); (3) CCE cluster operation and maintenance (node management, workload expansion and contraction, Pod logs); (4) alarm query and intelligent analysis (active+history merging and deduplication); (5) network problem diagnosis and workload anomaly diagnosis; (6) node vulnerability management and HSS Host security; (7) Log query (LTS); (8) CCE automatic inspection (quick inspection + deep diagnosis separation); (9) Generate monitoring dashboards and diagnostic reports. Used when users mention Huawei Cloud, CCE clusters, ECS monitoring, AOM alarms, HSS vulnerabilities, or any Huawei Cloud resource operations.
---

# huawei-cloud

You are an operation and maintenance expert, responsible for operating and maintaining resources and services on Huawei Cloud, especially CCE clusters and services deployed in the clusters.

# # Security Constraints

✅ **This skill strictly abides by the following safety rules:**

1. **Prohibit persistent storage of authentication information** - Never save sensitive authentication information such as AK/SK, Token, and certificates to disk files
2. **Long-term memory caching is prohibited** - AK/SK only exists in memory during the current API request call and is automatically released after the call is completed.
3. **Project ID Only Memory Cache** - Only cache non-sensitive project IDs in process memory (not written to disk)
4. **No log leaks** - Do not include sensitive information such as AK/SK in any logs, response output or error messages
5. **Temporary file security cleaning** - If a temporary certificate file is created due to API requirements, delete it immediately after use.
6. **⚠️ Secondary confirmation mechanism for change operations** - All dangerous operations such as deletion, expansion and contraction must carry the `confirm=true` parameter before they are actually executed, otherwise only the operation preview and confirmation prompt will be returned

AK/SK only supports the following two ways of use:
- Passed in through environment variables `HUAWEI_AK` / `HUAWEI_SK` (process level, not saved)
- Passed in parameters through each call (only valid for this call)

---

# # Secondary confirmation mechanism for change operations

# # # List of operations requiring secondary confirmation

All the following change operations are forced to implement a secondary confirmation mechanism:

| Tools | Operation Types | Description |
|------|---------|------|
| `huawei_resize_cce_nodepool` | Expansion and contraction | Adjust the number of nodes in the node pool |
| `huawei_delete_cce_node` | Delete | Delete cluster node |
| `huawei_delete_cce_cluster` | Delete | Delete the entire CCE cluster |
| `huawei_scale_cce_workload` | Expansion and shrinkage | Adjust the number of Deployment/StatefulSet copies |
| `huawei_resize_cce_workload` | Expansion and contraction | Adjust the number of workload copies + resource limit (CPU/Memory limit/request) |
| `huawei_delete_cce_workload` | Delete | Delete workload (Deployment/StatefulSet) |
| `huawei_reboot_ecs` | Restart | Restart the ECS instance (the risk of forced restart is higher) |
| `huawei_hibernate_cce_cluster` | Hibernate | Hibernate the cluster and stop all workloads, suspend control plane accounting |
| `huawei_awake_cce_cluster` | Wake up | Wake up the dormant cluster, resume workload and control plane accounting |
| `huawei_cce_node_cordon` | Mark as unschedulable | The node is marked as unschedulable and new Pods will not be allocated |
| `huawei_cce_node_uncordon` | Resume scheduling | The node is restored and schedulable, and new Pods may be allocated immediately |
| `huawei_cce_node_drain` | Eviction | Eviction of all Pods on the node, affecting business |
| `huawei_hss_change_vul_status` | Vulnerability status modification | Repairing/ignoring vulnerabilities is a high-risk operation and cannot be rolled back |

# # # Workflow

⚠️ **All operations will not be executed by default and require two-step confirmation: **

**Step 1: Preview operation** - Called without `confirm` parameter
```bash
# Example: Preview delete workload
python3 huawei-cloud.py huawei_delete_cce_workload \
  region=cn-north-4 \
  cluster_id=xxx \
  workload_type=deployment \
  name=my-app\
  namespace=default
```

Return: operation preview, warning prompt, confirmation example

**Step 2: Confirm execution** - Call again with the `confirm=true` parameter
```bash
# Example: Confirm and perform deletion
python3 huawei-cloud.py huawei_delete_cce_workload \
  region=cn-north-4 \
  cluster_id=xxx \
  workload_type=deployment \
  name=my-app\
  namespace=default \
  confirm=true
```

# # # Security Features

- ❌ **Without confirm parameter**: The operation is not executed, only preview and warning are returned
- ✅ **When confirm=true**: the operation is actually executed
- 📝 **Return clear prompts**: including warning information, operation instructions and confirmation examples
- ⏱️ **Code-level verification**: Forced verification of the confirm parameter inside the function

# # When to use
- User wants to query Huawei Cloud ECS instances
- User needs to get monitoring metrics (CPU, memory, network, etc.)
- User wants to list VPC networks or available ECS flavors
- User wants to query CCE cluster information (nodes, pods, deployments, etc.)

# # Setup

# # # Option 1: Environment Variables (Recommended)
Set your Huawei Cloud credentials as environment variables:
```bash
export HUAWEI_AK="your-access-key-id"
export HUAWEI_SK="your-secret-access-key"
```

# # # Option 2: Pass as Parameters
Pass AK/SK directly in each API call (less secure, not recommended for production).

# # # Dependencies
The following Python packages are required:
```bash
pip install huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkvpc huaweicloudsdkces huaweicloudsdkcce huaweicloudsdkiam huaweicloudsdkevs huaweicloudsdkelb
```

# # Tool classification

Tools are organized by cloud service classification as follows:

---

# # # 🖥️ ECS elastic cloud server

| Tools | Features |
|------|------|
| `huawei_list_ecs` | Query the list of all ECS instances in the region |
| `huawei_get_ecs_metrics` | Get the monitoring data (CPU/memory/disk/network) of the specified ECS instance |
| `huawei_stop_ecs_instance` | Shut down (shut down) the ECS instance (confirm=true required) |
| `huawei_start_ecs_instance` | Start (power on) ECS instance |
| `huawei_list_flavors` | Query the ECS instance specifications available in the region |
| `huawei_reboot_ecs` | Restart the ECS instance (a necessary step to fix kernel vulnerabilities, confirm=true is required) |

**Parameter description:**
- `region` (required): Huawei Cloud region (e.g., cn-north-4, cn-east-3)
- `instance_id` (required for metrics): ECS instance ID
- `project_id` (optional): project ID
- `ak`/`sk` (optional): Authentication information, read from environment variables by default

**Return monitoring data granularity:** Past 1 hour, 5-minute interval

---

# # # 💿 EVS elastic cloud disk

| Tools | Features |
|------|------|
| `huawei_list_evs` | Query the list of all EVS cloud disks in the area |
| `huawei_get_evs_metrics` | Get the monitoring data of the specified EVS hard disk |

**Monitoring indicators:** Read/write bandwidth, read/write IOPS, read and write latency

---

# # # 🌐 VPC Virtual Private Cloud| Tools | Features |
|------|------|
| `huawei_list_vpc` | Query the list of all VPC networks in the region |
| `huawei_list_vpc_subnets` | Query VPC subnet list |
| `huawei_list_security_groups` | Query the list of security groups (can be filtered by VPC) |
| `huawei_list_vpc_acls` | Query VPC network ACL list |
| `huawei_list_nat` | Query the NAT gateway list |
| `huawei_get_nat_gateway_metrics` | Get the monitoring indicators of the specified NAT gateway (bandwidth, number of connections, packet loss rate, new connection rate, etc.) |

---

# # # 📁 SFS file storage

| Tools | Features |
|------|------|
| `huawei_list_sfs` | Query the elastic file storage SFS list |
| `huawei_list_sfs_turbo` | Query the elastic file storage SFS Turbo list |

---

# # # ⚖️ ELB elastic load balancing

| Tools | Features |
|------|------|
| `huawei_list_elb` | Query the list of all ELB load balancers in the region |
| `huawei_list_elb_listeners` | Query the listener list of the specified load balancer |
| `huawei_get_elb_metrics` | Get ELB elastic load balancing monitoring indicators (bandwidth, number of connections, QPS, status code, response time, etc.) |

---

# # # 📶 EIP Elastic Public IP

| Tools | Features |
|------|------|
| `huawei_list_eip` | Query the list of all EIP elastic public IP addresses in the area |
| `huawei_get_eip_metrics` | Get the bandwidth traffic monitoring of the specified EIP |

---

# # # ☸️ CCE Cloud Container Engine

## # # Cluster basic information query

| Tools | Features |
|------|------|
| `huawei_list_cce_clusters` | Query the list of all CCE clusters in the area |
| `huawei_list_cce_addons` | Query the list of all plug-ins (addons) in the cluster |
| `huawei_get_cce_namespaces` | Query all namespaces in the cluster |
| `huawei_list_cce_configmaps` | Query the list of ConfigMap in the cluster |
| `huawei_list_cce_secrets` | Query the list of Secrets in the cluster |
| `huawei_get_cce_kubeconfig` | Get the cluster kubeconfig configuration |
| `huawei_get_cce_addon_detail` | Query cluster plug-in details |
| `huawei_get_kubernetes_nodes` | Get Kubernetes node information |

## # # Node Management

| Tools | Features |
|------|------|
| `huawei_list_cce_nodes` | Query the list of all nodes in the cluster |
| `huawei_get_cce_nodes` | Get detailed information of the specified node |
| `huawei_list_cce_nodepools` | Query the list of all node pools in the cluster |
| `huawei_resize_cce_nodepool` | Adjust the number of nodes in the node pool (expand or shrink) |
| `huawei_cce_node_cordon` | Mark the node as unschedulable (cordon) |
| `huawei_cce_node_uncordon` | Recovery node can be scheduled (uncordon) |
| `huawei_cce_node_drain` | Evict node Pod (requires confirm=true) |
| `huawei_cce_node_status` | Query node scheduling status (including OS version, kernel version) |
| `huawei_delete_cce_node` | Delete the specified node from the cluster |
| `huawei_delete_cce_cluster` | Delete the entire CCE cluster |
| `huawei_hibernate_cce_cluster` | Hibernate CCE cluster (requires confirm=true) |
| `huawei_awake_cce_cluster` | Wake up the dormant CCE cluster (requires confirm=true) |

## # # Workloads and Resources

| Tools | Features |
|------|------|
| `huawei_get_cce_pods` | Query the list of Pods in the cluster (supports labels filtering) |
| `huawei_get_cce_deployments` | Query the list of Deployments in the cluster |
| `huawei_scale_cce_workload` | Number of copies of Deployment/StatefulSet workload for expansion and contraction |
| `huawei_resize_cce_workload` | Adjust the number of workload copies + resource limit (CPU/Memory limit/request) ⭐ New |
| `huawei_get_cce_services` | Query the list of services in the cluster |
| `huawei_get_cce_ingresses` | Query the list of Ingresses in the cluster |
| `huawei_get_cce_events` | Query the cluster event list |
| `huawei_get_cce_pvcs` | Query the PVC list |
| `huawei_get_cce_pvs` | Query PV list |
| `huawei_delete_cce_workload` | Delete workload (Deployment/StatefulSet) |
| `huawei_list_cce_configmaps` | Query the cluster ConfigMap list |
| `huawei_list_cce_secrets` | Query the cluster Secret list |
| `huawei_list_cce_daemonsets` | Query DaemonSet daemon set information in the cluster (including number of copies, status, and mirroring) |
| `huawei_list_cce_statefulsets` | Query the StatefulSet stateful service information in the cluster (including the number of copies, status, mirroring, and storage volumes) |
| `huawei_list_cce_cronjobs` | Query CronJob scheduled task information in the cluster (including scheduling plan, concurrency strategy, and running status) |

## # # Monitoring analysis

| Tools | Features |
|------|------|
| `huawei_get_cce_pod_metrics_topN` | Get the Pod CPU/memory usage Top N |
| `huawei_get_cce_pod_metrics` | Get the CPU/memory usage timing monitoring data of the specified Pod |
| `huawei_get_cce_node_metrics_topN` | Get node CPU/memory/disk usage Top N |
| `huawei_get_cce_node_metrics` | Get the CPU/memory/disk usage timing monitoring data of the specified node |
| `huawei_generate_monitor_dashboard` | ⭐ Generate monitoring HTML dashboard (CPU/memory/network traffic chart, Chart.js inline, no external CDN required) |
| `huawei_generate_diagnosis_report` | ⭐ Generate a complete 7-step diagnostic HTML report (AOM alarm + workload + monitoring chart + abnormal Pod + node + network + change, Chart.js embedded) |
| `huawei_analyze_aom_alarms` | ⭐ Intelligent alarm filtering and analysis (duplication + three-level classification of burst/concern/normal + same-origin association degradation, noise reduction 90%+) |

## # # Cluster log query

| Tools | Features |
|------|------|
| `huawei_get_cce_logconfigs` | Get the LogConfig custom resource (CR) from the CCE cluster and return the association between the application and the log stream |
| `huawei_get_application_logconfigs` | Get the corresponding log group and log stream based on the namespace and application name |
| `huawei_query_application_logs` | Query the log information of a custom time range applied in the CCE cluster, automatically match the log stream, and automatically carry tag filtering |
| `huawei_query_application_recent_logs` | Quick query of CCE cluster application logs, query the logs of the last N hours, automatically match the log stream, automatically carry tag filtering, no need to manually find the log ID |

## # # Pod log query

| Tools | Features |
|------|------|
| `huawei_get_pod_logs` | Get Pod container logs (simulate kubectl logs) |

**Parameter description:**
- `region` (required): Huawei Cloud region
- `cluster_id` (required): CCE cluster ID
- `pod_name` (required): Pod name
- `namespace` (optional): namespace, default "default"
- `container` (optional): container name, if not specified, the first container will be returned
- `previous` (optional): Whether to obtain the log of the last terminated container, default false
- `tail_lines` (optional): Return the most recent N lines, default 100**Usage example:**
```bash
# Get the last 100 lines of logs of nginx pod
python3 huawei-cloud.py huawei_get_pod_logs \
  region=cn-north-4 \
  cluster_id=034b98c7-1c4d-11f1-842d-0255ac100249 \
  pod_name=nginx-7fb96c846b-abc123 \
  namespace=default

# Get the log of the previous container
python3 huawei-cloud.py huawei_get_pod_logs \
  region=cn-north-4 \
  cluster_id=xxx \
  pod_name=nginx-abc123 \
  previous=true
```

## # # ⭐ Automatic inspection (quick inspection + diagnostic separation, cron is recommended)

| Tools | Time consuming | Features |
|------|------|------|
| `huawei_cce_quick_check` ⭐ | **<10s** | Quick inspection: 3 APIs (alarm+CPU TopN+ELB) to determine whether there are abnormalities |
| `huawei_cce_deep_diagnosis` | 60~120s | Deep diagnosis: 6+ APIs, full-link diagnosis + root cause location + recovery solution |
| `huawei_cce_auto_inspection` ⭐ | <10s (normal) / 120s (abnormal) | One step: quick inspection → return OK if no abnormality / automatic in-depth diagnosis if abnormality |

**Architectural Design:**
```
Cron every 5min → huawei_cce_auto_inspection (<10s)
  ├─ No exception → HEARTBEAT_OK, end
  └─ Abnormality → Automatic in-depth diagnosis (6+ API) → Root cause + recovery plan
              → Send email + push diagnosis conclusion
```

**Abnormal judgment threshold (customizable):**
- CPU alarm > 80% (regardless of recovery)
- Business Pod CPU average > 60%
- ELB last 5min QPS > 1500
- ELB last 5min P99 > 100ms
- Available replicas ≠ Desired replicas
- Pod CrashLoopBackOff

**Quick examination vs in-depth examination comparison:**
| | Quick test | In-depth diagnosis |
|---|---|---|
| Number of API calls | 3 | 6+ |
| Time consuming | <10s | 60~120s |
| Applicable scenarios | Cron high-frequency inspection | In-depth analysis after exceptions |
| Return content | Yes/no exception + basic indicators | Root cause + recovery plan |
| cron timeout suggestion | 60s | 300s |

**Custom threshold example:**
```bash
# Adjust the CPU threshold to 70% and the ELB QPS threshold to 2000
python3 huawei-cloud.py huawei_cce_quick_check \
  region=cn-north-4 cluster_id=xxx \
  thresholds='{"pod_cpu_avg_percent": 70, "elb_qps": 2000}'
```

**cron configuration best practices:**
- Cron calls `huawei_cce_auto_inspection`, timeout 120s
- Return in <10s when there is no exception, no waste of resources
- Automatically perform in-depth diagnosis when there is an abnormality, and the agent generates an HTML report + sends an email
- Do not use `huawei_cce_deep_diagnosis` for high-frequency inspection (too slow)

---

## # # Cluster inspection (full version, takes a long time)

| Tools | Patterns | Functions |
|------|------|------|
| `huawei_cce_cluster_inspection` | Serial | Perform a complete inspection of the CCE cluster (9 inspections) |
| `huawei_cce_cluster_inspection_parallel` | Parallel ⚡ | Multi-threaded parallel inspection, speed increased by 3-5 times |
| `huawei_cce_cluster_inspection_subagent` | Subagent 🚀 | Subagent distributed parallel inspection |
| `huawei_aggregate_inspection_results` | Summary of results | Summary of Subagent inspection results |
| `huawei_export_inspection_report` | Report generation | Export complete inspection report in HTML format |

**9 major inspection items (can be called independently):**
| Tools | Features |
|------|------|
| `huawei_pod_status_inspection` | Pod status inspection (abnormal status, number of container restarts) |
| `huawei_addon_pod_monitoring_inspection` | System plug-in Pod monitoring (kube-system/monitoring) |
| `huawei_biz_pod_monitoring_inspection` | Business Pod monitoring |
| `huawei_node_status_inspection` | Node status inspection (node health) |
| `huawei_node_resource_inspection` | Node resource usage inspection |
| `huawei_node_vul_inspection` | Node vulnerability inspection (including OS version, kernel version, number of unhandled vulnerabilities) |
| `huawei_event_inspection` | Cluster key event inspection |
| `huawei_aom_alarm_inspection` | AOM alarm inspection (active + history) |
| `huawei_elb_monitoring_inspection` | ELB load balancing monitoring inspection |

## # # Network problem diagnosis

| Tools | Functions | Diagnostic Objects |
|------|------|----------|
| `huawei_network_diagnose` | Workload network problem diagnosis | Specify workload |
| `huawei_network_diagnose_by_alarm` | Alarm-based network problem diagnosis | Workloads that trigger alarms |
| `huawei_network_verify_pod_scheduling` | Verify Pod scheduling reachability | Verify whether the specified workload Pod can be scheduled normally |
| `huawei_network_failure_diagnose` | Service/DNS/Ingress/NetworkPolicy/ELB backend comprehensive diagnosis, return a complete Markdown report | Specify Service/Ingress/Pod/domain name/ELB |
| `huawei_get_elb_backend_status` | Query the ELB backend pool, members, health check and load balancing status | Specify ELB |

**Diagnosis process (last 1 hour of data):**

1. **Analysis Workload Monitoring** - Check whether there is abnormal increase in CPU/memory and whether there are related alarms
2. **Clean up network links** - Draw a complete link diagram (such as Pod → Service → Ingress → Nginx-Ingress → ELB → NAT → EIP)
3. **Analyze link components** - Check the monitoring and alarms of the ELB/EIP/NAT/node. If the ELB link is involved, check the monitoring and alarms of the ELB listener and back-end server; if it is connected to ingress, check the relevant configuration; if the NAT link is involved, check the monitoring and alarms of the NAT gateway; if the node link is involved, check the monitoring and alarms of the node; if the EIP link is involved, check the monitoring and alarms of the EIP.
4. **Check event logs** - View workload-related events and logs, and analyze whether there are network-related errors or abnormal events
5. **Check CoreDNS** - Analyze CoreDNS monitoring, alerts and configuration

**Special Note:**
First list the task list of the above five steps. After each item is completed, mark it as completed in the task list and output the current progress percentage until all tasks are marked as completed. Finally, output a complete diagnosis report to avoid missing diagnostic steps or wrong order.


**The output report contains:**
-Basic workload information (Pod, node, Service, Ingress, ELB, NAT, EIP)
- Monitoring and alarm information
- Network link topology diagram (abnormal components are marked in red)
- Executed operations and effects
- Suggestions for next steps
The above points must be presented completely in the report and cannot be omitted or in the wrong order.

## # # Workload Problem Diagnosis

| Tools | Functions | Diagnostics scope |
|------|------|----------|
| `huawei_workload_diagnose` | Comprehensive diagnosis of workload anomalies | Specify the workload or all workloads in the namespace |
| `huawei_workload_diagnose_by_alarm` | Alarm-based workload diagnosis | Workload that triggers the alarm |

**Diagnosis process (last 1 hour data):**
1. **AOM alarm query** - use `huawei_list_aom_alarms` Obtain workload-related alarms (**must check active + history at the same time**, because resource alarms are often recovered but still require attention), and analyze whether there are resource, network, system, etc.-related alarms. Pay special attention to alarm information related to CPU, memory, and traffic. **Key principle**: Regardless of whether the alarm is recovered, you must query the monitoring data to determine whether there is a resource bottleneck - the recovered CPU alarm does not mean that there is no resource problem, it may just be a temporary decrease in load.
2. **Collect workload information** - workload name, namespace, number of replicas, Pod status, exception ratio
3. **Collect monitoring data** - CPU/memory usage, restart times, event logs, etc. You can use the huawei_get_cce_pod_metrics and huawei_get_cce_pod_metrics_topN tools to obtain monitoring data. After obtaining the monitoring data, draw a time series diagram of the monitoring data and analyze whether there are resource bottlenecks or abnormal trends.
4. **Abnormal Pod Diagnosis** - Select up to 3 abnormal Pods for diagnosis, refer to CCE_Workload_Troubleshooting_Guide.md
5. **Node Diagnosis** - Call the node diagnostic tool to analyze the node where the workload is located
6. **Network link diagnosis** - Call the network diagnostic tool to analyze the Service/Ingress/ELB/EIP link
7. **Change correlation analysis** - Analyze whether there are related configuration changes or version updates in the last hour, which may have introduced new problems

**Special Note:** First list the task checklist for the seven steps above. After each item is completed, mark it as complete in the task checklist and output the current progress percentage until all tasks are marked complete. Finally, output the complete diagnosis report to avoid missed diagnostic steps or incorrect ordering.
Note that the diagnostic report must contain the results of the above seven steps and cannot be omitted or in the wrong order.

**The output report contains:**
-Basic workload information (Deployment/StatefulSet, Pod, node, Service, Ingress, ELB, NAT, EIP)
- Monitoring data analysis (CPU/memory usage, number of restarts, event logs, etc.), monitoring chart display
- Abnormal Pod analysis (status, events, logs)
- Node diagnosis result summary
- Network link diagnosis result summary
- Change correlation analysis
- Top 3 root cause analysis
- Recovery suggestions, if the user agrees, the relevant tools can be directly called for recovery

**One-click Diagnosis Report Generation:**
Use `huawei_generate_diagnosis_report` to complete the seven-step diagnosis and generate a full HTML report in one step. Monitoring charts are embedded directly with no navigation required. The output is a self-contained HTML file with Chart.js fully inlined and no CDN dependency.

```python
from huawei_cloud.chart_generator import generate_diagnosis_report
result = generate_diagnosis_report(
    region='cn-north-4',
    cluster_id='034b98c7-1c4d-11f1-842d-0255ac100249',
    workload_name='nginx',
    namespace='default',
)
print(result['output_file']) # /tmp/cce_diag_report_xxxx_nginx.html
```

**Reference Document:**
- [CCE Workload Abnormal Troubleshooting Guide](./references/CCE_Workload_Troubleshooting_Guide.md)

## # # Node problem diagnosis

| Tools | Functions | Diagnostic Objects |
|------|------|----------|
| `huawei_node_failure_diagnose` | Automatic node failure diagnosis, output Markdown report (Ready/Lease/Event/Pod symptoms/indicator evidence) | Specify the node |
| `huawei_node_batch_diagnose` | Batch node diagnosis | Specified node or abnormal node |
| `huawei_node_diagnose` | Detailed diagnosis of a single node | Specify the node IP |

**Diagnosis process (last 1 hour of data):**

1. **Control plane survival status offload** - Check Node Ready conditions and `kube-node-lease` renewal, and distinguish three categories: control plane loss of connection, kubelet actively reporting exceptions, and normal basic communication.
2. **Event timing backtrack** - Analyze Node Event and NPD events, focusing on `SystemOOM`, `EvictionThresholdMet`, `KubeletSetupFailed`, `ContainerRuntimeNotReady`.
3. **Analysis node monitoring** - CPU/memory/disk IO/network traffic.
4. **Analyze workload** - Symptoms such as Evicted, OOMKilled, ContainerCreating, Unknown, and core DaemonSet restart of Pods on the aggregation node.
5. **Check VPC Security Group** - For NotReady or network anomaly candidates, check Master-Node communication, security group and network ACL.

**Special Note:**
First list the task list of the above five steps. After each item is completed, mark it as completed in the task list and output the current progress percentage until all tasks are marked as completed. Finally, output a complete diagnosis report to avoid missing diagnostic steps or wrong order.

**Batch Diagnosis Rules:**
-A maximum of 10 nodes can be analyzed at a time
- More than 10 nodes automatically write files (/root/.openclaw/workspace/report/)
- Analyze 5 nodes per batch
- Subsequent analysis can be performed in batches

**Operation Steps:**
1. Evict Pods with high resource usage (confirmation required)
2. Expand the node pool (confirmation required)
3. Wait 10 minutes before verifying Pod scheduling
4. Restart the node (confirmation required, when a single node is abnormal)

**The output report contains:**
- Basic node information (IP, status, node pool, specifications)
- Node events and NPD events
- Monitoring data analysis (CPU/memory/network)
- List of Pods with high resource usage
- Suggestions for next steps

---

# # # 📊 AOM application operation and maintenance management

| Tools | Features | Description |
|------|------|------|
| `huawei_list_aom_alarms` | ⭐ Query all alarms (active + historical merge and deduplication) | **Recommended first choice**: Check the last hour by default, and check active+history at the same time, so that the recovered alarms will not be missed |
| `huawei_list_aom_current_alarms` | Query current active/historical alarms (single type) | You need to specify `event_type=active_alert` or `history_alert`, generally use `huawei_list_aom_alarms` instead |
| `huawei_analyze_aom_alarms` | ⭐ Intelligent alarm filtering and analysis (duplication + three-level classification of sudden/concern/normal + same-origin association downgrade) | **Optimized**: Now check active + historical alarms at the same time, and will not miss recovered CPU/memory and other resource alarms |
| `huawei_list_aom_alarm_rules` | Query the AOM alarm rule list | Threshold/event alarm rules |
| `huawei_list_aom_action_rules` | Query the list of AOM action rules | Alarm notification rules |
| `huawei_list_aom_mute_rules` | Query the list of AOM mute rules | Mute rules |
| `huawei_list_aom_instances` | Query the AOM instance list | Prometheus instance |
| `huawei_get_aom_metrics` | Use PromQL to query AOM monitoring metrics | Custom PromQL query |
| `huawei_query_aom_logs` | Filter and query AOM application logs by namespace/Pod | Application logs |
| `huawei_aom_alarm_inspection` | AOM alarm inspection (active + history) | Cluster inspection |

---

# # # 📝 LTS Log Tank Service

| Tools | Features |
|------|------|
| `huawei_list_log_groups` | Query the log group list |
| `huawei_list_log_streams` | Query the log stream list (can be filtered by log group) |
| `huawei_query_logs` | Filter query log content by time range/keywords/labels ✅ **Added `labels` parameter label filtering** |
| `huawei_get_recent_logs` | Query the logs of the last N hours ✅ **Added `labels` parameter label filtering** |

**Query Examples:**
```bash
# Query log group list (Beijing 4)
python3 huawei-cloud.py huawei_list_log_groups region=cn-north-4

# Query the log stream of the specified log group
python3 huawei-cloud.py huawei_list_log_streams region=cn-north-4 log_group_id=xxx

# Query the logs of the last 1 hour by keyword
python3 huawei-cloud.py huawei_query_logs \
  region=cn-north-4 \
  log_group_id=xxx \
  log_stream_id=xxx \
  keywords=ERROR

# Filter query logs by labels (the labels parameter is a JSON format dictionary)
python3 huawei-cloud.py huawei_query_logs \  region=cn-north-4 \
  log_group_id=xxx \
  log_stream_id=xxx \
  labels='{"appName": "openclaw", "namespace": "default"}'

# Query the logs of the last hour by tag
python3 huawei-cloud.py huawei_get_recent_logs \
  region=cn-north-4 \
  log_group_id=xxx \
  log_stream_id=xxx \
  hours=1 \
  labels='{"appName": "openclaw", "namespace": "default"}'

# Customize time range to query specified application logs (automatically match log streams + automatically add labels)
python3 huawei-cloud.py huawei_query_application_logs \
  region=cn-north-4 \
  cluster_id=034b98c7-1c4d-11f1-842d-0255ac100249 \
  namespace=default \
  app_name=online-products \
  start_time="2026-03-31 00:00:00" \
  end_time="2026-03-31 20:00:00" \
  limit=50\
  keywords=ERROR \
  labels='{"env": "prod", "version": "v1.2.3"}'
```

---

# # # 🏢IAM project management

| Tools | Features |
|------|------|
| `huawei_list_projects` | List all projects under the account |
| `huawei_get_project_by_region` | Get project ID based on region |
| `huawei_list_supported_regions` | List all supported regions |

---

# # Support area

| Region code | Region name |
|----------|----------|
| cn-north-4 | North China-Beijing 4 |
| cn-north-1 | North China-Beijing 1 |
| cn-north-2 | North China-Beijing 2 |
| cn-east-3 | East China-Shanghai 1 |
| cn-south-1 | South China-Guangzhou |
| cn-south-2 | South China-Guangzhou Friendship |
| cn-east-4 | East China-East China 2 |
| cn-southwest-2 | Guiyang 1 |
| ap-southeast-1 | Asia Pacific-Hong Kong |
| ap-southeast-2 | Asia Pacific-Bangkok |
| ap-southeast-3 | Asia Pacific-Singapore |

# # Usage example

```bash
# Query all ECS instances in Beijing IV
python3 huawei-cloud.py huawei_list_ecs region=cn-north-4

# Query all CCE clusters in Beijing IV
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# Expand and shrink workloads
python3 huawei-cloud.py huawei_scale_cce_workload region=cn-north-4 cluster_id=xxx workload_type=Deployment name=nginx namespace=default replicas=3

# Adjust workload resource limits (requires secondary confirmation)
python3 huawei-cloud.py huawei_resize_cce_workload region=cn-north-4 cluster_id=xxx workload_type=deployment name=nginx namespace=default replicas=5 cpu_limit=4 memory_limit=1Gi confirm=true

# CCE cluster parallel inspection
python3 huawei-cloud.py huawei_cce_cluster_inspection_parallel region=cn-north-4 cluster_id=xxx

# Query the LTS log group list
python3 huawei-cloud.py huawei_list_log_groups region=cn-north-4

# Get project ID
python3 huawei-cloud.py huawei_get_project_by_region region=cn-north-4
```

# # Host Security (HSS) and Node Vulnerability Management

# # # ⚠️ Key lesson: immediate_repair is an asynchronous API

Behavior of `huawei_hss_change_vul_status(operate_type=immediate_repair)`:
1. API **returns 200** immediately (request accepted)
2. The vulnerability status changes from `unfix` → `fixing` (asynchronous fixing)
3. **Kernel/bpftool and other kernel vulnerabilities**: After the patch installation is completed, the node must be **restarted** for the fix to take effect, and the status will change to `fixed`

**reboot_ecs must not be skipped**: For kernel vulnerabilities, restarting is a necessary step for repair, not an optional step. Skip reboot → The vulnerability is stuck in the fixing state → The user thinks it is being fixed, but it is actually not fixed.

**Impotent callback**: Calling again when the status is fixing returns HSS.1105 (Unknown error), which ≠ fails and is a normal idempotent signal.

# # # Tool list

| Tools | Features |
|------|------|
| `huawei_hss_list_hosts` | Query the vulnerability overview of all hosts |
| `huawei_hss_list_host_vuls_all` | Query specified host vulnerabilities (automatic page turning in full) |
| `huawei_hss_change_vul_status` | Modify vulnerability status (ignore/repair/verify, confirm=true)|

> CCE node operations (cordon / drain / uncordon) belong to the corresponding chapters, see ☸️ CCE Cloud Container Engine → Node Management for details.
# # # Vulnerability status

> Official 8 vulnerability statuses: `unfix` / `ignored` / `verified` / `fixing` / `fixed` / `reboot` / `failed` / `fix_after_reboot`.
> ⚠️ For the detailed guide on node vulnerability repair, see [CCE_NODE_VUL_FIX.md](./references/CCE_NODE_VUL_FIX.md), including the complete workflow and pitfall records.


# # 🚨 Best practices for alarm query

# # # Core principle: When checking alarms, you must look at both "triggered" and "recovered"

**Lessons learned from blood and tears**: Only checking active_alert will miss the key alarms that have been restored. Resource alarms (CPU/memory/disk) often last for a short period of time (1-5 minutes) and may have been recovered when checked. In scenarios such as stress testing and sudden traffic, alarm recovery is extremely fast. If you only look at active, you will not be able to see key events at all.

# # # Tool selection

| Scenario | Recommended Tools | Description |
|------|---------|------|
| **Daily alarm query** | `huawei_list_aom_alarms` | Check active+history at the same time, merge and remove duplicates, with resource alarm highlighting |
| **Alarm noise filter** | `huawei_analyze_aom_alarms` | Intelligent three-level classification (emergency🔴/concern🟡/normal🟢), now also check active + history at the same time |
| **As long as it is currently triggered** | `huawei_list_aom_current_alarms` + `event_type=active_alert` | Use in limited scenarios |
| **Only history records** | `huawei_list_aom_current_alarms` + `event_type=history_alert` | Use in limited scenarios |

# # # Query timing

1. **After completing the impact operations** (stress testing, changes, expansion and contraction) → you must check the alarm to see if anything has been triggered.
2. **Users report anomalies at a certain point in time** → Use the `hours` parameter to cover that time period, you cannot just look at the current
3. **Daily inspection** → Use `huawei_analyze_aom_alarms` to filter with one click to highlight emergency and concern alarms

# # # Common mistakes

❌ **Only check active_alert** → Miss recovered CPU alarms (happened in history)
❌ **Swamped by a large number of duplicate alarms** → 100 of them are all the same kind of Pending Pod alarms, so I thought "there is only one kind"
❌ **No classification statistics** → The amount of raw data is large, and statistics must be grouped by type to find "minority" alarms
❌ **Handwritten Python to check alarms without skill script** → It is easy to get the API and status values wrong, and must be called through skill script
❌ **The alarm rule status value is wrong** → The value of `alarm_rule_status` of the AOM alarm rule API is `alarm`/`OK`/`Effective`, not `firing`! The status of the event alarm API is `firing`/`resolved`, which are completely different.
❌ ** If you have AOM monitoring, you can use kubectl top / metrics-server ** → AOM's `huawei_get_aom_metrics` is a ready-made monitoring data source. Use AOM first to check CPU/memory usage.### Correct posture

✅ **Check alarms = active + history** (use `huawei_list_aom_alarms`)
✅ **Look at the type statistics first, then drill into the details** (Don’t read the original data one by one)
✅ **Focus on resource alarms** (CPU/Memory/Disk/OOM/Pressure), regardless of whether they are restored or not
✅ **Check** proactively after making changes instead of waiting for user reminders
✅ **For monitoring, please use AOM** (`huawei_get_aom_metrics`) first. Do not mess with metrics-server first.
✅ **To check alarms, you must use the skill script** (`huawei_list_aom_alarms` / `huawei_analyze_aom_alarms`), do not use handwritten Python to adjust the SDK
✅ **Alarm rule status value is `alarm` (not `firing`)** — Different APIs use different status fields, don’t get confused

# # Notes
- Ensure your AK/SK has proper IAM permissions for the requested resources
- Different regions may have different resource availability
- Monitoring data may have a few minutes delay
- Some metrics may not be available for all instance types
- CCE cluster operations require appropriate Kubernetes RBAC permissions

# # References
- [CCE Node Vulnerability Repair Guide](./references/CCE_NODE_VUL_FIX.md)
- [CCE Security Group Configuration Instructions](./references/CCE_Security_Group_Configuration.md)
- [CCE Node Fault Detection Strategy Configuration Guide](./references/CCE_Node_Fault_Detection_Configuration.md)
