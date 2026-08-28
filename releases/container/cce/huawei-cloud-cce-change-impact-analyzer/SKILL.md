---
name: huawei-cloud-cce-change-impact-analyzer
description: >
  Analyze whether a recent Huawei Cloud CCE change caused or amplified an incident using hcloud, read-only kubectl-cce, and observability evidence. Use this
  skill whenever the user mentions workload rollout, ConfigMap or Secret metadata, Service, Ingress, Gateway, NetworkPolicy, RBAC, Node, node-pool, or
  cloud-network changes and needs timeline correlation, blast radius, risk scoring, or an impact report.
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, change-impact, analysis]
---

# Huawei Cloud CCE Change Impact Analyzer

## Overview

Turn "what changed before the incident" into evidence-based causal attribution. Correlate current topology, Kubernetes Events, historical evidence, AOM alarms,
metrics, logs, and read-only cloud metadata to rank changes that may have caused or amplified a CCE incident.

Execution model:

```text
hcloud CCE discovery -> kubectl cce current state -> historical evidence handoff -> change classification -> timeline correlation -> blast radius -> report
```

Do not use Python SDK dispatchers, legacy skill execution actions, bundled SDK scripts, kubeconfig generation, direct IAM HTTP calls, or Huawei Cloud SDK
imports.

## Prerequisites

1. `hcloud`, `kubectl`, and kubectl-cce are available as platform-native binaries.
2. Credentials and project context are provided through approved protected channels.
3. IAM and Kubernetes RBAC permit the required read-only cluster, topology, Event, workload, policy, and metadata queries.
4. Read `references/kubectl-cce.md` before Kubernetes access. If a tool or plugin is missing, use `huawei-cloud-kubectl-cce-installer`; this skill must not
   install tools.
5. A fault time or bounded incident window is available, or its absence is explicitly recorded as a confidence limit.
6. Never print credentials, Authorization headers, plugin credential material, Secret values, sensitive ConfigMap values, registry credentials, or application
   secrets.

## Related Skills

| Skill                                            | When To Use                                                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `huawei-cloud-cce-observability-context-builder` | Build the shared scope, timeline, alarm, Event, log, metric, and data-gap context first                       |
| `huawei-cloud-cce-kubernetes-event-analyzer`     | Historical or current Kubernetes Events are needed beyond the normal Event window                             |
| `huawei-cloud-cce-alarm-correlation-engine`      | AOM active/history alarms, alarm storms, or alarm time anchors are needed                                     |
| `huawei-cloud-cce-metric-analyzer`               | Metrics are needed to validate degradation after a change                                                     |
| `huawei-cloud-cce-workload-failure-diagnoser`    | A workload image, command, probe, resource, environment, selector, or volume change is suspicious             |
| `huawei-cloud-cce-network-failure-diagnoser`     | A Service, Ingress, Gateway, NetworkPolicy, ELB, EIP, NAT, security-group, ACL, or route change is suspicious |
| `huawei-cloud-cce-node-failure-diagnoser`        | A Node taint, cordon/drain, node-pool, upgrade, pressure, or NotReady signal is suspicious                    |
| `huawei-cloud-cce-storage-failure-diagnoser`     | A PVC, StorageClass, CSI, topology, mount, or storage-backend change is suspicious                            |
| `huawei-cloud-cce-dependency-impact-analyzer`    | Blast radius and service topology must be mapped                                                              |
| `huawei-cloud-cce-root-cause-analyzer`           | Change findings must be ranked with other root-cause candidates                                               |

## Parameters

### Input Parameter Validation
This skill requires both `region` and `cluster_id` before analysis. It never performs a region-wide fallback. The supplied `cluster_id` must pass the following validation before any downstream query:
1. Check whether `cluster_id` is a standard UUID:
   - UUID: call `hcloud CCE ShowCluster` to verify it.
   - Otherwise: call `hcloud CCE ListClusters`, perform an exact and unique name match, convert it to a UUID, then call `ShowCluster` to verify it.
