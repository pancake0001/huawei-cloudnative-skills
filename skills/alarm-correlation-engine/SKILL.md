---
name: alarm-correlation-engine
description: Huawei Cloud AOM alarm correlation analysis skill supports querying active/history alarms, currently active alarms, alarm deduplication and merging, severity grouping, sudden/normal alarm identification, as well as alarm rule query, creation, modification, deletion, action rule and silent rule verification.
---

# Huawei Cloud AOM alarm correlation analysis

Huawei Cloud AOM alarm correlation analysis skills are used to organize CCE-related alarms from the original event stream into actionable alarm clues. The core principle is to consider both active and history to avoid missing resource alarms that have been recovered but affect diagnosis.

# # ⛔ Security Constraints

## # Alarm rule change secondary confirmation mechanism

> **This skill allows querying, creating, modifying and deleting AOM alarm rules, and supports deleting AOM notification action rules; the creation, modification and deletion operations must carry `confirm=true` to be actually executed, otherwise only a preview and confirmation prompt will be returned. **

### # List of operations requiring secondary confirmation

| Tools | Operation Type | Risk Level | Description |
|------|---------|---------|------|
| `huawei_create_aom_alarm_rule` | Create | 🟡 Medium | Create a new AOM alarm rule, which may introduce new alarm notifications |
| `huawei_configure_cce_aom_alarm_rules` | Batch creation | 🟡 Medium | Create AOM alarm rules for the specified cluster with one click according to the CCE Alarm Center default template |
| `huawei_update_aom_alarm_rule` | Modify | 🟠 High | Modify AOM alarm rule thresholds, switches, notification actions, descriptions and other configurations |
| `huawei_delete_aom_alarm_rule` | Delete | 🔴 High | Deleting AOM alarm rules may cause subsequent alarms to fail to be triggered |
| `huawei_disable_aom_alarm_rule` | Disable | 🔴 High | Disable AOM alarm rules, which may cause related alarms to no longer be triggered |
| `huawei_enable_aom_alarm_rule` | Enable | 🟠 High | Enable AOM alarm rules, may restore and trigger alarm notifications |
| `huawei_delete_aom_action_rule` | Delete | 🔴 High | Deleting AOM notification action rules may cause alarm notifications to fail to be sent |

### # Workflow

**Step 1: Preview operation** - Called without `confirm` parameter
```bash
# Example: Preview and create alarm rules
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

Returns: Action preview, target rule, rule fields and confirmation example, no actual creation is performed.

**Step 2: Confirm execution** - Call again with the `confirm=true` parameter
```bash
# Example: Confirm creation of alarm rules
python3 huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  metric_name=cpuUsage \
  namespace=PAAS.NODE \
  comparison_operator='>' \
  threshold=80 \
  period=60\
  evaluation_periods=3 \
  statistic=average \
  alarm_level=2 \
  confirm=true
```

### # Prohibited actions

| Action | Description |
|------|------|
| Create/update action rules | Do not create or update notification action rules |
| Modify silent rules | Do not create, update, or delete silent rules |
| Perform recovery actions | No scaling, restarting, draining, or deleting workloads or nodes |
| Modify cluster resources | Do not change CCE, ECS, ELB, EIP, VPC, security group and other resources |

If the analysis results require scaling, restarting, draining, vulnerability status changes, or other recovery actions, only suggestions must be output and forwarded to `auto-remediation-runner` for preview, confirmation, and post-execution verification.

## # Certification Information Security

✅ **This skill strictly abides by the following safety rules:**

1. **Prohibit persistent storage of authentication information** - Never save sensitive authentication information such as AK/SK, Token, and certificates to disk files
2. **Long-term memory caching is prohibited** - AK/SK only exists in memory during the current API request call and is automatically released after the call is completed.
3. **Project ID Only Memory Cache** - Only non-sensitive project IDs are cached in process memory (not written to disk)
4. **No log leaks** - Do not include sensitive information such as AK/SK in any logs, response output or error messages
5. **Output desensitization** - External output only displays alarm, resource and rule information, and does not display authentication credentials.

AK/SK only supports the following two ways of use:
- Pass in environment variables `HUAWEI_AK` / `HUAWEI_SK` (recommended)
- Passed in parameters through each call (only valid for this call)

---

# # Preconditions

## # Environment variable configuration

**Method 1: Environment variables (recommended)**
```bash
export HUAWEI_AK="your-access-key-id"
export HUAWEI_SK="your-secret-access-key"
```

**Method 2: Pass in parameters for each call**
Pass in the `ak` and `sk` parameters on every API call (not recommended for production environments).

## # Python dependencies

```bash
pip install huaweicloudsdkcore huaweicloudsdkaom huaweicloudsdkiam
```

## # IAM Permissions Policy

Make sure the IAM user has the following minimum permissions:

| Permissions | Description |
|------|------|
| `aom:event:list` | Query AOM alarm events |
| `aom:alarmRule:list` | Query AOM alarm rules |
| `aom:alarmRule:create` | Create AOM alarm rule |
| `aom:alarmRule:update` | Modify AOM alarm rules |
| `aom:alarmRule:delete` | Delete AOM alarm rules |
| `aom:actionRule:list` | Query AOM action rules |
| `aom:muteRule:list` | Query AOM mute rules |
| `cce:cluster:list` | Get the cluster name and auxiliary filtering information by cluster ID |

---

# # Tool classification

## # Alarm query and merge

| Tools | Features | Cluster Filtering | Parameters |
|------|------|---------|------|
| `huawei_list_aom_alarms` | Query active + history alarms and merge them to remove duplicates | Support `cluster_id` | `region` |
| `huawei_list_aom_current_alarms` | Query currently active alarms | Support `cluster_id` | `region` |
| `huawei_analyze_aom_alarms` | Deduplication, classification and sudden/normal identification of active + history alarms | Support `cluster_id` | `region` |

**Parameter description:**
- `region` (required): Huawei Cloud region, such as `cn-north-4`
- `cluster_id` (optional): CCE cluster ID; after passing it in, only alarms related to the cluster will be returned
- `ak` (optional): Access Key ID, priority is given to `HUAWEI_AK`
- `sk` (optional): Secret Access Key, `HUAWEI_SK` is preferred
- `project_id` (optional): Huawei Cloud project ID. If not passed, it will be automatically obtained by region.

**Usage example:**
```bash
# Query active + history alarms in the area
python3 huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4

