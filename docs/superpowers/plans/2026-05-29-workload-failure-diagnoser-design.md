# workload-failure-diagnoser 设计文档

**日期**: 2026-05-29
**阶段**: 设计优先，暂不实现 skill 内容
**目标 skill**: `workload-failure-diagnoser`
**定位**: 诊断 CCE 工作负载发布失败、滚动升级卡住、副本不满足、探针异常、Pod 新版本未派生等控制器级问题。

## 1. 背景与目标

现有 `pod-failure-diagnoser` 已能诊断单 Pod 的 CrashLoopBackOff、ImagePullBackOff、OOMKilled、Pending、Evicted、频繁重启等问题，但它缺少工作负载控制器视角：

- 不能可靠判断 Deployment 控制面是否已观察到最新 `generation`。
- 不能锁定 Deployment 最新 ReplicaSet，也不能区分 NewRS / OldRS。
- 不能解释“新版本为什么没有创建 Pod”或“滚动升级为什么卡在某个批次”。
- 不能按 Workload / ReplicaSet / Pod UID 精确清洗事件。
- 对 StatefulSet / DaemonSet 的 `updatedReplicas`、`readyReplicas`、`unavailableReplicas` 只做摘要展示，没有形成发布漏斗判断。

本 skill 的核心目标是把 **控制器状态、版本归属、事件树、Pod 运行时状态机** 串起来，形成确定性的发布失败诊断链路。Pod 级原因不重复造轮子，直接复用 `huawei_pod_failure_diagnose` 的运行时诊断。

## 2. 现有架构速览

仓库采用多 skill + 共享 Python 脚本架构：

- `skills/<skill>/SKILL.md`: skill 触发说明和流程。
- `skills/<skill>/skill-profile.yaml`: 机器可读工具边界。
- `skills/<skill>/manifest.json`: 由 `scripts/dev/generate_manifests.py` 从 profile 和 dispatcher 生成。
- `skills/<skill>/scripts -> ../../scripts`: 每个 skill 共享根目录脚本。
- `scripts/huawei-cloud.py`: CLI 入口。
- `scripts/huawei_cloud/dispatcher.py`: action 注册和参数分发。
- `scripts/huawei_cloud/*.py`: 华为云、Kubernetes、AOM、LTS、诊断、报告等实现。

实现新 skill 时应保持现有模式：

1. 新增 `skills/workload-failure-diagnoser/`。
2. 新增 `skill-profile.yaml` 声明只读诊断工具。
3. 在 `dispatcher.py` 注册新增 action。
4. 由 `generate_manifests.py` 生成 manifest。
5. 创建 `scripts` 软链指向根目录脚本。
6. 更新 catalog 和静态校验测试。

## 3. 可复用能力清单

### 3.1 直接复用

| 能力 | 现有工具/脚本 | 复用方式 | 当前限制 |
| --- | --- | --- | --- |
| Pod 列表和标签过滤 | `huawei_get_cce_pods` / `cce.get_kubernetes_pods` | 用于 `labelSelector = matchLabels` 拉取相关 Pod | 返回 Pod UID 缺失，需补齐；ownerReferences 已有但仅用于 Pod 归属 |
| Pod 状态机诊断 | `huawei_pod_failure_diagnose` / `pod_diagnosis.py` | 对 NewRS 异常 Pod 调用，避免重写 CrashLoop/ImagePull/Pending/OOM 逻辑 | 入口按 Pod / workload / labels 选对象，不知道 NewRS 集合；事件按 kind/name 匹配而非 UID |
| Pod 日志 | `huawei_get_pod_logs` | CrashLoop、OOMKilled、频繁重启时由 Pod 诊断工具调用 | ImagePull 不查日志，这一点已符合预期 |
| 事件列表 | `huawei_get_cce_events` / `cce.get_kubernetes_events` | 作为临时事件来源 | 不支持 `fieldSelector`；不返回 involvedObject.uid；未按时间排序 |
| Deployment 摘要 | `huawei_get_cce_deployments` | 可做粗略列表和副本摘要 | 缺 `metadata.uid`、`generation`、`observedGeneration`、selector、conditions、annotations |
| StatefulSet / DaemonSet 摘要 | `huawei_list_cce_statefulsets`、`huawei_list_cce_daemonsets` | 可复用部分状态字段 | 缺 selector、generation、conditions、uid，`include_data` 返回 SDK 对象不适合作为 JSON 输出 |
| 指标 | `huawei_get_cce_pod_metrics`、`huawei_get_cce_pod_metrics_topN` | 判断资源瓶颈、OOM/启动耗时等 | 发布卡住的首要判断仍应以控制器状态和事件为准 |
| 节点诊断 | `huawei_node_diagnose`、`huawei_node_batch_diagnose` | Pending/调度失败/节点压力时作为下钻 | workload skill 只引用结论，不执行节点动作 |
| 网络诊断 | `huawei_network_diagnose` | Running 但 Readiness 不通过、Service endpoint 缺失时可作为下钻 | 只有在证据指向网络/依赖时调用 |
| 报告生成 | `huawei_generate_diagnosis_report`、`chart_generator.py` | 后续可复用 HTML 报告能力 | 当前报告是 7 步综合诊断，不是发布漏斗专用结构 |

