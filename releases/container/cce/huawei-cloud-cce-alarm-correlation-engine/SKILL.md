---
name: huawei-cloud-cce-alarm-correlation-engine
description: |
  Huawei Cloud AOM alarm correlation analysis skill for CCE operations.
  Use this skill when the user wants to: (1) query AOM active and historical alarms, (2) analyze alarm deduplication, severity grouping, and burst/steady alarm identification, (3) inspect CCE cluster alarm health, (4) manage AOM alarm rules (query, create, update, delete, enable, disable), (5) check AOM action rules and mute rules for notification gaps, (6) create event alarm rules referencing CCE event lists or Prometheus metric alarms.
  Trigger: user mentions "alarm correlation", "AOM alarm", "alarm deduplication", "alarm storm", "alarm inspection", or "alarm rules".
tags: [cce, alarm-correlation, aom, observability, alarm-management]
---

# Huawei Cloud CCE Alarm Correlation Engine

> **⚠️ Execution Method (Must Read): This skill executes operations through the local Python dispatcher, and the dispatcher obtains Huawei Cloud data by invoking the `hcloud` CLI. Direct SDK imports, hand-written API signing, curl IAM calls, openstack, or other cloud access paths are prohibited.**
>
> - The dispatcher script is located at `scripts/huawei-cloud.py` within the skill directory
> - All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them. Do not run them directly in a shell.**
> - **Do not call Huawei Cloud APIs directly. The bundled scripts are the only place where `hcloud` should be invoked.**
> - **All paths are relative to the skill directory, which is the directory where this SKILL.md is located.**

## Overview

This skill correlates Huawei Cloud AOM active and historical alarms for CCE, transforming raw alarm event streams into actionable alarm leads. The core principle is to consider both active and history alarms, avoiding omission of resource-type alarms that have already recovered but still impact diagnosis.

This skill has **both read-only tools** (alarm query, analysis, inspection, rule query) and **mutation tools** (alarm rule create/update/delete, action rule delete). All mutation operations require a two-step confirmation workflow with `confirm=true`.

### Capabilities

- Query active/current/history AOM alarms and analyze alarm storms.
- Inspect CCE alarm health and hand off diagnosis to related CCE skills.
- Query and manage AOM alarm rules, notification action rules, and mute-rule visibility.
- Batch create or clean CCE recommended alarm rules from the cloud-side AOM CCE alarm template.

---

## Prerequisites

### Runtime Dependencies

The dispatcher script requires:

- Python >= 3.8
- Huawei Cloud KooCLI / `hcloud` >= 7.2.2 available in `PATH`
- A local `hcloud` profile configured with `hcloud configure`; the dispatcher relies on the local hcloud configuration for Huawei Cloud authentication and project/region resolution

### Credential Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| HUAWEI_AK | No | Fallback Huawei Cloud Access Key; used only when no explicit AK/SK parameters are provided and no local hcloud profile is configured |
| HUAWEI_SK | No | Fallback Huawei Cloud Secret Key; used only when no explicit AK/SK parameters are provided and no local hcloud profile is configured |
| HUAWEI_PROJECT_ID | No | Fallback Project ID; used only when no explicit `project_id` is provided and no local hcloud profile is configured |
| HUAWEI_SECURITY_TOKEN | No | Fallback temporary security token; used only with fallback environment AK/SK credentials |

🚫 **Never expose or log AK/SK values.** Credentials exist only in the current request call stack and are released after each invocation. Do not write credentials to files, logs, or responses.

✅ **This skill depends on the local hcloud configuration.** Use an hcloud profile (`hcloud configure`) for normal use. Credential priority is: explicit tool parameters > local hcloud profile > environment variables. Environment variables `HUAWEI_AK` / `HUAWEI_SK` are only a fallback when no hcloud profile is configured, but the dispatcher still invokes the local `hcloud` CLI.

**Security rules for credentials:**

