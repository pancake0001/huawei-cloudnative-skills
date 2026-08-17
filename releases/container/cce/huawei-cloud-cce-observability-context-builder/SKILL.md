---
name: huawei-cloud-cce-observability-context-builder
description: >
  Build a read-only observability context package for Huawei Cloud CCE incidents using hcloud and kubectl-cce before root-cause diagnosis. Use this skill
  whenever the user needs live Kubernetes state, Events, bounded Pod logs, AOM alarms, metrics, LTS context, topology, time windows, evidence gaps, or the next
  diagnostic handoff.
version: 1.0.0
tags: [huawei-cloud, cce, observability, kubectl, context]
---

# Huawei Cloud CCE Observability Context Builder

## Overview

This skill builds the first-pass observability context for an active or recent CCE incident. It does not decide the final root cause by itself. It collects a
compact evidence package so `huawei-cloud-cce-root-cause-analyzer` and focused domain diagnosers start with the same timeline, scope, signals, and data gaps.

Think of it as the production observability context step:

```text
scope + time window -> hcloud CCE/AOM/LTS context -> kubectl cce Events/logs/topology -> signal timeline -> root-cause handoff
```

Do not use legacy Python dispatchers, old skill execution actions, Huawei Cloud SDK imports, Kubernetes SDK clients, generated kubeconfig, or mutation commands.

## Related Skills

| Skill                                         | Role                                                     |
| --------------------------------------------- | -------------------------------------------------------- |
| `huawei-cloud-cce-root-cause-analyzer`        | Main consumer of the context package                     |
| `huawei-cloud-cce-alarm-correlation-engine`   | Deep AOM alarm grouping when alarms dominate the context |
| `huawei-cloud-cce-kubernetes-event-analyzer`  | Deep Event analysis when Events dominate the context     |
| `huawei-cloud-cce-metric-analyzer`            | Deep AOM/CES metrics when metrics dominate the context   |
| `huawei-cloud-cce-log-analyzer`               | Deep log pattern analysis when logs dominate the context |
| `huawei-cloud-cce-pod-failure-diagnoser`      | Pod-specific follow-up                                   |
| `huawei-cloud-cce-workload-failure-diagnoser` | Workload rollout and readiness follow-up                 |
| `huawei-cloud-cce-node-failure-diagnoser`     | Node pressure or node readiness follow-up                |
| `huawei-cloud-cce-network-failure-diagnoser`  | Service, DNS, Ingress, ELB/EIP/NAT follow-up             |
| `huawei-cloud-cce-storage-failure-diagnoser`  | PVC/PV/CSI follow-up                                     |

## Parameters

| Input                                           | Required    | Notes                                                   |
| ----------------------------------------------- | ----------- | ------------------------------------------------------- |
| `region`                                        | Yes         | Example: `cn-north-4`                                   |
| `project_id`                                    | Recommended | Required for reliable AK/SK and `kubectl cce` execution |
| `cluster_id`                                    | Preferred   | Resolve by exact cluster name when absent               |
| `namespace`                                     | Optional    | Narrow app-level collection                             |
| `workload`, `pod`, `node`, `service`, `ingress` | Optional    | Target object hints                                     |
| `fault_time`, `start_time`, `end_time`, `hours` | Recommended | Default to recent 1 hour if unclear                     |
| `symptoms`                                      | Recommended | User-visible symptom, alert text, or affected business  |

If the target is ambiguous, collect cluster/namespace-level context first and record ambiguity as a data gap.

## Explicit Credential Propagation

Accept `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token`. AK and SK must be supplied together; a token requires that pair. When
provided, append all supplied options to every `hcloud` and `kubectl cce` command, pass them unchanged to delegated skills, and do not use an hcloud profile
or authentication environment variables. Never print credential values.

## Prerequisites

1. `hcloud`, `kubectl`, and the kubectl-cce plugin are available as platform-native binaries.
2. Credentials are provided through approved parameters, protected environment variables, or an approved credential provider.
3. IAM and Kubernetes RBAC permit the required read-only cluster, Event, log, metric, alarm, and topology queries.
4. If tooling is missing, use `huawei-cloud-kubectl-cce-installer`. This skill must not download or execute installer scripts.
5. Never print AK, SK, tokens, Authorization headers, proxy credentials, or secrets found in logs.

