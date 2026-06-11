---
id: huawei-cloud-cce-root-cause-analyzer
name: huawei-cloud-cce-root-cause-analyzer
description: |
  Huawei Cloud CCE cross-domain root cause analysis skill using Python SDK dispatcher.
  Use this skill when a CCE incident spans alarms, workload rollout, Pod events/logs, recent changes, service topology, nodes, network, or metrics, and the user needs a complete Markdown root-cause report with investigation steps, evidence chain, impact scope, Top3 causes, confidence, and remediation handoff.
  Trigger: user mentions "root cause analysis", "根因分析", "multiple failures", "多类告警", "cross-resource diagnosis", "跨资源诊断", "comprehensive diagnosis", "综合诊断", "RCA", "故障定位", "impact scope", "影响面分析", "change correlation", "变更关联"
tags: [cce, root-cause-analysis, cross-domain-diagnosis, kubernetes, fault-diagnosis]
---

# CCE Root Cause Analysis

> **⚠️ Execution Method (Must Read): This skill executes diagnosis via local Python scripts using the `scripts/huawei-cloud.py` dispatcher. Using hcloud, kubectl, or other CLI tools or direct API calls is prohibited.**
>
> - All actions are dispatched through `scripts/huawei-cloud.py` with `--action <action_name>` and `--params <json_params>`
> - All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them; do not run them directly in a shell**
> - For action names and parameters, see the Core Tools section below
> - **Do not attempt hcloud, kubectl, curl IAM, or other CLI/API methods. This skill does not depend on these tools**
> - **All paths are relative to the skill directory, which is the directory where this SKILL.md resides**

## Overview

This skill converges multi-domain evidence into root cause conclusions for CCE incidents. A daily-inspector handoff such as `abnormal_object_analysis` is accepted only as a scope hint: it can identify suspected resources, symptoms, and time windows, but it is not root-cause evidence by itself. RCA must independently collect Events, workload rollout evidence, Pod/Node metrics, dependency topology, recent changes, AOM alarms, and related network/node evidence before ranking causes. It produces a complete Markdown report with investigation steps, timeline, evidence chain, impact scope, Top3 root causes, confidence, counter-evidence, and remediation handoff.

This skill is applicable to the following scenarios:

1. Cross-resource incidents involving multiple failure domains (workload + dependency + change + alarm)
2. Root cause analysis when alarms span multiple CCE resources and the user needs comprehensive diagnosis
3. Correlating recent changes (deployments, config updates, network/security policy changes, node changes) with observed failures
4. Dependency impact propagation analysis (Service → Ingress → Pod → Node chain)
5. Workload rollout failures requiring evidence funnel (generation → ReplicaSet → Pod Ready → events → logs → command/args → probes → image)
6. Producing structured Top3 root cause reports with evidence, counter-evidence, and confidence scores
7. Consuming `abnormal_object_analysis` from `huawei-cloud-cce-daily-cluster-inspector` as an optional scope hint when available

## RCA Entry Criteria

Use this skill only when the user needs to know **why** an abnormal condition happened, not merely whether a resource is abnormal. Prefer `huawei_root_cause_analyze` when the incident involves one or more abnormal objects with time correlation, relationship chains, repeated events, or multi-domain symptoms.

### Resource and Symptom Matrix

