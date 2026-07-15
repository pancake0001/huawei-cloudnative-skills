---
id: huawei-cloud-cce-alarm-correlation-engine
name: huawei-cloud-cce-alarm-correlation-engine
description: |
  面向 CCE 运维场景的华为云 AOM 告警关联分析与告警规则管理技能。
  当用户需要以下能力时使用本技能：(1) 查询 AOM 活跃告警和历史告警，(2) 分析告警去重、告警风暴、严重级别分组、突发告警和常态告警，(3) 巡检 CCE 集群告警健康状态，(4) 查询、创建、修改、删除、启用或停用 AOM 告警规则，(5) 查询或创建通知动作规则，(6) 基于云侧 CCE 告警模板批量配置或清理推荐告警规则。
  触发词：用户提到 "alarm correlation"、"AOM alarm"、"alarm rule"、"alarm storm"、"alarm inspection"、"notification rule"、"告警关联"、"AOM 告警"、"告警规则"、"告警风暴"、"通知规则" 或 "CCE 告警"。
tags: [cce, alarm-correlation, aom, observability, alarm-management]
---

# 华为云 CCE 告警关联分析引擎

## 概览

本技能用于关联分析华为云 AOM 活跃告警和历史告警，将原始告警流转换为可执行的排障线索。同时，本技能也支持通过严格的“先预览、再确认”流程管理 AOM 告警规则和通知动作规则。

**架构**：`python3 scripts/huawei-cloud.py` 调度器 -> 本机 `hcloud` (KooCLI) -> AOM/CCE/IAM 云服务操作 -> 告警查询、告警关联、告警规则管理、通知规则管理和 CCE 告警健康巡检。

> **执行方式**：所有华为云操作都必须通过技能内置 Python 调度器完成。调度器调用本机 `hcloud` CLI。禁止直接导入 SDK、手写 API 签名、curl IAM、openstack 命令，或使用任何工具之外的云访问路径。

**相关技能**：
- `huawei-cloud-cce-metric-analyzer` - CCE、AOM 和云资源指标检查
- `huawei-cloud-cce-kubernetes-event-analyzer` - Kubernetes Warning 事件分析
- `huawei-cloud-cce-pod-failure-diagnoser` - Pod 故障诊断
- `huawei-cloud-cce-node-failure-diagnoser` - Node 故障诊断
- `huawei-cloud-cce-auto-remediation-runner` - 修复动作预览与执行

**能力范围**：
- 查询 AOM 活跃告警、历史告警，以及活跃+历史合并视图
- 分析告警去重、严重级别分组、突发告警、关注告警和常态告警
- 巡检 CCE 告警健康状态，并输出后续诊断风险项
- 查询 AOM 告警规则，支持按 `cluster_id` 过滤
- 解析 CCE 集群绑定的 AOM Prometheus 实例
- 创建指标告警规则和事件告警规则
- 使用用户提供的 SMN 主题创建通知动作规则
- 基于云侧 CCE 告警模板批量配置 CCE 推荐告警规则
- 批量清理匹配云侧 CCE 告警模板的告警规则
- 修改、删除、启用和停用 AOM 告警规则
- 查询 AOM 动作规则和静默规则

**典型场景**：
- “查询这个 CCE 集群的 AOM 告警”
- “分析活跃和历史告警，看是否有告警风暴”
- “查看 `<cluster_id>` 当前配置了哪些告警规则”
- “使用这个通知规则创建 CCE 推荐告警规则”
- “清理这个集群的 CCE 模板告警规则”
- “使用这个 SMN 主题创建通知动作规则”
- “我确认后停用这个噪声告警规则”

## 前置条件

### 1. 运行依赖

- Python 3.8+，用于调度器和结果处理
- `PATH` 中可用的 hcloud (KooCLI) 7.2.2+
- 已通过 `hcloud configure` 配置本机 hcloud profile
- 首次使用前，如技能包提供环境检查脚本，应先运行检查

