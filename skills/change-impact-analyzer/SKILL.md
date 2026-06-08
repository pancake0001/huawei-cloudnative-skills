---
name: change-impact-analyzer
description: Use this skill when a Huawei Cloud CCE incident may be caused by recent changes, including workload releases, ConfigMap/Secret updates, Service/Ingress/Gateway route changes, NetworkPolicy/RBAC/security policy changes, node taints or infrastructure changes, and the user needs a complete Markdown report with timeline, evidence, blast radius, risk score, and conclusion.
---

# change-impact-analyzer

You are responsible for turning "what changed before and after the failure occurred" into a provable cause analysis. By default, a complete Markdown report is output, including the troubleshooting process, core change timeline, evidence matrix, explosion radius, Top risk warning, conclusion and data gaps.

# # Four-stage pipeline

1. **Scope & Ingestion**: Confirm `region`, `cluster_id`, `namespace` or the entire cluster range, target object and time window; generate `Analysis-Trace-ID`; collect audit logs, K8s historical events, AOM active+history alarms, and current resource topology snapshots in parallel.
2. **Filtering & Categorization**: Semantic noise reduction for audit write operations, filtering interference such as HPA copy changes, controller writes, Token/Lease/Status, etc.; retaining core changes such as images, environment variables, CoreDNS, Service/Ingress, NetworkPolicy, RBAC, and Node taint.
3. **Impact & Blast Radius Modeling**: Map core changes to current Pod, Service, Ingress, Node, ConfigMap/Secret, Security Group/VPC ACL snapshots, and infer the impact area and propagation path.
4. **Synthesis & Reporting**: Output Markdown reports based on change sensitivity, topology scope, safety boundary span, failure time proximity, and event/alarm correlation scores.

# # Recommended action

Preferred: `huawei_change_impact_analyze`. It returns structured fields and `report_markdown`, which can be used to write out `.md` files using `output_file`.

Commonly used parameters:

- `region`, `cluster_id`: required.
- `hours` or `start_time`/`end_time`: analysis window, default is 1 hour in the past.
- `namespace`, `target_name`, `workload_name`, `app_name`: Convergence target ranges, but don’t ignore cluster-wide changes such as kube-system/CoreDNS.
- `fault_time` or `incident_time`: Fault time point, used for time proximity scoring.
- `log_group_id`/`log_stream_id` or log group/stream name: manually specified when automatic audit log discovery fails.
- `include_audit`, `include_k8s_events`, `include_aom`, `include_snapshots`: Close certain types of collection on demand.
- `top_n`: The highest number of risk warnings in the report, default 3.

# # Processing principles

- First look for changes, then for impacts, and then align with alarm/event/fault time; do not directly determine the root cause just because the object has been updated.
- Basic configuration changes such as CoreDNS, kube-proxy, network plug-ins, and Ingress controllers must be included in business failure analysis even if they occur in `kube-system`.
- Deployment HPA-only adjustments to `replicas` are generally considered noise; changes in images, startup parameters, probes, resource specifications, environment variables, and ConfigMap/Secret references are considered core changes.
- NetworkPolicy/RBAC changes should focus on connection timeouts, 403, DNS exceptions, and cross-namespace access failures.
- Infrastructure changes such as Node taint, cordon/drain, node pool expansion and contraction, cluster upgrade, etc. need to be judged based on Pod Pending, Evicted, NotReady and node events.

# # References

- For specific pipeline and scoring rules, please read `references/workflow.md`.
- Read `references/capability-map.md` for reusable capabilities, current gaps and recommended atomic capabilities.
- Output fields and Markdown templates read `references/output-schema.md`.
- Read-only boundaries and recovery action handovers read `references/risk-rules.md`.

# # Risk constraints

This skill only performs read-only analysis and report generation. No modification of workload, no rollback, no change of ConfigMap/Secret, no adjustment of security group/ACL/NetworkPolicy/RBAC, no cordon/drain/reboot node. Any restoration actions must be forwarded to the `auto-remediation-runner` for preview and confirmed by the user.