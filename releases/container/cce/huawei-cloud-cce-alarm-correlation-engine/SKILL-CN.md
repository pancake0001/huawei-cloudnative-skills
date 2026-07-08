---
name: alarm-correlation-engine
description: 华为云 AOM 告警关联分析技能，支持查询 active/history 告警、当前活跃告警、告警去重归并、严重级别分组、突发/常态告警识别，以及告警规则查询、创建、修改、删除、动作规则和静默规则核对。
---

# 华为云 AOM 告警关联分析

华为云 AOM 告警关联分析技能，用于把 CCE 相关告警从原始事件流整理成可行动的告警线索。核心原则是同时考虑 active 和 history，避免漏掉已经恢复但影响诊断的资源类告警。

> **执行方式：本技能仍通过 `scripts/huawei-cloud.py` 统一入口执行，但入口内部使用 `hcloud` 获取华为云数据。禁止在技能外绕过 dispatcher 直接调用 SDK、curl IAM、openstack 或手写签名 API。**

## ⛔ 安全约束

### 告警规则变更二次确认机制

> **本技能允许查询、创建、修改和删除 AOM 告警规则，并支持删除 AOM 通知动作规则；其中创建、修改和删除类操作必须携带 `confirm=true` 才会真正执行，否则仅返回预览和确认提示。**

#### 需二次确认的操作列表

#### 风险等级定义

| 等级 | 含义 | 执行建议 |
|------|------|---------|
| R3 | 无风险只读操作 | 可自动执行 |
| R2 | 低风险变更，例如创建监控配置，不删除资源、不扩容、不直接增加费用 | 先预览；用户要求变更时再执行 |
| R1 | 有风险操作，例如类似重启影响、停用保护、可能增加费用或降低可观测性的变更 | 必须显式确认并携带 `confirm=true` |
| R0 | 致命级别操作，例如删除集群、应用，或删除影响面较大的通知/监控保护 | 禁止自动执行；需要明确确认、影响评估和回滚方案 |

| 工具 | 操作类型 | 风险等级 | 说明 |
|------|---------|---------|------|
| `huawei_create_aom_alarm_rule` | 创建 | R2 | 创建新的 AOM 告警规则，可能引入新的告警通知 |
| `huawei_create_aom_event_alarm_rule` | 创建 | R2 | 创建新的 AOM 事件告警规则，可能引入新的事件告警通知 |
| `huawei_configure_cce_aom_alarm_rules` | 批量创建 | R2 | 按 AOM 云侧 `CCE模板` 为指定集群批量创建告警规则；用户提供 SMN 主题参数时可自动创建集群通知动作规则 |
| `huawei_update_aom_alarm_rule` | 修改 | R1 | 修改 AOM 告警规则阈值、开关、通知动作、描述等配置 |
| `huawei_delete_aom_alarm_rule` | 删除 | R0 | 删除 AOM 告警规则，可能导致后续告警无法触发 |
| `huawei_disable_aom_alarm_rule` | 停用 | R1 | 停用 AOM 告警规则，可能导致相关告警不再触发 |
| `huawei_enable_aom_alarm_rule` | 启用 | R2 | 启用 AOM 告警规则，可能恢复并触发告警通知 |
| `huawei_delete_aom_action_rule` | 删除 | R0 | 删除 AOM 通知动作规则，可能导致告警无法发送通知 |

#### 工作流程

**第一步：预览操作** - 不带 `confirm` 参数调用
```bash
# 示例：预览创建告警规则
python3 huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  metric_name=cpuUsage \
  namespace=PAAS.NODE \
  comparison_operator='>' \
  threshold=80 \
  period=60 \
  evaluation_periods=3 \
  statistic=average \
  alarm_level=2

```

返回：操作预览、目标规则、规则字段和确认示例，不执行真实创建。

**第二步：确认执行** - 携带 `confirm=true` 参数再次调用
```bash
# 示例：确认创建告警规则
python3 huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  metric_name=cpuUsage \
  namespace=PAAS.NODE \
  comparison_operator='>' \
  threshold=80 \
  period=60 \
  evaluation_periods=3 \
  statistic=average \
  alarm_level=2 \
  confirm=true
```

#### 禁止动作

