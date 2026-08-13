---
id: huawei-cloud-cce-change-impact-analyzer
name: huawei-cloud-cce-change-impact-analyzer
description: >
  使用 hcloud CLI、kubectl-cce 插件命令、AOM/LTS 证据 skill 和只读拓扑快照，分析近期华为云 CCE 变更是否导致故障。适用于工作负载发布、ConfigMap/Secret 更新、Service/Ingress/Gateway 路由变更、NetworkPolicy/RBAC/安全策略变更、节点污点、节点池或基础设施变更、审计/事件/告警关联、影响面、风险评分和 Markdown 报告。不要使用 Python SDK dispatcher action。
tags: [cce, change-impact, risk-assessment, hcloud, kubectl-cce]
---

# 华为云 CCE 变更影响分析

本 skill 把“故障前后发生过什么变更”转成有证据支撑的诱因分析。它关联当前拓扑、Kubernetes Events、可用的历史事件/日志、AOM 告警和只读云资源元数据，识别可能导致或放大 CCE 故障的变更。

执行模型：

```text
hcloud CCE 查询集群 -> kubectl cce 当前拓扑/事件 -> 可选 AOM/LTS/告警证据 -> 变更分类 -> 影响面 -> Markdown 报告
```

不要使用 Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、`huawei_change_impact_*`、`huawei_query_*`、`huawei_get_cce_*`、捆绑 SDK 脚本、kubeconfig 生成或 Huawei Cloud SDK import。

**相关前置 skill**：如果需要安装或修复 `kubectl`/`kubectl-cce`，使用 `huawei-cloud-kubectl-cce-installer`。执行 Kubernetes 命令前先读 `references/kubectl-cce.md`。

## 相关 Skill

| Skill | 使用场景 |
| --- | --- |
| `huawei-cloud-cce-kubernetes-event-analyzer` | 需要当前或历史 Kubernetes Events，或当前 Event 窗口不够 |
| `huawei-cloud-cce-alarm-correlation-engine` | 需要 AOM 当前/历史告警、告警风暴或告警时间锚点 |
| `huawei-cloud-cce-metric-analyzer` | 需要指标证明变更后发生性能退化 |
| `huawei-cloud-cce-workload-failure-diagnoser` | 可疑变更涉及 workload 镜像、探针、资源、环境变量或启动命令 |
| `huawei-cloud-cce-network-failure-diagnoser` | 可疑变更涉及 Service、Ingress、NetworkPolicy、ELB、EIP、NAT、安全组或 ACL |
| `huawei-cloud-cce-node-failure-diagnoser` | 可疑变更涉及节点污点、cordon/drain、节点池、升级、压力或 NotReady |
| `huawei-cloud-cce-dependency-impact-analyzer` | 需要映射影响面和服务拓扑 |
| `huawei-cloud-cce-root-cause-analyzer` | 变更发现需要和其他根因候选一起排序 |
| `huawei-cloud-cce-auto-remediation-runner` | 用户明确确认后的恢复预览和执行 |

## 必要输入

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `region` | 是 | 例如 `cn-north-4` |
| `project_id` | 通常需要 | kubectl-cce 和多数 hcloud 操作需要 |
| `cluster_id` | 推荐 | 没有时先用 hcloud 按名称定位 |
| `namespace` | 可选 | 核心系统和网络变更要保留全集群视角 |
| `target_name` | 可选 | 工作负载、Service、Pod、Ingress、Node 或 app label |
| `fault_time` | 推荐 | 用于计算时间邻近度 |
| `hours` / `start_time` / `end_time` | 推荐 | 尽量使用明确故障窗口 |
| `log_group_id` / `log_stream_id` | 可选 | 仅在审计/LTS 自动发现失败时手工指定 |

## 证据采集

1. 验证 hcloud 和 kubectl-cce。缺插件时使用 `huawei-cloud-kubectl-cce-installer`。
2. 查询集群元数据：

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

3. 采集当前拓扑和当前响应信号：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,pods,svc,ingress,endpoints,endpointslices,networkpolicy,configmap,secret -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

4. 历史 Events、审计日志、AOM 告警和指标优先交给 event/alarm/metric/log 类 skill。所需 LTS/AOM/审计源不可用时，写成数据缺口，不要编造变更时间线。
5. 云侧当前状态可用只读 hcloud 命令补充，例如 CCE 节点池、ELB、EIP、NAT、VPC 安全组和 VPC ACL。具体 KooCLI operation 不确定时先查 `hcloud <service> <operation> --help`，不要猜字段。

## 分析流程

1. 范围和时间线：明确故障窗口、故障时间、受影响对象和已知现象。
2. 变更候选：结合当前 ReplicaSet/rollout history、近期 Events、可用审计/LTS 记录、用户提供的变更记录和云资源元数据。
3. 降噪：忽略 controller status 更新、Lease/Event 噪声、HPA 单纯副本调整、Pod binding、`/status` 写入、无故障证据的平台托管 RBAC。
4. 分类高风险变更：
   - workload：image、command/args、env、resources、probe、volume、selector、affinity、tolerations；
   - config：ConfigMap/Secret data、CoreDNS Corefile、kube-proxy 或核心 add-on 配置；
   - network：Service ports/selectors、Ingress/Gateway backends、NetworkPolicy ingress/egress；
   - security：改变访问边界的 RBAC 和 ServiceAccount；
   - infrastructure：节点污点、cordon/drain、节点池扩缩容、升级、安全组/ACL/路由变化。
5. 影响面：将每个候选映射到 Pod、Service、Ingress、Node、命名空间和上下游路径。
6. 相关性：根据变更是否早于故障、变更后是否出现 Event/告警/指标变化、是否命中受影响拓扑、聚焦诊断是否确认故障特征进行评分。
7. 输出 Top N 变更风险、证据、反证、数据缺口和下一步验证。

## 输出要求

Markdown 报告必须从以下内容开始：

1. `## 总结`：最可疑变更、影响范围、置信度和证据是否充分。
2. `## 变更影响分析`：Top N 高风险变更、时间线、受影响对象、证据、反证和分数。
3. `## 下一步措施`：验证命令、聚焦诊断 skill 交接和必要的恢复交接。
4. `## 证据时间线`：变更时间、Events、告警、指标/日志证据和用户现象。
5. `## 影响面`：受影响 Pod、Service、Ingress、Node、命名空间和依赖路径。
6. `## 数据缺口`：审计日志不可用、LTS stream 缺失、RBAC 拒绝、rollout history 缺失或云侧历史变更缺口。

不能只因为对象发生过更新就断定“变更导致故障”。必须同时具备时间先后关系，以及至少一个响应信号或聚焦诊断结论。

## 验证

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_change_impact|huawei_query_|huawei_get_cce_|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

期望结果：没有可执行 SDK dispatcher 入口，也没有裸 Kubernetes 访问路径。Markdown 中只能作为禁用项或验证项出现。

## References

- `references/kubectl-cce.md`：插件接入约束。
- `references/workflow.md`：变更关联流程和评分。
- `references/capability-map.md`：证据来源和已知缺口。
- `references/output-schema.md`：结构化输出和 Markdown 布局。
- `references/risk-rules.md`：只读边界和交接规则。
