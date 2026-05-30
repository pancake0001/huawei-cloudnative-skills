# Output Schema

## Log Query Summary

| Field | Description |
|------|-------------|
| `region` | Huawei Cloud region |
| `cluster_id` | CCE cluster ID when querying Kubernetes or CCE application logs |
| `namespace` | Kubernetes namespace when available |
| `pod_name` | Pod name when available |
| `container` | Container name when available |
| `log_group_id` | LTS log group ID when querying LTS |
| `log_stream_id` | LTS log stream ID when querying LTS |
| `time_range` | Effective start/end time or recent-hours window |
| `keywords` | Keyword filter used |
| `total` | Number of returned log entries |
| `has_more` | Whether an LTS scroll id indicates more data |

## Analysis Summary

When analyzing logs, prefer this structure:

| Field | Description |
|------|-------------|
| `error_patterns` | Recurring error messages or stack trace roots |
| `first_seen` | Earliest returned timestamp for a pattern |
| `last_seen` | Latest returned timestamp for a pattern |
| `affected_resources` | Pods, containers, workloads, or namespaces involved |
| `evidence` | Short redacted examples, not full raw logs |
| `next_steps` | Suggested follow-up query or diagnosis skill |
