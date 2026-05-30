# Skill Index

## L1 CCE to CCI elasticity

### cce-cci-bursting-deployer

Use for fast CCE to CCI 2.0 bursting setup, including subnet precheck, SWR and OBS VPCEP readiness, `virtual-kubelet` configuration, smoke workload deployment, and verification on `bursting-node`.

### availability-risk-scanner

Use for CCE availability risk checks covering replicas, PDBs, probes, affinity, AZ distribution, gateway workloads, and resource configuration.

### capacity-trend-forecaster

Use for periodic CCE capacity trend analysis, bottleneck forecasting, simulation, and elasticity tuning recommendations.

`skills/_catalog` 是总目录，不是可触发 skill，因此不放 `SKILL.md`。第一阶段采用简化架构：agent 通过各 skill 的 `description` 自动触发；需要人工查找时先看本文件，再进入对应 skill 的 `SKILL.md` 和 `references/*`。

第一阶段不实现复杂 `skill-router`，也不建立完整 runtime 平台。工具边界由每个 skill 的 `skill-profile.yaml` 声明，`manifest.json` 由 `scripts/dev/generate_manifests.py` 生成。

## L1 产品与资源生命周期管理

### container-migration-planner

适用：CCE 集群迁移、容器平台交付方案、资源盘点、迁移风险评估。

常见问题：需要从一个集群迁移到另一个集群；需要评估 VPC、ELB、EIP、存储和工作负载依赖；需要输出迁移方案。

常用工具：`huawei_list_cce_clusters`、`huawei_list_cce_nodes`、`huawei_get_cce_deployments`、`huawei_get_cce_services`、`huawei_get_cce_ingresses`、`huawei_get_cce_pvcs`、`huawei_list_vpc`、`huawei_list_elb`。

关系：只做盘点和方案，不执行真实迁移；如发现运行态异常，转给 `root-cause-analyzer`。

## L2 可观测与告警智能

### observability-context-builder

适用：需要汇聚指标、日志、事件、告警，建立故障上下文。

常见问题：Pod 异常但不知道先看什么；用户提供 CCE 告警需要补齐上下文；服务变慢需要拉取 AOM、LTS、Events、TopN 指标。

常用工具：`huawei_list_aom_alarms`、`huawei_get_aom_metrics`、`huawei_query_aom_logs`、`huawei_get_cce_events`、`huawei_get_cce_pod_metrics_topN`、`huawei_get_cce_node_metrics_topN`。

关系：负责收集证据，不给最终恢复动作；根因判断交给 `root-cause-analyzer`。

### alarm-correlation-engine

适用：AOM 告警很多，需要合并、去重、分级和关联分析。

常见问题：CCE 告警风暴；active/history 告警需要一起看；规则、静默、动作规则需要核对。

常用工具：`huawei_list_aom_alarms`、`huawei_list_aom_current_alarms`、`huawei_analyze_aom_alarms`、`huawei_list_aom_alarm_rules`、`huawei_aom_alarm_inspection`。

关系：输出告警线索和时间线；复杂跨域根因交给 `root-cause-analyzer`。

### log-analyzer

适用：需要查询 Kubernetes Pod 标准输出、CCE LogConfig 采集的应用日志、或华为云 LTS 日志并做错误模式分析。

常见问题：查看 Pod 最近日志；查询上一个崩溃容器日志；根据应用名找到 LTS 日志流；按关键词、时间范围或标签查询 LTS 日志。

常用工具：`huawei_get_pod_logs`、`huawei_get_cce_logconfigs`、`huawei_create_cce_logconfig`、`huawei_delete_cce_logconfig`、`huawei_get_application_logconfigs`、`huawei_query_cce_audit_logs`、`huawei_query_application_logs`、`huawei_query_application_recent_logs`、`huawei_analyze_application_logs`。

关系：只读查询和分析日志；如果日志指向 Pod、Node、Network 或恢复动作，转给对应诊断或自愈 skill。

### kubernetes-event-analyzer

适用：需要查询和分析 Kubernetes 事件，发现 Warning 事件、节点/Pod/工作负载异常、以及事件模式。

常见问题：查看集群最近的 Warning 事件；查找重复的 ImagePullBackOff、Evicted、FailedScheduling 事件；按 namespace 或时间窗口分析事件趋势；关联事件与具体 Pod/Node/Workload。