### 3.2 外部 cce-skills 可借鉴内容

用户提供的 `pancake0001/cce-skills` 中 `huawei-cloud/SKILL.md` 已列出大量重复工具，和本仓库本地 `skills/huawei-cloud/SKILL.md` 高度重叠。可借鉴但不建议直接照搬的点：

- 工作负载诊断流程强调 AOM active/history、监控、异常 Pod、节点、网络、变更关联，适合综合诊断。
- 网络诊断、节点诊断和集群巡检已有清晰任务清单，可作为下钻分支。
- 现有 `huawei_workload_diagnose` 适合做兜底综合分析，但它不是按 Kubernetes rollout 控制器状态设计的，因此不应作为本 skill 的核心算法。

## 4. 缺口分析

### 4.1 元数据缺口

新 skill 需要一次性采集完整发布上下文，当前工具不够：

| 需求 | 当前状态 | 需要补充 |
| --- | --- | --- |
| 读取单个 Workload 完整元数据 | 只有 Deployment 列表摘要；StatefulSet/DaemonSet 摘要 | 新增 `read_workload`，支持 Deployment/StatefulSet/DaemonSet，返回 uid、generation、observedGeneration、selector.matchLabels、replicas、updated/ready/available/unavailable、conditions、strategy |
| List Pods with labelSelector | 已支持 labels 参数 | 需要返回 Pod `metadata.uid`、ownerReferences.uid、controller=true、pod-template-hash、conditions、container details 已基本可用 |
| List ReplicaSets with labelSelector | 当前无工具 | 新增 `list_replicasets`，返回 uid、revision、ownerReferences、spec/status replicas、selector、pod-template-hash、conditions |
| List Events with fieldSelector | 当前只按 namespace / all list | 新增 `list_events` 支持 `field_selector=involvedObject.namespace=<Namespace>` 或 namespaced event list，并返回 involvedObject.uid/apiVersion/resourceVersion |
| Event 清洗和排序 | 当前事件未按 UID 清洗，未排序 | 新增清洗逻辑：仅保留 involvedObject.uid 属于 Workload UID ∪ RS UIDs ∪ Pod UIDs；按事件时间倒序 |

### 4.2 诊断逻辑缺口

| 场景 | 当前状态 | 新增判断 |
| --- | --- | --- |
| 控制面未响应 | 无 generation check | `observedGeneration < generation` 输出终点 A：控制面假死/限流诊断 |
| 最新版本无法派生 | 无 NewRS/OldRS | Deployment 按 `deployment.kubernetes.io/revision` 最大值锁 NewRS；NewRS 期望 > 0 但实际为 0 或无关联 Pod 时查 RS Warning Events |
| 配额/准入拦截 | Pod 诊断看不到 RS FailedCreate | 在 NewRS 事件中匹配 `FailedCreate`、quota、admission、denied、forbidden、limitrange、resourcequota |
| 滚动升级卡住 | 当前只看 Pod 异常 | 双向漏斗：Workload desired -> NewRS desired/current/ready -> NewRS Pods phase/ready -> container state/probe/event/log |
| 副本不满足但非发布场景 | 当前综合诊断较泛 | 根据 `readyReplicas < spec.replicas`、`availableReplicas < spec.replicas`、`unavailableReplicas > 0` 分类 |
| 探针异常 | Pod 诊断能给 PodNotReady，但探针类型不细 | 新增事件解析：`Unhealthy` message 区分 Startup/Liveness/Readiness；结合 container ready/restart/lastState |
| StatefulSet/DaemonSet 版本进度 | 当前只列表 | 以自身为控制器，用 `status.updatedReplicas`、`readyReplicas`、`currentRevision/updateRevision` 判断 |