1. **No persistent storage** — never write AK/SK, tokens, or certificates to disk files
2. **No long-term memory cache** — AK/SK exists only during the current hcloud invocation and is released afterward
3. **No custom project ID cache** — project/profile resolution is delegated to hcloud
4. **No log leakage** — never include AK/SK in logs, response output, or error messages
5. **Output desensitization** — output only alarm, resource, and rule information; never expose authentication credentials

AK/SK may be provided in three ways, in this priority order:
- Via per-call parameters `ak` and `sk` (highest priority, not recommended for production)
- Existing hcloud profile (recommended)
- Via environment variables `HUAWEI_AK` / `HUAWEI_SK` (fallback only when no profile is configured)

### IAM Permissions

| Permission | Description |
|------------|-------------|
| `aom:event:list` | Query AOM alarm events |
| `aom:alarmRule:list` | Query AOM alarm rules |
| `aom:alarmRule:create` | Create AOM alarm rules |
| `aom:alarmRule:update` | Update AOM alarm rules |
| `aom:alarmRule:delete` | Delete AOM alarm rules |
| `aom:actionRule:list` | Query AOM action rules |
| `aom:muteRule:list` | Query AOM mute rules |

---

## Core Tools

All actions are invoked via the dispatcher script:

```bash
python3 scripts/huawei-cloud.py <action> region=<region> [key=value ...]
```

### Two-Step Confirmation Workflow for Mutation Operations

> **Mutation operations (create, update, delete, enable, disable alarm rules; delete action rules) require `confirm=true` to execute. Without `confirm`, the tool returns a preview and confirmation prompt only.**

#### Risk Level Definitions

| Level | Meaning | Execution Guidance |
|-------|---------|--------------------|
| R3 | No-risk read-only operation | May run automatically |
| R2 | Low-risk change, such as creating monitoring configuration without deleting resources or increasing service capacity/cost | Preview first; execute only when the user asks for the change |
| R1 | Risky operation, such as restart-like impact, disabling protection, or changes that may increase cost or reduce observability | Requires explicit confirmation and `confirm=true` |
| R0 | Critical operation, such as deleting clusters, applications, or notification/monitoring protections with broad impact | Do not execute automatically; require explicit user confirmation, impact review, and rollback plan |

**Step 1: Preview** — call without `confirm`:
```bash
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule metric_name=cpuUsage \
  namespace=PAAS.NODE comparison_operator='>' threshold=80 \
  period=60 evaluation_periods=3 statistic=average alarm_level=2
```

Returns: operation preview, target rule, rule fields, and confirmation example. No real creation is performed.

**Step 2: Confirm execution** — call again with `confirm=true`:
```bash
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule metric_name=cpuUsage \
  namespace=PAAS.NODE comparison_operator='>' threshold=80 \
  period=60 evaluation_periods=3 statistic=average alarm_level=2 \
  confirm=true
```

#### Operations Requiring Confirmation

| Tool | Operation | Risk Level | Description |
|------|-----------|-----------|-------------|
| `huawei_create_aom_alarm_rule` | Create | R2 | Create new AOM alarm rule, may introduce new alarm notifications |
| `huawei_create_aom_event_alarm_rule` | Create | R2 | Create AOM event alarm rule, may introduce new event notifications |
| `huawei_create_aom_notification_action_rule` | Create | R2 | Create AOM notification action rule from a user-provided SMN topic |
| `huawei_configure_cce_aom_alarm_rules` | Batch create | R2 | Create recommended CCE AOM alarm rules using an explicit existing notification action rule |
| `huawei_cleanup_cce_aom_alarm_rules` | Batch delete | R0 | Delete CCE AOM alarm rules matching the cloud-side CCE alarm template for the target cluster |
| `huawei_update_aom_alarm_rule` | Update | R1 | Update AOM alarm rule threshold, toggle, notification action, description, etc. |
| `huawei_delete_aom_alarm_rule` | Delete | R0 | Delete AOM alarm rule, may prevent future alarms from triggering |
| `huawei_disable_aom_alarm_rule` | Disable | R1 | Disable AOM alarm rule, may stop related alarms from triggering |
| `huawei_enable_aom_alarm_rule` | Enable | R2 | Enable AOM alarm rule, may restore and trigger alarm notifications |
| `huawei_delete_aom_action_rule` | Delete | R0 | Delete AOM notification action rule, may prevent alarm notifications |

