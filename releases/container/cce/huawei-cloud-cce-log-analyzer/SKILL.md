---
name: huawei-cloud-cce-log-analyzer
description: >-
  Use when querying or analyzing Kubernetes Pod stdout/stderr logs, CCE LogConfig-collected application logs, Huawei Cloud LTS log streams, CCE audit logs for Pod deletion or workload change events, or when creating/deleting CCE LogConfig or LTS Access Config collection rules with preview confirmation. Covers Pod log retrieval, container and node file collection, LogConfig discovery, LTS group/stream mapping, keyword search, time-range queries, abnormality analysis with error ratios and incident windows, and audit event summarization.
  Trigger: log analysis, 日志分析, CCE logs, CCE 日志, LTS query, LTS 查询, application log, 应用日志, container log, 容器日志, log search, 日志搜索, Pod stdout, Pod 日志, LogConfig, audit log, 审计日志, abnormal log, 异常日志
tags: [cce, logs, lts, analysis]
---

# Huawei Cloud CCE Log Analyzer

## Overview

Query and analyze Kubernetes Pod stdout logs, CCE LogConfig-collected application logs, and Huawei Cloud LTS log streams for CCE workloads.

**Architecture**: `scripts/huawei-cloud.py` dispatcher → `kubectl` through external kubeconfig or `kubectl cce` (Pod stdout and LogConfig resources) / `hcloud` (LTS group, stream, and log queries).

**LTS Resource Management**: This skill does not expose LTS group or stream creation tools. When a log group or stream must be discovered, use `hcloud LTS ListLogGroups` and `hcloud LTS ListLogStreams`; when one must be created, use `hcloud LTS CreateLogGroup` or `hcloud LTS CreateLogStream` after the required confirmation. Pass the resulting IDs to `huawei_create_cce_logconfig` or `huawei_create_lts_access_config`.

### Log Collection Modes