| Resource | Trigger RCA When | Required / Preferred Evidence | Typical Root Cause Domains | Recovery Handoff Focus |
|----------|------------------|-------------------------------|----------------------------|------------------------|
| Pod | CrashLoopBackOff, OOMKilled, ImagePullBackOff, ErrImagePull, Pending, probe failure, repeated Warning Events, Pod TopN CPU/memory abnormal window | RCA-collected Events, Pod status/container states, logs when enabled, command/args, image, probes, limits/requests, Pod metrics, related workload/service/node | workload, image, runtime, scheduling, resource pressure | rollback, resize workload, fix image/pull secret, restart after verified cause |
| Workload | Deployment/StatefulSet/DaemonSet unavailable, rollout stuck, replicas not ready, new revision failure, workload linked to abnormal Pods | RCA-collected rollout funnel, ReplicaSet/Pod readiness, Events, current spec, recent image/config/HPA changes, Pod metrics, related services/nodes | rollout, config, image, probe, quota/admission, traffic/resource saturation | rollback previous revision, adjust probes/resources, scale after RCA |
| Node | Node NotReady, MemoryPressure/DiskPressure/PIDPressure, scheduling failures, many abnormal Pods on same node, node TopN CPU/memory/disk abnormal window | RCA-collected node conditions, taints, allocatable/capacity, node metric windows, affected Pods, system/node Events, ECS/security group context when available | node pressure, kubelet/runtime, ECS/network/storage | cordon/drain preview, node repair/reboot, nodepool scale-out |
| Service | Service unavailable, selector mismatch, no ready backend Pods, abnormal Pods behind same Service, ingress/backend errors | Service selector, selected Pods, Endpoint/Pod readiness, related Ingress/ELB/EIP, abnormal object relationships | dependency, workload backend, network, configuration | fix selector/backend, recover backend workload, network recovery plan |
| Ingress | Ingress access failure, backend Service abnormal, TLS/backend rule issue, ELB relation present | Ingress rules, backend Services, TLS config, related Service/Pod objects, ELB status/metrics | network, dependency, peripheral resource, config | update backend/rules, recover Service/ELB path |
| ELB / EIP / NAT | Service/Ingress chain points to peripheral resources and access, connection, bandwidth, backend health, or NAT/EIP status is abnormal | Peripheral status and metrics, ELB backend health, EIP/NAT state, Service/Ingress relationship chain | peripheral resource, network, dependency | network/peripheral recovery plan, backend health repair |
| AOM Alarm | Critical/Major alarms correlate with Events/metrics/object timeline, repeated alarms across resources, sudden alarm bursts | Alarm groups, firing/resolved state, alarm time window, matched abnormal objects | alarm correlation, resource pressure, workload/network symptoms | use as RCA evidence only, then hand recovery hints downstream |
| Recent Change | Failure window follows deployment, config, image, HPA, network, security group, nodepool, or addon change | RCA-collected audit/change timeline, changed object, before/after diff when available, Events and metrics after change | change, rollout, config, network, node | rollback or revert preview through remediation runner |
| Cluster / Addon | Multiple namespaces affected, system components abnormal, DNS/CoreDNS/CNI/storage/addon symptoms, broad scheduling or network issue | Cluster-level abnormal objects, addon Pod status, Events, node distribution, service impact scope | cluster, addon, network, storage, node | addon repair guidance, capacity/network/storage recovery plan |
| CoreDNS | CoreDNS CPU high, DNS success rate below 99%, or P99 DNS latency above 100ms | RCA-collected CoreDNS Prometheus metrics, CoreDNS Pod status/events, DNS error/latency timeline, related service impact scope | dns, addon, cluster | scale CoreDNS replicas first, then verify DNS CPU/success-rate/latency |

### Ranked Root Cause Candidate Types

Only fault-origin candidates should enter `top_causes`:

- Workload rollout/startup causes from rollout diagnoser, such as `RolloutTimeout`, `ImagePullBlocked`, `ContainerCommandNotFound`, `CrashLoopOrAppExit`, and `ProbeFailure`.
- `ImagePullBlocked` from RCA-collected Kubernetes image pull Events.
- `PodRuntimeFailure` from CrashLoop, OOMKilled, or container restart failure evidence.
- `SchedulingOrNodeConstraint` from FailedScheduling, insufficient capacity, node pressure, NotReady, taints, affinity, or quota constraints.
- `NodeCapacityOrSystemBottleneck` from abnormal Node conditions or Node CPU/memory/disk thresholds.
- `NodeConditionAbnormal` when Node conditions are abnormal but resource thresholds do not yet prove a capacity bottleneck.
- `ApplicationPerformanceOrQuotaBottleneck` when Pod resources are saturated while Nodes are normal; traffic spike evidence strengthens but is not mandatory.
- `DnsPerformanceBottleneck` when RCA-collected CoreDNS CPU is high or P99 DNS latency rises above 100ms; success rate below 99% strengthens the conclusion.
- `Change:<category>` only when a recent change is time-correlated with RCA-collected failure evidence.

Dependency propagation and alarm correlation are not ranked root causes by themselves:

- `DependencyImpactScope` belongs in `supporting_findings` and explains blast radius/propagation path.
- `AlarmEvidence` belongs in `supporting_findings` and strengthens or weakens other candidates by timeline correlation.

### Remediation Candidate Mapping