#### Prohibited Actions

| Action | Description |
|--------|-------------|
| Create/update arbitrary action rules | Only `huawei_create_aom_notification_action_rule` creates notification action rules; batch configure requires `bind_notification_rule_id` |
| Automatically choose notification rules | Never choose `bind_notification_rule_id` on behalf of the user. If the user has not provided it, call `huawei_list_aom_action_rules`, present the candidates, and wait for explicit user confirmation before batch creating alarm rules |
| Modify mute rules | Do not create, update, or delete mute rules |
| Execute remediation actions | Do not scale, reboot, drain, or delete workloads or nodes |
| Modify cluster resources | Do not change CCE, ECS, ELB, EIP, VPC, security groups, etc. |

If analysis results require scaling, rebooting, draining, vulnerability status changes, or other remediation actions, output recommendations only and hand off to `huawei-cloud-cce-auto-remediation-runner` for preview, confirmation, and post-verification.

### Alarm Query and Correlation (Read-Only)

| Action | Description | Risk Level | Cluster Filter | Required Params |
|--------|-------------|------------|---------------|-----------------|
| `huawei_list_aom_alarms` | Query active + history alarms, merged and deduplicated | R3 | Supports `cluster_id` | `region` |
| `huawei_list_aom_current_alarms` | Query current active alarms only | R3 | Supports `cluster_id` | `region` |
| `huawei_analyze_aom_alarms` | Analyze alarms: deduplication, severity grouping, burst/steady identification | R3 | Supports `cluster_id` | `region` |

```bash
# Query active + history alarms in a region
python3 scripts/huawei-cloud.py huawei_list_aom_alarms region=cn-north-4

# Query alarms for a specific cluster
python3 scripts/huawei-cloud.py huawei_list_aom_alarms \
  region=cn-north-4 cluster_id=xxx

# Query current active alarms for a cluster
python3 scripts/huawei-cloud.py huawei_list_aom_current_alarms \
  region=cn-north-4 cluster_id=xxx

# Analyze alarms for a cluster (burst, attention, steady groups)
python3 scripts/huawei-cloud.py huawei_analyze_aom_alarms \
  region=cn-north-4 cluster_id=xxx
```

## Core Commands

Use the following commands as the primary entry points for this skill. Run mutation commands in preview mode first, then add `confirm=true` only after the user explicitly confirms the operation.

| Command | Main Operation | Risk | Required Params |
|---------|----------------|------|-----------------|
| `huawei_list_aom_alarms` | Query active + history alarms and merge/deduplicate results | R3 | `region` |
| `huawei_list_aom_current_alarms` | Query current active alarms only | R3 | `region` |
| `huawei_analyze_aom_alarms` | Analyze alarm grouping, burst alarms, attention alarms, and chronic alarms | R3 | `region` |
| `huawei_aom_alarm_inspection` | Inspect CCE alarm health and output risk summary | R3 | `region`, `cluster_id` |
| `huawei_list_aom_alarm_rules` | Query AOM alarm rules; supports filtering by `cluster_id` only, not `cluster_name` | R3 | `region` |
| `huawei_list_aom_action_rules` | Query AOM notification/action rules before choosing `bind_notification_rule_id` | R3 | `region` |
| `huawei_create_aom_notification_action_rule` | Create an AOM notification action rule from a user-provided SMN topic | R2 | `region`, `rule_name`, `notification_topic_urn`, `notification_topic_name` |
| `huawei_configure_cce_aom_alarm_rules` | Batch create CCE recommended alarm rules from the AOM CCE alarm template; requires explicit `bind_notification_rule_id` | R2 | `region`, `cluster_id`, `bind_notification_rule_id` |
| `huawei_cleanup_cce_aom_alarm_rules` | Batch delete CCE alarm rules matching the AOM CCE alarm template | R0 | `region`, `cluster_id` |

