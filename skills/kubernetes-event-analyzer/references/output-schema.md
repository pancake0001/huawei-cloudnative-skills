# Output Schema

## Event Query Summary

| Field | Description |
|------|-------------|
| `region` | Huawei Cloud region |
| `cluster_id` | CCE cluster ID |
| `namespace` | Kubernetes namespace (optional filter) |
| `event_type` | Event type filter applied (e.g., Warning) |
| `time_range` | Effective start/end time or recent-hours window |
| `total_events` | Number of returned events |
| `warning_count` | Number of Warning events |
| `normal_count` | Number of Normal events |

## Analysis Summary

| Field | Description |
|------|-------------|
| `top_reasons` | Top event reasons with counts, sorted by frequency |
| `repeated_patterns` | Events with count > 1, grouped by reason |
| `namespace_breakdown` | Event counts by namespace |
| `first_warning` | Timestamp of first Warning event in window |
| `last_warning` | Timestamp of last Warning event in window |
| `affected_objects` | Count of unique involved objects with Warning events |
| `next_steps` | Suggested follow-up query or diagnosis skill |

## Event Detail (per event)

| Field | Description |
|------|-------------|
| `reason` | Event reason (e.g., FailedScheduling, ImagePullBackOff) |
| `message` | Event message (summarized, redacted) |
| `involved_object_kind` | Kind of the involved object (Pod, Node, Deployment, etc.) |
| `involved_object_name` | Name of the involved object |
| `namespace` | Namespace of the involved object |
| `count` | Number of times this event occurred |
| `first_timestamp` | First occurrence |
| `last_timestamp` | Most recent occurrence |
| `type` | Event type (Normal, Warning) |