- `ApplicationPerformanceOrQuotaBottleneck`: first propose `scale_workload_out` with `huawei_scale_cce_workload`; then propose `configure_hpa`; these are R2 only when they do not add cloud-resource cost. Use `resize_workload` as an R1 fallback when limits/requests are too small.
- `DnsPerformanceBottleneck`: propose `scale_coredns_out` with `huawei_scale_cce_workload` targeting `Deployment/kube-system/coredns`; this is R2 when current CoreDNS Pod count is known and scaling does not add cloud-resource cost, otherwise R1 preview.
- `NodeCapacityOrSystemBottleneck`: if affected node names are known, first propose `cordon_node` with `huawei_cce_node_cordon`; then propose `drain_node_after_cordon` as R1 only when existing Pods must be evicted or migrated.
- `NodeConditionAbnormal`: propose `cordon_node` only when the node is concrete and abnormal; otherwise return a manual node repair/observation preview.
- `SchedulingOrNodeConstraint`: propose node pool scale-out or scheduling adjustment preview when no single node should be isolated.
- `ImagePullBlocked`: first propose R3 image/pull secret verification; rollback is R1 when a new revision is unavailable and a previous stable revision exists.
- Rollout/startup failures: propose `rollback_previous_revision` when rollback is the safest recovery path.

### Inspector Input Boundary

Daily inspection output is useful as an entry point, not as a root-cause authority:

- It may provide suspected objects, abnormal points, related resources, and first/last abnormal timestamps.
- RCA may use those fields to narrow query scope, choose namespace/target/node, and set the initial time window.
- RCA must independently query and analyze required resources before ranking causes.
- A root cause candidate must cite RCA-collected evidence such as Events, rollout state, Pod/Node metrics, dependency topology, change records, alarms, logs, or peripheral resource status.
- Never rank a cause solely because it appears in `abnormal_object_analysis`.

Resource-specific RCA expectations:

- Workload abnormality: check whether failure appeared after a deployment/config/image/HPA change, whether Pod CPU/memory suggests traffic or resource saturation, whether Events/logs point to runtime/probe/image issues, and whether affected Pods concentrate on specific nodes.
- Node abnormality: check node conditions, taints, schedulability, CPU/memory/disk metrics, affected Pods, system/node Events, and whether symptoms point to kubelet/runtime/ECS/network/storage rather than only workload pressure.
- Service/Ingress/network abnormality: check Service selector/endpoints, Pod readiness, Ingress backends, ELB backend health, EIP/NAT metrics/status, and whether backend workload or node issues explain network symptoms.
- Alarm-only input: use alarms as a time and symptom signal, then verify with Events, metrics, objects, and changes before concluding.

Resource-usage RCA rules:

- If Pod CPU/memory is sustained high but rollout, Pod lifecycle Events, AOM alarms, dependency health, and Node CPU/memory/disk/conditions show no clear abnormality, RCA must check Pod traffic metrics before concluding `ApplicationPerformanceOrQuotaBottleneck`.
- If Pod traffic receive/transmit rate rises sharply in the same window, RCA may strengthen the conclusion to traffic-driven application/resource saturation.
- If traffic does not rise sharply or traffic metrics are unavailable, RCA may still conclude application performance bottleneck or Pod limit/request too small, but must record the missing or negative traffic evidence.
- If Node CPU/memory/disk reaches configured thresholds or Node conditions show `Ready=False`, `MemoryPressure=True`, `DiskPressure=True`, `PIDPressure=True`, `NetworkUnavailable=True`, or NPD `*Problem=True`, RCA may conclude `NodeCapacityOrSystemBottleneck`.
- Do not infer node bottleneck from a related node name alone. Node conclusions require RCA-collected node metrics or abnormal conditions.
- A healthy rollout is counter-evidence, not a root cause. It must not outrank resource bottleneck candidates.

### Do Not Start RCA For

1. Healthy heartbeat or quick check with `has_anomaly=false`
2. A single informational or already-resolved alarm without affected object, timeline, or repeated signal
3. One-time metric spike below agreed impact threshold and no Events, alarms, or user-visible impact
4. User only asks for read-only status summary, inventory, or monitoring TopN
5. Recovery execution requests without root-cause evidence; hand those to `huawei-cloud-cce-auto-remediation-runner` only after RCA or explicit authorized recovery context

This skill does NOT handle the following:

1. Executing any remediation actions (scale, delete, drain, reboot, vulnerability state modification, cluster sleep/wake)
2. Making root cause conclusions from a single alarm without timeline or evidence chain
3. Creating, modifying, or deleting CCE resources
4. Guessing or fabricating diagnosis results without evidence

---

## Prerequisites

**Before using, you must run the environment check script to complete environment validation and dependency installation in one step:**

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

> Windows Note: Do not use `&&` to chain commands (PowerShell 5.x does not support it). Use semicolons if you need to change directories first.

The script will check in sequence: Python >= 3.6 → install dependencies → validate SDK → validate credentials → validate service availability.
If the environment check fails, fix the issues before continuing with other actions.

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| HW_ACCESS_KEY | Yes | Huawei Cloud AK |
| HW_SECRET_KEY | Yes | Huawei Cloud SK |
| HW_REGION_NAME | No | Default cn-north-4 |
| HW_PROJECT_ID | No | Project ID (automatically obtained via IAM API when not set) |
| HW_SECURITY_TOKEN | No | Required when using temporary AK/SK |
| HW_CLUSTER_ID | No | Default CCE cluster ID (can also be passed per action) |

**Security Constraints:**

1. Never persist credentials (AK/SK/Token/Certificate) to the filesystem
2. AK/SK exist only within the current request call stack; released after use
3. Only non-sensitive project IDs are cached in process memory (never written to disk)
4. All temporary certificate files must be deleted immediately after use
5. Never expose AK/SK in logs, responses, or error messages

**Do not output the values of the above environment variables.**

---

### IAM Permission Requirements

| API Action | Permission | Purpose |
|-----------|------------|---------|
| cce:cluster:get | Get cluster | View cluster details |
| cce:cluster:list | List clusters | List CCE clusters |
| cce:node:list | List nodes | List cluster nodes |
| aom:*:get | Read AOM | Query AOM metrics and alarms |
| aom:event:list | List events | Query AOM alarm events |
| aom:alarmRule:list | List alarm rules | Query alarm rules |

**Permission Failure Handling**:
1. When any command fails due to permission errors, display required permission list
2. Guide the user to create a custom policy in the IAM console
3. Pause execution and wait for user confirmation

---

## Core Tools

All actions are dispatched through `scripts/huawei-cloud.py` using `skill action=exec`:

**Primary Comprehensive Diagnosis:**

| Action | Required Parameters | Description |
|--------|---------------------|-------------|
| `huawei_root_cause_analyze` | region, cluster_id | Primary comprehensive action: orchestrates workload rollout diagnosis, dependency impact, change impact, and AOM alarms into a unified root cause report with Top3 causes |

**Workload Domain Actions:**

| Action | Required Parameters | Description |
|--------|---------------------|-------------|
| `huawei_workload_rollout_diagnose` | region, cluster_id, namespace, kind, name | Diagnose Deployment/StatefulSet/DaemonSet rollout failures with funnel and Top causes |
| `huawei_workload_diagnose` | region, cluster_id | General workload status diagnosis |
| `huawei_workload_diagnose_by_alarm` | region, cluster_id | Workload diagnosis triggered by AOM alarm correlation |
| `huawei_pod_failure_diagnose` | region, cluster_id | Pod-level failure diagnosis (CrashLoop, ImagePull, OOM, Pending, etc.) |

**Dependency and Impact Actions:**

| Action | Required Parameters | Description |
|--------|---------------------|-------------|
| `huawei_dependency_impact_analyze` | region, cluster_id | Analyze Service/Ingress/Pod/Node propagation paths and impact scope for service unavailability |

**Change Impact Actions:**

| Action | Required Parameters | Description |
|--------|---------------------|-------------|
| `huawei_change_impact_analyze` | region, cluster_id | Correlate recent changes (deployment, config, network, security policy, node changes) with observed failures via audit log and AOM alarm timeline |

**Network and Node Domain Actions:**

| Action | Required Parameters | Description |
|--------|---------------------|-------------|
| `huawei_network_diagnose` | region, cluster_id | General network connectivity diagnosis |
| `huawei_network_diagnose_by_alarm` | region, cluster_id | Network diagnosis triggered by AOM alarm correlation |
| `huawei_network_failure_diagnose` | region, cluster_id | Network failure diagnosis (Service, Ingress connectivity) |
| `huawei_node_diagnose` | region, cluster_id | Node-level diagnosis (scheduling, pressure) |
| `huawei_node_failure_diagnose` | region, cluster_id | Node failure diagnosis |
| `huawei_node_batch_diagnose` | region, cluster_id | Batch node diagnosis for multi-node issues |

