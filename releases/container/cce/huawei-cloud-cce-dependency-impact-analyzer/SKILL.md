---
id: huawei-cloud-cce-dependency-impact-analyzer
name: huawei-cloud-cce-dependency-impact-analyzer
description: >
  Analyze Huawei Cloud CCE service topology impact with hcloud CLI for cluster discovery and kubectl-cce plugin commands for read-only Pod, Service, Ingress, EndpointSlice, and Node evidence. Use this skill when a CCE incident needs dependency impact analysis, blast radius, propagation paths, affected entrypoints, upstream/downstream impact, or a complete Markdown impact report. Do not use Python SDK dispatcher actions.
tags: [cce, dependency, impact, cascade, hcloud, kubectl-cce]
---

# Huawei Cloud CCE Dependency Impact Analyzer

This skill maps service topology and blast radius for CCE incidents. It explains how a failing workload or Pod set propagates through Service, EndpointSlice, Ingress, and Node placement.

Execution model:

```text
hcloud CCE discovery -> kubectl cce topology snapshot -> target matching -> propagation paths -> impact report -> diagnosis handoff
```

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, `huawei_dependency_impact_*`, `huawei_get_cce_*`, bundled SDK scripts, kubeconfig generation, or Huawei Cloud SDK imports.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` before running Kubernetes commands.

## Related Skills

| Skill | When To Use |
| --- | --- |
| `huawei-cloud-cce-workload-failure-diagnoser` | Target workload is unavailable, rollout is stuck, or Pods are not Ready |
| `huawei-cloud-cce-pod-failure-diagnoser` | Individual Pods show CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending, or Evicted |
| `huawei-cloud-cce-network-failure-diagnoser` | Service, Ingress, EndpointSlice, DNS, NetworkPolicy, ELB, or EIP evidence suggests network failure |
| `huawei-cloud-cce-change-impact-analyzer` | Impact began after a deployment, config, route, policy, or node/infrastructure change |
| `huawei-cloud-cce-root-cause-analyzer` | Multiple domains need final root cause ranking |
| `huawei-cloud-cce-auto-remediation-runner` | Remediation preview/execution after confirmation |

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Required by kubectl-cce |
| `cluster_id` | Preferred | Resolve by name with hcloud if absent |
| `namespace` | Recommended | Target namespace or `-A` for broad scan |
| `target_name` | Recommended | Workload, Service, Pod, or app label value |
| `label_selector` | Optional | Prefer this when provided because it is more precise than name-prefix matching |
| `failure_symptom` | Optional | Service unavailable, ingress failure, pod unavailable, node concentration, etc. |

## Collection

1. Discover and verify the cluster:

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

2. Collect topology through kubectl-cce. Use a namespace when known; otherwise collect all namespaces and keep the result bounded in the report:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods,svc,ingress,endpoints,endpointslices -n <namespace> -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

Use `-A` only when the namespace is unknown or the incident is cluster-wide. If `endpointslices` is unavailable due to Kubernetes version or RBAC, fall back to `endpoints` and record the gap.

## Analysis Workflow

1. Scope: confirm region, cluster, namespace, target object, selector, and failure symptom.
2. Target matching: find target Pods by `label_selector` first, then ownerReference, Pod prefix, app labels, or Service selector.
3. Upstream mapping: find Services whose selectors match target Pod labels. Flag selector mismatches and Services with zero ready endpoints.
4. Entrypoint mapping: find Ingress rules and default backends pointing to those Services. Include host, path, backend Service, and class/controller when available.
5. Node distribution: map affected Pods to Nodes. Highlight single-node concentration, NotReady/pressure nodes, and zone concentration.
6. Propagation paths: model external traffic as `Ingress -> Service -> EndpointSlice/Endpoints -> Pods -> Nodes`; model cluster traffic as `Service DNS -> EndpointSlice/Endpoints -> Pods -> Nodes`.
7. Impact scoring: combine target Pod readiness, number of affected Services/Ingresses, endpoint availability, node concentration, and known user-visible symptoms.
8. Handoff: use workload/pod/node/network/change diagnosers for cause-level evidence; this skill focuses on impact and topology.

## Output Requirements

The Markdown report must start with:

1. `## Summary`: impacted entrypoints, affected backend, estimated blast radius, confidence.
2. `## Impact Paths`: path table from Ingress/Service to Pods and Nodes.
3. `## Next Actions`: most useful verification and domain handoff.
4. `## Evidence`: Pod readiness, Service selectors, EndpointSlice/Endpoints, Ingress backends, Node distribution, Events.
5. `## Confidence Limits`: missing namespace, RBAC denial, missing EndpointSlice, no traffic logs, or unknown upstream consumers.

Do not claim real user traffic impact from static topology alone unless logs, metrics, alarms, or user symptoms support it.

## Verification

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_dependency_impact|huawei_get_cce_|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

Expected result: no executable SDK dispatcher entrypoints or bare Kubernetes access paths remain. Markdown hits should be prohibitions or verification checks only.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: topology and impact workflow.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/risk-rules.md`: read-only boundaries and confidence limits.