| 动作 | 说明 |
|------|------|
| 创建/更新动作规则 | 不创建、更新通知动作规则 |
| 修改静默规则 | 不创建、更新、删除静默规则 |
| 执行恢复动作 | 不扩缩容、不重启、不 drain、不删除工作负载或节点 |
| 修改集群资源 | 不变更 CCE、ECS、ELB、EIP、VPC、安全组等资源 |

如果分析结果需要扩缩容、重启、drain、漏洞状态变更或其它恢复动作，必须只输出建议，并转交 `auto-remediation-runner` 进行预览、确认和执行后验证。

### 认证信息安全

✅ **本技能严格遵守以下安全规则：**

1. **禁止持久化存储认证信息** - 从不将 AK/SK、Token、证书等敏感认证信息保存到磁盘文件
2. **禁止长期内存缓存** - AK/SK 仅在当前 hcloud 调用过程中存在于内存，调用结束后释放
3. **不做自定义项目 ID 缓存** - project/profile 解析交给 hcloud 处理
4. **禁止日志泄露** - 不在任何日志、响应输出或错误信息中包含 AK/SK 等敏感信息
5. **输出脱敏** - 对外输出只展示告警、资源和规则信息，不展示认证凭证

AK/SK 支持以下三种方式使用，优先级顺序为：
- 通过每次调用参数 `ak` / `sk` 传入（最高优先级，仅本次调用有效）
- 已配置的 hcloud profile（推荐）
- 通过环境变量 `HUAWEI_AK` / `HUAWEI_SK` 传入（仅在没有 hcloud profile 时作为兜底）

---

## 前置条件

### hcloud 配置

**方式一：使用 hcloud profile（推荐）**
```bash
hcloud configure init
```

**方式二：环境变量**
```bash
export HUAWEI_AK="your-access-key-id"
export HUAWEI_SK="your-secret-access-key"
```

**方式三：每次调用参数传入**
在每次脚本调用时传入 `ak` 和 `sk` 参数（不推荐用于生产环境）。

### 运行依赖

- Python 3.8+
- `hcloud` CLI 7.2.2+，并且可在 `PATH` 中直接执行
- 本机已通过 `hcloud configure` 配置可用 profile；dispatcher 依赖本机 hcloud 配置完成华为云认证以及 project/region 解析

### IAM 权限策略

确保 IAM 用户具有以下最小权限：

| 权限 | 说明 |
|------|------|
| `aom:event:list` | 查询 AOM 告警事件 |
| `aom:alarmRule:list` | 查询 AOM 告警规则 |
| `aom:alarmRule:create` | 创建 AOM 告警规则 |
| `aom:alarmRule:update` | 修改 AOM 告警规则 |
| `aom:alarmRule:delete` | 删除 AOM 告警规则 |
| `aom:actionRule:list` | 查询 AOM 动作规则 |
| `aom:muteRule:list` | 查询 AOM 静默规则 |

---

## 工具分类

### 告警查询与归并

| 工具 | 功能 | 风险等级 | 集群过滤 | 参数 |
|------|------|---------|---------|------|
| `huawei_list_aom_alarms` | 查询 active + history 告警并合并去重 | R3 | 支持 `cluster_id` | `region` |
| `huawei_list_aom_current_alarms` | 查询当前活跃告警 | R3 | 支持 `cluster_id` | `region` |
| `huawei_analyze_aom_alarms` | 对 active + history 告警做去重、分级和突发/常态识别 | R3 | 支持 `cluster_id` | `region` |

**参数说明：**
- `region` (required): 华为云区域，例如 `cn-north-4`
- `cluster_id` (optional): CCE 集群 ID；传入后只返回该集群相关告警
- `ak` (optional): Access Key ID，显式工具入参优先级最高
- `sk` (optional): Secret Access Key，显式工具入参优先级最高
- `project_id` (optional): 华为云项目 ID；显式入参优先，其次使用当前 hcloud profile/project 配置，最后才使用环境变量兜底

**使用示例：**
```bash
# 查询区域内 active + history 告警
python3 huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4

# 查询指定集群 active + history 告警
python3 huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4 \
  cluster_id=xxx

# 查询指定集群当前活跃告警
python3 huawei-cloud.py huawei_list_aom_current_alarms \
  region=cn-north-4 \
  cluster_id=xxx

# 分析指定集群告警，输出突发、关注、常态分组
python3 huawei-cloud.py huawei_analyze_aom_alarms \
  region=cn-north-4 \
  cluster_id=xxx
```

---

### 告警规则管理

