---
name: huawei-cloud-cce-dependency-impact-analyzer
description: >
  Analyze Huawei Cloud CCE dependency topology and blast radius using hcloud and read-only kubectl-cce evidence. Use this skill whenever the user asks which
  workloads, Pods, Services, Ingresses, EndpointSlices, Nodes, entrypoints, or upstream/downstream paths are affected by an incident and needs propagation
  paths, confidence limits, or a complete impact report.
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, dependency, impact]
---

# Huawei Cloud CCE Dependency Impact Analyzer

## Cluster Target Gate
For any operation that targets CCE resources inside a cluster, require `region` and `cluster_id` before invoking a downstream tool or command. Validate that the cluster ID is a standard UUID, or resolve an exact cluster name to one existing UUID in the supplied region. If either value is missing, invalid, or cannot be resolved, stop and ask the user for the correct region and cluster ID. Do not continue with an unscoped, region-wide, or all-namespaces fallback.

## Overview

Map CCE service topology and estimate incident blast radius. Explain how an unhealthy workload or Pod set can affect Services, EndpointSlices, Ingress
entrypoints, and Node placement without confusing a possible static path with observed user traffic loss.

Execution model:

```text
hcloud CCE discovery -> kubectl cce topology snapshot -> target matching -> propagation paths -> impact report -> diagnosis handoff
```

Do not use Python SDK dispatchers, legacy skill execution actions, bundled SDK scripts, kubeconfig generation, direct IAM HTTP calls, or Huawei Cloud SDK
imports.

## Prerequisites

1. `hcloud`, `kubectl`, and kubectl-cce are available as platform-native binaries.
2. Credentials and project context are provided through approved protected channels.
3. IAM permits read-only CCE cluster discovery, and Kubernetes RBAC permits the required workload, Pod, Service, Ingress, EndpointSlice, Node, and Event reads.
4. Read `references/kubectl-cce.md` before Kubernetes access. If a tool or plugin is missing, use `huawei-cloud-kubectl-cce-installer`; this skill must not
   install tools.
5. Never print credentials, Authorization headers, plugin credential material, registry secrets, application secrets, or sensitive values found in object data.

## Related Skills

| Skill                                            | When To Use                                                                                   |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `huawei-cloud-cce-observability-context-builder` | Alarms, logs, metrics, Events, and timeline context are needed to confirm observed impact     |
| `huawei-cloud-cce-workload-failure-diagnoser`    | Target workload is unavailable, rollout is stuck, or Pods are not Ready                       |
| `huawei-cloud-cce-pod-failure-diagnoser`         | Individual Pods show startup, image, scheduling, volume, probe, or eviction failures          |
| `huawei-cloud-cce-node-failure-diagnoser`        | Impact is concentrated on a Node or availability zone                                         |
| `huawei-cloud-cce-network-failure-diagnoser`     | Service, Ingress, EndpointSlice, DNS, policy, ELB, or EIP evidence suggests network failure   |
| `huawei-cloud-cce-storage-failure-diagnoser`     | Shared PVC, PV, CSI, attach, mount, or storage-backend dependencies are involved              |
| `huawei-cloud-cce-change-impact-analyzer`        | Impact began after a deployment, configuration, route, policy, Node, or infrastructure change |
| `huawei-cloud-cce-root-cause-analyzer`           | Multiple domains need final root-cause ranking                                                |

## Parameters

| Input             | Required    | Notes                                                        |
| ----------------- | ----------- | ------------------------------------------------------------ |
| `region`          | Yes         | Request context or `HW_REGION_NAME`; otherwise ask the user                                        |
| `project_id`      | Yes         | Pass explicitly to hcloud and kubectl-cce                    |
| `cluster_id`      | Preferred   | Resolve by name with hcloud if absent                        |
| `namespace`       | Recommended | Target namespace; use cluster-wide scope only when necessary |
| `target_name`     | Recommended | Workload, Service, Pod, Ingress, or stable app label value   |
| `label_selector`  | Optional    | Prefer an explicit selector over name-prefix matching        |
| `failure_symptom` | Optional    | User-visible failure or suspected affected path              |
| `fault_time`      | Recommended | Correlates topology with observability evidence              |

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

### 3. Collect Namespace Topology

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespace <namespace> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,pods,svc,ingress,endpoints,endpointslices -n <namespace> -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