| Mode | Configuration resource | Dependency | Tools | Guidance |
|------|------------------------|------------|-------|----------|
| CCE Cloud Native Logging | Cluster `LogConfig` | Cloud Native Logging add-on in the CCE cluster | `huawei_get_cce_logconfigs`, `huawei_create_cce_logconfig`, `huawei_delete_cce_logconfig` | Use for CCE-native workload collection and when managing collection policies alongside Kubernetes resources. [CCE documentation](https://support.huaweicloud.com/usermanual-cce/cce_10_0416.html) |
| LTS Access Config collection | LTS Access Config | `K8S_CCE` CCE stdout creation uses the official LTS SDK; `AGENT` collection requires healthy iCagent | `huawei_list_lts_access_configs`, `huawei_create_lts_access_config`, `huawei_delete_lts_access_config` | Use `K8S_CCE` for scoped CCE container stdout. Use `AGENT` for iCagent-based high-throughput or file collection. [LTS documentation](https://support.huaweicloud.com/usermanual-lts/lts_07_1118.html) |

**Related Skills**:
- `huawei-cloud-cce-pod-failure-diagnoser` - Pod startup, scheduling, crash-loop diagnosis
- `huawei-cloud-cce-workload-failure-diagnoser` - Deployment/StatefulSet rollout issues
- `huawei-cloud-cce-node-failure-diagnoser` - Node NotReady, disk pressure, network issues
- `huawei-cloud-cce-kubernetes-event-analyzer` - Kubernetes Warning events and patterns

**Capabilities**:
- Query Kubernetes Pod stdout/stderr and previous container logs through `kubectl`
- List, create, and delete CCE LogConfig collection rules through `kubectl`
- List, create, and delete LTS Access Config collection rules through `hcloud`
- Discover application LogConfig policies and map to LTS log groups/streams
- Query CCE Kubernetes audit logs for Pod deletion and workload change events
- Query application logs from LTS by time range, keywords, or recent hours
- Analyze application logs for abnormal keywords, HTTP errors, incident windows, recovery time, and abnormal ratios

**Typical Use Cases**:

- "Check my Pod logs for crash errors"
- "Find the LTS stream for my application"
- "Query recent application logs for ERROR keywords"
- "Analyze logs in the last hour for abnormalities"
- "Who deleted this Pod? Check audit logs"
- "Create a LogConfig to collect my workload stdout"
- "Remove this LogConfig collection rule"
- "Query container file logs from /var/log/*.log"
- "Collect node files such as /var/log/messages"
- "Create an LTS Access Config for CCE container logs"

## Prerequisites

### 1. Python Runtime

- Python 3.8+ installed
- Run `python3 --version` to verify

### 2. Huawei Cloud Credentials

- `hcloud` profile or valid Huawei Cloud credentials for external kubeconfig access and LTS queries
- `kubectl` for Pod stdout and LogConfig operations
- `kubectl-cce` when the cluster has no usable external endpoint; see `huawei-cloud-kubectl-cce-installer`
- Kubernetes access order is: external kubeconfig through hcloud, then `kubectl cce` fallback
- The **Cloud Native Logging** add-on must be installed and running in the target cluster before using `huawei_get_cce_logconfigs`, `huawei_create_cce_logconfig`, or `huawei_delete_cce_logconfig`. These tools manage the `logconfigs.logging.openvessel.io` resource supplied by that add-on.
- `huawei_list_lts_access_configs`, `huawei_create_lts_access_config`, and `huawei_delete_lts_access_config` manage LTS Access Config rules. The hcloud `CreateAccessConfig` schema only accepts `AGENT`, so `K8S_CCE` creation uses the official LTS SDK with AK/SK and project ID; `AGENT` creation remains on hcloud. iCagent must be installed and healthy for `AGENT` CCE collection. Creating an Access Config never installs iCagent.
- **Security Rules**:
  - 🚫 Never expose AK/SK values in code, conversation, or output
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_AK`, `HUAWEI_SK`, `HUAWEI_REGION`
  - ✅ Prefer IAM users over root account for cloud operations

**Configuration Method** (Environment Variables):

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

### 3. IAM Permission Requirements

| API Action | Permission | Purpose |
|------------|------------|---------|
| `cce:cluster:get` | Get cluster | View cluster details |
| `cce:logConfig:list` | List LogConfig | Query LogConfig collection rules |
| `cce:logConfig:create` | Create LogConfig | Create log collection rules |
| `cce:logConfig:delete` | Delete LogConfig | Remove log collection rules |
| `lts:logs:list` | List LTS logs | Query log streams and log records |
| `lts:groups:list` | List LTS groups | Query log group information |
| `lts:accessConfig:list/create/delete` | Manage LTS Access Config | Inspect and manage LTS collection rules |

## Security Constraints

### Dangerous Operation Confirmation Mechanism

> **This skill enforces a preview-then-confirm mechanism for all mutating operations.**

| Operation | Risk Level | Description |
|-----------|------------|-------------|
| `huawei_create_cce_logconfig` | 🟡 Medium | Creates a container stdout, container file, or node file LogConfig rule; preview by default, create with `confirm=true` |
| `huawei_delete_cce_logconfig` | 🟠 High | Deletes a LogConfig collection rule; preview by default, delete with `confirm=true` |
| `huawei_create_lts_access_config` | 🟡 Medium | Creates an LTS Access Config; preview by default, create with `confirm=true` |
| `huawei_delete_lts_access_config` | 🟠 High | Deletes an LTS Access Config and stops its collection; preview by default, delete with `confirm=true` |

**Process**: Call without `confirm=true` → inspect preview output → user confirms → call with `confirm=true`

### Credential & Data Security

- **Never expose** AK/SK, tokens, kubeconfig certificates, or full sensitive log payloads in summaries
- **Redact** tokens, passwords, cookies, authorization headers, and personally identifiable data from log output
- **Prefer time-bounded queries** — if no time range provided, use recent logs with small limits

### Scope Boundaries

- This skill is **read-only by default** for log queries and LogConfig inspection
- Creating/deleting LogConfig or LTS Access Config is allowed **only** through the dedicated tools with `confirm=true`
- **Do not** modify workloads, LTS groups/streams, LTS data, or other cloud resources
- If logs indicate failures, **hand off** to the relevant diagnosis skill with evidence, do not remediate here

## Scenario Routing

| User Intent | Tool(s) | Reference Document |
|-------------|----------|-------------------|
| Query Pod stdout/stderr logs | `huawei_get_pod_stdout_logs` | [references/workflow.md](references/workflow.md) |
| Sample and analyze newly produced Pod stdout logs | `huawei_analyze_pod_stdout_realtime_logs` | [references/workflow.md](references/workflow.md) |
| Query previous terminated container logs | `huawei_get_pod_stdout_logs` (previous=true) | [references/workflow.md](references/workflow.md) |
| List cluster LogConfig rules | `huawei_get_cce_logconfigs`; requires the Cloud Native Logging add-on | [references/workflow.md](references/workflow.md) |
| Create LogConfig for stdout/file collection | `huawei_create_cce_logconfig`; requires the Cloud Native Logging add-on | [references/workflow.md](references/workflow.md) |
| Delete a LogConfig rule | `huawei_delete_cce_logconfig`; requires the Cloud Native Logging add-on | [references/workflow.md](references/workflow.md) |
| List LTS Access Config rules | `huawei_list_lts_access_configs` | [references/workflow.md](references/workflow.md) |
| Create an LTS Access Config | `huawei_create_lts_access_config` | [references/workflow.md](references/workflow.md) |
| Delete an LTS Access Config | `huawei_delete_lts_access_config` | [references/workflow.md](references/workflow.md) |
| Query audit logs for Pod deletion | `huawei_query_cce_audit_logs` | [references/workflow.md](references/workflow.md) |
| Query audit logs for workload changes | `huawei_query_cce_audit_logs` | [references/workflow.md](references/workflow.md) |
| Analyze Pod or workload audit change timelines | `huawei_analyze_cce_audit_timeline` | [references/workflow.md](references/workflow.md) |
| Query application logs by recent window or explicit time range | `huawei_query_application_logs` | [references/workflow.md](references/workflow.md) |
| Analyze logs for abnormalities | `huawei_analyze_application_logs` | [references/workflow.md](references/workflow.md) |
| Risk constraints & guardrails | — | [references/risk-rules.md](references/risk-rules.md) |
| Output schema reference | — | [references/output-schema.md](references/output-schema.md) |

## Core Commands

Before `huawei_query_application_logs` or `huawei_analyze_application_logs`, first list the target cluster's collection rules with `huawei_get_cce_logconfigs` and `huawei_list_lts_access_configs`. Show the CCE LogConfig rules and only the LTS Access Config rules whose `cluster_id` equals the target cluster. Wait for the user to select exactly one rule; never infer the selection from the workload name, rule name, or match score.

### 1. Kubernetes Pod Stdout Logs

```bash
# Query recent stdout from a Pod
python3 scripts/huawei-cloud.py huawei_get_pod_stdout_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=default \
  pod_name=<pod-name> \
  tail_lines=200

# Query previous terminated container logs
python3 scripts/huawei-cloud.py huawei_get_pod_stdout_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=default \
  pod_name=<pod-name> \
  container=<container-name> \
  previous=true \
  tail_lines=200

# Sample a Pod twice and analyze only logs produced during the interval
python3 scripts/huawei-cloud.py huawei_analyze_pod_stdout_realtime_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=default \
  pod_name=<pod-name> \
  wait_seconds=30 \
  tail_lines=200
```

### 2. LogConfig Discovery & Management

```bash
# List all LogConfig resources in a cluster
python3 scripts/huawei-cloud.py huawei_get_cce_logconfigs \
  region=cn-north-4 \
  cluster_id=<cluster-id>


# Preview then create a workload stdout LogConfig
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=container_stdout \
  workload_namespace=default \
  workload_name=<workload-name> \
  workload_kind=Deployment \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>
# Then call again with confirm=true after user confirms

# Preview then create a container file LogConfig
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=container_file \
  workload_namespace=default \
  workload_name=<workload-name> \
  workload_kind=Deployment \
  container=<container-name> \
  log_path=/var/log \
  file_pattern="*.log" \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>

# Preview then create a node file LogConfig for all cluster nodes
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=host_file \
  log_path=/var/log/messages \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>
# Then call again with confirm=true after user confirms

# Preview then delete a LogConfig
python3 scripts/huawei-cloud.py huawei_delete_cce_logconfig \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  logconfig_namespace=kube-system
# Then call again with confirm=true after user confirms
```

### 3. CCE Audit Logs

```bash
# Query Pod deletion audit events
python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  audit_type=pod_delete \
  namespace=default \
  hours=6 \
  log_group_id=<audit-lts-group-id> \
  log_stream_id=<audit-lts-stream-id>

# Query workload change audit events
python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  audit_type=workload_change \
  namespace=default \
  start_time="2026-05-30 10:00:00" \
  end_time="2026-05-30 11:00:00"

# Analyze audit lifecycle for a workload or Pod
python3 scripts/huawei-cloud.py huawei_analyze_cce_audit_timeline \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=default \
  resource_name=<pod-or-workload-name> \
  resources=pods,deployments,statefulsets \
  hours=24
```

### 4. Application Log Query & Analysis

```bash
# Query application logs with a user-selected CCE LogConfig
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<selected-logconfig-name> \
  logconfig_namespace=kube-system \
  hours=1 \
  keywords=ERROR \
  auto_paginate=true \
  max_pages=5 \
  limit=100

# Analyze an LTS Access Config log window for abnormal logs
python3 scripts/huawei-cloud.py huawei_analyze_application_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  access_config_id=<selected-access-config-id> \
  start_time="2026-05-30 10:00:00" \
  end_time="2026-05-30 11:00:00" \
  auto_paginate=true \
  max_pages=5 \
  limit=1000
```

## Parameter Reference

### Common Parameters

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `region` | Yes | Huawei Cloud region ID | `cn-north-4` |
| `cluster_id` | Yes | CCE cluster ID | — |
| `namespace` | Most tools | Kubernetes namespace | `default` |

### Pod Log Parameters

| Parameter | Tool | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `pod_name` | Pod log tools | Yes | Pod name | Must reference existing Pod |
| `container` | Pod log tools | No | Container name | Required for multi-container Pods |
| `previous` | `huawei_get_pod_stdout_logs` | No | Previous terminated container | `true`/`false` |
| `tail_lines` | `huawei_get_pod_stdout_logs` | No | Number of most recent log lines | Default 1000; recommended 100-1000 |
| `tail_lines` | `huawei_analyze_pod_stdout_realtime_logs` | No | Number of recent lines per sample | Default 100; recommended 100-500 |
| `wait_seconds` | `huawei_analyze_pod_stdout_realtime_logs` | No | Delay between the two samples | Default 30; range 1-300 |

### LogConfig Parameters

| Parameter | Tool | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `logconfig_name` | create/delete | Yes | LogConfig policy name | Unique within namespace |
| `source_type` | create | Yes | Collection source type | `container_stdout`, `container_file`, or `host_file` |
| `workload_name` | create | Yes | Target workload name | Must reference existing workload |
| `workload_kind` | create | Yes | Workload type | `Deployment`, `StatefulSet`, `DaemonSet` |
| `workload_namespace` | create | Yes | Workload namespace | — |
| `container` | create (file) | No | Container name | Required for container_file |
| `log_path` | create (file) | No | Log directory or complete file path | Required for `container_file` and `host_file`; without `file_pattern`, a path not ending in `/` is treated as a complete file path |
| `file_pattern` | create (file) | No | File name pattern | e.g. `*.log`; pass it when `log_path` is a directory, otherwise it is inferred from the complete path |
| `log_group_id` / `log_stream_id` | create | Yes to create | LTS destination IDs | Provide both explicitly. When both are omitted, the tool lists only `k8s-log-<cluster-id>` and its streams; it never creates or selects a destination. Create a missing group or stream with hcloud, then provide both IDs. |
| `confirm` | create/delete | No | Execute confirmation | Preview without it; `true` to execute |
| `logconfig_namespace` | delete | Yes | LogConfig namespace | — |

### LTS Access Config Parameters

| Parameter | Tool | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `access_config_name` | create/list | Create: Yes | Access Config name | Unique in the LTS project |
| `access_config_id` | delete | Yes | Access Config ID | Get it from `huawei_list_lts_access_configs` |
| `access_config_type` | create | No | LTS access type | `K8S_CCE` or `AGENT`; hcloud is used only for `AGENT` |
| `cluster_id` | create | Conditional | CCE cluster ID | Required for `K8S_CCE` and CCE-related `AGENT` collection |
| `path_type` | create | Conditional | CCE source type | `K8S_CCE` supports `CONTAINER_STDOUT`; `AGENT` supports `CONTAINER_STDOUT`, `CONTAINER_FILE`, or `HOST_FILE` |
| `paths` | create | Conditional | Collection paths | Omit for `K8S_CCE` stdout; `AGENT` stdout defaults to `/var/log/containers`, and `AGENT` file collection requires paths |
| `format_mode` / `format_value` | create | No / Conditional | LTS log timestamp format | `system` by default and sends the current timestamp; set `wildcard` with a required `format_value` time pattern when logs include a parseable timestamp |
| `namespace_regex` | create | Conditional | Namespace filter | Required for `K8S_CCE` |
| `pod_name_regex` | create | Conditional | Pod-name filter | Required for `K8S_CCE` |
| `container_name_regex` | create | No | Container-name filter | Defaults to `^.*$` to match all containers; set an explicit regex to narrow the scope |
| `host_group_id` | create | No | LTS host group | `K8S_CCE` auto-discovers the exact `k8s-log-<cluster-id>` group; provide this only when the standard group cannot be discovered |
| `stdout` / `stderr` | create | No | Stdout/stderr switches | Both default to true for `K8S_CCE`; `AGENT` stdout defaults to true and stderr to false |
| `log_group_id` / `log_stream_id` | create | Yes to create | LTS destination | Provide both explicitly. When both are omitted with `cluster_id`, the tool only lists the exact `k8s-log-<cluster-id>` group and its streams; it never creates or selects a destination. If none exists, create the group and stream with hcloud first, then provide both IDs. |
| `confirm` | create/delete | No | Execute confirmation | Preview without it; `true` to execute |

### Audit Log Parameters

| Parameter | Tool | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `audit_type` | `huawei_query_cce_audit_logs` | No | Keyword preset | `pod_delete` or `workload_change` |
| `resource_name` | audit tools | No | Pod or workload name | Filters a single resource name |
| `resources` | audit tools | No | Resource type list | e.g. `pods,deployments,statefulsets` |
| `verbs` | audit timeline | No | Audit verbs to retain | Defaults to mutating verbs only |
| `include_read_events` | audit timeline | No | Include get/list/watch events | `true`/`false`, default `false` |
| `timeline_limit` | audit timeline | No | Maximum events in timeline | Default 500 |
| `hours` | audit | No | Recent hours window | Used when no start_time/end_time |
| `start_time` | audit | No | Start time | UTC `YYYY-MM-DD HH:MM:SS` format |
| `end_time` | audit | No | End time | UTC `YYYY-MM-DD HH:MM:SS` format |
| `log_group_id` | audit | Recommended | Audit LTS group ID | Defaults to `k8s-log-<cluster-id>` lookup if omitted |
| `log_stream_id` | audit | Recommended | Audit LTS stream ID | Defaults to `audit-<cluster-id>` lookup if omitted |

### Application Log Parameters

| Parameter | Tool | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `app_name` | application log destination discovery/query/analysis | Discovery: Yes | Workload name | Optional label filter for query/analysis |
| `logconfig_name` | application log query/analysis | One selector: Yes | Selected CCE LogConfig | Resolves its LTS destination; use `logconfig_namespace` when the name is not unique |
| `access_config_name` / `access_config_id` | application log query/analysis | One selector: Yes | Selected LTS Access Config | Resolves its LTS destination and verifies the cluster ID |
| `logconfig_namespace` | application log query/analysis | Conditional | CCE LogConfig namespace | Required when more than one matching LogConfig name exists |
| `keywords` | app log tools | No | Keyword filter | LTS keyword search |
| `hours` | application logs | No | Recent hours window | Used when no explicit time range is supplied; default 1 |
| `start_time` | application logs | No | Start time | UTC `YYYY-MM-DD HH:MM:SS`; takes precedence with `end_time` |
| `end_time` | application logs | No | End time | UTC `YYYY-MM-DD HH:MM:SS`; takes precedence with `start_time` |
| `auto_paginate` | app log tools | No | Enable pagination | `true`/`false` |
| `max_pages` | app log tools | No | Max pages to fetch | Caps total work when paginating |
| `limit` | LTS list and app log tools | No | Result limit (per page for log queries) | Optional for groups/streams; recommended 100-1000 for logs |

## Common Region IDs

| Region Name | Region ID |
|-------------|-----------|
| North China - Beijing 4 | `cn-north-4` |
| North China - Beijing 1 | `cn-north-1` |
| East China - Shanghai 1 | `cn-east-3` |
| East China - Shanghai 2 | `cn-east-2` |
| South China - Guangzhou | `cn-south-1` |
| South China - Shenzhen | `cn-south-4` |
| Southwest China - Guiyang 1 | `cn-southwest-2` |
| Asia Pacific - Bangkok | `ap-southeast-2` |
| Asia Pacific - Singapore | `ap-southeast-1` |
| Asia Pacific - Hong Kong | `ap-southeast-3` |
| Europe - Paris | `eu-west-0` |

## Best Practices

1. **Narrowest scope first** — use Pod stdout when the user names a Pod, application LTS logs when they name a workload
2. **Recent windows before broad searches** — prefer `hours=1`; use the 1000-line Pod-log default unless a narrower sample is sufficient
3. **Resolve the LTS destination** — first list all target-cluster LogConfig and LTS Access Config rules, show them to the user, and use only the rule the user selects. The application log tools resolve that selected rule's LTS group and stream.
4. **Preview before mutating** — always call create/delete LogConfig without `confirm=true` first; only call with `confirm=true` after user reviews the preview
5. **Use auto_paginate for multi-page results** — set `auto_paginate=true` with `max_pages` to cap total work; `limit` controls per-page size
6. **Redact sensitive data** — never include tokens, passwords, cookies, authorization headers, or PII in log summaries
7. **Group repeated patterns** — when summarizing logs, group repeated lines by pattern and include counts
8. **Hand off for remediation** — if logs indicate Pod startup, image pull, scheduling, node, or network failures, recommend the corresponding diagnosis skill with exact evidence

## Common Pitfalls

| Pitfall | Symptom | Quick Fix |
|---------|---------|-----------|
| Missing LogConfig for app | No LTS stream found | Create LogConfig with `huawei_create_cce_logconfig` |
| Wrong log collection rule | Logs from wrong stream | List cluster LogConfig and LTS Access Config rules, then ask the user to select one |
| keywords filter skews analysis ratios | Abnormal ratio too high/low | Do not set `keywords` unless user explicitly wants keyword-scoped ratios |
| Audit type misunderstood | Audit results too broad/narrow | `audit_type` is keyword preset only; `pod_delete` adds `delete+pods`, `workload_change` adds workload-related keywords |
| No confirm=true on create/delete | Preview-only, no actual change | Call again with `confirm=true` after reviewing preview |
| Large time window without pagination | Partial or slow results | Use `auto_paginate=true` with `max_pages` and reasonable `limit` |
| Previous container log not found | "previous" flag on running container | Use `previous=true` only when container has restarted; check Pod status first |
| AK/SK exposed in output | Credential leak | Redact all credentials; summarize patterns instead of raw values |

## Notes

- **LogConfig tools are the only mutation path** — creating and deleting LogConfig resources is only supported through `huawei_create_cce_logconfig` and `huawei_delete_cce_logconfig` with `confirm=true`
- **Audit logs are keyword-based** — `huawei_query_cce_audit_logs` uses pure keyword search over LTS audit content; all convenience parameters (`pod_name`, `resource_name`, `workload_name`, `namespace`, `user`, `verb`, `resource`, `status_code`) are converted into keywords, not parsed-field filters
- **stdout vs container_file** — use `source_type=container_stdout` for Pod standard output, `source_type=container_file` for application file logs collected from paths like `/var/log/*.log`
- **host_file collection scope** — use `source_type=host_file` for node-local files. CCE applies the rule to every cluster node; the LogConfig API does not provide a node selector, so confirm the path and cluster scope before creation.
- **Analysis tool denominator** — `huawei_analyze_application_logs` calculates ratios over the queried log set; adding `keywords` changes the denominator to only matched logs, so avoid it unless explicitly requested
- **Analysis returns** — abnormal ratio, log rates, first/last abnormal time, observed recovery time, incident windows, top patterns, status-code distribution, and samples

## Output Format

All tools return JSON with structured log data, analysis results, or LogConfig previews. See [references/output-schema.md](references/output-schema.md) for detailed response schemas.

## Verification

1. Run environment check script
2. Query a known Pod log with huawei_get_recent_logs
3. Verify the LogConfig preview/confirm workflow
4. Confirm read-only behavior for query operations

## Reference Documents

| Document | Description |
|----------|-------------|
| [workflow.md](references/workflow.md) | Detailed workflow for Pod stdout, application LTS logs, LogConfig management, and audit queries |
| [risk-rules.md](references/risk-rules.md) | Risk constraints, security rules, and scope boundaries |
| [output-schema.md](references/output-schema.md) | Log query and analysis output schema reference |
