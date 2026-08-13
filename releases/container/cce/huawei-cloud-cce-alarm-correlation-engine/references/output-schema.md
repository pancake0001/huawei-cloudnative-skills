# Output Schema

Alarm correlation output should be Markdown with decision-making information first.

## Required Sections

1. `## Summary`
   - Top alarm signal.
   - Affected cluster/namespace/resource scope.
   - Severity and confidence.

2. `## Root Cause Signal`
   - Whether alarms support, weaken, or cannot verify the suspected cause.
   - First relevant alarm and the timestamp relative to the symptom.

3. `## Next Actions`
   - Specific diagnoser or evidence source to use next.
   - Concrete checks such as Pod Events, node Conditions, ELB metrics, or storage attach state.

4. `## Alarm Groups`
   - Grouped table sorted by severity and time proximity.

5. `## Evidence Timeline`
   - User symptom, first alarm, alarm burst, related Events/metrics/changes, and recovery markers.

6. `## Notification Context`
   - Only include if rule/action/mute evidence was queried.

7. `## Data Gaps`
   - Missing permissions, unavailable history, ambiguous cluster, or incomplete timestamps.

8. `## Commands Used`
   - Sanitized `hcloud` commands.

## Alarm Group Table

| Column | Meaning |
| ------ | ------- |
| Severity | Critical, major, minor, warning, info, or provider value |
| Status | Active, resolved, historical, or unknown |
| Count | Number of related alarms |
| Resource | Cluster, namespace, workload, Pod, node, component, or cloud resource |
| First Seen | Earliest timestamp in the group |
| Last Seen | Latest timestamp in the group |
| Signal | Operational interpretation |
| Next Step | Targeted diagnoser or evidence query |

## Confidence Guidance

| Confidence | Meaning |
| ---------- | ------- |
| High | Alarm timing, affected resource, and at least one corroborating evidence source align |
| Medium | Alarm timing and resource align, but corroborating evidence is partial |
| Low | Alarm is generic, chronic, stale, or lacks matching resource/time evidence |
| Unknown | Alarm query failed or history is unavailable |