### 2. 认证配置

- 支持通过显式工具参数、本机 hcloud profile 或环境变量 fallback 提供华为云认证
- hcloud 调用的认证优先级：显式工具参数 > 本机 hcloud profile > 环境变量
- 需要 `project_id` 的工具会尽量内部解析：显式 `project_id` 参数优先，然后使用目标区域的 hcloud profile/IAM project 查询，最后使用环境变量 fallback

**安全规则**：
- 禁止在代码、命令、日志或回复中暴露 AK/SK、token 或任何认证派生敏感信息
- 禁止运行 `echo $HUAWEI_AK` 或 `echo $HUAWEI_SK`
- 禁止将认证信息写入文件
- 常规使用优先采用 hcloud profile
- 使用最小权限 IAM 用户

**可选环境变量 fallback**：

```bash
export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_REGION=cn-north-4
export HUAWEI_PROJECT_ID=<project-id>
export HUAWEI_SECURITY_TOKEN=<security-token>
```

### 3. IAM 权限要求

| 权限 | 用途 |
| ---- | ---- |
| `aom:event:list` | 查询 AOM 活跃告警和历史告警 |
| `aom:alarmRule:list` | 查询 AOM 告警规则 |
| `aom:alarmRule:create` | 创建 AOM 告警规则 |
| `aom:alarmRule:update` | 修改、启用或停用 AOM 告警规则 |
| `aom:alarmRule:delete` | 删除 AOM 告警规则 |
| `aom:actionRule:list` | 查询 AOM 动作/通知规则 |
| `aom:actionRule:create` | 创建 AOM 通知动作规则 |
| `aom:actionRule:delete` | 删除 AOM 通知动作规则 |
| `aom:muteRule:list` | 查询 AOM 静默规则 |
| `cce:cluster:get` | 解析 CCE 集群及其 AOM Prometheus 绑定关系 |

**权限失败处理**：

1. 展示失败操作和缺失权限。
2. 提醒用户补充对应 IAM 权限。
3. 对于变更类操作，等待用户确认权限已准备好后再继续。

## 核心命令

所有命令都使用 Python 调度器脚本：

```bash
python3 scripts/huawei-cloud.py <action> <key=value>...
```

## KooCLI命令格式标准

本技能不要求用户直接运行原始 `hcloud` 命令。所有云侧操作必须使用调度器命令格式：

```bash
python3 scripts/huawei-cloud.py <tool-name> key=value key=value
```

调度器会将工具参数转换为标准 KooCLI 调用：

```bash
hcloud <service> <operation> --cli-region=<region> --cli-output=json [--cli-jsonInput=<file>]
```

执行命令时遵循以下规则：

- 使用 `key=value` 参数；包含空格、`>`、`<`、`|`、JSON 或 PromQL 的值必须加引号。
- 不打印、不落盘 AK/SK、security token 或生成的 JSON input 文件内容。
- R2/R1/R0 工具必须先看预览输出，只有用户明确确认后才添加 `confirm=true`。
- 优先使用 hcloud profile 凭据；工具入参优先级高于 profile 和环境变量兜底。
- 安装和验证方式见 [CLI Installation Guide](references/cli-installation-guide.md)。

### 1. 告警查询与关联

```bash
# 查询区域内活跃 + 历史告警
python3 scripts/huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4

# 查询指定集群活跃 + 历史告警
python3 scripts/huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4 cluster_id=<cluster-id>

# 仅查询当前活跃告警
python3 scripts/huawei-cloud.py huawei_list_aom_current_alarms \
  region=cn-north-4 cluster_id=<cluster-id>

# 分析去重、突发、关注和常态告警分组
python3 scripts/huawei-cloud.py huawei_analyze_aom_alarms \
  region=cn-north-4 cluster_id=<cluster-id>
```

