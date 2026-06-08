# CapabilityMap

# # Current project structure

This warehouse adopts a simplified multi-skill architecture:

- Each skill is placed independently in `skills/<skill>/`.
- Capability implementation is concentrated in the root directory `scripts/huawei_cloud/`.
- `scripts/huawei-cloud.py` serves as the unified CLI entry.
- `scripts/huawei_cloud/dispatcher.py` maintains the mapping from action to Python handler.
- `skill-profile.yaml` declares tool boundaries and `scripts/dev/generate_manifests.py` generates `manifest.json`.

`change-impact-analyzer` does not copy scripts, but only reuses shared capabilities through `skills/change-impact-analyzer/scripts -> ../../scripts`.

# # Reusability

| Capability domain | Existing action/script | Reuse method |
| --- | --- | --- |
| Audit changes | `huawei_query_cce_audit_logs` / `cce_app_logs.py` | Get the create/update/patch/delete change shadow in Kubernetes audit, including executor, verb, resource, namespace, name, requestURI, statusCode, raw audit. |
| K8s historical events | `huawei_query_k8s_events_from_lts` / `cce_events_lts.py` | Read historical events from LTS to make up for the problem that the K8s API can only see recent events. |
| Current events | `huawei_get_cce_events` / `cce.py` | When LTS Event is unavailable, query the current Events. |
| Alarm correlation | `huawei_analyze_aom_alarms` / `aom.py` | Analyze active + history alarms at the same time to avoid missing recovered resource alarms. |
| Release Diagnostics | `huawei_workload_rollout_diagnose` / `workload_rollout_diagnosis.py` | Change pointer to Deployment/StatefulSet/DaemonSet Drill down when release fails. |
| Network Diagnostics | `huawei_network_failure_diagnose` / `network_failure_diagnosis.py` | Drill down when changing the link pointing to Service/Ingress/NetworkPolicy/ELB. |
| Node diagnosis | `huawei_node_failure_diagnose` / `node_failure_diagnosis.py` | Drill down when changes point to Node taint, NotReady, scheduling exceptions, and node resource pressure. |
| Current topology | `huawei_get_cce_pods`, `huawei_get_cce_services`, `huawei_get_cce_ingresses`, `huawei_get_kubernetes_nodes` | Build the Pod-Service-Ingress-Node influence surface. |
| Configuration snapshot | `huawei_list_cce_configmaps`, `huawei_list_cce_secrets` | Identify the current status of CoreDNS, kube-proxy, and business configuration objects. |
| Cloud network snapshot | `huawei_list_security_groups`, `huawei_list_vpc_acls` | Provides the current status of security groups/ACLs for reporting gaps and manual verification. |

The `huawei-cloud` skill of external `pancake0001/cce-skills` also covers these directions: unified Huawei Cloud resource query, CCE resource query, AOM alarm active+history analysis, LTS log, network/workload/node diagnosis, automatic inspection and HTML diagnostic report. The current warehouse has split these capabilities into finer diagnosers and shared dispatchers, which are suitable for reuse in `change-impact-analyzer` rather than repeated implementations.

# # Supplemented combination capabilities

New action: `huawei_change_impact_analyze`.

It is not a single query tool, but a combined orchestration:

1. Generate `Analysis-Trace-ID`.
2. Collect audit logs, K8s historical events, AOM alarms, and current resource snapshots.
3. Perform core change classification and noise elimination on audit write operations.
4. Map the changes to the current topology and calculate the blast radius.
5. Correlate with failure time, events, and alarms.
6. Output structured `top_changes`, complete `changes` and customer deliverable `report_markdown`.

# # Noise reduction rules optimized based on real cluster cases

Audit records of `ClusterRole/system:cce:packageversion` updated by `system:masters` / CCE platform components have appeared in real clusters. This object belongs to CCE self-managed component metadata and should not be output as abnormal changes in customer business. The current version has eliminated the following runtime or platform hosting behaviors from core changes:

- `serviceaccounts/token` sub-resource creation.
- `nodes/status` patch.
- All `/status` subresources are written, even if the audit log requestObject echoes the full spec.
- kube-scheduler `pods/binding`.
- deployment/replicaset/statefulset/daemonset controller drives state-generated workload writes.
- CCE platform self-managed RBAC: `system:cce:*`, `cce:*` and executors match CCE/platform components.

RBAC changes by normal users, unknown actors, or non-CCE managed objects remain high risk.

# # Atomic abilities that still need to be completed

| Gap | Reason | Suggested action |
| --- | --- | --- |
| CTS/Cloud Audit History | Currently, Kubernetes audit can only be restored well, and historical changes of CCE console, node pool, cluster upgrade, ELB, security group, and VPC ACL cannot be reliably restored. | `huawei_query_cts_traces`, supports service/resource/user/time/filter. |
| before/after YAML snapshot | Audit If `requestObject`/`patch` is not recorded, only object-level judgment can be made, and strict Semantic Diff cannot be done. | `huawei_get_k8s_resource_history` or connect to GitOps/backup system. |
| NetworkPolicy Current Topology | The existing network diagnosis has internal policy judgment, but lacks independent listing/parsing actions. | `huawei_list_cce_networkpolicies`, output selector, ingress, egress and hit Pod. |
| RBAC current topology | Missing Role/ClusterRole/Binding query, unable to evaluate permission boundary specific diffusion. | `huawei_list_cce_rbac`, output subject -> role -> verbs/resources. |
| Gateway API current topology | Gateway/HTTPRoute in audit has been identified, but the current snapshot lacks independent queries. | `huawei_list_cce_gateway_api_resources`. |
| ConfigMap/Secret usage relationship | Currently, it can only be inferred by namespace or core component name, and "which Pods/Workloads reference this configuration" is missing. | `huawei_find_config_consumers`, scan volumes/envFrom/env/valueFrom. |
| Node taint/toleration precise impact | Currently only associated node Pod, lack of Pod tolerations and scheduling constraint simulation. | `huawei_analyze_node_taint_impact`. |
| Cloud network changes diff | Only current SG/ACL snapshot, missing historical rule changes and executors. | Depend on CTS and add `huawei_analyze_cloud_network_change`. |

# # Conclusion of checking and filling in gaps

The current warehouse already has the main capabilities of "observation, auditing, events, alarms, and Workload/Node/Network drill-down", which is sufficient to implement the first version of the change impact attribution report. The main shortcomings are historical changes on the cloud side and strict before/after diff; these cannot be completed by reasoning through combined skills, and require subsequent atomic capabilities such as CTS, NetworkPolicy/RBAC/Gateway independent query and configuration reference relationship scanning.