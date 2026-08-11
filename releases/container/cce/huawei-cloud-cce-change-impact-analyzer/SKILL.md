---
id: huawei-cloud-cce-change-impact-analyzer
name: huawei-cloud-cce-change-impact-analyzer
description: >
  Analyze whether recent Huawei Cloud CCE changes caused an incident using hcloud CLI, kubectl-cce plugin commands, AOM/LTS evidence skills, and read-only topology snapshots. Use this skill for change impact analysis involving workload releases, ConfigMap/Secret updates, Service/Ingress/Gateway route changes, NetworkPolicy/RBAC/security policy changes, node taints, node pool or infrastructure changes, audit/event/alarm correlation, blast radius, risk scoring, and Markdown reports. Do not use Python SDK dispatcher actions.
tags: [cce, change-impact, risk-assessment, hcloud, kubectl-cce]
---

# Huawei Cloud CCE Change Impact Analyzer

This skill turns "what changed before the incident" into evidence-based causal attribution. It correlates current topology, Kubernetes Events, historical Events/logs when available, AOM alarms, and read-only cloud metadata to identify changes that plausibly caused or amplified a CCE incident.

Execution model:

```text
hcloud CCE discovery -> kubectl cce current topology/events -> optional AOM/LTS/alarm evidence -> change classification -> blast radius -> Markdown report
```

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, `huawei_change_impact_*`, `huawei_query_*`, `huawei_get_cce_*`, bundled SDK scripts, kubeconfig generation, or Huawei Cloud SDK imports.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` before running Kubernetes commands.

## Related Skills

| Skill | When To Use |
| --- | --- |
| `huawei-cloud-cce-kubernetes-event-analyzer` | Historical or current Kubernetes Events are needed beyond the normal event window |
| `huawei-cloud-cce-alarm-correlation-engine` | AOM active/history alarms, alarm storms, or alarm time anchors are needed |
| `huawei-cloud-cce-metric-analyzer` | Metrics are needed to validate degradation after a change |
| `huawei-cloud-cce-workload-failure-diagnoser` | A workload release, image, probe, resource, env, or command change is suspicious |
| `huawei-cloud-cce-network-failure-diagnoser` | Service, Ingress, NetworkPolicy, ELB, EIP, NAT, security group, or ACL changes are suspicious |
| `huawei-cloud-cce-node-failure-diagnoser` | Node taint, cordon/drain, node pool, upgrade, pressure, or NotReady symptoms are suspicious |
| `huawei-cloud-cce-dependency-impact-analyzer` | The blast radius and service topology need to be mapped |
| `huawei-cloud-cce-root-cause-analyzer` | Change findings must be ranked with other root cause candidates |
| `huawei-cloud-cce-auto-remediation-runner` | Remediation preview/execution after explicit confirmation |

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Required by kubectl-cce and many hcloud operations |
| `cluster_id` | Preferred | Resolve by name with hcloud if absent |
| `namespace` | Optional | Use cluster-wide scope for core-system and network changes |
| `target_name` | Optional | Workload, Service, Pod, Ingress, Node, or app label |
| `fault_time` | Recommended | Needed to score temporal proximity |
| `hours` / `start_time` / `end_time` | Recommended | Default to a narrow incident window when possible |
| `log_group_id` / `log_stream_id` | Optional | Use only if audit/LTS discovery cannot find the correct stream |

## Evidence Collection

1. Verify hcloud and kubectl-cce access. Missing plugin setup belongs to `huawei-cloud-kubectl-cce-installer`.
2. Discover cluster metadata:

```bash
hcloud CCE ListClusters --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --cli-region=<region> --cli-output=json
```

3. Collect current topology and current response signals:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,rs,pods,svc,ingress,endpoints,endpointslices,networkpolicy,configmap,secret -A -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o json
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

4. For historical Events, audit logs, AOM alarms, and metrics, prefer the dedicated event, alarm, metric, or log skills. If the required LTS/AOM/audit source is not available, record it as a data gap instead of inventing a change timeline.
5. For cloud-side current state, use read-only hcloud commands when identifiers are known or safely derived, such as CCE node pools, ELB, EIP, NAT, VPC security groups, and VPC ACLs. Run `hcloud <service> <operation> --help` when the exact KooCLI operation shape is uncertain, and document the command category rather than guessing fields.

## Analysis Workflow

1. Scope and timeline: define incident window, fault time, affected objects, and known symptoms.
2. Candidate changes: collect workload spec deltas from current ReplicaSets/rollout history when available, recent Events, audit/LTS records when available, and cloud metadata changes supplied by the user or logs.
3. Noise reduction: ignore controller status updates, Lease/Event churn, HPA-only replica noise, Pod binding, `/status` writes, and platform-managed RBAC unless evidence ties them to the incident.
4. Classify risky changes:
   - workload: image, command/args, env, resources, probes, volumes, selectors, affinity, tolerations;
   - config: ConfigMap/Secret data, CoreDNS Corefile, kube-proxy or core add-on config;
   - network: Service ports/selectors, Ingress/Gateway backends, NetworkPolicy ingress/egress;
   - security: RBAC and ServiceAccount changes that alter access boundaries;
   - infrastructure: node taints, cordon/drain, node pool scale, upgrade, security group/ACL route changes.
5. Blast radius: map each candidate to Pods, Services, Ingresses, Nodes, namespaces, and upstream/downstream paths.
6. Correlation: score each candidate by whether it happened before the fault, whether Events/alarms/metrics changed after it, whether it touches the affected topology, and whether a focused diagnoser confirms the failure signature.
7. Report Top N change risks with evidence, counter-evidence, data gaps, and next verification.

## Output Requirements

The Markdown report must start with:

1. `## Summary`: most likely change, impact scope, confidence, and whether evidence is sufficient.
2. `## Change Impact Analysis`: Top N risky changes with timeline, affected objects, evidence, counter-evidence, and score.
3. `## Next Actions`: verification commands, focused diagnosis skill handoff, and remediation handoff if needed.
4. `## Evidence Timeline`: change time, Events, alarms, metrics/log evidence, and user symptoms.
5. `## Blast Radius`: impacted Pods, Services, Ingresses, Nodes, namespaces, and dependency paths.
6. `## Data Gaps`: unavailable audit logs, LTS streams, RBAC denial, missing rollout history, or cloud-side history gaps.

Do not conclude "change caused the incident" from object updates alone. Require temporal order plus at least one response signal or focused diagnoser finding.

## Verification

```bash
rg -n "scripts/huawei-cloud.py|skill action=exec|huawei_change_impact|huawei_query_|huawei_get_cce_|huaweicloudsdk|KubernetesClusterCertRequest|CreateKubernetesClusterCert" . --glob "!*.md"
rg -n -P "^kubectl (?!cce|version|plugin)" .
```

Expected result: no executable SDK dispatcher entrypoints or bare Kubernetes access paths remain. Markdown hits should be prohibitions or verification checks only.

## References

- `references/kubectl-cce.md`: plugin access contract.
- `references/workflow.md`: change correlation workflow and scoring.
- `references/capability-map.md`: evidence sources and known gaps.
- `references/output-schema.md`: structured output and Markdown layout.
- `references/risk-rules.md`: read-only boundaries and handoff rules.