> 不能因为“没有活跃告警”就判断没有问题。诊断最近发生或已恢复的问题时，必须同时参考历史告警。

### 2. 告警规则查询

```bash
# 查询区域内所有告警规则
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4

# 查询某个 CCE 集群相关的告警规则
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>

# 解析集群 AOM Prometheus 实例
python3 scripts/huawei-cloud.py huawei_resolve_cce_aom_prom_instance \
  region=cn-north-4 cluster_id=<cluster-id>
```

`huawei_list_aom_alarm_rules` 只支持通过 `cluster_id` 进行集群过滤，不支持使用 `cluster_name` 作为过滤条件。

### 3. 通知规则

```bash
# 查询已有动作/通知规则
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules \
  region=cn-north-4

# 预览：使用 SMN 主题创建通知动作规则
python3 scripts/huawei-cloud.py huawei_create_aom_notification_action_rule \
  region=cn-north-4 rule_name=auto-cluster-xxx \
  notification_topic_name=<smn-topic-name> \
  notification_topic_urn=<smn-topic-urn>

# 确认创建
python3 scripts/huawei-cloud.py huawei_create_aom_notification_action_rule \
  region=cn-north-4 rule_name=auto-cluster-xxx \
  notification_topic_name=<smn-topic-name> \
  notification_topic_urn=<smn-topic-urn> \
  confirm=true
```

禁止自动选择通知规则。如果批量创建告警规则时缺少 `bind_notification_rule_id`，应先列出可用动作规则并等待用户明确选择，或让用户提供 SMN 主题后先创建通知规则。

### 4. 告警规则创建

```bash
# 预览：创建 CCE 模板指标告警规则
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  alarm_item=NodeCPUUsageHigherThanEightyPercent

# 确认：创建 CCE 模板指标告警规则
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  alarm_item=NodeCPUUsageHigherThanEightyPercent \
  bind_notification_rule_id=<action-rule-id> \
  confirm=true

# 预览：创建事件告警规则
python3 scripts/huawei-cloud.py huawei_create_aom_event_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  event_name="<event-name>"

# 确认：创建事件告警规则
python3 scripts/huawei-cloud.py huawei_create_aom_event_alarm_rule \
  region=cn-north-4 cluster_id=<cluster-id> \
  event_name="<event-name>" \
  bind_notification_rule_id=<action-rule-id> \
  confirm=true
```

指标告警使用 `cluster_id` + `alarm_item`、事件告警使用 `event_name` 时，都会走与批量创建一致的 CCE 模板 payload 和默认命名；只有用户明确要求自定义名称时才传 `rule_name`。单条创建确认执行时必须显式传入 `bind_notification_rule_id`，要求与批量配置 CCE 告警规则一致。事件告警规则的 `event_name` 应参考 `references/cce-event-list.md`；指标 `alarm_item` 使用 CCE 模板 alias 或规则名。

### 5. CCE 模板告警规则

```bash
# 预览：批量创建 CCE 推荐告警规则
python3 scripts/huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  bind_notification_rule_id=<action-rule-id>

# 确认：批量创建
python3 scripts/huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  bind_notification_rule_id=<action-rule-id> confirm=true

# 预览：清理某个集群的 CCE 模板告警规则
python3 scripts/huawei-cloud.py huawei_cleanup_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>

# 确认：清理
python3 scripts/huawei-cloud.py huawei_cleanup_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  delete_auto_notification_rule=true confirm=true
```

`huawei_configure_cce_aom_alarm_rules` 必须显式传入 `bind_notification_rule_id`。如果用户没有提供，不应由该工具返回或选择 `available_notification_rules`；应单独调用 `huawei_list_aom_action_rules` 并展示候选项，由用户确认。

### 6. 告警规则变更