常用工具：`huawei_get_cce_events`、`huawei_query_k8s_events_from_lts`。

关系：只读查询事件；如果事件指向具体故障，转给对应诊断 skill（Pod 问题 -> `pod-failure-diagnoser`，Node 问题 -> `node-failure-diagnoser`，工作负载问题 -> `workload-failure-diagnoser`）。当集群开启 K8s 事件 LTS 采集时，可使用 `huawei_query_k8s_events_from_lts` 从 LTS 查询历史事件；否则使用 `huawei_get_cce_events` 从 K8s API 实时查询。

## L3 故障诊断与自愈恢复

### pod-failure-diagnoser

适用：CrashLoopBackOff、ImagePullBackOff、OOMKilled、Pending、Evicted、Pod 日志异常。

常见问题：Pod 一直重启；Pod Pending；单个 Pod OOMKilled；用户只给了 namespace 和应用名。

常用工具：`huawei_pod_failure_diagnose`、`huawei_get_cce_pods`、`huawei_get_pod_logs`、`huawei_get_cce_events`、`huawei_get_cce_pod_metrics`、`huawei_workload_diagnose`。

关系：定位 Pod 运行时问题；如果问题是发布失败、滚动升级卡住或副本不满足，转给 `workload-failure-diagnoser`。

### workload-failure-diagnoser

适用：Deployment/StatefulSet/DaemonSet 发布失败、滚动升级卡住、副本不满足、新 ReplicaSet 无法创建 Pod、探针异常导致不可用。

常见问题：Deployment rollout 卡住；发布后 readyReplicas 不足；NewRS 没有 Pod；StatefulSet updatedReplicas 不增长；Running 但 readiness probe 失败。

常用工具：`huawei_workload_rollout_diagnose`、`huawei_get_workload_rollout_context`、`huawei_pod_failure_diagnose`、`huawei_get_cce_events`、`huawei_get_pod_logs`。

关系：负责控制器、版本、ReplicaSet、Pod 事件漏斗；Pod 运行时细节复用 `pod-failure-diagnoser`；恢复动作交给 `auto-remediation-runner`。

### node-failure-diagnoser

适用：Node NotReady、Ready=Unknown、Lease 超时、资源压力、NPD 事件、CNI/网络异常、kubelet/CRI 异常、节点漏洞。

常见问题：节点 NotReady；Pod 集中调度失败；节点 CPU/内存/磁盘压力；FailedCreatePodSandBox/CNI 错误；SystemOOM；ContainerRuntimeNotReady；HSS 漏洞影响节点。

常用工具：`huawei_node_failure_diagnose`、`huawei_get_kubernetes_nodes`、`huawei_get_cce_events`、`huawei_get_cce_pods`、`huawei_get_cce_node_metrics`、`huawei_node_diagnose`、`huawei_node_batch_diagnose`、`huawei_hss_list_host_vuls_all`。

关系：定位节点层问题；cordon、drain、reboot 由 `auto-remediation-runner` 预览和确认。

### network-failure-diagnoser

适用：Service 不通、DNS/CoreDNS 异常、Ingress 502/504、NetworkPolicy 拦截、ELB 后端异常、ELB/EIP/NAT 链路问题、Pod 调度后的连通性验证。

常见问题：外部访问 502；Service 没有后端；域名无法解析；NetworkPolicy 阻断；Ingress 到 ELB 链路异常；节点安全组或网络 ACL 可疑。

常用工具：`huawei_network_failure_diagnose`、`huawei_get_cce_services`、`huawei_get_cce_ingresses`、`huawei_get_elb_backend_status`、`huawei_get_elb_metrics`、`huawei_list_eip`、`huawei_network_diagnose`。

关系：定位网络链路；涉及绑定/解绑 EIP 或扩缩容验证时交给 `auto-remediation-runner`。

### storage-failure-diagnoser

适用：PVC Pending、PV/PVC 绑定异常、EVS 可用区调度冲突、VolumeAttachment 挂载失败、SFS/SFS Turbo NFS timeout、OBS 403/签名错误、容量或 Inode 耗尽、只读文件系统、ConfigMap/Secret subPath 挂载异常、PVC Terminating 删除保护。

常见问题：为什么我的卷挂不上；PVC 为什么一直 Pending；Pod 卡在 ContainerCreating 且 FailedMount；EVS 云盘 attach 失败；SFS 挂载超时；OBS 挂载 403；应用写入报 no space left/read-only file system；PVC 删除不掉。

