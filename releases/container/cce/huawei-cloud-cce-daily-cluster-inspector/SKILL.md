---
id: huawei-cloud-cce-daily-cluster-inspector
name: huawei-cloud-cce-daily-cluster-inspector
description: Run read-only Huawei Cloud CCE daily health checks, quick checks, inspections, and evidence summaries. Trigger when users request cluster inspection or health verification.
tags: [cce, inspection, health-check, daily]
---

# Huawei Cloud CCE Daily Cluster Inspector

## Overview

Perform periodic, low-risk CCE health inspections. Start with a quick check and gather deeper read-only evidence only when observations warrant it. The skill never remediates, scales, drains, restarts, or changes cluster resources.

## Dependencies And Authentication

Use `hcloud` for CCE, AOM, ELB, and CES evidence. Node and Pod inspections prefer AOM Prometheus; Warning-event inspections prefer the cluster Event-to-LTS stream; ELB inspection uses ELB listener/detail APIs and CES. Use `huawei-cloud-kubectl-cce-installer` only when monitoring or logging evidence is unavailable, with namespace- or resource-scoped reads by default. `huawei_cce_quick_check` is the explicit exception: its fallback may use cluster-wide Pod and Warning Event reads to preserve whole-cluster coverage, but it only reads the required status fields, uses server-side Warning filtering, `--chunk-size=200`, a 45-second request timeout, and bounded returned findings. Node and Pod history requires the CCE Cloud Native Monitoring (`cie-collector`) add-on to be connected to AOM Prometheus and to expose `kube-state-metrics`. Warning-event history requires the CCE Cloud Native Logging add-on and an Event-to-LTS LogConfig. ELB metrics require CES permissions but do not require a CCE add-on. Explicit CLI credentials take precedence, then hcloud profile, then `HW_ACCESS_KEY`/`HW_SECRET_KEY` with optional `HW_SECURITY_TOKEN` and `HW_PROJECT_ID`. Resolve region from input/context, then `HW_REGION_NAME`, or ask the user.

## Tools

| Tool | Purpose | Risk |
| --- | --- | --- |
| `huawei_cce_quick_check` | Run the fixed, lightweight cluster health check | R3 |
| `huawei_cce_deep_diagnosis` | Run the complete read-only cluster diagnosis | R3 |
| `huawei_pod_status_inspection`, `huawei_node_status_inspection` | Inspect Pod or node health | R3 |
| `huawei_event_inspection` | Inspect historical Warning events for one namespace | R3 |
| `huawei_aom_alarm_inspection` | Return cluster alarm-rule configuration plus active and historical AOM alarms | R3 |
| `huawei_elb_monitoring_inspection` | Associate ELBs through listener `description.cluster_id`, then inspect ELB/listener state and CES metrics | R3 |
| `huawei_export_inspection_report` | Write an explicitly supplied inspection result to a local Markdown or JSON report | R3 |

## Parameter Reference

| Parameter | Required | Description |
| --- | --- | --- |
| `region` | Yes | Huawei Cloud region. |
| `cluster_id` | Yes | CCE cluster UUID or exact cluster name. |
| `hours` | No; default `1`, range `1-24` | Historical inspection window in hours for node, Pod, Warning-event, AOM-event, and ELB CES metric checks. Values outside the range are rejected. |
| `thresholds`, `top_n` | No | Inspection scope and thresholds. |
| `namespace` | Required for `huawei_pod_status_inspection` and `huawei_event_inspection`; optional for aggregate inspection | Kubernetes namespace to inspect. |
| `event_limit`, `pod_limit`, `alarm_limit` | No | These cap returned Warning events, abnormal Pod details, and AOM alarms. `pod_limit` is also passed to each abnormal-Pod Prometheus query to bound its returned series. All default to 200. |
| `results`, `result`, `output_file` | Required only for aggregation/export | JSON array of check results, JSON inspection result, and local report destination. Use a `.md` or `.markdown` output path for a Markdown report; other extensions produce JSON. |
| `--cli-access-key`, `--cli-secret-key`, `--cli-security-token` | No | Explicit credentials. |

### Input Parameter Validation