```bash
# 预览修改
python3 scripts/huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule threshold=80

# 确认修改
python3 scripts/huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule threshold=80 confirm=true

# 预览删除
python3 scripts/huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule

# 确认删除
python3 scripts/huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule confirm=true

# 预览停用或启用
python3 scripts/huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 rule_id=<rule-id>

python3 scripts/huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 rule_id=<rule-id>
```

### 7. 动作规则和静默规则可见性

```bash
# 查询静默规则
python3 scripts/huawei-cloud.py huawei_list_aom_mute_rules \
  region=cn-north-4

# 预览删除动作规则
python3 scripts/huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 rule_name=<rule-name>
```

### 8. 集群告警巡检

```bash
python3 scripts/huawei-cloud.py huawei_aom_alarm_inspection \
  region=cn-north-4 cluster_id=<cluster-id>
```

## 风险等级

本技能同时包含只读查询工具和变更工具。变更工具必须先预览，并等待用户明确确认后才能使用 `confirm=true`。

| 等级 | 含义 | 执行要求 |
| ---- | ---- | -------- |
| R3 | 无风险只读查询或本地分析 | 可自动执行 |
| R2 | 低风险监控配置变更，例如创建告警或通知配置，不删除资源、不扩容、不直接增加费用 | 先预览；用户明确确认后执行 |
| R1 | 有风险监控变更，例如修改或停用规则，可能降低可观测性 | 先预览；需要明确确认和 `confirm=true` |
| R0 | 致命级别监控保护移除，例如删除告警规则、动作规则或批量清理 | 需要明确确认、影响评估和回滚计划后才允许 `confirm=true` |

| 工具 | 操作类型 | 风险等级 | 说明 |
| ---- | -------- | -------- | ---- |
| `huawei_list_aom_alarms` | 查询 | R3 | 查询活跃 + 历史告警，并合并去重 |
| `huawei_list_aom_current_alarms` | 查询 | R3 | 仅查询当前活跃告警 |
| `huawei_analyze_aom_alarms` | 查询 + 本地分析 | R3 | 分析告警分组、突发、关注和常态告警 |
| `huawei_aom_alarm_inspection` | 查询 + 本地分析 | R3 | 巡检集群告警健康状态 |
| `huawei_list_aom_alarm_rules` | 查询 | R3 | 查询 AOM 告警规则；支持可选 `cluster_id` |
| `huawei_resolve_cce_aom_prom_instance` | 查询 | R3 | 解析集群 AOM Prometheus 实例 |
| `huawei_list_aom_action_rules` | 查询 | R3 | 查询动作/通知规则 |
| `huawei_list_aom_mute_rules` | 查询 | R3 | 查询静默规则 |
| `huawei_create_aom_alarm_rule` | 创建 | R2 | 创建 AOM 指标告警规则 |
| `huawei_create_aom_event_alarm_rule` | 创建 | R2 | 创建 AOM 事件告警规则 |
| `huawei_create_aom_notification_action_rule` | 创建 | R2 | 使用用户提供的 SMN 主题创建通知动作规则 |
| `huawei_configure_cce_aom_alarm_rules` | 批量创建 | R2 | 使用显式已有通知动作规则创建 CCE 推荐告警规则 |
| `huawei_enable_aom_alarm_rule` | 启用 | R2 | 启用 AOM 告警规则 |
| `huawei_update_aom_alarm_rule` | 修改 | R1 | 修改 AOM 告警规则 |
| `huawei_disable_aom_alarm_rule` | 停用 | R1 | 停用 AOM 告警规则 |
| `huawei_delete_aom_alarm_rule` | 删除 | R0 | 删除 AOM 告警规则 |
| `huawei_cleanup_cce_aom_alarm_rules` | 批量删除 | R0 | 删除目标集群的 CCE 模板告警规则 |
| `huawei_delete_aom_action_rule` | 删除 | R0 | 删除通知动作规则 |

## 参数参考

### 通用参数

