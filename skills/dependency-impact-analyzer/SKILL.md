---
name: dependency-impact-analyzer
description: Use this skill when a Huawei Cloud CCE incident needs service topology impact analysis, including Service/Ingress/Pod/Node propagation paths, upstream/downstream blast radius, affected entrypoints, and a complete Markdown impact report with evidence and confidence limits.
---

# dependency-impact-analyzer

You are responsible for determining the fault propagation path and upstream and downstream impacts based on the Kubernetes service topology. By default, a complete Markdown report is output, including the troubleshooting process, topology evidence, propagation path, impact conclusion and capability gaps.

# # Processing steps

1. Specify `region`, `cluster_id`, `namespace`, target workload/service name or `label_selector`.
2. It is preferred to call `huawei_dependency_impact_analyze` to collect the current snapshots of Pod, Service, Ingress and Node.
3. Use Service selector to identify the upstream service of the target Pod, and use Ingress backend to identify the external entrance.
4. Give the impact level based on Pod Ready status, Service/Ingress number and propagation path.
5. Output the impact area, propagation path, evidence table and confidence limit.
6. If the impact comes from recent changes, hand it over to `change-impact-analyzer`; if recovery is needed, hand it over to `auto-remediation-runner`.

# # Recommended action

Preferred: `huawei_dependency_impact_analyze`.

Supplementary queries: `huawei_get_cce_pods`, `huawei_get_cce_services`, `huawei_get_cce_ingresses`, `huawei_get_kubernetes_nodes`.

Related diagnostics: `huawei_workload_rollout_diagnose`, `huawei_network_failure_diagnose`, `huawei_change_impact_analyze`.

# # References

- Read `references/workflow.md` for specific pipeline.
- The output structure reads `references/output-schema.md`.
- Read-only bounds and confidence limits read `references/risk-rules.md`.

# # Risk constraints

This skill only performs read-only topology analysis and report generation. Does not modify Service, Ingress, Deployment, NetworkPolicy, ELB, or node status. Restoration actions must be given to `auto-remediation-runner` for preview and confirmation.