**Alarm and Report Actions:**

| Action | Required Parameters | Description |
|--------|---------------------|-------------|
| `huawei_analyze_aom_alarms` | region, cluster_id | Analyze AOM alarm patterns and correlation across resources |
| `huawei_generate_diagnosis_report` | region, cluster_id | Generate structured Markdown diagnosis report |
| `huawei_generate_monitor_dashboard` | region, cluster_id | Generate monitoring dashboard for ongoing observation |

**Supporting Evidence Actions:**

| Action | Required Parameters | Description |
|--------|---------------------|-------------|
| `huawei_get_cce_events` | region, cluster_id | List Kubernetes Events in the cluster |

---

## Parameter Reference

**Common Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| region | Yes | Huawei Cloud region, e.g., cn-north-4 |
| cluster_id | Yes | CCE cluster ID |
| namespace | Yes* | Kubernetes namespace (required for workload-specific actions) |
| kind | Yes* | Workload type: Deployment, StatefulSet, or DaemonSet |
| name | Yes* | Workload name |

*Required only for `huawei_workload_rollout_diagnose`.

**Optional Parameters (passed via `--params` JSON):**

| Parameter | Description |
|-----------|-------------|
| ak | Override AK (uses HW_ACCESS_KEY by default) |
| sk | Override SK (uses HW_SECRET_KEY by default) |
| project_id | Override project ID (auto-obtained via IAM when not set) |
| target_name | Optional workload/app/service name for scope narrowing |
| hours | Metric/query time range in hours (default 1) |
| top_n | Number of top results for ranking (default 3) |
| abnormal_object_analysis | Optional JSON object from daily inspector; used only as scope hints, not root-cause proof |
| root_cause_handoff | Optional JSON handoff from daily inspector; may contain `evidence.abnormal_object_analysis` scope hints |
| inspection_result | Optional full daily inspection JSON; may contain `diagnosis.abnormal_object_analysis` scope hints |

---

## Output Format

### Primary Comprehensive: `huawei_root_cause_analyze`

```json
{
  "success": true,
  "analysis_trace_id": "RCA-...",
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "target_name": "optional workload/app/service"
  },
  "summary": {
    "top_cause": {},
    "cause_count": 3,
    "data_sources": {
      "rollout": true,
      "dependency": true,
      "change": true,
      "alarms": true
    }
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "ContainerCommandNotFound",
      "title": "New version container startup command or entry file does not exist",
      "domain": "workload",
      "confidence": 0.94,
      "evidence": [],
      "counter_evidence": [],
      "recommendation": [],
      "remediation_hint": {
        "skill": "huawei-cloud-cce-auto-remediation-runner",
        "action": "huawei_auto_remediation_run",
        "strategy": "rollback_previous_revision",
        "requires_confirmation": true
      }
    }
  ],
  "remediation_candidates": [
    {
      "skill": "huawei-cloud-cce-auto-remediation-runner",
      "strategy": "rollback_previous_revision | configure_hpa | resize_workload | fix_image_or_pull_secret_preview | node_cordon_drain_or_scale_nodepool_preview",
      "action": "huawei_rollback_cce_workload | huawei_configure_cce_hpa | huawei_resize_cce_workload | manual_review_image_pull_secret | manual_select_node_or_nodepool_action",
      "risk_level": "R0 | R1 | R2 | R3",
      "target": {},
      "params": {},
      "reason": "why this recovery candidate is suitable",
      "verification": [],
      "requires_confirmation": true
    }
  ],
  "remediation_handoff": {
    "skill": "huawei-cloud-cce-auto-remediation-runner",
    "input_field": "remediation_candidates"
  },
  "report_markdown": "# CCE Comprehensive Root Cause Analysis Report...",
  "report_file": "optional"
}
```

Pass `remediation_candidates` directly to `huawei_auto_remediation_run`:

```bash
python3 releases/container/cce/huawei-cloud-cce-auto-remediation-runner/scripts/huawei-cloud.py \
  huawei_auto_remediation_run \
  region=<region> \
  cluster_id=<cluster_id> \
  remediation_candidates='<this output remediation_candidates JSON>'
```