| 参数 | 必填/可选 | 说明 | 默认值 |
| ---- | --------- | ---- | ------ |
| `region` | 必填 | 华为云区域 | `HUAWEI_REGION` |
| `cluster_id` | 视工具而定 | CCE 集群 ID；集群级操作必填 | N/A |
| `ak` | 可选 | 显式 AK；hcloud 调用最高优先级 | profile/env fallback |
| `sk` | 可选 | 显式 SK；hcloud 调用最高优先级 | profile/env fallback |
| `project_id` | 可选 | 显式 Project ID | hcloud/IAM/env fallback |
| `confirm` | 仅变更工具 | 设为 `true` 时执行已预览的变更 | `false` |

### 告警查询参数

| 工具 | 必填 | 可选 |
| ---- | ---- | ---- |
| `huawei_list_aom_alarms` | `region` | `cluster_id`、时间窗口/过滤参数 |
| `huawei_list_aom_current_alarms` | `region` | `cluster_id`、过滤参数 |
| `huawei_analyze_aom_alarms` | `region` | `cluster_id`、时间窗口/过滤参数 |
| `huawei_aom_alarm_inspection` | `region`, `cluster_id` | 过滤参数 |

### 告警规则参数

| 工具 | 必填 | 说明 |
| ---- | ---- | ---- |
| `huawei_list_aom_alarm_rules` | `region` | 可选 `cluster_id`；不支持 `cluster_name` 过滤 |
| `huawei_create_aom_alarm_rule` | `region` | 模板模式传 `cluster_id`, `alarm_item`；手工模式传 metric 字段。确认执行必须传 `bind_notification_rule_id` |
| `huawei_create_aom_event_alarm_rule` | `region`, `cluster_id`, `event_name` | R2；确认执行必须传 `bind_notification_rule_id`；可选 `rule_name` 会覆盖模板命名 |
| `huawei_create_aom_notification_action_rule` | `region`, `rule_name`, `notification_topic_urn`, `notification_topic_name` | R2；用户必须提供主题 |
| `huawei_configure_cce_aom_alarm_rules` | `region`, `cluster_id`, `bind_notification_rule_id` | R2；用户必须明确选择通知规则 |
| `huawei_cleanup_cce_aom_alarm_rules` | `region`, `cluster_id` | R0；可选 `delete_auto_notification_rule=true` |
| `huawei_update_aom_alarm_rule` | `region`, `rule_name` | R1；可更新字段由工具支持范围决定 |
| `huawei_delete_aom_alarm_rule` | `region`, `rule_name` | R0 |
| `huawei_disable_aom_alarm_rule` | `region`, `rule_id` | R1 |
| `huawei_enable_aom_alarm_rule` | `region`, `rule_id` | R2 |

## 输出格式

完整 JSON 响应结构见 [Output Schema](references/output-schema.md)。

**关键输出字段**：
- `success`：命令是否成功
- `error`：`success=false` 时的失败原因
- `preview`：未提供 `confirm=true` 时的变更预览
- `requires_confirmation`：是否需要用户确认
- `report`：告警关联分析摘要
- `issues`：巡检风险项
- `alarms`, `rules`, `action_rules`, `mute_rules`：查询到的资源

## 工作流

详细告警关联流程见 [Workflow](references/workflow.md)。

推荐流程：

1. 读取用户提供的告警名、资源、时间窗口和严重级别。
2. 默认查询最近 1 小时，除非用户给出其他故障时间窗口。
3. 使用 `huawei_list_aom_alarms` 查询活跃 + 历史告警。
4. 使用 `huawei_analyze_aom_alarms` 分析告警分组。
5. 当怀疑通知缺失或静默影响时，查询告警规则、动作规则和静默规则。
6. 按资源、命名空间、节点、工作负载和告警类型分组。
7. 将 Pod、Node、Network、Storage 或 Workload 根因分析交给对应诊断技能。

## 验证

先执行只读检查：

```bash
python3 scripts/huawei-cloud.py huawei_list_aom_alarms region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules region=cn-north-4
```