Validate required parameters before execution. A UUID `cluster_id` is verified with `hcloud CCE ShowCluster`; a name must exactly and uniquely resolve through `hcloud CCE ListClusters`, then its UUID is verified. Missing, invalid, unmatched, or ambiguous values stop inspection. Never infer or substitute a cluster.

## Core Commands

```bash
python3 scripts/huawei-cloud.py huawei_cce_quick_check \
  region=<region> cluster_id=<cluster-id-or-name>

python3 scripts/huawei-cloud.py huawei_cce_deep_diagnosis \
  region=<region> cluster_id=<cluster-id-or-name> hours=1

python3 scripts/huawei-cloud.py huawei_elb_monitoring_inspection \
  region=<region> cluster_id=<cluster-id-or-name> hours=1
```

## Workflow

1. Validate region and cluster.
2. For a quick check, verify that the cluster is available before collecting dependent evidence. Then inspect the requested `hours` window (default `1`, maximum `24`) of node and Pod status through AOM Prometheus, Warning events through LTS, and both active and historical AOM alerts. Use deeper targeted checks only when needed.
3. Aggregate successful checks and report unavailable evidence as data gaps.
4. Export a local Markdown or JSON report only when explicitly requested; do not remediate.

## Deep Diagnosis Coverage

`huawei_cce_deep_diagnosis` validates the target cluster before any diagnosis. It stops when the cluster is not available; otherwise it performs the following read-only checks and returns one aggregated result:

1. Cluster availability through `hcloud CCE ShowCluster`.
2. Control-plane health through AOM Prometheus: API server QPS, 5xx rate, P95 request latency, and inflight requests.
3. Node health through AOM Prometheus: node readiness, standard pressure conditions, NPD/custom NodeConditions, unschedulable state, and `NoSchedule`/`NoExecute` taints. If Prometheus data is unavailable, use `kubectl cce` for a current-state snapshot only.
4. Node and Pod resource utilisation through AOM Prometheus. CPU and memory utilisation at or above 85 percent of configured limits or capacity is reported.
5. Cluster-wide Pod health through AOM Prometheus, with `kubectl cce` current-state fallback when kube-state metrics are unavailable. It detects NotReady, abnormal phase, common container waiting reasons, and OOMKilled.
6. Cluster Warning events through the Event-to-LTS stream, with a `kubectl cce` current-event fallback. Event findings retain resource identity, so node-, Pod-, and Service-related events remain distinguishable.
7. Add-on metrics when their workloads are present. CoreDNS checks error rate and P95 latency; nginx-ingress checks 5xx QPS and P95 latency; Everest checks CSI Pod readiness, Pending PVCs, and CSI operation errors; Cluster Autoscaler checks unschedulable Pods, errors, and scale-up/scale-down activity during the preceding hour. Missing workloads or uncollected add-on metrics are reported as not observed, not as failures. Cluster Autoscaler metrics require its PodMonitor to be enabled.
8. Current active AOM alarms matched to the target cluster. Recovered alarm history is not included in this check.
9. ELB resources associated with the cluster through a listener `description.cluster_id` match. It checks ELB and listener administrative state, provisioning state, abnormal backend count, capacity usage, dropped connections, HTTP 5xx rate, and response time for the requested time window.

Unavailable monitoring, logging, or component metrics are returned as data gaps. A successful `kubectl cce` fallback is also marked as a data gap when it provides only current-state evidence instead of the requested historical window. These gaps do not suppress the results of the other checks.

## ELB Inspection Coverage

`huawei_elb_monitoring_inspection` and the ELB check inside `huawei_cce_deep_diagnosis` use the following read-only flow:

1. Page through `hcloud ELB ListListeners`.
2. Associate a listener only when its `description` contains an exact `cluster_id` field equal to the validated target cluster UUID. Arbitrary ELB names, descriptions, VPCs, backend nodes, and generic string inclusion are not accepted as ownership evidence.
3. Fetch only the associated ELB details with `hcloud ELB ShowLoadBalancer`.
4. Inspect ELB and listener administrative state, plus ELB provisioning state.
5. Query CES `SYS.ELB` data at a five-minute granularity for the requested time window: abnormal backend servers, Layer 4/Layer 7 connection usage, dropped connections, Layer 7 HTTP 5xx rate, and Layer 7 average response time.