**事件告警创建约束：**
- 使用 `huawei_create_aom_event_alarm_rule` 创建事件告警时，`event_name` 必须优先参考 `references/cce-event-list.md` 中的事件列表与命名格式（推荐 `中文事件描述##事件名称`）。
- 创建事件告警时，默认启用告警降噪（`route_group_enable=true`）。

**指标告警创建约束：**
- 使用 `huawei_create_aom_alarm_rule` 创建指标告警时，PromQL/指标口径与阈值应优先参考 `references/cce-prometheus-metric-alarms.md`。

| 工具 | 功能 | 风险等级 | 需确认 | 参数 |
|------|------|---------|-------|------|
| `huawei_list_aom_alarm_rules` | 查询 AOM 告警规则 | R3 | 否 | `region`；可选 `cluster_id`, `cluster_name` |
| `huawei_resolve_cce_aom_prom_instance` | 解析目标集群 AOM Prometheus 实例 | R3 | 否 | `region`, `cluster_id` |
| `huawei_create_aom_alarm_rule` | 创建 AOM 告警规则 | R2 | **是** | `region`, `rule_name`, `metric_name`, `namespace`, `comparison_operator`, `threshold`, `period`, `evaluation_periods`, `statistic`, `alarm_level` |
| `huawei_create_aom_event_alarm_rule` | 创建 AOM 事件告警规则 | R2 | **是** | `region`, `cluster_id`, `rule_name`, `event_name` |
| `huawei_configure_cce_aom_alarm_rules` | 使用 AOM `CCE模板` 一键批量创建 CCE 推荐告警规则 | R2 | **是** | `region`, `cluster_id` |
| `huawei_update_aom_alarm_rule` | 修改 AOM 告警规则 | R1 | **是** | `region`, `rule_name` |
| `huawei_delete_aom_alarm_rule` | 删除 AOM 告警规则 | R0 | **是** | `region`, `rule_name` |
| `huawei_disable_aom_alarm_rule` | 停用 AOM 告警规则 | R1 | **是** | `region`, `rule_id` |
| `huawei_enable_aom_alarm_rule` | 启用 AOM 告警规则 | R2 | **是** | `region`, `rule_id` |
| `huawei_list_aom_action_rules` | 查询 AOM 告警动作规则 | R3 | 否 | `region`, `enterprise_project_id` |
| `huawei_delete_aom_action_rule` | 删除 AOM 告警动作规则（通知规则） | R0 | **是** | `region`, `rule_name` |
| `huawei_list_aom_mute_rules` | 查询 AOM 静默规则 | R3 | 否 | `region` |

**参数说明：**
- `region` (required): 华为云区域
- `cluster_id` (optional for list alarm rules): CCE 集群 ID；传入后只返回规则内容中关联该集群 ID 的告警规则
- `cluster_name` (optional for list alarm rules): CCE 集群名称；传入后只返回规则内容中关联该集群名称的告警规则
- `metric_name` (required for create): 指标名称
- `namespace` (required for create): 指标命名空间
- `comparison_operator` (required for create): 阈值比较符，例如 `>`、`<`、`>=`、`<=`
- `threshold` (required for create): 告警阈值
- `period` (required for create): 统计周期，单位秒
- `evaluation_periods` (required for create): 连续触发周期数
- `statistic` (required for create): 统计方式，例如 `average`、`max`、`min`
- `alarm_level` (required for create): 告警级别
- `rule_name` (required for update): 告警规则名称，AOM 更新接口通过规则名称定位规则
- `rule_name` (required for delete): 告警规则名称
- `rule_id` (required for disable): 需要停用的告警规则 ID
- `rule_id` (required for enable): 需要启用的告警规则 ID
- `rule_name` (required for delete action rule): AOM 通知动作规则名称
- `enterprise_project_id` (optional for list action rules): 企业项目范围，默认 `all_granted_eps`
- `bind_notification_rule_id` (optional for create/configure): 绑定已有 AOM 通知规则 ID/名称；未传时批量创建会尝试自动创建 `auto-cluster-{cluster_id}`，但必须由用户提供 SMN 订阅主题参数
- `notification_topic_urn` (optional for configure): 自动创建 `auto-cluster-{cluster_id}` 时必填，SMN 主题 URN
- `notification_topic_name` (optional for configure): 自动创建 `auto-cluster-{cluster_id}` 时必填，SMN 主题名称
- `notification_topic_display_name` (optional for configure): 自动创建通知动作规则时使用的 SMN 主题显示名
- `notification_user_name` (optional for configure): 自动创建通知动作规则时记录的用户名
- `alarm_template_id` (optional for configure): 批量创建使用的 AOM 告警模板 ID，默认使用云侧 CCE 模板 `at0000000000000000cce001`
- `rule_name_prefix` (optional for configure): 批量创建规则名前缀，默认使用 `cluster_id`
- `include_metric_alarms` (optional for configure): 是否创建 Prometheus 指标类模板，默认 `true`
- `include_event_alarms` (optional for configure): 是否创建 CCE 事件类模板，默认 `true`
- `alarm_items` (optional for configure): 逗号分隔的告警项白名单，仅创建指定模板或事件名
- `skip_existing` (optional for configure): 确认执行时跳过集群下已有同名规则，默认 `true`
- `prom_instance_id` (optional for configure): 可选覆盖值；批量创建会默认从目标集群 `cie-collector` 插件配置自动解析 AOM Prometheus 实例 ID
- `fields` (optional): 创建规则时的额外 JSON 字段，例如 `{"unit":"%","is_turn_on":true}`
- `updates` (optional): JSON 格式的批量更新字段，例如 `{"threshold":"80","is_turn_on":true}`
- `confirm` (optional): 创建、修改或删除时必须显式设置为 `true` 才会执行
- `ak` (optional): Access Key ID，显式工具入参优先级最高
- `sk` (optional): Secret Access Key，显式工具入参优先级最高
- `project_id` (optional): 华为云项目 ID；显式入参优先，其次使用当前 hcloud profile/project 配置，最后才使用环境变量兜底