Key requirements:
- Do not choose `bind_notification_rule_id` automatically. If the user has not provided it, call `huawei_list_aom_action_rules`, show the candidates, and wait for explicit user confirmation.
- `huawei_list_aom_alarm_rules` only supports `cluster_id` for cluster filtering. Do not use `cluster_name`.
- R2/R1/R0 mutation commands must be previewed first and require `confirm=true` for execution.

### Alarm Rule Management (Mutation Requires `confirm=true`)

**Event alarm rule constraints:**
- When creating event alarm rules via `huawei_create_aom_event_alarm_rule`, the `event_name` must reference the event list and naming format in `references/cce-event-list.md` (recommended format: `Chinese event description##Event name`).
- Event alarm rules are created with alarm noise reduction enabled by default (`route_group_enable=true`).

**Metric alarm rule constraints:**
- When creating metric alarm rules via `huawei_create_aom_alarm_rule`, PromQL/metric thresholds should reference `references/cce-prometheus-metric-alarms.md`.

| Action | Description | Risk Level | Requires `confirm` | Required Params |
|--------|-------------|------------|--------------------|-----------------|
| `huawei_list_aom_alarm_rules` | Query AOM alarm rules | R3 | No | `region`; optional `cluster_id` |
| `huawei_resolve_cce_aom_prom_instance` | Resolve target cluster AOM Prometheus instance | R3 | No | `region`, `cluster_id` |
| `huawei_create_aom_alarm_rule` | Create AOM metric alarm rule | R2 | **Yes** | `region`, `rule_name`, `metric_name`, `namespace`, `comparison_operator`, `threshold`, `period`, `evaluation_periods`, `statistic`, `alarm_level` |
| `huawei_create_aom_event_alarm_rule` | Create AOM event alarm rule | R2 | **Yes** | `region`, `cluster_id`, `rule_name`, `event_name` |
| `huawei_create_aom_notification_action_rule` | Create AOM notification action rule from an SMN topic | R2 | **Yes** | `region`, `rule_name`, `notification_topic_urn`, `notification_topic_name` |
| `huawei_configure_cce_aom_alarm_rules` | Batch create recommended CCE AOM alarm rules from the AOM CCE alarm template | R2 | **Yes** | `region`, `cluster_id`, `bind_notification_rule_id` |
| `huawei_cleanup_cce_aom_alarm_rules` | Batch delete CCE AOM alarm rules matching the AOM CCE alarm template | R0 | **Yes** | `region`, `cluster_id` |
| `huawei_update_aom_alarm_rule` | Update AOM alarm rule | R1 | **Yes** | `region`, `rule_name` |
| `huawei_delete_aom_alarm_rule` | Delete AOM alarm rule | R0 | **Yes** | `region`, `rule_name` |
| `huawei_disable_aom_alarm_rule` | Disable AOM alarm rule | R1 | **Yes** | `region`, `rule_id` |
| `huawei_enable_aom_alarm_rule` | Enable AOM alarm rule | R2 | **Yes** | `region`, `rule_id` |
| `huawei_list_aom_action_rules` | Query AOM action/notification rules | R3 | No | `region` |
| `huawei_delete_aom_action_rule` | Delete AOM notification action rule | R0 | **Yes** | `region`, `rule_name` |
| `huawei_list_aom_mute_rules` | Query AOM mute rules | R3 | No | `region` |

