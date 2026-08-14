# Workflow

## Kubernetes Pod Stdout Logs

1. Identify `region`, `cluster_id`, `namespace`, `pod_name`, and optional `container`.
2. Use `huawei_get_pod_stdout_logs` for stdout/stderr retrieval through `kubectl`. It first uses a temporary kubeconfig for an externally reachable cluster endpoint, then falls back to `kubectl cce`.
3. Use `tail_lines` for focused recent output; use `previous=true` for a previously terminated container.
4. Summarize errors, warnings, stack traces, restarts, or repeated messages.
5. If logs indicate Pod startup, image pull, scheduling, node, or network failures, hand off to the relevant diagnosis skill with exact evidence.

**Example workflow**:

```
User: "Check Pod my-app-xyz123 logs for errors"
  → huawei_get_pod_stdout_logs (tail_lines=200)
  → Summarize: 3 OOMKilled restarts, last crash at 2026-05-30 10:15
  → Recommend: huawei-cloud-cce-pod-failure-diagnoser (OOM pattern detected)
```

## CCE Application Logs Through LTS

All explicit `start_time` and `end_time` values for LTS application and audit log queries use UTC in `YYYY-MM-DD HH:MM:SS` format. When omitted, the tools generate the recent time window in UTC.

### Step 1: List Cluster Collection Rules

Before querying or analyzing application logs, always list both collection-rule types for the target cluster. Do this even when the user already names an application, so the user can see and select the actual configured collection rule.

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_logconfigs \
  region=cn-north-4 \
  cluster_id=<cluster-id>

python3 scripts/huawei-cloud.py huawei_list_lts_access_configs \
  region=cn-north-4