### 4.3 工程缺口

- `scripts/huawei_cloud/cce.py` 和 `cce_k8s.py` 存在功能重叠；dispatcher 当前仍调用 `cce.py`，不要在本次设计中顺手大搬迁。
- `get_kubernetes_deployments` 重复 K8s client 初始化逻辑，后续新增脚本宜复用 `cce_k8s._setup_k8s_client` 或抽取公共 helper，避免继续复制 50 行证书逻辑。
- Manifest 生成器只能读取 `ACTION_SPECS` 必填字段；新增 action 的可选参数要在 `SKILL.md` / references 中写清楚。
- `validate_skills.py` 的 `PHASE_ONE_SKILLS` 是固定集合；新增 skill 需要同步更新测试或将其定义改为更开放的阶段集合。

## 5. 新增工具设计

建议新增两个只读 action，而不是把所有能力塞进现有 `huawei_workload_diagnose`。

### 5.1 `huawei_workload_rollout_diagnose`

**定位**: 面向发布失败和副本不可用的主入口。

**必填参数**:

- `region`
- `cluster_id`
- `namespace`
- `kind`: `Deployment` / `StatefulSet` / `DaemonSet`
- `name`

**可选参数**:

- `include_pod_diagnosis`: 默认 `true`
- `include_logs`: 默认 `true`，透传给 Pod 诊断
- `include_metrics`: 默认 `false`
- `event_limit`: 默认 `500`
- `max_pods`: 默认 `20`
- `hours`: 默认 `1`
- `label_selector`: 可选；不传则由 Workload `spec.selector.matchLabels` 生成

**输出要点**:

- `summary.status`: `control_plane_not_observed | new_version_not_created | rollout_blocked | replicas_unavailable | probe_failure | healthy | inconclusive`
- `workload`: 完整摘要，含 generation check。
- `version`: Deployment 下 NewRS/OldRS；StatefulSet/DaemonSet 下 controller 自身版本进度。
- `funnel`: desired/current/updated/ready/available/unavailable 各层对比。
- `events`: 清洗后的 Workload/RS/Pod 事件时间线。
- `pod_diagnosis`: NewRS 或新版本异常 Pod 的诊断结果。
- `top_causes`: Top3 根因，带证据和置信度。
- `handoff`: 建议转交的 skill，例如 `pod-failure-diagnoser`、`node-failure-diagnoser`、`network-failure-diagnoser`、`auto-remediation-runner`。

### 5.2 `huawei_get_workload_rollout_context`

**定位**: 只采集元数据，不做根因判断，方便排查或测试。

**必填参数**:

- `region`
- `cluster_id`
- `namespace`
- `kind`
- `name`

**可选参数**:

- `event_limit`
- `label_selector`

**输出要点**:

- 原始但已 JSON 化的 `workload`、`replicasets`、`pods`、`events`。
- `event_filter`: UID 集合数量、过滤前/过滤后事件数。
- `warnings`: selector 缺失、RBAC 不足、事件 UID 缺失等。

这个工具让主诊断逻辑更容易单测：先测 context 采集，再测诊断分类。

## 6. 元数据采集算法

入口参数：`region`、`cluster_id`、`namespace`、`kind`、`name`。

1. 读取 Workload：
   - Deployment: `AppsV1Api.read_namespaced_deployment`
   - StatefulSet: `read_namespaced_stateful_set`
   - DaemonSet: `read_namespaced_daemon_set`
2. 解析 selector：
   - 优先 `spec.selector.match_labels`
   - 转换为 `k=v,k2=v2` 的 label selector 字符串。
   - 如用户传入 `label_selector`，记录覆盖来源。
3. List Pods：
   - `CoreV1Api.list_namespaced_pod(namespace, label_selector=selector)`
   - Pod 必须返回 `metadata.uid`、labels、ownerReferences、conditions、phase、containerStatuses、initContainerStatuses。
