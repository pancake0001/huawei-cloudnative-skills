# Workflow

## 1. Gateway Phase

先做双重路由，不要直接进入 HPA 或 CA 细节。

语义意图：

- 命中 Pod、工作负载、Deployment、StatefulSet、副本、实例：`Target=WORKLOAD`。
- 命中 Node、节点、ECS、虚拟机、服务器、主机：`Target=NODE`。
- “为什么不自动扩容了”等模糊描述：`Target=UNKNOWN`。

能力发现：

- `Has_HPA`：`huawei_list_cce_hpas` 返回 HPA 总数或目标范围匹配 HPA。
- `Has_CA`：`huawei_list_cce_addons` 识别 CCE 弹性引擎/Cluster Autoscaler，或 `huawei_list_cce_nodepools` 中存在开启 autoscaling 的节点池。

路由矩阵：

| Target | Has_HPA / Has_CA | 路径 |
| --- | --- | --- |
| WORKLOAD | 任意 | A：工作负载弹性诊断 |
| NODE | 任意 | B：节点弹性诊断 |
| UNKNOWN | True / False | A：工作负载弹性诊断 |
| UNKNOWN | False / True | B：节点弹性诊断 |
| UNKNOWN | True / True | C：双层级联诊断 |
| 任意 | False / False | 阻断：未配置自动弹性能力 |

## 2. 路径 A：Pod 层 HPA 闭环

目标：解释副本数为什么没有从 N 到 N+1。

检查顺序：

1. HPA 是否存在且 scaleTargetRef 指向正确的 Deployment/StatefulSet。
2. HPA status：`currentReplicas`、`desiredReplicas`、`minReplicas`、`maxReplicas`、conditions。
3. HPA Events：`FailedGetResourceMetric`、`FailedComputeMetricsReplicas`、`FailedGetScale`、`Selector`、`missing request`。
4. 指标条件：当前 CPU/内存或自定义指标是否超过目标阈值；若比例落在 HPA 忍受度内，标记为“条件未满足”。
5. 资源请求：CPU/Memory 利用率型 HPA 必须检查目标 Pod 容器是否有对应 `resources.requests`。
6. 指标组件：metrics-server、AOM、Prometheus 或 custom/external metrics 链路是否可见。
7. 上限与冷却：`maxReplicas`、`ScalingLimited`、behavior/stabilization/cooldown 相关 Event。

典型根因：

- 未配置 HPA 或 HPA 未匹配目标工作负载。
- 缺少 CPU/Memory request，HPA 无法计算利用率。
- 指标缺失或 metrics/AOM/Prometheus 流中断。
- 当前指标未超过阈值，或在默认约 10% 忍受度内。
- 达到 `maxReplicas`。
- scaleTargetRef、selector 或 labels 错配。

## 3. 路径 B：Node 层 CA 闭环

目标：解释节点数为什么没有从 M 到 M+1，或缩容为什么被保护策略阻断。

**前置优先步骤：分析 CA 组件 Pod 日志。**

CA 组件（CCE 集群弹性引擎/Cluster Autoscaler）以 Pod 形式运行在 `kube-system` 名字空间。其标准输出日志是判断节点伸缩问题**最直接、置信度最高**的证据源。排查前优先拉取 CA Pod 日志：

- 通过 `huawei_get_cce_pods` 定位 `kube-system` 下名称包含 `autoscaler`/`cce-elastic`/`elastic-engine` 的 Pod。
- 用 `huawei_get_pod_logs`（`tail_lines=200`）拉取该 Pod 日志。
- 在日志中检索关键信号（`huawei_autoscaling_diagnose` 主工具已自动执行此步骤）。

**CA 日志关键信号速查：**