Do not replace the candidate handoff with rollback-only parameters unless the selected candidate is specifically `rollback_previous_revision`.

### Supporting Domain Outputs

Each domain action (`huawei_workload_rollout_diagnose`, `huawei_dependency_impact_analyze`, `huawei_change_impact_analyze`, `huawei_analyze_aom_alarms`) produces its own structured JSON output. See individual skill documentation for domain-specific schemas.

---

## Verification

1. Run the environment check script to confirm dependencies and credentials are available
2. Use `huawei_root_cause_analyze` on a known healthy cluster to verify it returns `success: true` with zero or low-confidence causes
3. Use `huawei_root_cause_analyze` on a cluster with known multi-domain failures to verify Top3 causes are accurately identified
4. Compare `huawei_root_cause_analyze` summary with individual domain action outputs for consistency
5. Verify that evidence chains reference specific objects, events, and API fields (not generic statements)
6. Verify that counter-evidence is present for each top cause candidate
7. Confirm that low-confidence conclusions are clearly labeled with required supplementary data

---

## Best Practices

1. Always start with `huawei_root_cause_analyze` for comprehensive diagnosis; drill down into individual domain actions only when specific evidence requires deeper analysis
2. For workload rollout failures, prioritize the rollout funnel: generation/observedGeneration → ReplicaSet → Pod Ready → Events → Logs → command/args → probes → image
3. For service unavailability, use `huawei_dependency_impact_analyze` to trace Service selector → Ingress backend → Pod Ready → Node distribution propagation paths
4. For suspected change-induced failures, use `huawei_change_impact_analyze` to build "change occurred before failure" causal chain with audit logs, K8s historical events, and AOM alarms
5. Never conclude root cause from a single alarm alone; always provide timeline or evidence chain
6. Record supporting evidence, counter-evidence, data gaps, and remediation handoff for each root cause candidate
7. Sort root causes by impact scope, timeline alignment, evidence strength, and recoverability
8. Clearly label low-confidence conclusions with required supplementary data
9. All remediation actions must be output as recommendations only and handed off to `huawei-cloud-cce-auto-remediation-runner`

---

## Reference Documents

- Evidence chain and root cause ranking workflow: `references/workflow.md`
- Output structure specification: `references/output-schema.md`
- Risk boundaries and handoff rules: `references/risk-rules.md`
- [Huawei Cloud CCE Documentation](https://support.huaweicloud.com/cce/index.html)
- [Huawei Cloud Python SDK Documentation](https://support.huaweicloud.com/api-cce/cce_02_0113.html)

---

## Notes

1. This skill is read-only diagnosis and report generation only; no write, scale, delete, cordon, drain, reboot, vulnerability state modification, or cluster sleep/wake operations
2. Do not output the values of HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN, or other environment variables
3. All scripts must be executed via `skill action=exec`; do not run them directly in a shell
4. Any action requiring `confirm=true` must be handed off to `huawei-cloud-cce-auto-remediation-runner`; this skill never executes remediation
5. The environment check script must be run before any diagnosis action
6. When using temporary AK/SK, HW_SECURITY_TOKEN must be set

---

## Common Pitfalls

1. **Concluding root cause from a single alarm** — Always require timeline or evidence chain; a single alarm without temporal correlation is insufficient evidence
2. **Skipping `huawei_root_cause_analyze` and drilling into individual domains first** — Always start with comprehensive analysis; individual domain drill-down is for supplementary evidence only
3. **Ignoring counter-evidence** — Each root cause candidate must include counter-evidence and data gaps; omitting these leads to false confidence
4. **Not building a fault timeline** — Establish user-perceived time, alarm trigger time, Kubernetes event time, and change time before ranking causes
5. **Attempting remediation actions from this skill** — All changes must be handed off to `huawei-cloud-cce-auto-remediation-runner`; this skill only outputs recommendations
6. **Failing to label low-confidence conclusions** — When evidence is insufficient, write "insufficient evidence" explicitly; never present guesses as conclusions
7. **Not correlating changes with failures** — When a recent deployment, config, network, or security policy change exists, use `huawei_change_impact_analyze` to verify the "change before failure" causal chain
8. **Treating dependency propagation as single-direction** — Dependency impact can propagate bidirectionally (upstream failure affects downstream, and downstream back-pressure affects upstream); analyze both directions