4. Deployment 专属：List ReplicaSets：
   - `AppsV1Api.list_namespaced_replica_set(namespace, label_selector=selector)`
   - 返回 revision、uid、ownerReferences、spec/status replicas、available/ready replicas。
   - 仅把 ownerReferences 指向目标 Deployment UID 的 RS 纳入版本判断；selector 只是第一层过滤。
5. List Events：
   - 用 namespaced event list 或 `field_selector=involvedObject.namespace=<Namespace>`。
   - 事件必须返回 `involvedObject.uid`。
6. 清洗 Events：
   - 构建 UID 集合：`{workload.uid} ∪ {rs.uid} ∪ {pod.uid}`。
   - 仅保留 `event.involvedObject.uid in uid_set` 的事件。
   - 事件时间取 `eventTime`、`lastTimestamp`、`metadata.creationTimestamp` 中最新可用字段。
   - 按时间戳倒序排列。

## 7. 诊断决策树

### Step 1: 控制面协同校验

断言：

```text
if workload.status.observedGeneration < workload.metadata.generation:
    status = control_plane_not_observed
```

输出终点 A：控制面未观察到最新 spec，建议下钻：

- kube-controller-manager / apiserver 限流或异常。
- 集群控制面压力、AOM 告警、事件堆积。
- RBAC/准入 webhook 卡顿仅作为可能分支，需证据支持。

### Step 2: 版本锁定

Deployment：

1. 从 RS 中读取 annotation `deployment.kubernetes.io/revision`。
2. revision 最大且 ownerReferences 指向目标 Deployment 的 RS 标记为 `NewRS`。
3. 其余同 owner 的 RS 标记为 `OldRS`。
4. NewRS Pods 通过 ownerReferences.uid 或 ownerReferences.name 归属。

StatefulSet / DaemonSet：

1. 工作负载自身作为控制器。
2. 用 `updatedReplicas`、`readyReplicas`、`currentRevision`、`updateRevision` 判断版本进度。
3. Pod 新旧版本可通过 `controller-revision-hash`、labels 或 ownerReferences 归属。

### Step 3: 滚动升级与副本数漏斗

#### 3.1 新版本无法派生

条件：

- Deployment: `NewRS.spec.replicas > 0 and NewRS.status.replicas == 0`
- 或 NewRS 关联 Pod 数量为 0。

动作：

- 在清洗后的 Event 树里检索 `involvedObject.uid == NewRS.uid` 且 `type == Warning`。
- 命中 `FailedCreate` 时输出终点 B：配额超限、准入拦截、LimitRange、ResourceQuota、PodSecurity、镜像策略、webhook 超时等。

#### 3.2 Pod 停留在非 Ready

条件：

- NewRS / 新版本 Pod 数量大于 0。
- `readyReplicas < expectedReady` 或存在 `Ready=False` / `ContainersReady=False`。

动作：

- 对异常 Pod 调用 `huawei_pod_failure_diagnose`，限定 `pod_name` 或由主工具内部调用 `pod_diagnosis._diagnose_pod`。
- 保持 Pod 状态机如下：

```text
Pod Phase
├─ Pending
│  ├─ PodScheduled=False -> FailedScheduling / 配额 / 亲和性 / 污点 / 节点资源
│  └─ PodScheduled=True  -> FailedMount / FailedAttachVolume / Sandbox / CNI
└─ Running
   ├─ container Waiting  -> ImagePullBackOff / CrashLoopBackOff / CreateContainerConfigError
   └─ Running but NotReady
      ├─ Unhealthy StartupProbe
      ├─ Unhealthy LivenessProbe
      └─ Unhealthy ReadinessProbe
```

#### 3.3 旧版本阻塞或可用副本约束

需要补充判断：

- Deployment `maxUnavailable=0` 且 NewRS Pod 不 Ready，OldRS 不会继续缩容，这是正常保护，不应误判控制面异常。
- Deployment `progressDeadlineSeconds` 超时且 condition `Progressing=False, reason=ProgressDeadlineExceeded`，应优先输出 rollout timeout。
- `minReadySeconds` 未满足时，Pod Ready 但 availableReplicas 不增长，应输出等待窗口说明。
- PDB 主要影响驱逐，不直接阻塞 Deployment 创建 Pod；只有涉及 drain/节点维护时作为下钻。

## 8. 根因分类规则

