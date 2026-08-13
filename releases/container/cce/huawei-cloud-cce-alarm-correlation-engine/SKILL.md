---
id: huawei-cloud-cce-alarm-correlation-engine
name: huawei-cloud-cce-alarm-correlation-engine
description: |
  Correlate Huawei Cloud AOM active and historical alarms for CCE incidents with hcloud CLI evidence. Use this skill when the user needs alarm storm analysis, active/history alarm grouping, severity/resource correlation, CCE alarm health inspection, or alarm timeline evidence for root-cause analysis. This skill is read-only and must not create, update, disable, enable, or delete alarm rules.
tags: [cce, alarms, aom, observability, root-cause, hcloud, read-only]
---

# Huawei Cloud CCE Alarm Correlation Engine

## Overview

This skill turns AOM alarm streams into root-cause evidence. It queries active and historical alarms, groups related alarms, detects alarm storms and chronic alarms, and identifies the CCE resources that need follow-up diagnosis.

Use this skill as an evidence provider for:

- `huawei-cloud-cce-root-cause-analyzer`
- `huawei-cloud-cce-change-impact-analyzer`
- `huawei-cloud-cce-metric-analyzer`
- `huawei-cloud-cce-kubernetes-event-analyzer`
- Pod, workload, node, network, and storage diagnosers

Access path:

```text
hcloud AOM/CCE/IAM read-only commands -> local alarm grouping -> Markdown report
```

Do not use Huawei Cloud SDK imports, old dispatcher actions, hand-written IAM token flows, curl-based cloud APIs, or Kubernetes access for alarm evidence.

## Scope

Allowed:

- Query active AOM alarms.
- Query historical AOM alarms over a bounded window.
- Query AOM alarm rules, action rules, and mute rules only when needed to explain notification gaps.
- Query CCE cluster metadata to resolve cluster ID/name context.
- Group alarms by severity, resource, namespace, workload, node, component, alarm type, and time.
- Generate a Markdown report with summary, root-cause signal, next actions, timeline, and data gaps.

Not allowed:

- Create, update, enable, disable, or delete AOM alarm rules.
- Create or delete notification action rules.
- Configure or clean CCE recommended alarm templates.
- Mutate cloud or Kubernetes resources.

## Inputs

| Input | Required | Notes |
| ----- | -------- | ----- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Recommended | Required for unambiguous AK/SK execution |
| `cluster_id` | Recommended | Use when analyzing a specific CCE cluster |
| `cluster_name` | Optional | Resolve to exact `cluster_id` before filtering |
| `start_time`, `end_time`, `hours` | Recommended | Default to last 1 hour for active incidents |
| `severity` | Optional | Filter after collecting broad evidence when possible |
| `namespace`, `workload`, `pod`, `node` | Optional | Use for grouping and follow-up routing |

## Evidence Commands

Use sanitized `hcloud` commands. Never print or persist AK/SK, security tokens, Authorization headers, or raw credential material.

### Cluster Context

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud CCE ShowCluster --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
```

### AOM Alarm Events

Use AOM event listing for both active and historical alarm evidence. Keep the time window bounded and include the query scope in the report.

```bash
hcloud AOM ListEvents --cli-region=<region> --cli-output=json --project_id=<project-id> --event_type=alarm
hcloud AOM ListEvents --cli-region=<region> --cli-output=json --project_id=<project-id> --event_type=alarm --from=<start-ms> --to=<end-ms>
```

If the CLI or service model uses different parameter names in the installed hcloud version, run `hcloud AOM ListEvents --help` and adapt only the parameter names. Keep the evidence source as `hcloud AOM ListEvents`.

### Alarm Rules And Notification Context

Use rule/action/mute queries only to explain why alarms did or did not notify. These are still read-only.

```bash
hcloud AOM ListMetricOrEventAlarmRule --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud AOM ListActionRule --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud AOM ListMuteRule --cli-region=<region> --cli-output=json --project_id=<project-id>
```

Do not mutate rules from this skill. If the user asks to change alarm rules, report that this skill is read-only and hand off to a dedicated remediation or alarm-management workflow.

## Workflow

1. Resolve region, project ID, cluster ID, and cluster name.
2. Define the alarm window:
   - Active incident: last 1 hour.
   - Known incident time: start 30 minutes before symptom and end 30 minutes after recovery, unless the user requests otherwise.
3. Query active and historical AOM alarms. Do not conclude health from active alarms alone.
4. Normalize alarm records: name, severity, status, resource, namespace, workload, Pod, node, component, first/last timestamp, and message.
5. Group alarms by resource and type. Detect bursts, repeated chronic alarms, and first-firing alarms near the symptom time.
6. Map alarm groups to follow-up diagnosers:
   - Pod image, restart, OOM, scheduling, or readiness alarms -> Pod/workload diagnoser.
   - NodeNotReady, pressure, runtime, or disk alarms -> node diagnoser.
   - ELB, ingress, DNS, EIP, NAT, or connectivity alarms -> network diagnoser.
   - PVC, attach, mount, or storage latency alarms -> storage diagnoser.
   - Broad cross-domain alarms -> root-cause analyzer.
7. Produce the report with summary and next actions first.

## Output Format

Every response should be Markdown:

1. `## Summary`: top alarm signal, affected scope, severity, and confidence.
2. `## Root Cause Signal`: whether alarms support, weaken, or cannot verify the suspected cause.
3. `## Next Actions`: targeted diagnoser handoff and specific checks.
4. `## Alarm Groups`: grouped table with severity, status, count, resource, first/last time, and interpretation.
5. `## Evidence Timeline`: first alarm, burst window, related Events/metrics/changes, and recovery markers.
6. `## Notification Context`: action/mute/rule evidence if queried.
7. `## Data Gaps`: missing history, permissions, time-window ambiguity, or unavailable rule context.
8. `## Commands Used`: sanitized hcloud commands.

See [references/output-schema.md](references/output-schema.md) for table fields.

## Risk Rules

Read [references/risk-rules.md](references/risk-rules.md) before acting.

- This skill is read-only.
- Use `hcloud` for AOM, CCE, and IAM/project evidence.
- Do not use SDK clients, old dispatcher actions, direct IAM curl flows, or cloud mutation commands.
- Never make a high-confidence root cause claim from alarms alone unless another evidence type corroborates it.

## Verification

```bash
hcloud CCE ShowCluster --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
hcloud AOM ListEvents --cli-region=<region> --cli-output=json --project_id=<project-id> --event_type=alarm
hcloud AOM ListMetricOrEventAlarmRule --cli-region=<region> --cli-output=json --project_id=<project-id>
```

Repository checks:

```bash
rg -n "huaweicloudsdk|scripts/huawei-cloud.py|skill action=exec|huawei_.*alarm|AddOrUpdateMetricOrEventAlarmRule|DeleteMetricOrEventAlarmRule" . --glob "!*.md"
git diff --check
```

## References

| Document | Description |
| -------- | ----------- |
| [Workflow](references/workflow.md) | Alarm grouping and handoff flow |
| [Risk Rules](references/risk-rules.md) | Read-only guardrails |
| [Output Schema](references/output-schema.md) | Markdown report sections and table fields |
| [IAM Policies](references/iam-policies.md) | Read-only permissions |
| [Acceptance Criteria](references/acceptance-criteria.md) | Functional and safety checks |
