---
name: log-analyzer
description: Use this skill to query and analyze Kubernetes Pod stdout logs, CCE LogConfig-collected application logs, node file logs, and Huawei Cloud LTS logs.
---

# Log Analyzer

Query and analyze Kubernetes standard output logs and Huawei Cloud LTS logs for CCE workloads.

This skill reuses the shared Huawei Cloud dispatcher in `scripts/huawei-cloud.py`; implementation code lives in:

- `scripts/huawei_cloud/cce.py` for Kubernetes Pod stdout logs through `kubectl` / `kubectl cce` (`huawei_get_pod_stdout_logs`)
- `scripts/huawei_cloud/cce_app_logs.py` for CCE LogConfig discovery and management through `kubectl` / `kubectl cce`, plus application log stream matching
- `scripts/huawei_cloud/lts.py` for LTS log group, stream, and log queries through `hcloud`

**LTS Resource Management**: This skill does not expose LTS group or stream creation tools. When a log group or stream must be discovered, use `hcloud LTS ListLogGroups` and `hcloud LTS ListLogStreams`; when one must be created, use `hcloud LTS CreateLogGroup` or `hcloud LTS CreateLogStream` after the required confirmation. Pass the resulting IDs to `huawei_create_cce_logconfig` or `huawei_create_lts_access_config`.

## 日志采集方式

