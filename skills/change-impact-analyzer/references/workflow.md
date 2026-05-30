# Workflow

## 1. Scope & Ingestion

1. 收集 `region`、`cluster_id`、`namespace` 或全集群范围、目标对象、故障现象、`fault_time`、`start_time`/`end_time` 或 `hours`。
2. 生成 `Analysis-Trace-ID`，报告和结构化输出必须保留该 ID。
3. 并行采集四类影子数据：
   - 应用与配置变更：CCE 审计日志中的 Deployment/StatefulSet/DaemonSet、ConfigMap、Secret 写操作。
   - 网络与路由变更：Service、Ingress、Gateway API、HTTPRoute/TCPRoute 等写操作。
   - 安全策略变更：NetworkPolicy、Role、ClusterRole、RoleBinding、ClusterRoleBinding、ServiceAccount 写操作。
   - 基础设施变更：Node 写操作、taint/cordon/drain 迹象、节点池当前快照、集群插件/核心配置快照。
4. 同步采集响应信号：K8s 历史事件、AOM active+history 告警、当前 Pod/Service/Ingress/Node/ConfigMap/Secret/Security Group/VPC ACL 快照。

## 2. Filtering & Categorization

1. 只保留 `create`、`update`、`patch`、`delete`、`replace` 等写操作。
2. 降噪：
   - 丢弃 Lease、Event、TokenReview、SubjectAccessReview、Pod status、Endpoint/EndpointSlice 常规 controller 写入。
   - 丢弃 ServiceAccount token 子资源创建、Node status patch、NPD/kubelet 心跳等运行态状态写入。
   - 丢弃 kube-scheduler 的 Pod binding，以及 deployment/replicaset/statefulset/daemonset controller 推进状态产生的写入；它们是控制面闭环，不是用户变更。
   - 丢弃所有 `/status` 子资源写入；审计日志可能回显完整 spec，但 status 子资源本身不是配置变更。
   - 丢弃 HPA 或 controller 仅修改 `replicas` 的工作负载更新。
   - 丢弃临时 token Secret 等短生命周期对象。
   - 丢弃 CCE 平台自管理 RBAC，如 `system:cce:*`、`cce:*` 且执行者为 CCE/平台组件的维护更新；普通用户或未知对象的 RBAC 变更仍保留为高风险。
3. 语义字段保留：
   - Workload：`image`、`env`、`resources`、`readinessProbe`、`livenessProbe`、`ports`、`selector`、`affinity`、`tolerations`。
   - Config：`data`、`stringData`、CoreDNS `Corefile`、upstream DNS。
   - Network：Service `ports/selector`、Ingress/Gateway `rules/tls/backend`。
   - Security：NetworkPolicy `ingress/egress/policyTypes`、RBAC `roleRef/subjects`。
   - Node：`taints`、`unschedulable`、调度相关字段。

## 3. Impact & Blast Radius Modeling

1. Service 变更：用 selector 找当前匹配 Pod，反查引用该 Service 的 Ingress。
2. Ingress/Gateway 变更：抽取 backend Service，推断外部入口到后端微服务路径。
3. Workload 变更：按工作负载名关联当前 Pod，再查 Service 选择器。
4. ConfigMap/Secret 变更：普通对象按命名空间影响面提示；CoreDNS/kube-proxy/核心插件配置按全集群处理。
5. Node 变更：关联该节点上的 Pod；taint/unschedulable 关联 Pending、FailedScheduling、Evicted 事件。
6. NetworkPolicy/RBAC 变更：按安全边界跨度加权；当前版本先以审计对象和事件/告警关键词关联，后续补当前策略拓扑查询。

## 4. Risk Scoring

基础分：

| 变更类别 | 典型核心操作 | 波及范围 | 基础风险 |
| --- | --- | --- | --- |
| 基础配置 | CoreDNS / kube-proxy / 核心插件配置 | Global | Critical / 90 |
| 安全策略 | NetworkPolicy / RBAC 提权或收敛 | 跨服务或跨命名空间 | High / 75 |
| 基础设施 | Node taint / cordon / drain / 节点池变化 | 节点及调度路径 | High / 70 |
| 网络路由 | Ingress / Gateway / Service 端口或后端变化 | 入口至微服务 | Medium / 60 |
| 配置对象 | ConfigMap / Secret | 命名空间内依赖对象 | Medium / 55 |
| 工作负载 | 镜像、探针、资源、环境变量 | 单服务及上下游 | Low-Medium / 45 |

加分项：

- 距离 `fault_time` 越近，加 0-15 分。
- 变更后窗口内出现相关 K8s 事件，加 0-10 分。
- 变更后窗口内出现相关 AOM 告警，加 0-12 分。
- 当前拓扑影响实体越多，加 0-12 分。
- 命中用户目标对象或目标 namespace，加 4-8 分。

## 5. Reporting

报告必须包含：

1. 分析摘要和 `Analysis-Trace-ID`。
2. 排查过程，说明四阶段做了什么。
3. 数据源采集状态和缺口。
4. 核心变更时间线。
5. Top N 最高风险预警。
6. 爆炸半径与传播路径。
7. 证据矩阵。
8. 结论、置信度和下一步只读验证建议。
