# Capability Map

## 当前项目架构

本仓库采用简化多 skill 架构：

- 每个 skill 独立放在 `skills/<skill>/`。
- 能力实现集中在根目录 `scripts/huawei_cloud/`。
- `scripts/huawei-cloud.py` 作为统一 CLI 入口。
- `scripts/huawei_cloud/dispatcher.py` 维护 action 到 Python handler 的映射。
- `skill-profile.yaml` 声明工具边界，`scripts/dev/generate_manifests.py` 生成 `manifest.json`。

`change-impact-analyzer` 不复制脚本，只通过 `skills/change-impact-analyzer/scripts -> ../../scripts` 复用共享能力。

## 可复用能力

| 能力域 | 已有 action / 脚本 | 复用方式 |
| --- | --- | --- |
| 审计变更 | `huawei_query_cce_audit_logs` / `cce_app_logs.py` | 获取 Kubernetes audit 中 create/update/patch/delete 变更影子，包含执行人、verb、resource、namespace、name、requestURI、statusCode、raw audit。 |
| K8s 历史事件 | `huawei_query_k8s_events_from_lts` / `cce_events_lts.py` | 从 LTS 中读取历史 Event，弥补 K8s API 只能看到近期事件的问题。 |
| 当前事件 | `huawei_get_cce_events` / `cce.py` | 当 LTS Event 不可用时，查询当前 Events。 |
| 告警关联 | `huawei_analyze_aom_alarms` / `aom.py` | 同时分析 active + history 告警，避免遗漏已恢复的资源类告警。 |
| 发布诊断 | `huawei_workload_rollout_diagnose` / `workload_rollout_diagnosis.py` | 变更指向 Deployment/StatefulSet/DaemonSet 发布失败时下钻。 |
| 网络诊断 | `huawei_network_failure_diagnose` / `network_failure_diagnosis.py` | 变更指向 Service/Ingress/NetworkPolicy/ELB 链路时下钻。 |
| 节点诊断 | `huawei_node_failure_diagnose` / `node_failure_diagnosis.py` | 变更指向 Node taint、NotReady、调度异常、节点资源压力时下钻。 |
| 当前拓扑 | `huawei_get_cce_pods`、`huawei_get_cce_services`、`huawei_get_cce_ingresses`、`huawei_get_kubernetes_nodes` | 构建 Pod-Service-Ingress-Node 影响面。 |
| 配置快照 | `huawei_list_cce_configmaps`、`huawei_list_cce_secrets` | 识别 CoreDNS、kube-proxy、业务配置对象当前状态。 |
| 云网络快照 | `huawei_list_security_groups`、`huawei_list_vpc_acls` | 提供安全组/ACL 当前状态，用于报告缺口和人工核对。 |

外部 `pancake0001/cce-skills` 的 `huawei-cloud` skill 也覆盖这些方向：统一华为云资源查询、CCE 资源查询、AOM 告警 active+history 分析、LTS 日志、网络/工作负载/节点诊断、自动巡检和 HTML 诊断报告。当前仓库已经把这些能力拆成更细的 diagnoser 和共享 dispatcher，适合在 `change-impact-analyzer` 中复用，而不是重复实现。

## 已补充的组合能力

新增 action：`huawei_change_impact_analyze`。

它不是单一查询工具，而是组合编排：

1. 生成 `Analysis-Trace-ID`。
2. 采集审计日志、K8s 历史事件、AOM 告警、当前资源快照。
3. 对审计写操作做核心变更分类和噪声消除。
4. 将变更映射到当前拓扑并计算爆炸半径。
5. 与故障时间、事件、告警做关联。
6. 输出结构化 `top_changes`、完整 `changes` 和客户可交付的 `report_markdown`。

## 已根据真实集群案例优化的降噪规则

真实集群中出现过 `ClusterRole/system:cce:packageversion` 由 `system:masters` / CCE 平台组件更新的审计记录。该对象属于 CCE 自管理组件元数据，不应作为客户业务异常变更输出。当前版本已将以下运行态或平台托管行为从核心变更中剔除：

- `serviceaccounts/token` 子资源创建。
- `nodes/status` patch。
- 所有 `/status` 子资源写入，即使审计日志 requestObject 回显完整 spec。
- kube-scheduler `pods/binding`。
- deployment/replicaset/statefulset/daemonset controller 推进状态产生的工作负载写入。
- CCE 平台自管理 RBAC：`system:cce:*`、`cce:*` 且执行者匹配 CCE/平台组件。

普通用户、未知执行者或非 CCE 托管对象的 RBAC 变更仍保留为高风险。

## 仍需补齐的原子能力

| 缺口 | 原因 | 建议 action |
| --- | --- | --- |
| CTS/云审计历史 | 当前只能很好还原 Kubernetes audit，无法可靠还原 CCE 控制台、节点池、集群升级、ELB、安全组、VPC ACL 的历史变更。 | `huawei_query_cts_traces`，支持 service/resource/user/time/filter。 |
| before/after YAML 快照 | Audit 若未记录 `requestObject`/`patch`，只能对象级判断，无法做严格 Semantic Diff。 | `huawei_get_k8s_resource_history` 或接入 GitOps/备份系统。 |
| NetworkPolicy 当前拓扑 | 现有网络诊断内部有策略判断，但缺少独立列出/解析 action。 | `huawei_list_cce_networkpolicies`，输出 selector、ingress、egress 和命中的 Pod。 |
| RBAC 当前拓扑 | 缺少 Role/ClusterRole/Binding 查询，无法评估权限边界具体扩散。 | `huawei_list_cce_rbac`，输出 subject -> role -> verbs/resources。 |
| Gateway API 当前拓扑 | 已能识别 audit 中 Gateway/HTTPRoute，但当前快照缺少独立查询。 | `huawei_list_cce_gateway_api_resources`。 |
| ConfigMap/Secret 使用关系 | 当前只能按命名空间或核心组件名称推断，缺少“哪些 Pod/Workload 引用该配置”。 | `huawei_find_config_consumers`，扫描 volumes/envFrom/env/valueFrom。 |
| Node taint/toleration 精确影响 | 当前只关联节点 Pod，缺少 Pod tolerations 与调度约束模拟。 | `huawei_analyze_node_taint_impact`。 |
| 云网络变更 diff | 只有当前 SG/ACL 快照，缺少历史规则变化和执行人。 | 依赖 CTS，并补 `huawei_analyze_cloud_network_change`。 |

## 查缺补漏结论

当前仓库已经具备“观测、审计、事件、告警、Workload/Node/Network 下钻”的主体能力，足以实现第一版变更影响归因报告。主要短板在云侧历史变更和严格 before/after diff；这些不是组合 skill 能靠推理补齐的，需要后续补 CTS、NetworkPolicy/RBAC/Gateway 独立查询和配置引用关系扫描等原子能力。