| 方式 | 配置资源 | 依赖 | 对应工具 | 建议 |
|------|----------|------|----------|------|
| 云原生日志采集 | CCE 集群内的 `LogConfig` | 云原生日志采集插件 | `huawei_get_cce_logconfigs`、`huawei_create_cce_logconfig`、`huawei_delete_cce_logconfig` | 适用于 CCE 工作负载日志采集和 Kubernetes 内的采集策略管理。[CCE 文档](https://support.huaweicloud.com/usermanual-cce/cce_10_0416.html) |
| LTS Access Config 日志采集 | LTS Access Config | `K8S_CCE` 的 CCE stdout 通过官方 LTS SDK 创建；`AGENT` 采集要求 iCagent 状态正常 | `huawei_list_lts_access_configs`、`huawei_create_lts_access_config`、`huawei_delete_lts_access_config` | CCE 容器标准输出使用 `K8S_CCE`；高吞吐或文件采集选择基于 iCagent 的 `AGENT`。[LTS 文档](https://support.huaweicloud.com/usermanual-lts/lts_07_1118.html) |

## Scope

Use this skill when the user asks to:

- Query Kubernetes Pod standard output or previous container logs
- Inspect CCE LogConfig resources for stdout collection
- Create CCE LogConfig resources for container stdout, container file, or node file collection
- Delete CCE LogConfig resources when the user explicitly asks to remove log collection rules
- Find the LTS log group/stream for an application or namespace
- Query CCE Kubernetes audit logs for Pod deletion or workload change events
- Query LTS logs by time range, recent hours, keywords, or labels
- Analyze returned logs for repeated errors, stack traces, restarts, or failure clues

Do not use this skill to modify workloads, LTS groups/streams, LTS data, or other cloud resources. Creating or deleting LogConfig and LTS Access Config resources is supported only through the dedicated tools and must use `confirm=true` after preview.

LTS 应用日志和审计日志的 `start_time`、`end_time` 使用 UTC 的 `YYYY-MM-DD HH:MM:SS` 格式；未传入时，工具也会按 UTC 生成最近时间窗口。

## Tools

| Tool | Purpose | Required parameters |
|------|---------|---------------------|
| `huawei_get_pod_stdout_logs` | Query Kubernetes Pod stdout/stderr through `kubectl` or `kubectl cce` | `region`, `cluster_id`, `pod_name` |
| `huawei_analyze_pod_stdout_realtime_logs` | Sample a running Pod twice and analyze only newly produced stdout logs | `region`, `cluster_id`, `pod_name` |
| `huawei_list_lts_access_configs` | List LTS Access Config collection rules through `hcloud` | `region` |
| `huawei_create_lts_access_config` | Create an LTS Access Config; first discovers only `k8s-log-<cluster-id>` and its streams when the destination IDs are omitted, then requires the user to provide both IDs; preview by default, create with `confirm=true` | `region`, `access_config_name`; `log_group_id` and `log_stream_id` are both required before creation |
| `huawei_delete_lts_access_config` | Delete an LTS Access Config through `hcloud`; preview by default, delete with `confirm=true` | `region`, `access_config_id` |
| `huawei_get_cce_logconfigs` | List CCE LogConfig resources in a cluster; requires the Cloud Native Logging add-on | `region`, `cluster_id` |
| `huawei_create_cce_logconfig` | Create a CCE LogConfig for container stdout, container file, or node file collection. If destination IDs are omitted, only discovers `k8s-log-<cluster-id>` and its streams; user must provide both IDs before preview. Requires the Cloud Native Logging add-on; preview by default, create with `confirm=true` | `region`, `cluster_id`, `logconfig_name`, `source_type`; `log_group_id` and `log_stream_id` are both required before creation |
| `huawei_delete_cce_logconfig` | Delete a CCE LogConfig by name; requires the Cloud Native Logging add-on; preview by default, delete with `confirm=true` | `region`, `cluster_id`, `logconfig_name` |
| `huawei_query_cce_audit_logs` | Query CCE audit logs from LTS and summarize Pod deletion, workload changes, verbs, users, resources, namespaces, and response codes | `region`, `cluster_id` |
| `huawei_analyze_cce_audit_timeline` | Analyze Pod or workload audit change timelines from LTS audit logs | `region`, `cluster_id` |
| `huawei_query_application_logs` | 查询应用日志；用户选择一个 CCE LogConfig 或 LTS Access Config，工具解析其日志组和日志流 | `region`, `cluster_id`, `logconfig_name` 或 `access_config_name`/`access_config_id` |
| `huawei_analyze_application_logs` | 分析应用日志；用户选择一个 CCE LogConfig 或 LTS Access Config，工具解析其日志组和日志流 | `region`, `cluster_id`, `logconfig_name` 或 `access_config_name`/`access_config_id` |

在调用 `huawei_query_application_logs` 或 `huawei_analyze_application_logs` 前，必须先调用 `huawei_get_cce_logconfigs` 和 `huawei_list_lts_access_configs` 查询目标集群的日志采集规则。向客户展示该集群的 CCE LogConfig，以及 `cluster_id` 等于目标集群 ID 的 LTS Access Config；等待客户明确选择一条规则后再查询或分析，禁止根据应用名、规则名或匹配结果自动选择。

## Examples

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

# Preview then delete a LogConfig
python3 scripts/huawei-cloud.py huawei_delete_cce_logconfig \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  logconfig_namespace=kube-system

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

# Query recent application logs after the user selects a destination
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<selected-logconfig-name> \
  hours=1 \
  keywords=ERROR \
  auto_paginate=true \
  max_pages=5 \
  limit=100

# Analyze an application log window for abnormal logs
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

## Analysis Guidance

- Kubernetes resource access first uses an externally reachable cluster endpoint with a temporary kubeconfig and `kubectl`; if that route is unavailable, it falls back to `kubectl cce`. Ensure `kubectl` and the `kubectl-cce` plugin are installed before using Pod or LogConfig tools. `huawei_get_cce_logconfigs`, `huawei_create_cce_logconfig`, and `huawei_delete_cce_logconfig` also require the Cloud Native Logging add-on, which supplies the `logconfigs.logging.openvessel.io` resource.
- `huawei_list_lts_access_configs`、`huawei_create_lts_access_config` 和 `huawei_delete_lts_access_config` 管理 LTS Access Config。hcloud 的 `CreateAccessConfig` 本地 schema 仅支持 `AGENT`，因此 `K8S_CCE` 创建使用 AK/SK 和 project ID 调用官方 LTS SDK；`AGENT` 创建仍使用 hcloud。创建 `K8S_CCE` 时，工具会按 `k8s-log-<cluster-id>` 自动发现并绑定集群主机组；未传 `container_name_regex` 时，默认使用 `^.*$` 匹配全部容器，用户可传入更精确的正则缩小范围。采集 `AGENT` 类型的 CCE 应用或节点日志时，目标集群必须先安装且 iCagent 状态正常。创建 Access Config 不会自动安装 iCagent。
- Start with the narrowest useful scope: pod/container stdout first when the user names a pod, application LTS logs when they name a workload.
- Prefer recent windows (`hours=1`). `huawei_get_pod_stdout_logs` returns 1000 recent lines by default; use a smaller `tail_lines` value when a narrower sample is sufficient.
- Before application log query or analysis, list all target-cluster LogConfig and LTS Access Config rules, show them to the user, and use only the rule the user selects. The application log tools resolve the selected rule's LTS log group and stream.
- For LogConfig creation, first call without `confirm=true` and inspect `request_body`. Only call again with `confirm=true` after the user confirms the generated LogConfig.
- For LogConfig deletion, first call without `confirm=true` and inspect the returned `existing` target summary. Only call again with `confirm=true` after the user confirms the exact `logconfig_name` and namespace.
- Use `huawei_query_cce_audit_logs` for Kubernetes audit questions. It is pure keyword search over audit log content: `pod_name`, `resource_name`, `workload_name`, `namespace`, `user`, `verb`, `resource`, and `status_code` are all converted into query/content keywords instead of parsed-field filters.
- Use `audit_type=pod_delete` or `audit_type=workload_change` only as keyword presets. For example `pod_delete` adds `delete` and `pods`; the result is still based on keyword matching.
- Use the stdout policy for container standard output, use a `container_file` policy for application file logs, and use `host_file` for node-local files. A `host_file` rule applies to every cluster node because CCE LogConfig does not provide a node selector; always preview and confirm the cluster-wide path.
- Use `auto_paginate=true` when the user needs more than one LTS page. Keep `limit` as the per-page size and set `max_pages` to cap total work.
- Use `huawei_analyze_application_logs` when the user asks whether a time range contains exceptions, errors, recovery, abnormal proportions, or incident timing. Avoid adding `keywords` unless the user wants to analyze only logs matched by that keyword, because ratios are calculated over the queried log set.
- When summarizing logs, group repeated lines by pattern and include counts when possible.
- Redact tokens, passwords, cookies, authorization headers, and personally identifiable data.
- If logs point to Pod startup, image pull, scheduling, node, or network failures, recommend the corresponding diagnosis skill with the exact evidence found.

## References

- Workflow: `references/workflow.md`
- Risk rules: `references/risk-rules.md`
- Output schema: `references/output-schema.md`