# Query the active + history alarms of the specified cluster
python3 huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4 \
  cluster_id=xxx

# Query the current active alarms of the specified cluster
python3 huawei-cloud.py huawei_list_aom_current_alarms \
  region=cn-north-4 \
  cluster_id=xxx

# Analyze specified cluster alarms and output burst, concern, and normal groupings
python3 huawei-cloud.py huawei_analyze_aom_alarms \
  region=cn-north-4 \
  cluster_id=xxx
```

---

## # Alarm rule management**Event alarm creation constraints:**
- When using `huawei_create_aom_event_alarm_rule` to create an event alarm, `event_name` must first refer to the event list and naming format in `references/cce-event-list.md` (`Chinese event description ## event name` is recommended).
- When creating an event alarm, alarm noise reduction is enabled by default (`route_group_enable=true`).

**Indicator alarm creation constraints:**
- When using `huawei_create_aom_alarm_rule` to create metric alarms, PromQL/metric calibers and thresholds should first refer to `references/cce-prometheus-metric-alarms.md`.

| Tools | Functions | Risk Level | Confirmation Required | Parameters |
|------|------|---------|-------|------|
| `huawei_list_aom_alarm_rules` | Query AOM alarm rules | 🟢 Low | No | `region` |
| `huawei_create_aom_alarm_rule` | Create AOM alarm rule | 🟡 Medium | **Yes** | `region`, `rule_name`, `metric_name`, `namespace`, `comparison_operator`, `threshold`, `period`, `evaluation_periods`, `statistic`, `alarm_level` |
| `huawei_configure_cce_aom_alarm_rules` | Create CCE default alarm rules with one click | 🟡 Medium | **Yes** | `region`, `cluster_id` |
| `huawei_update_aom_alarm_rule` | Modify AOM alarm rules | 🟠 High | **Yes** | `region`, `rule_name` |
| `huawei_delete_aom_alarm_rule` | Delete AOM alarm rule | 🔴 High | **Yes** | `region`, `rule_name` |
| `huawei_disable_aom_alarm_rule` | Disable AOM alarm rule | 🔴 High | **Yes** | `region`, `rule_id` |
| `huawei_enable_aom_alarm_rule` | Enable AOM alarm rule | 🟠 High | **Yes** | `region`, `rule_id` |
| `huawei_list_aom_action_rules` | Query AOM alarm action rules | 🟢 Low | No | `region`, `enterprise_project_id` |
| `huawei_delete_aom_action_rule` | Delete AOM alarm action rule (notification rule) | 🔴 High | **Yes** | `region`, `rule_name` |
| `huawei_list_aom_mute_rules` | Query AOM mute rules | 🟢 Low | No | `region` |

