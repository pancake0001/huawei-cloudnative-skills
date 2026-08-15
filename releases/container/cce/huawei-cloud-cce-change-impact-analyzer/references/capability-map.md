# Capability Map

## Primary Evidence Sources

| Capability          | Preferred Source                                 | Notes                                                                                                                                                                  |
| ------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cluster metadata    | hcloud CCE read-only commands                    | Use `ListClusters` / `ShowCluster` for identity and cluster context.                                                                                                   |
| Current topology    | `kubectl cce`                                    | Pods, workloads, ReplicaSets, Services, Ingresses, Endpoints, EndpointSlices, NetworkPolicies, Nodes, and ConfigMap/Secret metadata only. Never collect Secret values. |
| Current Events      | `kubectl cce get events` or event analyzer       | Use sorted Events for the current event window.                                                                                                                        |
| Historical Events   | `huawei-cloud-cce-kubernetes-event-analyzer`     | Prefer LTS-backed history when current Events are insufficient.                                                                                                        |
| AOM alarms          | `huawei-cloud-cce-alarm-correlation-engine`      | Use active/history alarm grouping and alarm storm analysis.                                                                                                            |
| Metrics             | `huawei-cloud-cce-metric-analyzer`               | Use only when metric evidence can confirm degradation after a change.                                                                                                  |
| Logs                | log/event skills or user-provided log source     | Treat missing log group/stream as a data gap.                                                                                                                          |
| Cloud network state | hcloud ELB/EIP/NAT/VPC read-only commands        | Use only current state unless CTS/audit history is available.                                                                                                          |
| Domain diagnosis    | workload, pod, node, network, storage diagnosers | Use to validate that the changed field matches the failure signature.                                                                                                  |

## Known Gaps

| Gap                                 | Impact                                                                                 | Handling                                                                                                                                  |
| ----------------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| CCE audit logs unavailable          | Cannot prove actor/operation for Kubernetes object changes                             | Record data gap; rely on rollout history, Events, and user-provided change records.                                                       |
| CTS/cloud-side history unavailable  | Cannot reconstruct ELB, Security Group, VPC ACL, node pool, or cluster upgrade history | Record data gap; compare current cloud state and ask for change window evidence.                                                          |
| Before/after manifest unavailable   | Cannot compute strict semantic diff                                                    | Compare retained ReplicaSets, rollout history, Events, and user-provided sanitized manifests. Do not infer prior Secret/ConfigMap values. |
| Secret or ConfigMap values withheld | Cannot prove a value-level configuration delta                                         | Use metadata, audit records, hashes, or user-provided sanitized field summaries; never retrieve Secret values.                            |
| LTS Event stream unavailable        | Historical Kubernetes Events may be missing                                            | Use current Events and mark limited event window.                                                                                         |
| RBAC denies resource reads          | Topology or policy relationship may be incomplete                                      | Record denied resource and reduce confidence.                                                                                             |

## Handoff Rules

- Workload field changes -> `huawei-cloud-cce-workload-failure-diagnoser` and `huawei-cloud-cce-pod-failure-diagnoser`.
- Node or scheduling changes -> `huawei-cloud-cce-node-failure-diagnoser`.
- Route, Service, Ingress, NetworkPolicy, or cloud network changes -> `huawei-cloud-cce-network-failure-diagnoser`.
- Storage-related changes -> `huawei-cloud-cce-storage-failure-diagnoser`.
- Blast radius questions -> `huawei-cloud-cce-dependency-impact-analyzer`.
- Multi-domain final ranking -> `huawei-cloud-cce-root-cause-analyzer`.
- Remediation preview/execution -> `huawei-cloud-cce-auto-remediation-runner` after explicit confirmation.