Use `-A` only when the namespace is unknown or the incident is cluster-wide, and keep the report bounded. If EndpointSlice is unavailable because of Kubernetes
version or RBAC, use Endpoints and record the data gap.

### 4. Add Corroborating Evidence

Use the observability context builder or dedicated alarm, event, metric, and log skills when actual traffic or historical impact must be proved. Static object
relationships show possible propagation paths only.

### 5. Record Collection Gaps

Record the denied resource, scope, sanitized error, fallback used, and confidence impact. Do not bypass kubectl-cce with kubeconfig or SDK access.

## Analysis Workflow

1. Confirm region, project, cluster, namespace, target object, selector, symptom, and incident time.
2. Match the target using `label_selector` first, then workload ownership, Service selector, Pod name, or stable labels. Follow Pod -> ReplicaSet -> Deployment
   and equivalent StatefulSet/DaemonSet ownership chains.
3. Find Services whose selectors match target Pod labels. For selectorless or `ExternalName` Services, inspect type and associated Endpoints/EndpointSlices
   instead of treating the missing selector as an error.
4. Find Ingress rules and default backends that reference matched Services. Include host, path, backend Service/port, ingress class, and controller when
   available.
5. Map target and endpoint Pods to Nodes and zones. Highlight single-Node concentration, NotReady or pressured Nodes, and availability-zone concentration.
6. Model external paths as `Ingress -> Service -> EndpointSlice/Endpoints -> Pods -> Nodes` and internal paths as
   `Service DNS -> EndpointSlice/Endpoints -> Pods -> Nodes`.
7. Score impact using Pod readiness, exposed entrypoints, ready endpoint ratios, Node or zone concentration, and corroborating alarms, logs, metrics, Events, or
   user symptoms.
8. Hand cause-level evidence to focused workload, Pod, Node, network, storage, change, or root-cause skills. This skill owns topology and impact analysis, not
   remediation.

## Output Format

The Markdown report must start with:

1. `## Summary`: affected entrypoints/backends, estimated blast radius, confidence, and whether impact is observed or only possible.
2. `## Impact Paths`: path table from Ingress or Service to workloads, Pods, and Nodes.
3. `## Next Actions`: highest-value verification and focused diagnosis handoff.
4. `## Evidence`: workload ownership, Pod readiness, Service selectors/types, EndpointSlice/Endpoints, Ingress backends, Node distribution, and Events.
5. `## Confidence Limits`: missing scope, RBAC denial, unavailable EndpointSlice, absent traffic evidence, unknown consumers, or stale topology.
6. `## Appendix`: bounded command trace and sanitized collection failures.

Do not claim real user traffic impact from static topology alone. Require logs, metrics, alarms, synthetic checks from an approved test path, or explicit user
symptoms.

## Best Practices

- Separate possible propagation paths from observed impact.
- Prefer stable selectors and owner references over name-prefix matching.
- Treat selectorless and `ExternalName` Services as special cases, not automatic errors.
- Keep cluster-wide snapshots bounded and state the snapshot time.
- Preserve negative evidence and unknown upstream consumers when assigning confidence.

## Notes And Safety Rules

- Use only read-only hcloud and kubectl-cce operations.
- Do not run apply, create, patch, edit, delete, scale, rollout undo, restart, exec, attach, port-forward, packet capture, stress tests, or active traffic
  generation.
- Do not generate kubeconfig or call cloud/Kubernetes SDK clients.
- Do not expose credentials, Secret values, ConfigMap-sensitive values, or application data in evidence or reports.
- Hand remediation to the approved remediation workflow after explicit confirmation.

## Verification

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]dependency[-_]impact|huawei[-_]get[-_]cce|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
git diff --check
```

Expected result: no executable SDK dispatcher entrypoint, bare Kubernetes access path, or mutating command remains. Markdown matches must be prohibitions or
verification text.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: topology matching, propagation, and handoff workflow.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/risk-rules.md`: read-only boundaries and confidence limits.


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.


## Cluster ID Input

`cluster_id` must use a standard UUID. If the input is not a standard UUID, first list CCE clusters and perform an exact cluster-name match; convert the name to its UUID only when there is one match. If there is no match or more than one match, require the user to provide a UUID. Never guess or arbitrarily select a cluster.