| 信号 | 含义 | 严重级别 |
| --- | --- | --- |
| `No expansion options` | CA 无可用扩容选项，通常因节点池规格/AZ/子网不满足待调度 Pod 需求 | critical |
| `max node group size reached` | 节点组已达 max_nodes 上限 | critical |
| `Scale-up: final scale-up plan is empty` | 扩容最终计划为空，所有节点组被跳过 | critical |
| `Quota exceeded` / `quota limit` | 云资源（ECS/EVS/EIP）配额不足 | critical |
| `subnet ip exhausted` / `no available ip` | VPC 子网可用 IP 耗竭 | critical |
| `iam` / `permission denied` / `agency` / `forbidden` | IAM 委托或权限异常 | critical |
| `Failed to refresh` / `cannot connect` | CA 无法连接云 API 或控制面 | high |
| `skipping node group` | CA 跳过某个节点组，日志中会注明原因 | high |
| `pod ... is unschedulable` | CA 已识别到不可调度的 Pod | info |
| `ScaleDown: no candidates` | 缩容无候选节点 | info |
| `node ... is not suitable for removal` | 节点不满足缩容条件 | high |
| `not safe to evict` / `safe-to-evict=false` | PDB 或 annotation 保护阻止驱逐 | high |

扩容检查顺序：

1. **优先查阅 CA Pod 日志**：主工具 `huawei_autoscaling_diagnose` 已自动拉取并分析。手工兜底时优先执行此步骤——CA 日志往往直接暴露根因。
2. 是否安装 CCE 集群弹性引擎/Cluster Autoscaler，版本是否低于 1.13.8。
3. 节点池/伸缩组是否开启 autoscaling，是否配置 min/max。
4. 是否存在 Pending Pod，尤其是 `FailedScheduling` 且包含 `Insufficient cpu/memory/pods/ephemeral-storage`。
5. 节点池是否达到 `max_nodes`。
6. Pending 是否由亲和性、反亲和、nodeSelector、污点/容忍度不匹配导致；这种情况可能不是单纯加节点能解决。
7. 云资源信号：VPC 子网 IP 不足、ECS/EVS/EIP 配额不足、IAM 委托权限异常（CA 日志通常包含明确错误信息）。

缩容检查顺序：

1. **优先查阅 CA Pod 日志**：缩容类信号如 `not suitable for removal`、`not safe to evict`、`no candidates` 均在 CA 日志中明确记录。
2. 节点 requests 是否低于缩容阈值并持续满足冷却窗口。
3. PodDisruptionBudget 是否不允许驱逐。
4. Pod 是否设置 `cluster-autoscaler.kubernetes.io/safe-to-evict=false`。
5. 节点上是否存在 kube-system 非 DaemonSet Pod 或非控制器管理 Pod。

## 4. 路径 C：双层级联

按时序溯源：

1. 先跑路径 A，判断 HPA 是否已提高目标副本或使工作负载 desired replicas 大于 ready replicas。
2. 如果 HPA 未扩容，结论收敛到 Pod 层阻塞，不继续把问题归因到节点。
3. 如果 HPA 已扩容且新增 Pod Pending，再把这些 Pending Pod 作为路径 B 的输入，检查 CA 为什么没有补节点（**包含 CA Pod 日志分析**）。
4. 如果无法证明 HPA 已扩容，也没有 Pending Pod，报告为”联动证据不足”，列出需要补采的历史 HPA Event、Deployment revision 或指标时间线。
5. 级联场景中 CA Pod 日志同时包含 CA 侧的调度尝试记录和云 API 调用错误，可作为 HPA→CA 联动的关键补证。

## 5. 手工兜底工具顺序

当 `huawei_autoscaling_diagnose` 不可用或失败时：

1. `huawei_list_cce_hpas`
2. `huawei_list_cce_addons`
3. `huawei_list_cce_nodepools`
4. `huawei_get_cce_deployments` / `huawei_list_cce_statefulsets`
5. `huawei_get_cce_pods`（**额外拉取 `namespace=kube-system` 以定位 CA 组件 Pod**）
6. **`huawei_get_pod_logs`**：定位 `kube-system` 下名称含 `autoscaler`/`cce-elastic`/`elastic-engine` 的 Pod，拉取其日志（`tail_lines=200`）。在日志中查找 `NoExpansionOptions`、`QuotaExceeded`、`subnet`、`permission denied`、`skipping node group`、`max node group size`、`scale up plan empty`、`not suitable for removal`、`safe-to-evict` 等信号——这一步往往是**确认 CA 侧根因的最关键步骤**。
7. `huawei_get_cce_events`
8. `huawei_get_cce_pod_metrics_topN` / `huawei_get_cce_node_metrics_topN`
9. 必要时用 `huawei_get_aom_metrics` 查询自定义 PromQL。
