# Kubernetes Event Analyzer

Analyze Kubernetes events in Huawei Cloud CCE clusters to find warning events, anomalies, and failure patterns.

## Scope

Use this skill when the user asks to:

- Query Kubernetes events in a cluster or namespace
- Find Warning events (type=Warning) related to Pods, Nodes, Workloads, or Services
- Identify event patterns such as repeated ImagePullBackOff, Evictions, NodeNotReady, FailedScheduling
- Correlate events with specific workloads or time windows
- Summarize event trends and frequencies to support diagnosis

This skill is read-only. If events point to specific failures, hand off to the appropriate skill:
- Pod failures -> `pod-failure-diagnoser`
- Workload rollout issues -> `workload-failure-diagnoser`
- Node issues -> `node-failure-diagnoser`
- Service/Network issues -> `network-failure-diagnoser`

## Tools

| Tool | Purpose | Required parameters |
|------|---------|---------------------|
| `huawei_get_cce_events` | Query CCE Kubernetes events via K8s API | `region`, `cluster_id` |
| `huawei_query_k8s_events_from_lts` | Query K8s events from LTS log streams | `region`, `cluster_id`, `start_time`, `end_time` |

## Usage

### huawei_get_cce_events

Fetches raw Kubernetes events from the cluster API Server. All filtering is done client-side after fetching.

Supported API filters:
- `namespace` - filter by Kubernetes namespace
- `limit` - maximum number of events (default 500)

Unsupported filters (apply client-side):
- `event_type` (Warning/Normal)
- `reason` (FailedScheduling, ImagePullBackOff, etc.)
- `involved_object_kind` / `involved_object_name`
- time range (`hours`, `start_time`, `end_time`)

### huawei_query_k8s_events_from_lts

Queries K8s events that have been collected to LTS via Event→LTS LogConfig. Requires a LogConfig with event collection enabled and pointing to LTS output.

Required parameters:
- `region` - Huawei Cloud region
- `cluster_id` - CCE cluster ID
- `start_time` - Start time in `YYYY-MM-DD HH:MM:SS` format
- `end_time` - End time in `YYYY-MM-DD HH:MM:SS` format

Optional parameters:
- `keywords` - Filter events by keywords (matches reason/message)

If no Event→LTS LogConfig is found with events enabled, returns an error. In that case, use `huawei_get_cce_events` instead.

## Examples

### Query via K8s API (huawei_get_cce_events)

```bash
# Query all events in a cluster (namespace filter optional)
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 \
  cluster_id=<cluster-id>

# Query events in a specific namespace
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=default

# Limit event count
python3 scripts/huawei-cloud.py huawei_get_cce_events \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  limit=100
```

### Query via LTS (huawei_query_k8s_events_from_lts)

```bash
# Query events from LTS in a time window
python3 scripts/huawei-cloud.py huawei_query_k8s_events_from_lts \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  start_time="2026-05-30 06:00:00" \
  end_time="2026-05-30 08:00:00"

# Query with keyword filter
python3 scripts/huawei-cloud.py huawei_query_k8s_events_from_lts \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  start_time="2026-05-30 00:00:00" \
  end_time="2026-05-30 23:59:59" \
  keywords=FailedScheduling
```

## Analysis Guidance

1. Fetch events using `huawei_get_cce_events`
2. Apply filters client-side:
   - Filter by `type == "Warning"` for warning events
   - Filter by `reason` for specific patterns (FailedScheduling, ImagePullBackOff, etc.)
   - Filter by `involved_object.kind` and `involved_object.name` for specific resources
   - Filter by `namespace` for namespace-specific analysis
3. Group and aggregate:
   - Group by `reason` to find top event patterns
   - Group by `namespace` to find high-noise namespaces
   - Flag events with `count > 1` as repeated patterns
4. Summarize findings with counts, timestamps, and affected objects

## Output Format

### From huawei_get_cce_events (K8s API)

| Field | Description |
|------|-------------|
| `region` | Huawei Cloud region |
| `cluster_id` | CCE cluster ID |
| `namespace` | Kubernetes namespace filter (if applied) |
| `total_fetched` | Number of events returned by the API |
| `events` | Raw event list (apply filters client-side) |
| `warning_count` | Number of Warning events (calculated) |
| `top_reasons` | Top event reasons with counts (calculated) |
| `repeated_patterns` | Events with count > 1 grouped by reason |
| `namespace_breakdown` | Event counts by namespace |
| `next_steps` | Suggested follow-up query or diagnosis skill |

### From huawei_query_k8s_events_from_lts (LTS)

| Field | Description |
|------|-------------|
| `region` | Huawei Cloud region |
| `cluster_id` | CCE cluster ID |
| `log_group_id` | LTS log group ID |
| `log_stream_id` | LTS log stream ID |
| `keywords` | Keywords used for filtering |
| `event_count` | Number of events returned |
| `events` | Parsed event list with normalized structure |
| `time_range` | Start/end time of the query |
| `log_config` | LogConfig info (name, events enabled, etc.) |

## References

- Workflow: `references/workflow.md`
- Risk rules: `references/risk-rules.md`
- Output schema: `references/output-schema.md`