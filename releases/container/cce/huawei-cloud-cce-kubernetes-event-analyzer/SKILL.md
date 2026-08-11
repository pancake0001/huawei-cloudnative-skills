---
name: huawei-cloud-cce-kubernetes-event-analyzer
description: >
  Query and analyze Kubernetes Events in Huawei Cloud CCE clusters with kubectl-cce plugin commands for current Events and hcloud/LTS read-only queries for historical Events when configured. Trigger when users ask about CCE events, Kubernetes warning events, FailedScheduling, FailedMount, ImagePullBackOff, event patterns, historical events in LTS, or event-based diagnosis for a CCE cluster or namespace. Do not use Python SDK dispatcher actions or generated kubeconfig.
tags: [CCE, Kubernetes, events, observability, hcloud, kubectl-cce]
---

# Huawei Cloud CCE Kubernetes Event Analyzer

This skill queries and analyzes Kubernetes Events to identify Warning patterns, repeated failures, affected resources, and useful handoffs to diagnosis skills.

Execution model:

```text
kubectl cce current Events -> optional kubectl cce LogConfig discovery -> optional hcloud LTS bounded query -> event grouping -> diagnosis handoff
```

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, `huawei_get_cce_events`, `huawei_query_k8s_events_from_lts`, `huawei_analyze_cce_events`, generated kubeconfig, external kubeconfig fallback, raw Kubernetes SDK calls, or Huawei Cloud SDK imports.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` before running Kubernetes commands.

## Related Skills

- `huawei-cloud-cce-pod-failure-diagnoser` - Pod event causes such as ImagePullBackOff, OOMKilled, CrashLoopBackOff, FailedMount
- `huawei-cloud-cce-workload-failure-diagnoser` - rollout and ReplicaSet event correlation
- `huawei-cloud-cce-node-failure-diagnoser` - NodeNotReady, Evicted, pressure, lease, and node agent events
- `huawei-cloud-cce-storage-failure-diagnoser` - FailedMount, FailedAttachVolume, PVC, PV, and CSI event analysis
- `huawei-cloud-cce-network-failure-diagnoser` - FailedCreatePodSandBox, CoreDNS, network plugin, Service/Ingress events
- `huawei-cloud-cce-root-cause-analyzer` - cross-domain synthesis

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Required by kubectl-cce |
| `cluster_id` | Yes | CCE cluster ID |
| `namespace` | Optional | Use `-A` only when namespace is unknown or cluster-wide |
| `event_type` | Optional | Default to `Warning` for diagnosis |
| `reason` / `keywords` | Optional | FailedScheduling, FailedMount, ImagePullBackOff, etc. |
| `start_time` / `end_time` | Optional | Required for historical LTS query |
| `limit` | Optional | Keep output bounded |

## Current Events

Use kubectl-cce directly:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --field-selector type=Warning --sort-by=.lastTimestamp
```

Group by `type`, `reason`, namespace, involved object, and repeated `count`. For very large outputs, filter to Warning first and summarize top reasons before showing samples.

## Historical Events

For historical windows beyond the Kubernetes Event retention window:

1. Check whether the Cloud Native Log Collection add-on and `default-event` LogConfig exist:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get logconfigs.logging.openvessel.io -A -o json
```

2. If the LogConfig contains LTS group/stream identifiers, query LTS through hcloud with an explicit bounded time range. If the exact KooCLI LTS operation or IDs are unavailable, record the historical Event gap instead of fabricating history.

## Analysis Workflow

1. Collect current Events for the target namespace or cluster.
2. Filter Warning Events first, then apply reason, keyword, object, or time filters.
3. Group by reason, namespace, involved object kind/name, and repeated count.
4. Build a short event timeline around the incident window.
5. Map patterns to handoff targets:
   - ImagePullBackOff/ErrImagePull -> pod/workload diagnoser;
   - FailedScheduling/Preempting -> workload or node diagnoser;
   - FailedMount/FailedAttachVolume -> storage diagnoser;
   - Evicted/NodeNotReady -> pod or node diagnoser;
   - FailedCreatePodSandBox/CNI/DNS -> network diagnoser.
6. Report data gaps such as missing RBAC, no Event retention, absent LogConfig, or unavailable LTS stream.

## Output Requirements

The Markdown report must start with:

1. `## Summary`: top event pattern, affected scope, and confidence.
2. `## Event Patterns`: top reasons with counts, sample messages, and affected resources.
3. `## Next Actions`: focused diagnosis handoff and verification.
4. `## Event Timeline`: ordered event samples around the incident window.
5. `## Data Gaps`: RBAC, retention, LTS, or filtering gaps.

Keep object names in evidence when needed for diagnosis, but redact secrets and avoid exposing sensitive payloads.

## Verification

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_get_cce_events|huawei_query_k8s_events_from_lts|huawei_analyze_cce_events|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert|external kubeconfig|temporary kubeconfig" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

Expected result: no executable SDK dispatcher entrypoints, generated kubeconfig path, or bare Kubernetes access paths remain. Markdown hits should be prohibitions or verification checks only.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: event query and grouping workflow.
- `references/risk-rules.md`: read-only boundaries.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/acceptance-criteria.md`: acceptance checks.