```

Show all returned CCE LogConfig rules for the cluster. From the LTS response, show only rules whose `cluster_id` equals the target cluster ID. Do not choose a rule based on a matching workload, namespace, policy name, or destination.

### Step 2: User Selects the Collection Rule

Show the two rule lists from step 1 to the user. The user must select exactly one collection rule; do not select a rule automatically, including when the rule name appears to match the workload.

Selection guidance:
- Use **stdout policies** for standard output logs
- Use **container_file policies** for file logs collected from configured paths (e.g., `/var/log/*.log`)
- For a CCE LogConfig, pass `logconfig_name` and `logconfig_namespace` when needed.
- For an LTS Access Config, pass `access_config_id` (or an unambiguous `access_config_name`).

### Step 3: Query Application Logs

`huawei_query_application_logs` requires one user-selected CCE LogConfig or LTS Access Config. It resolves that rule's LTS destination internally, and never chooses a rule.

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<selected-logconfig-name> \
  logconfig_namespace=kube-system \
  hours=1
```

For **recent logs** (time window in hours):

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  access_config_id=<selected-access-config-id> \
  namespace=default \
  app_name=<workload-name> \
  hours=1
```

For **explicit time windows**:

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<selected-logconfig-name> \
  namespace=default \
  app_name=<workload-name> \
  start_time="2026-05-30 10:00:00" \
  end_time="2026-05-30 11:00:00"
```

### Step 4: Paginate Large Results

Use `auto_paginate=true` when more than one LTS page is needed. `limit` controls per-page size and `max_pages` caps total pages fetched.

```bash
python3 scripts/huawei-cloud.py huawei_query_application_logs \
  ... \
  auto_paginate=true \
  max_pages=5 \
  limit=100
```

### Step 5: Analyze for Abnormalities

Use `huawei_analyze_application_logs` for time-window abnormality analysis. It requires one user-selected CCE LogConfig or LTS Access Config, detects exception/error/fatal/timeout/OOM patterns and HTTP 5xx status codes, then returns:

- Abnormal ratio
- Log rates (total and abnormal per time unit)
- First/last abnormal timestamp
- Observed recovery time
- Incident windows
- Top abnormal patterns
- Status-code distribution
- Redacted samples

**Important**: Do not set `keywords` unless the user explicitly wants a keyword-scoped ratio. Keyword filtering changes the denominator to only matched logs, which distorts the abnormal ratio.

```bash
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

## LogConfig Management

`huawei_get_cce_logconfigs`, `huawei_create_cce_logconfig`, and `huawei_delete_cce_logconfig` use the CCE Cloud Native Logging collection mode. They require the Cloud Native Logging add-on to be installed and running in the target cluster. The add-on provides the `logconfigs.logging.openvessel.io` resource used by these tools. Install or recover the add-on before attempting LogConfig discovery or mutation. See the [CCE Cloud Native Logging documentation](https://support.huaweicloud.com/usermanual-cce/cce_10_0416.html).

### List LogConfig Resources

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_logconfigs \
  region=cn-north-4 \
  cluster_id=<cluster-id>
```

### Create a LogConfig (Preview → Confirm)

Before previewing a creation, call the tool without `log_group_id` or `log_stream_id`. It lists only the target cluster's `k8s-log-<cluster-id>` group and its streams. The user must select a stream and explicitly provide both IDs in the next call. The tool never creates or selects LTS destinations. If the group or stream is missing, create it directly with `hcloud LTS CreateLogGroup` and `hcloud LTS CreateLogStream`, then provide the returned IDs.

1. Call without `confirm=true` to preview the generated `request_body`
2. Inspect the preview output with the user
3. Call with `confirm=true` only after user confirmation

```bash
# Step 1: Preview
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

# Step 2: Confirm (after user review)
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  ... \
  confirm=true
```

For **container file collection**:

```bash
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
```

For **node file collection** on every cluster node, use `source_type=host_file`. This mode has no node selector, so inspect the preview carefully before confirmation.

```bash
python3 scripts/huawei-cloud.py huawei_create_cce_logconfig \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  source_type=host_file \
  log_path=/var/log/messages \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>
```

### Delete a LogConfig (Preview → Confirm)

1. Call without `confirm=true` to preview the exact target summary
2. Inspect the returned `existing` LogConfig details with the user
3. Call with `confirm=true` only after user confirms the exact `logconfig_name` and namespace

```bash
# Step 1: Preview
python3 scripts/huawei-cloud.py huawei_delete_cce_logconfig \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  logconfig_name=<policy-name> \
  logconfig_namespace=kube-system

# Step 2: Confirm (after user review)
python3 scripts/huawei-cloud.py huawei_delete_cce_logconfig \
  ... \
  confirm=true
```

## LTS Access Config Management

Use these tools for LTS iCagent collection rules managed directly through the LTS API and hcloud. They are independent of CCE LogConfig resources. For CCE application or node collection, install iCagent in the target CCE cluster and verify it is healthy before creating an Access Config; rule creation does not install iCagent. Prefer this mode for high-throughput collection. See the [LTS iCagent documentation](https://support.huaweicloud.com/usermanual-lts/lts_07_1118.html).

### List Access Configs

```bash
python3 scripts/huawei-cloud.py huawei_list_lts_access_configs \
  region=cn-north-4
```

### Create an Access Config (Preview -> Confirm)

Before previewing a creation, discover the destination with `region`, `access_config_name`, and `cluster_id`, without `log_group_id` or `log_stream_id`. The tool lists only the cluster-specific log group named `k8s-log-<cluster-id>` and its streams. The user must select a destination and explicitly provide both IDs in the next call. It never creates a log group or log stream and never chooses one on the user's behalf. If the group or stream does not exist, create it directly with hcloud, then provide the returned IDs:

```bash
hcloud LTS CreateLogGroup --cli-region=<region> \
  --log_group_name=k8s-log-<cluster-id> --ttl_in_days=<1-365>
hcloud LTS CreateLogStream --cli-region=<region> \
  --log_group_id=<lts-group-id> --log_stream_name=<stream-name>
```

For CCE stdout collection:

```bash
# Step 1: Preview
python3 scripts/huawei-cloud.py huawei_create_lts_access_config \
  region=cn-north-4 \
  access_config_name=<access-config-name> \
  access_config_type=K8S_CCE \
  cluster_id=<cluster-id> \
  path_type=CONTAINER_STDOUT \
  namespace_regex='^default$' \
  pod_name_regex='<pod-name-regex>' \
  log_group_id=<lts-group-id> \
  log_stream_id=<lts-stream-id>

# Step 2: Execute only after user confirmation
python3 scripts/huawei-cloud.py huawei_create_lts_access_config \
  ... \
  confirm=true
```

`K8S_CCE` creation uses the official LTS SDK because hcloud rejects that enum locally. It requires `cluster_id`, `namespace_regex`, and `pod_name_regex`, supports only `CONTAINER_STDOUT`, omits `paths`, and collects both stdout and stderr unless either switch is explicitly set to false. It defaults `container_name_regex` to `^.*$` to match all containers; provide an explicit regex when the scope must be narrowed. It automatically discovers and attaches the exact LTS host group named `k8s-log-<cluster-id>`; provide `host_group_id` only when that standard group cannot be discovered. It uses LTS single-line `format_mode=system` with the current timestamp and requires explicit AK/SK and project ID (or their supported environment variables). Provide `format_mode=wildcard` and `format_value=<time-pattern>` only when logs contain a timestamp that must be parsed.

Use `access_config_type=AGENT` for hcloud and iCagent collection. `AGENT` stdout defaults `paths` to `/var/log/containers`; file collection requires `path_type=CONTAINER_FILE` or `path_type=HOST_FILE` and explicit paths such as `/var/log/messages`. Node-file collection applies to every applicable cluster node; no node selector is available in this API.

### Delete an Access Config (Preview -> Confirm)

First use `huawei_list_lts_access_configs` to obtain the exact `access_config_id`.

```bash
# Step 1: Preview
python3 scripts/huawei-cloud.py huawei_delete_lts_access_config \
  region=cn-north-4 \
  access_config_id=<access-config-id>

# Step 2: Execute only after user confirmation
python3 scripts/huawei-cloud.py huawei_delete_lts_access_config \
  ... \
  confirm=true
```

## CCE Audit Logs

Use `huawei_query_cce_audit_logs` for Kubernetes audit questions. It is pure keyword search over audit log content in LTS; all convenience parameters are converted into keywords and no parsed-field filtering is applied.

### Audit Type Presets

| `audit_type` | Keywords added | Use case |
|---------------|----------------|----------|
| `pod_delete` | `delete`, `pods` | Find Pod deletion events |
| `workload_change` | Workload-related keywords | Find Deployment/StatefulSet changes |

### Required vs Auto-Discovered Parameters

- The tool first calls `CCE ShowClusterConfig` and requires `audit.enable=true`.
- If LTS IDs are omitted, it resolves the exact group `k8s-log-<cluster-id>` and stream `audit-<cluster-id>` through hcloud.
- Explicit `log_group_id` and `log_stream_id` can be used when the standard LTS names are unavailable.

### Example: Pod Deletion Audit

```bash
python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  audit_type=pod_delete \
  namespace=default \
  hours=6 \
  log_group_id=<audit-lts-group-id> \
  log_stream_id=<audit-lts-stream-id>
```

### Example: Workload Change Audit

```bash
python3 scripts/huawei-cloud.py huawei_query_cce_audit_logs \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  audit_type=workload_change \
  namespace=default \
  start_time="2026-05-30 10:00:00" \
  end_time="2026-05-30 11:00:00"
```

### Analyze Resource Change Timeline

Use `huawei_analyze_cce_audit_timeline` to group retained audit events by resource and return observed create, update, patch, and delete times. It supports Pods and workload resources such as Deployments, StatefulSets, DaemonSets, Jobs, and CronJobs. It reports only evidence retained in audit logs and does not determine the resource's current state.

```bash
python3 scripts/huawei-cloud.py huawei_analyze_cce_audit_timeline \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=default \
  resource_name=<resource-name> \
  resources=deployments,statefulsets \
  hours=24
```

### Additional Audit Filter Parameters

All of these are converted into LTS keyword search terms, not structured filters:

| Parameter | Converted to keyword |
|-----------|---------------------|
| `pod_name` | Pod name in audit content |
| `resource_name` | Resource name in audit content |
| `workload_name` | Workload name in audit content |
| `namespace` | Namespace in audit content |
| `user` | User/actor in audit content |
| `verb` | Operation verb (create, delete, update, etc.) |
| `resource` | Resource type (pods, deployments, etc.) |
| `status_code` | Response status code in audit content |

## Analysis Strategy

- Start with the narrowest useful scope: Pod stdout first when the user names a Pod, application LTS logs when they name a workload
- Prefer recent windows (`hours=1`, `tail_lines=100-500`) before broad historical searches
- For workload-level LTS queries, first list target-cluster LogConfig and LTS Access Config rules, then wait for the user to select one
- When summarizing logs, group repeated lines by pattern and include counts when possible
- Redact tokens, passwords, cookies, authorization headers, and personally identifiable data
- If logs point to specific failures, recommend the corresponding diagnosis skill with exact evidence