The response includes `association_summary`, matched listener evidence under each `loadbalancers` item, compact latest/peak metric values, and `data_gaps` for CES metrics that cannot be read. No matching listener is a successful empty result: it means no ELB ownership can be proven for the target cluster, not that every ELB in the project is healthy.

## Quick Check Coverage

`huawei_cce_quick_check` is a read-only inspection with a default one-hour window. Set `hours` from `1` to `24` when more historical context is needed:

| Area | Primary source | Checks |
| --- | --- | --- |
| Cluster availability | `hcloud CCE ShowCluster` | The cluster must be available before dependent checks run. |
| Node health | AOM Prometheus | `Ready=False/Unknown`; `DiskPressure`, `MemoryPressure`, `PIDPressure`, and `NetworkUnavailable`; unschedulable state; `NoSchedule`/`NoExecute` taints; and true NPD/custom NodeConditions outside the standard conditions. |
| Pod health | AOM Prometheus | NotReady; `Pending`, `Failed`, or `Unknown`; `CrashLoopBackOff`; `ImagePullBackOff`/`ErrImagePull`; `CreateContainerConfigError`; and `OOMKilled`. Findings for the same Pod are merged and summarized by namespace. |
| Warning events | Cluster-specific LTS event stream | Keyword-filtered LTS records whose Kubernetes Event `type` is verified as `Warning`, read through bounded pagination. Repeated records are merged by namespace, resource kind, resource name, and event name; each result retains reasons, first/last observed time, maximum count, and raw-record count. |
| AOM alarms | AOM rules and events | `huawei_aom_alarm_inspection` returns configured rules plus active and historical alarms observed in the requested `hours` window. Events are matched to the cluster through structured cluster fields, exact cluster name, or PromQL cluster labels, then summarized by event name and state. |

If AOM Prometheus is unavailable, node and Pod checks fall back to `kubectl cce` cluster-wide current-state reads. If LTS is unavailable, Warning events fall back to current `kubectl cce` Event records filtered to the requested window. These fallbacks are marked with their source and do not provide equivalent historical coverage.

A namespace with no observed Pods is returned as a successful empty result (`scope_empty=true`); it is distinct from unavailable kube-state-metrics data.

## Notes

- Do not conclude the cluster is healthy solely because no active alarm exists; include event/history evidence.
- Kubernetes reads must normally specify a namespace or named resource and must not use `-A`. `huawei_cce_quick_check` is the sole exception: its current-state fallback may use `-A` for Pod and Warning Event health checks, with status-only fields, server-side Warning filtering, `--chunk-size=200`, a 45-second request timeout, and bounded findings.
- `huawei_cce_quick_check` uses the requested `hours` window, defaulting to one hour and rejecting values above 24. It checks node and Pod history through AOM Prometheus and `kube-state-metrics`, including NPD/custom NodeConditions that are true outside the standard Ready and pressure conditions; it aggregates Pod findings by namespace, collapses repeated LTS Warning records by namespace, resource, event name, and reason, and queries both active and historical AOM alarms. It returns each type of evidence up to its configured limit. If it falls back to `kubectl cce`, node and Pod results are explicitly marked as current-state snapshots, while Event results are explicitly marked as current Event records filtered to the requested window; these fallbacks do not provide equivalent historical coverage.
- The quick-check response gives every check a `status` of `healthy`, `degraded`, or `unavailable`, and its summary contains an `overall_status` plus per-status counts. A non-available cluster stops dependent checks before they are queried.
- `huawei_aom_alarm_inspection` and `huawei_elb_monitoring_inspection` use `hcloud`; node and Pod checks prefer AOM Prometheus, and event checks prefer LTS. `kubectl cce` is a current-state fallback; node resource checks query AOM Prometheus. ELB inspection does not claim ownership or query CES metrics until a listener `description.cluster_id` match is found.
- Retry a `kubectl cce` x509 upstream failure with `--cce-insecure-upstream-tls=true`.

## References

[Workflow](references/workflow.md) · [Output Schema](references/output-schema.md) · [IAM Policies](references/iam-policies.md) · [CLI Dependencies](references/cli-installation-guide.md) · [Verification Method](references/verification-method.md) · [Acceptance Criteria](references/acceptance-criteria.md)
