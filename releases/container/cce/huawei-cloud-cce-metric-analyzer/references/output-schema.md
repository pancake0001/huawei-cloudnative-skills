# Output Schema

Metric analyzer output should be a Markdown report. Put decision-making information before raw details.

## Required Sections

1. `## Summary`
   - Overall metric status: `critical`, `warning`, `normal`, or `unknown`.
   - Affected scope: cluster, namespace, workload, Pod, node, component, or cloud resource.
   - Confidence: high, medium, or low.

2. `## Root Cause Signal`
   - State whether metric evidence supports, weakens, or cannot verify the suspected cause.
   - Name the strongest metric and the time it changed.
   - Mention required corroboration such as Events, logs, alarms, or change history.

3. `## Next Actions`
   - Concrete checks or handoff steps.
   - Prefer targeted diagnosers for Pod, workload, node, network, storage, or event follow-up.

4. `## Metric Findings`
   - Tables for each evidence lane queried.
   - Include source, time window, latest value, peak value, status, and interpretation.

5. `## Evidence Timeline`
   - Align user symptom, metric spike/drop, Events, alarms, changes, and recovery attempts.

6. `## Data Gaps`
   - List unavailable AOM, CES, Metrics API, RBAC, endpoint, or resource-association evidence.
   - Explain how each gap affects confidence.

7. `## Commands Used`
   - Sanitized `hcloud` and `kubectl cce` commands.
   - Do not include secrets or signed headers.

## Metric Finding Table

| Column | Meaning |
| ------ | ------- |
| Source | `hcloud CES`, `AOM Prometheus`, or `kubectl cce top` |
| Target | Pod, node, component, ELB, EIP, NAT, ECS, or cluster |
| Metric | CPU, memory, disk, QPS, latency, packet loss, connection count, replicas, etc. |
| Window | Query start and end |
| Latest | Latest datapoint or `N/A` |
| Peak | Max datapoint in the window or `N/A` |
| Status | `critical`, `warning`, `normal`, or `unknown` |
| Interpretation | One-line operational meaning |

## Status Rules

| Status | Typical Meaning |
| ------ | --------------- |
| `critical` | Threshold breach or sharp anomaly matches the incident window and affected scope |
| `warning` | Elevated metric that may contribute but needs more evidence |
| `normal` | Queried metric is within expected range for the selected window |
| `unknown` | Query failed, metric series is missing, or source is unavailable |

## Suggested Wording

- `Metrics support the suspected node pressure because node memory crossed 90% five minutes before Pod evictions started.`
- `Metrics do not prove traffic loss: ELB QPS is stable, but backend Events still need review.`
- `AOM Pod time series were unavailable in this runtime, so Pod-level pressure remains a data gap.`