| 分类 | 主要信号 | 证据 |
| --- | --- | --- |
| `ControlPlaneNotObserved` | observedGeneration < generation | workload metadata/status |
| `ReplicaSetCreateBlocked` | NewRS 期望 > 0 但实际 0；RS Warning FailedCreate | NewRS spec/status + RS events |
| `QuotaOrAdmissionRejected` | FailedCreate message 包含 quota/admission/forbidden/denied/limitrange/webhook | RS events |
| `SchedulingBlocked` | Pending + PodScheduled=False + FailedScheduling | Pod conditions + events |
| `StorageMountBlocked` | Pending + FailedMount/FailedAttachVolume | Pod events + PVC/PV |
| `ImagePullBlocked` | ImagePullBackOff/ErrImagePull | Pod container state + events |
| `CrashLoopOrAppExit` | CrashLoopBackOff / restart storm / exit code | Pod diagnosis + previous logs |
| `ContainerCommandNotFound` | StartError/FailedStart 中出现 `exec: "...": executable file not found in $PATH` | Pod last termination + events |
| `OOMKilled` | lastState OOMKilled / exit 137 / memory spike | Pod diagnosis + metrics |
| `ProbeFailure` | Running but NotReady + Unhealthy probe events | Pod conditions + events + container ready |
| `RolloutTimeout` | Deployment condition ProgressDeadlineExceeded | workload conditions |
| `MinReadySecondsWaiting` | Ready Pod 未进入 available，minReadySeconds 未满足 | workload spec + timestamps |
| `HealthyOrConverging` | updated/ready/available 达预期或仍在合理窗口 | workload status |

## 9. Skill 内容设计

### 9.1 `SKILL.md`

保持精简，建议包含：

- 触发场景：发布失败、滚动升级卡住、副本不满足、工作负载 unavailable、探针异常、Deployment/StatefulSet/DaemonSet rollout。
- 必要参数：`region`、`cluster_id`、`namespace`、`kind`、`name`。
- 推荐 action：首选 `huawei_workload_rollout_diagnose`，只取元数据用 `huawei_get_workload_rollout_context`。
- Pod 异常下钻：复用 `huawei_pod_failure_diagnose`。
- 风险约束：只读诊断，不扩缩容、不删除、不重启；恢复动作转交 `auto-remediation-runner`。

### 9.2 references

建议新增：

- `references/workflow.md`: 本文第 6、7 节的精简版运行流程。
- `references/output-schema.md`: 输出 JSON schema 示例。
- `references/risk-rules.md`: 只读边界、恢复动作交接规则。

### 9.3 skill-profile.yaml

初版建议工具：

```yaml
tools:
  - huawei_workload_rollout_diagnose
  - huawei_get_workload_rollout_context
  - huawei_pod_failure_diagnose
  - huawei_get_cce_pods
  - huawei_get_cce_events
  - huawei_get_pod_logs
  - huawei_get_cce_pod_metrics
  - huawei_get_cce_pod_metrics_topN
  - huawei_get_cce_pvcs
  - huawei_get_cce_pvs
  - huawei_node_diagnose
  - huawei_network_diagnose
```

不放 `huawei_scale_cce_workload`、`huawei_resize_cce_workload`、`huawei_delete_cce_workload`，避免诊断 skill 携带高风险动作。

## 10. 脚本实现建议

新增文件：

- `scripts/huawei_cloud/workload_rollout_diagnosis.py`

建议内部函数：

- `_setup_apps_core_clients(...)`: 建议复用或迁移 `cce_k8s._setup_k8s_client`。
- `_read_workload(kind, name, namespace)`
- `_selector_from_match_labels(match_labels)`
- `_list_related_pods(namespace, selector)`
- `_list_related_replicasets(namespace, selector, workload_uid)`
- `_list_namespace_events(namespace, limit)`
- `_serialize_workload(obj, kind)`
- `_serialize_replicaset(rs)`
- `_serialize_pod(pod)`: 可复用 `cce.py` 里的 `_k8s_container_status` 等 helper，或将 helper 提到公共模块。
- `_serialize_event(event)`
- `_filter_events_by_uid(events, uid_set)`
- `_pick_new_rs(replicasets)`
- `_classify_rollout(context)`
- `_diagnose_abnormal_pods(context, include_logs, include_metrics)`
- `get_workload_rollout_context(...)`
- `workload_rollout_diagnose(...)`