**Parameter description:**
- `region` (required): Huawei Cloud region
- `metric_name` (required for create): metric name
- `namespace` (required for create): indicator namespace
- `comparison_operator` (required for create): threshold comparison operator, such as `>`, `<`, `>=`, `<=`
- `threshold` (required for create): Alarm threshold
- `period` (required for create): statistical period, in seconds
- `evaluation_periods` (required for create): Number of consecutive trigger periods
- `statistic` (required for create): statistical method, such as `average`, `max`, `min`
- `alarm_level` (required for create): Alarm level
- `rule_name` (required for update): Alarm rule name, the AOM update interface locates the rule through the rule name
- `rule_name` (required for delete): Alarm rule name
- `rule_id` (required for disable): ID of the alarm rule that needs to be disabled
- `rule_id` (required for enable): Alarm rule ID that needs to be enabled
- `rule_name` (required for delete action rule): AOM notification action rule name
- `enterprise_project_id` (optional for list action rules): Enterprise project scope, default `all_granted_eps`
- `bind_notification_rule_id` (optional for configure): AOM notification rule name/ID bound when creating a CCE alarm rule with one click; if not passed, the default is `auto-cluster-{cluster_id}`
- `smn_topic_urn` (conditionally required for configure): SMN topic URN used to automatically create notification rules when `bind_notification_rule_id` is not specified and the `auto-cluster-{cluster_id}` notification rule does not exist
- `smn_topic_name` (optional for configure): SMN topic name; if not passed, it will be automatically derived from the last segment of `smn_topic_urn`
- `smn_topic_display_name` (optional for configure): SMN topic display name
- `rule_name_prefix` (optional for configure): Create rule name prefixes in batches, using `cluster_id` by default
- `include_metric_alarms` / `include_event_alarms` (optional for configure): Whether to create indicator/event alarms, both are created by default
- `alarm_items` (optional for configure): Comma-separated alarm item whitelist, only create specified alarm items
- `skip_existing` (optional for configure): Whether to skip existing rules with the same name, default `true`
- `prom_instance_id` (optional for configure): Specify the AOM Prometheus instance; if not passed, press `cluster_id` to automatically match
- `fields` (optional): Additional JSON fields when creating rules, for example `{"unit":"%","is_turn_on":true}`
- `updates` (optional): Batch update fields in JSON format, such as `{"threshold":"80","is_turn_on":true}`
- `confirm` (optional): must be explicitly set to `true` before it will be executed when creating, modifying or deleting
- `ak` (optional): Access Key ID
- `sk` (optional): Secret Access Key
- `project_id` (optional): Huawei Cloud project ID

**Usage example:**
```bash
# Query alarm rules
python3 huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4

# Preview the created alarm rule and do not execute it
python3 huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  metric_name=cpuUsage \
  namespace=PAAS.NODE \
  comparison_operator='>' \
  threshold=80 \
  period=60\
  evaluation_periods=3 \
  statistic=average \
  alarm_level=2

# Confirm creation of alarm rules
python3 huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  metric_name=cpuUsage \
  namespace=PAAS.NODE \
  comparison_operator='>' \
  threshold=80 \
  period=60\
  evaluation_periods=3 \
  statistic=average \
  alarm_level=2 \
  confirm=true

# Preview the default rules of CCE alarm center created with one click and do not execute them
python3 huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 \
  cluster_id=xxx# Confirm the one-click creation of CCE alarm center default rules
python3 huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 \
  cluster_id=xxx \
  bind_notification_rule_id=auto-cluster-xxx \
  confirm=true

# When no notification rules are specified, the tool will give priority to auto-cluster-{cluster_id};
# If the notification rule does not exist, use smn_topic_urn to automatically create the notification rule and then create the alarm rule.
python3 huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 \
  cluster_id=xxx \
  smn_topic_urn=urn:smn:cn-north-4:project-id:topic-name \
  confirm=true

# Preview and modify the alarm rules without executing them
python3 huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  threshold=80

# Confirm to modify the alarm rules
python3 huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=my-rule \
  threshold=80 \
  confirm=true

# Preview and delete alarm rules without executing them
python3 huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=xxx

# Confirm deletion of alarm rules
python3 huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 \
  rule_name=xxx \
  confirm=true

# Preview the deactivation alarm rule and do not execute it
python3 huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx

# Confirm to disable the alarm rule
python3 huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx \
  confirm=true

# Preview and enable alarm rules without executing them
python3 huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx

# Confirm to enable alarm rules
python3 huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 \
  rule_id=xxx \
  confirm=true


# Query action rules
python3 huawei-cloud.py huawei_list_aom_action_rules \
  region=cn-north-4

# Preview delete action rules and do not execute them
python3 huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 \
  rule_name=xxx

# Confirm deletion action rule
python3 huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 \
  rule_name=xxx \
  confirm=true

# Query silent rules
python3 huawei-cloud.py huawei_list_aom_mute_rules \
  region=cn-north-4
```

