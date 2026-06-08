# SkillIndex

`skills/_catalog` is the general catalog for manual search, and is not a triggerable Skill. Agent automatically matches capabilities through the `description` in `SKILL.md` of each Skill.

Currently displaying **33 Business Skills**. `huawei-cloud` is an aggregation portal compatible with historical calls. It is not displayed as an independent business skill and is not included in the quantity.

# # 1. Life cycle and resource management

## # CCE

| Skill | Ability Description |
| --- | --- |
| `huawei-cloud-cce-cluster-management` | Manage the full life cycle of CCE clusters, node pools, nodes, plug-ins, EIP and kubeconfig. |
| `cce-cluster-upgrade-planner` | Plan CCE Kubernetes version upgrade, check upgrade path, plug-in compatibility, differences and upgrade window. |
| `cce-workload-manager` | Manage CCE workloads and Kubernetes resources, including Deployment, StatefulSet, DaemonSet, Job, CronJob, HPA, Service, Ingress and configuration resources. |

## # CCI

| Skill | Ability Description |
| --- | --- |
| `huawei-cloud-cci-instance-management` | Manage CCI container instances, including Namespace, network, Deployment, StatefulSet, Pod, EIPPool, logs and metrics. |

## # SWR

| Skill | Ability Description |
| --- | --- |
| `huawei-cloud-swr-image-management` | Manage SWR namespace, image warehouse, labels, login credentials and quotas. |
| `huawei-cloud-swr-image-governance` | Manage SWR permissions, retention policies, sharing policies, delegation and immutable rules. |
| `huawei-cloud-swr-image-automation` | Manage SWR image synchronization, triggers and automatic deployment process. |
| `huawei-cloud-swr-enterprise-instance` | Manage SWR enterprise instances, intra-instance namespaces, warehouses, artifacts, credentials, endpoints, and domain names. |

# # 2. Observable and intelligent alarms

| Skill | Ability Description |
| --- | --- |
| `observability-context-builder` | Aggregates AOM alerts, metrics, LTS logs, Pod logs, and Kubernetes events to form diagnostic context. |
| `alarm-correlation-engine` | Correlation analysis of AOM active/history alarms, complete deduplication and merging, severity grouping and alarm rule checking. |
| `log-analyzer` | Query and analyze Pod standard output, CCE LogConfig application logs and LTS logs. |
| `kubernetes-event-analyzer` | Query and analyze Kubernetes Warning events, recurring patterns, and Pod, Node, and Workload exceptions. |
| `metric-analyzer` | Query and analyze CCE Pod, Node, ECS, ELB, EIP, and NAT indicators, and identify threshold anomalies. |

# # 3. Fault diagnosis and self-healing recovery

| Skill | Ability Description |
| --- | --- |
| `pod-failure-diagnoser` | Diagnose Pod failures such as CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending, Evicted and frequent restarts. |
| `workload-failure-diagnoser` | Diagnose Deployment, StatefulSet, DaemonSet release failure, rolling upgrade stuck, insufficient replicas and probe exceptions. |
| `node-failure-diagnoser` | Diagnoses Node NotReady, resource pressure, NPD, CNI, kubelet and container runtime exceptions. |
| `autoscaling-diagnoser` | Diagnoses HPA, Cluster Autoscaler and CCE resiliency engine link failures. |
| `network-failure-diagnoser` | Diagnoses Service, DNS, Ingress, NetworkPolicy, ELB, EIP, NAT and VPC network failures. |
| `storage-failure-diagnoser` | Diagnoses PVC, PV, EVS, SFS, OBS, mount, capacity and delete protection related failures. |
| `root-cause-analyzer` | Summarizes cross-domain evidence and outputs Top root causes, impact scope, confidence and recovery handover. |
| `change-impact-analyzer` | Analyze the impact of failures caused by changes in releases, configurations, networks, security policies, and nodes. |
| `dependency-impact-analyzer` | Analyzes fault propagation paths and upstream and downstream impacts based on Service, Ingress, Pod and Node topology. |
| `auto-remediation-runner` | Generates and executes controlled recovery actions, with all high-risk changes previewed by default and requiring explicit confirmation. |

# # 4. Inspection, governance and continuous operation and maintenance

