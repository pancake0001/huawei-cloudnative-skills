# Output Schema

Output a Markdown observability context package.

## Required Sections

1. `## Summary`

   - One paragraph with incident scope, time window, strongest signals, and confidence.

2. `## Scope`

   - Region, project ID, cluster, namespace, target objects, and assumed/defaulted values.

3. `## High-Signal Findings`

   - Short bullets for the highest-value observations.
   - Each item should include source, object, timestamp or window, and why it matters.

4. `## Timeline`

   - Ordered user symptom, alarms, Events, metric spikes, log errors, rollout/change hints, and recovery attempts.

5. `## Evidence By Source`

   - Separate tables for Kubernetes state, Events, logs, alarms, metrics, and cloud metadata.

6. `## Data Gaps`

   - Missing source, failure reason, affected confidence, and how to fill the gap.

7. `## Recommended Handoff`

   - Next skill, reason, and exact target object/scope to pass.

8. `## Commands Used`
   - Sanitized `hcloud` and `kubectl cce` commands.

## Evidence Table

| Column         | Meaning                                                                                   |
| -------------- | ----------------------------------------------------------------------------------------- |
| Source         | `kubectl cce`, `hcloud`, alarm analyzer, metric analyzer, log analyzer, or event analyzer |
| Object         | Cluster, namespace, workload, Pod, node, Service, Ingress, PVC, or cloud resource         |
| Time           | Event time, log time, metric window, or snapshot time                                     |
| Signal         | The observed condition                                                                    |
| Severity       | `critical`, `warning`, `normal`, or `unknown`                                             |
| Interpretation | Why the signal matters                                                                    |
| Next Step      | Recommended diagnoser or query                                                            |

## Context Package JSON Shape

Use this shape when a downstream tool expects structured context:

```json
{
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "targets": []
  },
  "time_window": {
    "start": "optional",
    "end": "optional",
    "assumption": "last 1 hour if unspecified"
  },
  "signals": {
    "kubernetes_state": [],
    "events": [],
    "logs": [],
    "alarms": [],
    "metrics": [],
    "cloud_metadata": []
  },
  "timeline": [],
  "data_gaps": [],
  "recommended_handoff": {
    "skill": "huawei-cloud-cce-root-cause-analyzer",
    "reason": "multiple domains need synthesis",
    "scope": {}
  }
}
```