```bash
# Query alarm rules
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules region=cn-north-4

# Query alarm rules related to a CCE cluster
python3 scripts/huawei-cloud.py huawei_list_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>

# Preview create alarm rule (no execution)
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule metric_name=cpuUsage \
  namespace=PAAS.NODE comparison_operator='>' threshold=80 \
  period=60 evaluation_periods=3 statistic=average alarm_level=2

# Confirm create alarm rule
python3 scripts/huawei-cloud.py huawei_create_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule metric_name=cpuUsage \
  namespace=PAAS.NODE comparison_operator='>' threshold=80 \
  period=60 evaluation_periods=3 statistic=average alarm_level=2 \
  confirm=true

# Preview batch create recommended CCE alarm rules for a cluster
python3 scripts/huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>

# If the user has not provided bind_notification_rule_id, list notification rules first.
# Do not choose one automatically; ask the user to confirm which rule to use.
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules region=cn-north-4

# Confirm batch create and bind an existing notification rule
python3 scripts/huawei-cloud.py huawei_configure_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  bind_notification_rule_id=auto-cluster-xxx confirm=true

# Preview batch cleanup of CCE template alarm rules for a cluster
python3 scripts/huawei-cloud.py huawei_cleanup_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id>

# Confirm batch cleanup; optionally delete the auto-created notification action rule
python3 scripts/huawei-cloud.py huawei_cleanup_cce_aom_alarm_rules \
  region=cn-north-4 cluster_id=<cluster-id> \
  delete_auto_notification_rule=true confirm=true

# Preview update alarm rule
python3 scripts/huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule threshold=80

# Confirm update alarm rule
python3 scripts/huawei-cloud.py huawei_update_aom_alarm_rule \
  region=cn-north-4 rule_name=my-rule threshold=80 confirm=true

# Preview delete alarm rule
python3 scripts/huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 rule_name=xxx

# Confirm delete alarm rule
python3 scripts/huawei-cloud.py huawei_delete_aom_alarm_rule \
  region=cn-north-4 rule_name=xxx confirm=true

# Preview disable alarm rule
python3 scripts/huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 rule_id=xxx

# Confirm disable alarm rule
python3 scripts/huawei-cloud.py huawei_disable_aom_alarm_rule \
  region=cn-north-4 rule_id=xxx confirm=true

# Preview enable alarm rule
python3 scripts/huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 rule_id=xxx

# Confirm enable alarm rule
python3 scripts/huawei-cloud.py huawei_enable_aom_alarm_rule \
  region=cn-north-4 rule_id=xxx confirm=true

# Query action rules
python3 scripts/huawei-cloud.py huawei_list_aom_action_rules region=cn-north-4

# Preview create notification action rule from an SMN topic
python3 scripts/huawei-cloud.py huawei_create_aom_notification_action_rule \
  region=cn-north-4 rule_name=auto-cluster-xxx \
  notification_topic_name=<smn-topic-name> \
  notification_topic_urn=<smn-topic-urn>

# Confirm create notification action rule from an SMN topic
python3 scripts/huawei-cloud.py huawei_create_aom_notification_action_rule \
  region=cn-north-4 rule_name=auto-cluster-xxx \
  notification_topic_name=<smn-topic-name> \
  notification_topic_urn=<smn-topic-urn> \
  confirm=true

# Preview delete action rule
python3 scripts/huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 rule_name=xxx

# Confirm delete action rule
python3 scripts/huawei-cloud.py huawei_delete_aom_action_rule \
  region=cn-north-4 rule_name=xxx confirm=true

# Query mute rules
python3 scripts/huawei-cloud.py huawei_list_aom_mute_rules region=cn-north-4
```

### Cluster Alarm Inspection (Read-Only)

| Action | Description | Risk Level | Required Params |
|--------|-------------|------------|-----------------|
| `huawei_aom_alarm_inspection` | Inspect AOM alarms for a CCE cluster and output risk items | R3 | `region`, `cluster_id` |

```bash
# Inspect alarms for a specific cluster
python3 scripts/huawei-cloud.py huawei_aom_alarm_inspection \
  region=cn-north-4 cluster_id=xxx
```

---

## References

Read these references when the task needs deeper parameter details, output expectations, verification steps, or rule templates:

| Document | Use |
|----------|-----|
| `references/operation-guide.md` | Detailed parameters, output expectations, verification, diagnosis hand-off, and pitfalls |
| `references/workflow.md` | Alarm correlation workflow |
| `references/output-schema.md` | Output JSON schema |
| `references/risk-rules.md` | Risk boundary rules |
| `references/cce-event-list.md` | CCE event names for event alarm rules |
| `references/cce-prometheus-metric-alarms.md` | Prometheus metric alarm references |