If a required `cluster_id` is missing, or any supplied `cluster_id` is invalid, unmatched, or ambiguous, stop the operation and require the user to provide the correct region and cluster ID. A supplied invalid `cluster_id` must never fall back to a global query; never guess or select a cluster. For any other required resource identifier, first use the corresponding read-only query tool to list candidates when the user cannot provide an unambiguous value, then ask the user to choose; never select a candidate automatically.

### Input Parameters

| Input                               | Required    | Notes                                                                              |
| ----------------------------------- | ----------- | ---------------------------------------------------------------------------------- |
| `region`                            | Yes         | Request context or `HW_REGION_NAME`; otherwise ask the user                                                              |
| `project_id`                        | Yes         | Pass explicitly to hcloud and kubectl-cce                                          |
| `cluster_id`                        | Yes         | Target CCE cluster UUID, or an exact cluster name resolved through hcloud          |
| `namespace`                         | Optional    | Prefer scoped collection; retain cluster-wide view for core-system/network changes |
| `target_name`                       | Optional    | Workload, Service, Pod, Ingress, Gateway, Node, or stable app label                |
| `fault_time`                        | Recommended | Anchor for temporal ordering                                                       |
| `hours` / `start_time` / `end_time` | Recommended | Use the narrowest useful incident window                                           |
| `known_changes`                     | Optional    | User-provided deployment, configuration, policy, or infrastructure records         |
| `log_group_id` / `log_stream_id`    | Optional    | Use only when approved log discovery cannot resolve the source                     |

## Region Selection

Use the region supplied by the current request or established task context. If it is absent, use `HW_REGION_NAME`. If neither source provides a region, stop and ask the user to provide `region` or set `HW_REGION_NAME`; never infer it from an hcloud profile.

## Explicit Credential Propagation

Accept `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token`. AK and SK must be supplied together; a token requires that pair. When
provided, append all supplied options to every `hcloud` and `kubectl cce` command, pass them unchanged to delegated skills, and do not use an hcloud profile
or authentication environment variables. Never print credential values.

## Core Commands

### 1. Verify Tools And Plugin

```bash
hcloud version
hcloud configure list
kubectl version --client
kubectl plugin list
```

If a tool or plugin is missing, stop and use `huawei-cloud-kubectl-cce-installer`. Do not download installers or fall back to SDK or kubeconfig access.

### 2. Discover Cluster Context

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

### 3. Collect Current Workload And Topology State

Use namespace scope when known. Use `-A` only for cluster-wide changes and keep evidence bounded.

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,pods,svc,ingress,endpoints,endpointslices,networkpolicy -n <namespace> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

For rollout evidence, inspect retained controller revisions without changing the workload:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout history <deployment|statefulset|daemonset>/<workload-name> -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get rs -n <namespace> -o json
```

### 4. Collect Configuration And Security Metadata Safely

Collect ConfigMap and Secret metadata only. Do not retrieve `data`, `binaryData`, or `stringData` from the cluster.

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get configmap,secret -n <namespace> -o custom-columns='KIND:.kind,NAMESPACE:.metadata.namespace,NAME:.metadata.name,RESOURCE_VERSION:.metadata.resourceVersion,CREATED_AT:.metadata.creationTimestamp'
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get role,rolebinding,serviceaccount -n <namespace> -o json
```

