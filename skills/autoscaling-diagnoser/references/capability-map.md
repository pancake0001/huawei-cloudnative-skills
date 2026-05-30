# Capability Map

## 已可复用能力

来自当前仓库：

- `huawei_list_cce_hpas`：读取 HPA 规格、current/desired replicas、current metrics、conditions。
- `huawei_generate_cce_hpa_manifest`、`huawei_configure_cce_hpa`：生成 HPA YAML 和配置预览，整改时复用但本诊断不直接执行。
- `huawei_list_cce_addons`、`huawei_get_cce_addon_detail`：识别 CCE 弹性引擎、metrics/AOM/Prometheus 等插件。
- `huawei_list_cce_nodepools`：读取节点池、伸缩组、autoscaling enable、min/max、当前节点数。
- `huawei_get_cce_pods`：读取 Pod phase、owner、container state、resources.requests/limits、annotation keys。
- `huawei_get_cce_deployments`、`huawei_list_cce_statefulsets`：读取目标工作负载 desired/current/ready replicas。
- `huawei_get_cce_events`：读取 HPA、Pod、Scheduler 事件，识别 FailedScheduling、FailedGetResourceMetric 等。
- `huawei_get_cce_pod_metrics_topN`、`huawei_get_cce_node_metrics_topN`、`huawei_get_aom_metrics`：补充 AOM/Prometheus 指标证据。
- 现有 `pod-failure-diagnoser`、`workload-failure-diagnoser`、`node-failure-diagnoser` 可承接下钻。
- `cost-optimization-advisor` 和 `capacity-trend-forecaster` 已有 HPA 覆盖、节点池 autoscaling、request/usage、容量趋势分析，可复用治理建议。

来自外部 `pancake0001/cce-skills` 的可迁移经验：

- 安全边界：AK/SK 不落盘，危险操作必须二次确认。
- CCE 工具族：集群、节点池、插件、Pod、Deployment、Events、AOM、监控、诊断报告能力已经覆盖 autoscaling 诊断所需的大部分基础证据。
- 输出习惯：先列诊断步骤，再输出完整报告；报告需要包含证据、结论、建议。

## 已补充能力

- `huawei_autoscaling_diagnose`：新增只读组合诊断动作。
- 自动完成 Gateway：意图识别、HPA/CA 能力发现、路径 A/B/C 路由。
- 自动生成 Markdown 报告：包含排查过程、证据、结论、置信度、建议和数据缺口。
- 识别核心根因：HPA 未配置、缺 request、指标缺失、阈值未满足、maxReplicas、CA 未安装/版本低、节点池未开启伸缩、max_nodes、无 Pending、资源不足 Pending、亲和性/污点冲突、子网 IP/配额/权限可疑信号、缩容保护信号。
- **CA Pod 日志分析**：自动发现 `kube-system` 下的 CA 组件 Pod（CCE 弹性引擎/Cluster Autoscaler），通过 `huawei_get_pod_logs` 拉取其标准输出日志，按 16 种诊断模式匹配关键信号（NoExpansionOptions、MaxNodeGroupSize、QuotaExceeded、SubnetIPExhausted、IAM 权限、safe-to-evict 保护、节点不可移除等），将高置信度发现合并到 issues 和 evidence 中。

## 仍建议补齐的原子能力

这些能力不是首版必需，但会显著提高诊断置信度：

- `huawei_get_cce_hpa_events`：按 HPA 对象精确读取历史事件，避免只依赖当前 Event 窗口。
- `huawei_get_k8s_api_resources`：确认 `metrics.k8s.io`、`custom.metrics.k8s.io`、`external.metrics.k8s.io` APIService 可用性。
- `huawei_get_cce_pdbs`：读取 PodDisruptionBudget，用于缩容阻断判定。
- `huawei_get_cce_pod_annotations`：读取完整 annotation key/value，确认 `safe-to-evict=false` 而不仅是 key 存在。
- `huawei_get_cce_resourcequotas`：区分 Namespace ResourceQuota 与集群/云资源配额问题。
- `huawei_get_cce_ca_logs`：~~读取 CCE 弹性引擎/Cluster Autoscaler 日志，确认 NoExpansionOptions、MaxNodeGroupSizeReached、QuotaExceeded、SubnetIPExhausted、IAM denied 等原因。~~ ✅ **已通过 `huawei_autoscaling_diagnose` 内置的 CA Pod 发现 + `huawei_get_pod_logs` 组合实现**。首版诊断已覆盖 CA 日志中的 16 种关键信号。后续可考虑封装为独立原子工具以支持更灵活的日志查询（如指定时间范围、LTS 集成、调试级别日志）。
- `huawei_get_ecs_quotas` 或统一云资源配额查询：确认 ECS、EVS、EIP 等配额是否阻断扩节点。
- `huawei_get_vpc_subnet_ip_usage`：确认节点池子网剩余 IP。
- `huawei_get_cce_agency_status`：确认 CCE 委托/IAM 权限是否被删除或收窄。
- `huawei_get_workload_selector_context`：读取 workload selector 与 Pod template labels，精确判断 selector 错配。