常用工具：`huawei_storage_failure_diagnose`、`huawei_get_cce_pvcs`、`huawei_get_cce_pvs`、`huawei_get_cce_storageclasses`、`huawei_get_cce_volumeattachments`、`huawei_get_cce_node_stats_summary`、`huawei_get_cce_everest_csi_logs`、`huawei_list_evs`、`huawei_list_sfs`、`huawei_list_sfs_turbo`。

关系：定位存储生命周期问题；若证据落到节点 NotReady/资源压力，转给 `node-failure-diagnoser`；若落到安全组/ACL/VPC 链路，转给 `network-failure-diagnoser`；删除残留 Pod、扩容、迁移、detach 等动作转给 `auto-remediation-runner`。

### root-cause-analyzer

适用：跨 Pod、Node、Network、AOM 告警的综合根因分析。

常见问题：用户只描述业务不可用；多个告警同时出现；需要 Top3 根因、证据链和报告。

常用工具：`huawei_workload_diagnose`、`huawei_network_diagnose`、`huawei_node_diagnose`、`huawei_generate_diagnosis_report`、`huawei_analyze_aom_alarms`。

关系：汇总诊断结论；恢复动作交给 `auto-remediation-runner`，巡检入口交给 `daily-cluster-inspector`。

### auto-remediation-runner

适用：用户已经明确要求恢复动作，或诊断结果需要生成可确认的恢复预案。

常见问题：扩容工作负载；cordon/drain 节点；重启 ECS；修复 HSS 漏洞；休眠或唤醒 CCE 集群。

常用工具：`huawei_scale_cce_workload`、`huawei_configure_cce_hpa`、`huawei_resize_cce_nodepool`、`huawei_cce_node_cordon`、`huawei_cce_node_drain`、`huawei_reboot_ecs`、`huawei_hss_change_vul_status`。

关系：默认只预览，不自动加 `confirm=true`；执行后调用只读诊断工具做验证。

## L4 巡检、治理与连续运维

### daily-cluster-inspector

适用：每日巡检、快速健康检查、自动巡检任务、巡检报告生成。

常见问题：每天早上检查 CCE 集群；只想快速知道是否异常；需要在异常时再深度诊断。

常用工具：`huawei_cce_quick_check`、`huawei_cce_auto_inspection`、`huawei_cce_cluster_inspection_parallel`、`huawei_pod_status_inspection`、`huawei_aom_alarm_inspection`。

关系：正常时输出简报；异常时转给 `root-cause-analyzer` 或对应诊断 skill。

### cost-optimization-advisor

适用：空闲资源、过量 Request、低利用率节点、HPA/autoscaler 弹性策略优化。

常见问题：集群平均 CPU/内存利用率长期低于 30%；某些节点明显低于整体平均；业务命名空间工作负载 request 明显大于实际使用；需要生成 HPA 或节点池 autoscaler 优化建议。

常用工具：`huawei_analyze_cce_cost_optimization`、`huawei_list_cce_nodes`、`huawei_list_cce_nodepools`、`huawei_get_cce_pods`、`huawei_get_cce_deployments`、`huawei_list_cce_hpas`、`huawei_generate_cce_hpa_manifest`、`huawei_configure_cce_hpa`、`huawei_get_cce_node_metrics_topN`、`huawei_get_cce_pod_metrics_topN`、`huawei_get_aom_metrics`。

关系：负责分析、HPA 查询、HPA YAML 生成和配置预览；实际配置 HPA、autoscaler 或缩容节点池时必须经过人工确认流程。

### capacity-trend-forecaster

适用：CCE 周期性容量趋势分析、资源瓶颈预测、HPA 和节点池弹性策略模拟、趋势图和历史对比报告。

常见问题：需要按 1 小时到 1 个月窗口看容量趋势；需要每 6 小时、每日、每周或每月做容量报告；需要评估 HPA 目标利用率或节点 autoscaler 上下限。

常用工具：`huawei_analyze_cce_capacity_trend`、`huawei_list_cce_clusters`、`huawei_get_kubernetes_nodes`、`huawei_list_cce_nodepools`、`huawei_get_cce_deployments`、`huawei_list_cce_hpas`、`huawei_get_cce_node_metrics_topN`、`huawei_get_aom_metrics`、`huawei_generate_cce_hpa_manifest`、`huawei_configure_cce_hpa`。