集群级检查：

```bash
python3 scripts/huawei-cloud.py huawei_aom_alarm_inspection \
  region=cn-north-4 cluster_id=<cluster-id>
```

变更验证：

1. 不带 `confirm=true` 执行命令。
2. 检查 `preview`、影响资源和预期影响。
3. 等待用户明确确认。
4. 重新执行并带上 `confirm=true`。
5. 使用对应查询命令验证结果。

## 最佳实践

1. **诊断时使用活跃 + 历史告警** - 只看活跃告警可能遗漏已恢复的问题。
2. **按 `cluster_id` 过滤** - 集群级告警规则和告警分析使用精确集群 ID。
3. **所有变更都先预览** - R2/R1/R0 工具不得跳过预览步骤。
4. **不要自动选择通知规则** - 必须等待用户选择 `bind_notification_rule_id`。
5. **通知配置保持显式** - 只使用用户提供的 SMN 主题创建通知动作规则。
6. **分析和修复分离** - 本技能只给出建议，修复交给修复类技能。
7. **保护可观测性** - 除非影响已明确且用户确认，不要停用或删除规则。

## 注意事项

- 告警诊断必须同时参考活跃告警和历史告警，不能因为没有活跃告警就判断集群没有问题。
- R2/R1/R0 工具必须先预览，再等待用户明确确认后执行。
- 不允许自动替用户选择通知规则、SMN 主题、集群或模板。
- 禁止通过本技能提供的工具之外的方式修改告警资源。
- 集群范围过滤使用 `cluster_id`；`huawei_list_aom_alarm_rules` 不接受集群名称。

## 故障排查

| 现象 | 可能原因 | 处理方式 |
| ---- | -------- | -------- |
| hcloud 命令失败 | profile、区域或 IAM 权限缺失 | 检查 `hcloud configure list` 和 IAM 策略 |
| 没有活跃告警 | 问题可能已恢复或只存在于历史中 | 查询活跃 + 历史告警 |
| 批量配置因缺少通知规则失败 | 缺少 `bind_notification_rule_id` | 查询动作规则或基于 SMN 主题创建通知规则后重试 |
| 集群告警规则查询返回过多规则 | 缺少 `cluster_id` 过滤 | 使用精确 `cluster_id` 重新查询 |
| Project ID 报错 | profile/project 解析失败 | 显式提供 `project_id` 或修复 hcloud profile |

## 限制

- 本技能不修改 CCE、ECS、ELB、EIP、VPC、安全组、节点、工作负载或 Kubernetes 资源。
- 本技能不得创建、修改或删除静默规则。
- 本技能不得通过工具之外的云命令修改告警资源。
- 本技能不能替用户安全推断通知规则。
- `huawei_list_aom_alarm_rules` 按 `cluster_id` 过滤，不按集群名称过滤。

## 参考文档

| 文档 | 用途 |
| ---- | ---- |
| [Operation Guide](references/operation-guide.md) | 详细参数、输出预期、验证、诊断交接和常见问题 |
| [Workflow](references/workflow.md) | 告警关联工作流 |
| [Output Schema](references/output-schema.md) | 输出 JSON 结构 |
| [Risk Rules](references/risk-rules.md) | 风险边界和确认规则 |
| [CLI Installation Guide](references/cli-installation-guide.md) | hcloud/KooCLI 安装和 profile 检查 |
| [IAM Policies](references/iam-policies.md) | AOM、CCE、IAM 所需权限 |
| [Verification Method](references/verification-method.md) | 功能和变更验证清单 |
| [Acceptance Criteria](references/acceptance-criteria.md) | 技能验收标准和测试用例 |
| [CCE Event List](references/cce-event-list.md) | 事件告警规则使用的 CCE 事件名 |
| [Prometheus Metric Alarms](references/cce-prometheus-metric-alarms.md) | Prometheus 指标告警参考 |