**使用示例：**
```bash
# 查询告警规则
python3 huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4

# 查询指定集群相关的告警规则
python3 huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4 \
  cluster_id=<cluster-id>

# 预览创建告警规则，不执行
python3 huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  metric_name=cpuUsage \
  namespace=PAAS.NODE \
  comparison_operator='>' \
  threshold=80 \
  period=60 \
  evaluation_periods=3 \
  statistic=average \
  alarm_level=2

# 确认创建告警规则
python3 huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  metric_name=cpuUsage \
  namespace=PAAS.NODE \
  comparison_operator='>' \
  threshold=80 \
  period=60 \
  evaluation_periods=3 \
  statistic=average \
  alarm_level=2 \
  confirm=true

# 预览一键批量创建 CCE 推荐告警规则，不执行
python3 huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 \
  cluster_id=<cluster-id>

# 确认批量创建，并绑定已有通知规则
python3 huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  bind_notification_rule_id=auto-cluster-xxx \
  confirm=true

# 确认批量创建，并使用用户提供的 SMN 主题自动创建集群通知动作规则
python3 huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  notification_topic_name=<smn-topic-name> \
  notification_topic_urn=<smn-topic-urn> \
  confirm=true

# 预览修改告警规则，不执行
python3 huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  threshold=80

# 确认修改告警规则
python3 huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  threshold=80 \
  confirm=true

# 预览删除告警规则，不执行
python3 huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=xxx

# 确认删除告警规则
python3 huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=xxx \
  confirm=true

# 预览停用告警规则，不执行
python3 huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx

# 确认停用告警规则
python3 huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx \
  confirm=true

# 预览启用告警规则，不执行
python3 huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx

# 确认启用告警规则
python3 huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx \
  confirm=true


# 查询动作规则
python3 huawei-cloud.py huawei_list_aom_action_rules \
  region=cn-north-4

# 预览删除动作规则，不执行
python3 huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 \
  rule_name=xxx

# 确认删除动作规则
python3 huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 \
  rule_name=xxx \
  confirm=true

# 查询静默规则
python3 huawei-cloud.py huawei_list_aom_mute_rules \
  region=cn-north-4
```

### 集群告警巡检

| 工具 | 功能 | 风险等级 | 集群过滤 | 参数 |
|------|------|---------|---------|------|
| `huawei_aom_alarm_inspection` | 对指定 CCE 集群做 AOM 告警巡检并输出风险项 | R3 | `cluster_id` 必填 | `region`, `cluster_id` |