关系：负责趋势分析、图表、模拟和配置预览；真实 HPA 或节点池变更必须由用户明确授权，并建议变更后再次生成容量记录做对比。

### availability-risk-scanner

适用：CCE 可用性风险扫描，包括单副本、缺失 PDB、探针缺失或异常、AZ 分布不均、网关集中、核心插件反亲和和 request/limit 风险。

常见问题：需要上线前或巡检时检查可用性短板；担心 nginx-ingress、CoreDNS 或关键业务工作负载单点；需要输出整改优先级和人工复核点。

常用工具：`huawei_scan_cce_availability_risk`、`huawei_list_cce_clusters`、`huawei_get_kubernetes_nodes`、`huawei_get_cce_pods`、`huawei_get_cce_deployments`、`huawei_get_cce_services`、`huawei_get_cce_ingresses`、`huawei_list_cce_nodepools`、`huawei_list_cce_daemonsets`、`huawei_list_cce_statefulsets`、`huawei_get_cce_node_metrics_topN`、`huawei_get_aom_metrics`。

关系：负责只读风险识别和整改建议；不自动创建 PDB、不改探针、不迁移节点，执行整改交给授权后的变更流程。

### ops-report-generator

适用：CCE 周报、月报、SLA、容量和稳定性报告，汇总巡检、容量趋势、可用性风险、成本优化和 on-call 上下文。

常见问题：需要给客户或团队输出周期性运维报告；需要把多个诊断/治理结果合成 Markdown 和 HTML；需要在报告里明确数据缺口和后续行动。

常用工具：`huawei_generate_ops_report`、`huawei_cce_auto_inspection`、`huawei_analyze_cce_capacity_trend`、`huawei_scan_cce_availability_risk`、`huawei_analyze_cce_cost_optimization`。

关系：负责汇总评估和报告，不执行写操作；报告中涉及整改时转给对应 skill 或 `auto-remediation-runner`。

## L5 解决方案与交付专家

第一阶段由 `container-migration-planner` 覆盖容器迁移和交付方案类问题。后续可以扩展容量规划、成本优化、灾备设计等独立 skill。

## L6 多云、多集群与混合云管理

第一阶段暂不实现多云控制面。多集群清单和迁移盘点先由 `container-migration-planner` 处理。

## L7 知识库、Runbook 与智能体底座

第一阶段以各 skill 的 `references/workflow.md`、`references/risk-rules.md`、`references/output-schema.md` 承载 runbook。后续如果 skill 数量超过 20 个，再评估独立 router 或知识库索引。

## 常见问题路由

| 用户问题 | 推荐 skill |
| --- | --- |
| Pod 一直重启、Pending、OOMKilled | `pod-failure-diagnoser` |
| 发布失败、滚动升级卡住、副本不满足、探针异常 | `workload-failure-diagnoser` |
| 节点 NotReady、资源压力、节点漏洞 | `node-failure-diagnoser` |
| Ingress 502、Service 不通、ELB 链路异常 | `network-failure-diagnoser` |
| PVC Pending、FailedMount、VolumeAttachment、容量/Inode、PVC Terminating | `storage-failure-diagnoser` |
| CCE 告警很多，需要合并分析 | `alarm-correlation-engine` |
| 查询 Pod 标准输出或 LTS 应用日志 | `log-analyzer` |
| 需要分析 Kubernetes 事件趋势和 Warning 事件 | `kubernetes-event-analyzer` |
| 需要先把日志、事件、指标、告警都收集齐 | `observability-context-builder` |
| 业务不可用，需要综合根因分析 | `root-cause-analyzer` |
| 需要扩容、重启、drain、漏洞修复等动作 | `auto-remediation-runner` |
| 做每日巡检或周期性健康检查 | `daily-cluster-inspector` |
| 做成本优化、Request 过量分析、弹性策略建议 | `cost-optimization-advisor` |
| 做容量趋势预测、弹性模拟、周期容量图表 | `capacity-trend-forecaster` |
| 做可用性风险扫描、PDB/探针/AZ 分布检查 | `availability-risk-scanner` |
| 做周报、月报、SLA、容量或稳定性运维报告 | `ops-report-generator` |
| 做容器迁移方案和资源盘点 | `container-migration-planner` |