## Core Commands And Access Paths

### Access Preflight

```bash
hcloud version
kubectl version --client
kubectl plugin list
```

If a tool or plugin is missing, stop and use `huawei-cloud-kubectl-cce-installer`. Do not download an installer or fall back to SDK or kubeconfig access in this
skill.

### Cluster And Inventory Context

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json --project_id=<project-id>
hcloud CCE ShowCluster --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
hcloud CCE ListNodes --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
```

Use the installed `hcloud` help if a parameter name differs in the local KooCLI version. Keep the evidence source as hcloud, not SDK.

### Kubernetes Current Context

Read [references/kubectl-cce.md](references/kubectl-cce.md) before running Kubernetes commands.

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,svc,ingress,endpoints,endpointslices -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes,pv,pvc,storageclass -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

For scoped targets:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe pod <pod-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --previous --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top nodes
```

`top`, logs, and previous logs may fail due to Metrics API, RBAC, container restart history, or plugin limitations. Record the failure as a data gap.

### Alarm, Metric, And Log Context

- Use `huawei-cloud-cce-alarm-correlation-engine` for AOM active/history alarm grouping.
- Use `huawei-cloud-cce-metric-analyzer` for AOM/CES time-series and cloud-resource metrics.
- Use `huawei-cloud-cce-log-analyzer` or `hcloud LTS` read-only queries when LTS log context is required and the local hcloud service model supports the needed
  operation.
- If an AOM/LTS source is unavailable, record the source, time window, and missing permission/source as a data gap.

Do not hand-roll IAM signing or query raw cloud APIs from this skill.

## Workflow

1. Confirm incident scope: symptom, time window, region, project ID, cluster, namespace, and target objects.
2. Resolve cluster identity and health with `hcloud CCE`.
3. Collect current Kubernetes state with `kubectl cce`: Pods, workloads, Services/Ingress, Endpoints/EndpointSlices, Nodes, PVC/PV, Events, and bounded logs
   when needed.
4. Collect observability signals through dedicated read-only skills: alarms, metrics, Events, and logs.
5. Normalize all signals into one timeline. Preserve source, timestamp, object, severity, message, and confidence.
6. Summarize the context without over-diagnosing. Point to the most relevant next diagnoser or root-cause analyzer.
7. Output a Markdown context package with summary, high-signal findings, timeline, gaps, and commands used.

## Output Format

See [references/output-schema.md](references/output-schema.md). The output must put useful context first:

1. `## Summary`
2. `## Scope`
3. `## High-Signal Findings`
4. `## Timeline`
5. `## Evidence By Source`
6. `## Data Gaps`
7. `## Recommended Handoff`
8. `## Commands Used`

## Best Practices

- Fix the scope and time window before collecting evidence.
- Keep logs and metrics bounded and preserve source timestamps for timeline correlation.
- Distinguish observed facts, interpretations, and data gaps in the context package.
- Route deep analysis to the matching domain skill instead of duplicating its workflow.

## Notes And Guardrails

Read [references/risk-rules.md](references/risk-rules.md) before acting.

- Read-only only.
- Use `hcloud` and `kubectl cce`.
- Do not generate kubeconfig.
- Do not use SDK clients or old dispatcher actions.
- Do not run unbounded log streams or interactive commands.
- Do not copy secrets from logs; describe the hit location and redact values.

## Verification

```bash
hcloud CCE ShowCluster --cli-region=<region> --cli-output=json --cluster_id=<cluster-id> --project_id=<project-id>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

Repository checks:

```bash
rg -n "huawei-cloud[.]py|skill action=ex[e]c|huawei[-_]|huaweicloudsdk|KubernetesClusterCert|CreateKubernetesClusterCert|--kubeconfig" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
git diff --check
```

## References

| Document                                       | Description                          |
| ---------------------------------------------- | ------------------------------------ |
| [Workflow](references/workflow.md)             | Context collection sequence          |
| [Risk Rules](references/risk-rules.md)         | Read-only safety rules               |
| [Output Schema](references/output-schema.md)   | Context package report format        |
| [kubectl-cce Usage](references/kubectl-cce.md) | Plugin setup and command constraints |