| Skill | Ability Description |
| --- | --- |
| `daily-cluster-inspector` | Perform periodic CCE health checks, quick inspections and continuous operation and maintenance summaries. |
| `availability-risk-scanner` | Scans for high availability, AZ distribution, single replica, PDB, probe, affinity, gateway and resource overprovisioning risks. |
| `capacity-trend-forecaster` | Analyze periodic capacity trends, predict resource bottlenecks, and simulate HPA and node resiliency strategies. |
| `cost-optimization-advisor` | Analyze idle resources, excessive Requests, low-utilization nodes, and resiliency policy optimization opportunities. |
| `ops-report-generator` | Summarizes inspection, capacity, availability, cost and on-call context, and generates weekly, monthly, SLA, capacity and stability reports. |

# # 5. Solution and Delivery

| Skill | Ability Description |
| --- | --- |
| `cce-cci-bursting-deployer` | Configure, deploy and verify the elastic expansion capabilities of CCE to CCI 2.0, including VPCEP, virtual-kubelet and smoke verification. |
| `container-migration-planner` | Inventory container platform resources and dependencies, output migration batches, risks and verification plans, without performing actual migration. |
| `Full-link stress test` | Construct a stress test link from the k6 client to the business Pod via ELB, nginx-ingress, collect observation data and output performance reports. |

# # 6. Multi-cloud, multi-cluster management

| Skill | Ability Description |
| --- | --- |
| `ucs-cluster-onboarding-manager` | Manage UCS cluster management, lifecycle, fleet grouping, kubeconfig and resource quotas. |
| `ucs-policy-governor` | Manage UCS policy instances, policy definitions, start and stop operations, execution status, and fleet compliance auditing. |

# # FAQ Routing| User Questions | Recommended Skills |
| --- | --- |
| Pod keeps restarting, Pending, OOMKilled | `pod-failure-diagnoser` |
| Release failed, rolling upgrade stuck, copy not satisfied | `workload-failure-diagnoser` |
| Node NotReady, resource pressure, node vulnerability | `node-failure-diagnoser` |
| HPA does not expand Pods, CA does not expand nodes | `autoscaling-diagnoser` |
| Ingress 502, Service unavailable, ELB link abnormality | `network-failure-diagnoser` |
| PVC Pending, FailedMount, capacity exhausted | `storage-failure-diagnoser` |
| There are many alarms and need to be combined and analyzed | `alarm-correlation-engine` |
| Query Pod standard output or LTS application log | `log-analyzer` |
| Analyze Kubernetes event trends | `kubernetes-event-analyzer` |
| Query Pod, Node or cloud resource metrics | `metric-analyzer` |
| Aggregate logs, events, metrics and alerts | `observability-context-builder` |
| The business is unavailable and requires comprehensive root cause analysis | `root-cause-analyzer` |
| Failure after change | `change-impact-analyzer` |
| Analyze the scope of impact of service failure | `dependency-impact-analyzer` |
| Perform expansion, restart, drain or recovery actions | `auto-remediation-runner` |
| Do daily inspections or periodic health checks | `daily-cluster-inspector` |
| Do cost optimization analysis | `cost-optimization-advisor` |
| Do capacity trend prediction and elasticity simulation | `capacity-trend-forecaster` |
| Do an availability risk scan | `availability-risk-scanner` |
| Generate weekly, monthly or SLA reports | `ops-report-generator` |
| Make container migration plan and resource inventory | `container-migration-planner` |
| Configure elastic expansion from CCE to CCI | `cce-cci-bursting-deployer` |
| Do full-link stress testing and performance evaluation | `Full-link stress testing` |
| Manage CCE cluster life cycle | `huawei-cloud-cce-cluster-management` |
| Planning CCE cluster version upgrade | `cce-cluster-upgrade-planner` |
| Managing CCE workloads | `cce-workload-manager` |
| Manage CCI container instances | `huawei-cloud-cci-instance-management` |
| Manage SWR image life cycle | `huawei-cloud-swr-image-management` |
| Manage SWR image governance policy | `huawei-cloud-swr-image-governance` |
| Manage SWR image synchronization and triggers | `huawei-cloud-swr-image-automation` |
| Manage SWR enterprise instance | `huawei-cloud-swr-enterprise-instance` |
| Manage UCS cluster onboarding and fleet | `ucs-cluster-onboarding-manager` |
| Manage UCS policy and compliance auditing | `ucs-policy-governor` |