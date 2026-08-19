---
name: huawei-cloud-cce-root-cause-analyzer
description: >
  Analyze cross-domain Huawei Cloud CCE incidents using hcloud, kubectl-cce, an observability context package, and related diagnosis skills. Use this skill
  whenever the user mentions a cross-domain incident spanning alarms, workload rollouts, Pod Events or logs, recent changes, service topology, nodes, network,
  storage, or metrics and needs ranked root causes, evidence chains, impact scope, confidence, next actions, or remediation handoff.
version: 1.0.0
tags: [huawei-cloud, cce, root-cause, kubectl, diagnosis]
---

# Huawei Cloud CCE Root Cause Analyzer

## Overview

This skill converges multi-domain CCE evidence into ranked root cause conclusions and a customer-ready Markdown report. It orchestrates evidence collection
through `hcloud`, `kubectl cce`, and focused read-only diagnosis skills, then ranks causes by timeline alignment, evidence strength, impact scope,
counter-evidence, and recoverability.

Execution model:

```text
observability context package -> hcloud CCE discovery -> kubectl cce current Kubernetes evidence -> optional hcloud/AOM/LTS evidence -> domain diagnoser handoff -> root cause ranking -> Markdown report
```

Do not use Python SDK dispatchers, legacy skill execution actions, old Huawei diagnosis actions, bundled SDK scripts, kubeconfig generation, or Huawei Cloud SDK
imports.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` before
running Kubernetes commands.

## Prerequisites

1. `hcloud`, `kubectl`, and kubectl-cce are available as platform-native binaries.
2. Credentials and project context are available through approved protected channels.
3. IAM and Kubernetes RBAC permit the read-only evidence required by selected domain skills.
4. Build or reuse an observability context package before assigning high-confidence root causes.
5. If tooling is missing, use `huawei-cloud-kubectl-cce-installer`; do not download or execute installers in this skill.

## Evidence Dependency Skills

Use these read-only skills as evidence providers when their domain is relevant:

| Skill                                            | Role                                                                                                     |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `huawei-cloud-cce-observability-context-builder` | First-pass alarms, Events, logs, metrics, topology, time-window, and data-gap context package            |
| `huawei-cloud-cce-workload-failure-diagnoser`    | Deployment/StatefulSet/DaemonSet rollout funnel, ReplicaSet, probe, image, command, and readiness causes |
| `huawei-cloud-cce-pod-failure-diagnoser`         | Pod CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending, Evicted, logs, and events                    |
| `huawei-cloud-cce-node-failure-diagnoser`        | NodeNotReady, pressure, taints, lease timeout, kubelet/runtime, and node-level workload impact           |
| `huawei-cloud-cce-network-failure-diagnoser`     | Service, EndpointSlice, DNS/CoreDNS, Ingress, NetworkPolicy, ELB/EIP/NAT/VPC evidence                    |
| `huawei-cloud-cce-storage-failure-diagnoser`     | PVC/PV, StorageClass, CSI, attach/mount, and storage provisioning evidence                               |
| `huawei-cloud-cce-dependency-impact-analyzer`    | Service/Ingress/Pod/Node propagation paths and blast radius                                              |
| `huawei-cloud-cce-change-impact-analyzer`        | Recent deployment, config, route, security, node, and infrastructure change correlation                  |
| `huawei-cloud-cce-alarm-correlation-engine`      | AOM active/history alarm grouping, alarm storm detection, and alarm time anchors                         |
| `huawei-cloud-cce-kubernetes-event-analyzer`     | Current and historical Kubernetes Event analysis                                                         |
| `huawei-cloud-cce-metric-analyzer`               | AOM/Prometheus and cloud resource metrics when metric evidence is needed                                 |

**Remediation handoff only**: `huawei-cloud-cce-auto-remediation-runner` is not an evidence dependency. Mention it only after the root cause is established and
the user asks for a preview or confirms a recovery action.

## Parameters

| Input                  | Required    | Notes                                                       |
| ---------------------- | ----------- | ----------------------------------------------------------- |
| `region`               | Yes         | Request context or `HW_REGION_NAME`; otherwise ask the user                                       |
| `project_id`           | Usually     | Required by kubectl-cce and most hcloud operations          |
| `cluster_id`           | Preferred   | Resolve by name with `hcloud CCE ListClusters` if absent    |
| `namespace`            | Optional    | Use when the incident is scoped to an application namespace |
| `target_name`          | Optional    | Workload, Service, Pod, Ingress, or business target         |
| `fault_time` / `hours` | Recommended | Needed for event, alarm, metric, and change correlation     |
| `symptoms`             | Recommended | User-visible failure signals and known alarms               |
| `--cli-access-key`     | Optional    | Explicit AK for this diagnosis chain                        |
| `--cli-secret-key`     | Optional    | Explicit SK; must be supplied with the explicit AK          |
| `--cli-security-token` | Optional    | STS token; valid only with the explicit AK/SK pair          |

If the target is ambiguous, first collect a broad read-only snapshot and state what object still needs confirmation before assigning high confidence.

## Region Selection

Use the region supplied by the current request or established task context. If it is absent, use `HW_REGION_NAME`. If neither source provides a region, stop and ask the user to provide `region` or set `HW_REGION_NAME`; never infer it from an hcloud profile.

## Explicit Credential Propagation

When the user provides `--cli-access-key` and `--cli-secret-key`, pass that pair and the optional `--cli-security-token` unchanged to every selected
evidence dependency and to every `hcloud` or `kubectl cce` command. Do not use hcloud profiles or authentication environment variables in that execution
chain. Reject an AK without an SK, an SK without an AK, or a security token without the AK/SK pair. Do not print credential values.

## Core Commands And Evidence Collection

### 1. Build Or Reuse Context

Build or reuse an observability context package with `huawei-cloud-cce-observability-context-builder` unless the user provided equivalent alarms, Events, logs,
metrics, scope, timeline, and data gaps.

### 2. Verify Tools

Verify `hcloud`, `kubectl`, and `kubectl-cce` availability. If the plugin is missing, use `huawei-cloud-kubectl-cce-installer`.

```bash
hcloud version
kubectl version --client
kubectl plugin list
```

### 3. Discover Cluster Metadata

Use read-only hcloud commands:

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

### 4. Collect Current Kubernetes Evidence

Use the plugin and always pass cluster, region, and project explicitly:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,svc,ingress,endpoints,endpointslices -A -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes,pv,pvc,storageclass -A -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

### 5. Add Focused Domain Evidence

Use dependent skills when a signal crosses domains. Do not duplicate full domain logic inside this skill.

### 6. Add Historical Evidence

Use AOM/LTS/metrics skills for historical alarms, historical Events, logs, and time-series when current Kubernetes state is insufficient.

### 7. Record Data Gaps

Record every failed collector with the command category, object scope, sanitized error, and impact on confidence.

## Root Cause Workflow

1. Build the incident timeline: user-perceived time, alarm time, Kubernetes Event time, rollout/change time, and recovery attempts.
2. Identify affected objects and blast radius: target workload/Pod/Service/Ingress/Node, namespace, entrypoints, and dependent paths.
3. Run or consult focused domain diagnosers according to evidence:
   - rollout, replica, probe, command, image, CrashLoop, or not-ready symptoms -> workload and pod diagnosers;
   - node pressure, NotReady, taints, kubelet/runtime, scheduling spread -> node diagnoser;
   - Service, DNS, Ingress, EndpointSlice, NetworkPolicy, ELB/EIP/NAT/VPC symptoms -> network diagnoser;
   - PVC/PV/CSI/attach/mount symptoms -> storage diagnoser;
   - service topology and upstream/downstream impact -> dependency-impact analyzer;
   - recent release, config, network, security, node, or cloud-side change -> change-impact analyzer.
4. Convert findings into root cause candidates. Each candidate must include supporting evidence, counter-evidence, data gaps, affected scope, confidence, and
   verification steps.
5. Rank Top3 causes by timeline alignment, direct evidence, blast radius, known failure signature, counter-evidence, and recoverability.
6. Output remediation only as recommendations or handoff instructions. Mutations belong to `huawei-cloud-cce-auto-remediation-runner` after explicit
   confirmation.

## Output Format

The Markdown report must put the most important information first:

1. `## Summary`: one-paragraph incident summary, primary root cause, impact scope, confidence, and report time.
2. `## Root Cause Analysis`: Top3 causes with direct evidence, counter-evidence, confidence, and why lower-ranked causes are less likely.
3. `## Next Actions`: immediate verification, mitigation, owner handoff, and remediation skill handoff.
4. `## Evidence Timeline`: ordered user symptom, alarm, Event, rollout/change, metric/log evidence.
5. `## Investigation Steps`: commands/skills used, sanitized errors, and data gaps.
6. `## Impact Scope`: affected workloads, Pods, Services, Ingresses, Nodes, namespaces, and upstream/downstream dependencies.
7. `## Appendix`: raw evidence summaries, command categories, and limitations.

Never write only "image pull failed", "node abnormal", "network issue", or "change caused failure" when more evidence is available. Explain the concrete failure
signature, why it maps to the cause, what evidence is missing, and how to verify the next step.

## Best Practices

- Build one shared timeline and object scope before comparing domain hypotheses.
- Rank causes by direct evidence and counter-evidence, not by symptom frequency alone.
- Preserve data gaps and lower confidence when a required collector fails.
- Keep domain-specific logic in its diagnoser and use this skill for synthesis.

## Notes And Safety Rules

- Use only read-only `hcloud` and `kubectl cce` operations.
- Do not generate kubeconfig or call cloud/Kubernetes SDK clients.
- Do not run remediation, rollout, node, network, or storage mutations.
- Redact credentials, tokens, headers, proxy details, registry secrets, and sensitive log values.

## Verification

Before treating the skill as ready, verify:

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]root[-_]cause|huawei[-_].*[-_]diagnose|huawei[-_].*[-_]analyze|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

Expected result: no executable SDK dispatcher entrypoints or bare Kubernetes access paths remain. Mentions in Markdown should appear only as explicit
prohibitions or verification checks.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: evidence chain and root cause ranking.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/risk-rules.md`: read-only boundaries and handoff rules.


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.