When a Gateway API or cluster-wide RBAC change is suspected, collect only the relevant objects and record unavailable CRDs or RBAC as data gaps:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get gateway,httproute -n <namespace> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get clusterrole,clusterrolebinding -o json
```

Current resourceVersion, creation timestamps, managed fields, and retained ReplicaSets do not by themselves prove the change time, actor, prior value, or
causality.

### 5. Collect Historical And Observability Evidence

Use the observability context builder and dedicated Event, alarm, metric, or log skills for historical evidence. Use approved audit/CTS/LTS records or
user-provided sanitized before/after manifests when available. If no historical source exists, record the gap; do not invent a change timeline or infer Secret
contents.

### 6. Collect Cloud-Side Current State

Use read-only hcloud operations only when resource identifiers are known or safely derived. For node-pool, ELB, EIP, NAT, VPC, security-group, and ACL evidence,
use the focused Node or Network skill and correlate its command trace. Run `hcloud <service> <operation> --help` when the installed KooCLI operation shape
differs. Current cloud state is not cloud-side change history unless CTS/audit evidence supports it.

## Analysis Workflow

1. Define the incident window, fault time, affected objects, user symptoms, and known change records.
2. Build change candidates from retained workload revisions, current Events, approved audit/LTS/CTS records, alarms, logs, metrics, and user-provided change
   evidence.
3. For each candidate, record source, timestamp, actor when available, object, changed field summary, and whether a reliable before/after value exists.
4. Ignore low-signal controller status updates, Lease/Event churn, HPA-only replica noise, Pod binding, status-subresource writes, and platform-managed RBAC
   unless other evidence links them to the incident.
5. Classify candidates as workload, configuration, network, security, storage, or infrastructure changes. Never include Secret values in the classification
   evidence.
6. Map each candidate to current Pods, Services, Ingresses/Gateways, Nodes, namespaces, storage objects, and upstream/downstream dependency paths.
7. Rank candidates using temporal order, topology overlap, post-change response signals, focused diagnosis confirmation, and counter-evidence. A numeric score
   is comparative, not proof of causality.
8. Report Top N change risks with evidence, counter-evidence, data gaps, confidence, and the next discriminating verification.

## Output Format

The Markdown report must start with:

1. `## Summary`: most likely change, impact scope, confidence, evidence sufficiency, and whether causality is confirmed or only suspected.
2. `## Change Impact Analysis`: ranked changes with time, source, changed-field summary, affected objects, evidence, counter-evidence, score, and confidence.
3. `## Next Actions`: highest-value verification, focused diagnosis handoff, and approved remediation handoff when needed.
4. `## Evidence Timeline`: change, Event, alarm, metric/log, diagnosis, and user-symptom timestamps in one ordered timeline.
5. `## Blast Radius`: impacted workloads, Pods, Services, Ingresses/Gateways, Nodes, namespaces, storage objects, and dependency paths.
6. `## Data Gaps`: unavailable audit/LTS/CTS history, missing before/after state, RBAC denial, missing revisions, unknown actor, or cloud-side history gaps.
7. `## Appendix`: bounded command trace, evidence sources, and sanitized collector errors.

Do not conclude that a change caused the incident from an object update alone. Require temporal order plus at least one matching response signal or focused
diagnosis finding.

## Best Practices

- Build one shared incident timeline before ranking changes.
- Distinguish current state, retained revision history, audit history, and user claims.
- Prefer field-level summaries and hashes over sensitive configuration values.
- Preserve counter-evidence and candidates that occurred after the fault.
- Use focused domain diagnosers to confirm that a changed field matches the failure mode.

## Notes And Safety Rules

- Use only read-only hcloud and kubectl-cce operations.
- Do not run rollback, apply, create, patch, edit, delete, scale, restart, drain, reboot, rollout undo, exec, attach, port-forward, packet capture, or active
  traffic generation.
- Never retrieve or report Kubernetes Secret values. Do not retrieve ConfigMap data by default; use metadata or user-provided sanitized before/after evidence.
- Do not generate kubeconfig or call cloud/Kubernetes SDK clients.
- Hand remediation to the approved remediation workflow after explicit confirmation.

## Verification

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]change[-_]impact|huawei[-_]query|huawei[-_]get[-_]cce|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
git diff --check
```

Expected result: no executable SDK dispatcher entrypoint, bare Kubernetes access path, mutating command, or Secret-value collection remains. Markdown matches
must be prohibitions or verification text.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: change-candidate, correlation, scoring, and handoff workflow.
- `references/capability-map.md`: evidence sources, privacy controls, and known gaps.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/risk-rules.md`: read-only boundaries and remediation handoff rules.


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.