**参数说明：**
- `region` (required): 华为云区域
- `cluster_id` (required): CCE 集群 ID
- `ak` (optional): Access Key ID，显式工具入参优先级最高
- `sk` (optional): Secret Access Key，显式工具入参优先级最高
- `project_id` (optional): 华为云项目 ID；显式入参优先，其次使用当前 hcloud profile/project 配置，最后才使用环境变量兜底

**使用示例：**
```bash
# 巡检指定集群 AOM 告警
python3 huawei-cloud.py huawei_aom_alarm_inspection \
  region=cn-north-4 \
  cluster_id=xxx
```

---

## 推荐工作流

### 场景一：查询指定集群告警

1. 明确 `region` 和 `cluster_id`
2. 调用 `huawei_list_aom_alarms` 查询 active + history 合并结果
3. 按告警类型、资源对象、状态和严重级别归并
4. 输出当前触发中告警、已恢复但仍需关注的历史告警、Top 资源对象

### 场景二：告警风暴或重复告警降噪

1. 调用 `huawei_analyze_aom_alarms`
2. 将原始告警归并为唯一告警组
3. 区分突发告警、关注告警和常态告警
4. 输出噪音削减比例、Top 关注项和推荐诊断 skill

### 场景三：查询、创建、修改或删除告警规则

1. 调用 `huawei_list_aom_alarm_rules` 查询告警规则
2. 需要创建时先调用 `huawei_create_aom_alarm_rule` 获取预览
3. 需要修改时先调用 `huawei_update_aom_alarm_rule` 获取预览
4. 需要删除时先调用 `huawei_delete_aom_alarm_rule` 获取预览
5. 需要停用时先调用 `huawei_disable_aom_alarm_rule` 获取预览
6. 用户明确确认后再次调用并携带 `confirm=true`
7. 创建、修改、删除或停用后再次调用 `huawei_list_aom_alarm_rules` 验证规则状态

### 场景四：确认告警是否被动作规则或静默影响

1. 调用 `huawei_list_aom_action_rules` 查询通知动作规则
2. 如需删除失效动作规则，先调用 `huawei_delete_aom_action_rule` 预览，再由用户确认后携带 `confirm=true` 执行
3. 调用 `huawei_list_aom_mute_rules` 查询静默规则
4. 判断是否存在动作规则异常或静默导致的通知缺失

### 场景五：集群巡检入口

1. 调用 `huawei_aom_alarm_inspection`
2. 汇总指定集群告警总数、触发中数量、已恢复数量和严重级别分布
3. 输出资源告警列表和需要进一步诊断的对象
4. 如涉及 Pod、Node、Network 问题，转交对应诊断 skill

---

## 输出要求

### 告警摘要

输出必须包含：

| 字段 | 说明 |
|------|------|
| `region` | 查询区域 |
| `cluster_id` | 如用户指定集群，则输出集群 ID |
| `total_count` | 告警总数 |
| `firing_count` | 当前触发中告警数量 |
| `resolved_count` | 已恢复告警数量 |
| `severity_stats` | 严重级别分布 |
| `type_stats` | 按告警类型归并统计 |

### 资源线索

对 CCE 告警，优先输出以下资源维度：

| 字段 | 说明 |
|------|------|
| `cluster_name` | 集群名称 |
| `namespace` | 命名空间 |
| `pod_name` | Pod 名称 |
| `resource_kind` | 资源类型 |
| `event_name` | 告警名称 |
| `message` | 告警消息 |

### 推荐诊断 skill

| 告警特征 | 推荐 skill |
|----------|------------|
| `CrashLoopBackOff`、`BackOffStart`、`FailedStart`、`ImagePullBackOff` | `pod-failure-diagnoser` |
| `FailedScheduling`、`Insufficient cpu`、`Insufficient memory` | `pod-failure-diagnoser` 或 `node-failure-diagnoser` |
| `NodeNotReady`、节点资源压力、NPD 事件 | `node-failure-diagnoser` |
| `Ingress 502/504`、Service 不通、ELB 异常 | `network-failure-diagnoser` |
| 多类告警同时出现且影响业务 | `root-cause-analyzer` |
| 需要扩缩容、重启、drain 等恢复动作 | `auto-remediation-runner` |

---

## References

- 告警归并步骤读 `references/workflow.md`
- 只读边界和误报处理读 `references/risk-rules.md`
- 输出结构按 `references/output-schema.md`
- Prometheus 指标告警规则参考 `references/cce-prometheus-metric-alarms.md`