## # Cluster alarm inspection

| Tools | Features | Cluster Filtering | Parameters |
|------|------|---------|------|
| `huawei_aom_alarm_inspection` | Perform AOM alarm inspection on the specified CCE cluster and output risk items | `cluster_id` required | `region`, `cluster_id` |

**Parameter description:**
- `region` (required): Huawei Cloud region
- `cluster_id` (required): CCE cluster ID
- `ak` (optional): Access Key ID
- `sk` (optional): Secret Access Key
- `project_id` (optional): Huawei Cloud project ID

**Usage example:**
```bash
# Check the AOM alarm of the specified cluster
python3 huawei-cloud.py huawei_aom_alarm_inspection \
  region=cn-north-4 \
  cluster_id=xxx
```

---

# # Recommended workflow

## # Scenario 1: Query specified cluster alarms

1. Clarify `region` and `cluster_id`
2. Call `huawei_list_aom_alarms` to query active + history merged results
3. Merge by alarm type, resource object, status and severity level
4. Output currently triggered alarms, historical alarms that have been recovered but still require attention, and Top resource objects

## # Scenario 2: Alarm storm or repeated alarm noise reduction

1. Call `huawei_analyze_aom_alarms`
2. Merge original alarms into a unique alarm group
3. Distinguish between emergency alarms, attention alarms and normal alarms
4. Output noise reduction ratio, top concerns and recommended diagnosis skills

## # Scenario 3: Query, create, modify or delete alarm rules

1. Call `huawei_list_aom_alarm_rules` to query the alarm rules
2. When you need to create, first call `huawei_create_aom_alarm_rule` to get a preview
3. When modification is required, first call `huawei_update_aom_alarm_rule` to get a preview
4. When deletion is required, first call `huawei_delete_aom_alarm_rule` to get a preview
5. When you need to disable it, first call `huawei_disable_aom_alarm_rule` to get a preview.
6. After the user explicitly confirms, call it again and carry `confirm=true`
7. After creating, modifying, deleting or deactivating, call `huawei_list_aom_alarm_rules` again to verify the rule status.

## # Scenario 4: Confirm whether the alarm is affected by action rules or silence

1. Call `huawei_list_aom_action_rules` to query notification action rules
2. If you need to delete the invalid action rule, first call `huawei_delete_aom_action_rule` to preview, and then execute it with `confirm=true` after confirmation by the user.
3. Call `huawei_list_aom_mute_rules` to query mute rules
4. Determine whether there are abnormal action rules or missing notifications caused by silence

## # Scenario 5: Cluster inspection entrance

1. Call `huawei_aom_alarm_inspection`
2. Summarize the total number of alarms in the specified cluster, the number of alarms being triggered, the number of recovered alarms, and the severity distribution
3. Output the resource alarm list and objects that require further diagnosis
4. If there are problems with Pod, Node, or Network, transfer them to the corresponding diagnosis skill

---

# # Output requirements

## # Alarm summary

The output must contain:

| Field | Description |
|------|------|
| `region` | Query region |
| `cluster_id` | If the user specifies a cluster, output the cluster ID |
| `total_count` | Total number of alarms |
| `firing_count` | Number of alarms currently being triggered |
| `resolved_count` | Number of recovered alarms |
| `severity_stats` | Severity level distribution |
| `type_stats` | Merge statistics by alarm type |

## # Resource clues

For CCE alarms, the following resource dimensions are output first:

| Field | Description |
|------|------|
| `cluster_name` | Cluster name |
| `namespace` | namespace |
| `pod_name` | Pod name |
| `resource_kind` | Resource type |
| `event_name` | Alarm name |
| `message` | Alarm message |

## # Recommended diagnostic skill| Alarm characteristics | Recommended skills |
|----------|------------|
| `CrashLoopBackOff`, `BackOffStart`, `FailedStart`, `ImagePullBackOff` | `pod-failure-diagnoser` |
| `FailedScheduling`, `Insufficient cpu`, `Insufficient memory` | `pod-failure-diagnoser` or `node-failure-diagnoser` |
| `NodeNotReady`, node resource pressure, NPD events | `node-failure-diagnoser` |
| `Ingress 502/504`, Service failure, ELB exception | `network-failure-diagnoser` |
| Multiple types of alarms appear simultaneously and affect the business | `root-cause-analyzer` |
| Requires recovery operations such as scaling, restarting, and draining | `auto-remediation-runner` |

---

# # References

- Read `references/workflow.md` for the alarm merging step
- Read-only boundaries and false positive handling read `references/risk-rules.md`
- The output structure is according to `references/output-schema.md`
- Prometheus metric alarm rules reference `references/cce-prometheus-metric-alarms.md`