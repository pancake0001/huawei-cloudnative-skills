# Workflow

## Event Query Sequence

1. Identify `region`, `cluster_id`, and optional `namespace` from the user query.
2. Fetch events using `huawei_get_cce_events`.
3. Apply client-side filters based on user needs:
   - `type == "Warning"` for warning events
   - `reason` patterns (FailedScheduling, ImagePullBackOff, etc.)
   - `involved_object.kind` / `involved_object.name` for specific resources
   - `first_timestamp` / `last_timestamp` for time-window analysis
4. Group events by `reason`, `type`, or `namespace`.
5. Summarize top reasons, repeated patterns, and affected resources.

## Event Pattern Recognition

| Pattern | Likely Cause |
|---------|-------------|
| `ImagePullBackOff` repeated | Wrong image or pull secret missing |
| `FailedScheduling` + `insufficient` | Resource pressure or node not ready |
| `Evicted` pods | Budget disruption or node pressure |
| `NodeNotReady` | Node agent or network issue |
| `Unhealthy` + Readiness probe | Application issue or startup failure |
| `FailedCreatePodSandBox` | CNI or network issue |
| `OOMKilled` | Memory limit exceeded |

## Time-Window Analysis

1. Events include `first_timestamp` and `last_timestamp` fields.
2. If the user provides an incident window, filter events by these timestamps.
3. Compare event frequency before, during, and after the incident window.
4. Flag events that started or peaked during the incident window.

## Event Aggregation

1. For large event volumes, aggregate by `reason` and show top N patterns with total counts.
2. For repeated events (count > 1), show the first and last timestamp and the object involved.
3. If a namespace has > 50% of events, flag it as high-noise and suggest namespace-level investigation.
4. Report `warning_count` vs `normal_count` to give a quick health signal.