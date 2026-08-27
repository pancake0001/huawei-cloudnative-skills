# Workflow

## 1. Scope And Evidence Sources

1. Confirm region, project_id, cluster_id, namespace or cluster-wide scope, target object, symptoms, fault_time, and time window.
2. Read `kubectl-cce.md`, verify `hcloud`, `kubectl`, and `kubectl-cce`, and resolve cluster metadata with hcloud.
3. Collect current Kubernetes topology and current Events through `kubectl cce`.
4. Collect historical Events, AOM alarms, metrics, and logs through the dedicated event, alarm, metric, or log skills when the current state is not enough.
5. Collect cloud-side read-only state with hcloud when identifiers are known: CCE node pools/add-ons, ELB/EIP/NAT/VPC/security groups/ACLs.
6. If audit logs, LTS streams, CTS traces, or cloud-side history are unavailable, record a data gap and reduce confidence.

## 2. Candidate Changes

Retain changes or change signals that can plausibly affect the incident:

- Workload: image, command/args, env, resources, probes, volumes, selector, affinity, tolerations.
- Config: ConfigMap/Secret metadata or user-provided sanitized before/after summaries, CoreDNS Corefile, kube-proxy, or core add-on config. Never retrieve
  Secret values.
- Network: Service ports/selectors, Ingress/Gateway backend/rules/TLS, NetworkPolicy ingress/egress.
- Security: RBAC, ServiceAccount, or policy changes that alter access boundaries.
- Infrastructure: node taints, cordon/drain, node pool scale, upgrade, security group/ACL/route changes.

## 3. Noise Reduction

Ignore low-signal control-plane noise unless other evidence links it to the incident:

- Lease, Event, TokenReview, SubjectAccessReview, and short-lifecycle token Secret churn.
- Pod binding, status-subresource writes, Node status patches, NPD/kubelet heartbeat.
- HPA-only replica adjustments without saturation or failed scaling evidence.
- Deployment/ReplicaSet/StatefulSet/DaemonSet controller status advancement.
- Platform-managed RBAC such as `system:cce:*` when the actor is clearly a CCE/platform component.

## 4. Blast Radius And Scoring

1. Map each candidate to current Pods, Services, Ingresses, Nodes, namespaces, and dependency paths.
2. Score temporal proximity: a candidate before the fault is stronger than one after the fault.
3. Score response signals: post-change Events, alarms, metrics, or logs that match the symptom increase confidence.
4. Score topology overlap: changes touching the affected object, namespace, entrypoint, node, or dependency path are stronger.
5. Score focused diagnosis: workload/pod/node/network/storage findings that match the changed field increase confidence.
6. Preserve counter-evidence: healthy rollout, unaffected endpoints, no post-change Events, unrelated namespace, or alarm before change.
7. Treat numeric risk scores as comparative ranking only; they do not prove causality.

## 5. Reporting

The report must include Summary, Change Impact Analysis, Next Actions, Evidence Timeline, Blast Radius, Data Gaps, and Appendix. Do not state that a change
caused the incident unless temporal order plus response evidence or focused diagnosis supports it.