Dispatcher：

- 新增 `_get_workload_rollout_context_action(params)`
- 新增 `_workload_rollout_diagnose_action(params)`
- `ACTION_SPECS` 注册两个 action。

测试：

- `scripts/test_workload_rollout_diagnosis.py`
- 覆盖 NewRS 选择、Event UID 清洗、Generation Check、FailedCreate、Probe Unhealthy、StatefulSet updatedReplicas 未满足。
- `scripts/test_modular_dispatch.py` 增加 action 注册与异常处理。
- `scripts/test_skill_profiles.py` 的高风险动作规则保持通过。

## 11. 输出结构草案

```json
{
  "success": true,
  "action": "workload_rollout_diagnose",
  "target": {
    "region": "cn-north-4",
    "cluster_id": "cluster-id",
    "namespace": "default",
    "kind": "Deployment",
    "name": "api"
  },
  "summary": {
    "status": "rollout_blocked",
    "headline": "Deployment api 最新版本已有 Pod，但 readyReplicas 未达预期",
    "expected_replicas": 4,
    "ready_replicas": 2,
    "top_cause": "ProbeFailure"
  },
  "generation_check": {
    "generation": 18,
    "observed_generation": 18,
    "observed": true
  },
  "version": {
    "strategy": "DeploymentReplicaSet",
    "new_rs": {
      "name": "api-66c9b7d9f",
      "uid": "rs-uid",
      "revision": 12,
      "spec_replicas": 4,
      "status_replicas": 4,
      "ready_replicas": 2
    },
    "old_rs": []
  },
  "funnel": [
    {"layer": "workload_desired", "expected": 4, "actual": 4, "status": "pass"},
    {"layer": "new_rs_created", "expected": 4, "actual": 4, "status": "pass"},
    {"layer": "new_pods_ready", "expected": 4, "actual": 2, "status": "fail"}
  ],
  "events": {
    "filtered_count": 6,
    "timeline": []
  },
  "pod_diagnosis": {},
  "top_causes": [
    {
      "rank": 1,
      "type": "ProbeFailure",
      "confidence": 0.88,
      "evidence": [],
      "recommendation": []
    }
  ],
  "handoff": [
    {
      "skill": "pod-failure-diagnoser",
      "reason": "需要继续查看异常 Pod previous/current logs"
    }
  ],
  "warnings": []
}
```

## 12. 实施顺序

1. 新增 `workload_rollout_diagnosis.py`，先实现纯函数和单元测试 fixture，不接真实云。
2. 实现 K8s 采集函数，补齐 workload/rs/pod/event 序列化字段。
3. 注册 dispatcher action，并补测试。
4. 新增 `skills/workload-failure-diagnoser` 的 `SKILL.md`、profile、references 和 scripts 软链。
5. 运行 `generate_manifests.py` 更新 manifest。
6. 更新 `skills/_catalog/skill-index.md`。
7. 运行静态校验和新增单测。

## 13. 需要特别避免的坑

- 不要用 Pod 名称前缀判断 Deployment 版本归属，优先用 ownerReferences.uid。
- 不要直接把 namespace 下所有 Warning Events 当证据，必须按 UID 清洗。
- 不要在工作负载诊断里重复实现 CrashLoop/ImagePull/OOM 的日志分析，复用 Pod 诊断。
- 不要把恢复动作放入本 skill profile；扩容、resize、删除、drain、reboot 都属于 `auto-remediation-runner`。
- 不要因为 `availableReplicas < replicas` 就直接判故障，需考虑 `minReadySeconds` 和 rollout 合理收敛窗口。
- 不要把 `observedGeneration` 缺失当成 0；不同资源和旧版本 Kubernetes 可能为空，输出 `inconclusive` 并给 warning。

## 14. 当前结论

当前仓库已经具备 60% 左右可复用基础，尤其是 Pod 诊断、日志、指标、节点/网络下钻和报告能力。真正需要补的是 **工作负载 rollout 元数据采集器** 与 **发布漏斗判定器**。建议后续实现以两个新增只读 action 为核心：先做 `huawei_get_workload_rollout_context`，再做 `huawei_workload_rollout_diagnose`，最后包装成独立 skill。
