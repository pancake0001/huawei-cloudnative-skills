# RiskRules

# # Default read-only

The default behavior of this skill only allows reading and reporting, and does not allow direct changes to the cluster status.

Disable automatic execution:

- Create, replace or delete HPA.
- Modify Deployment/StatefulSet replicas, requests, and limits.
- Modify the node pool min/max and manually expand the node pool.
- Install, upgrade, and uninstall CCE plug-ins.
- cordon, drain, delete, reboot nodes.
- Expand VPC subnets, apply for quotas, and modify IAM delegation.

# # Outputable rectification content

Allow output:

- HPA YAML suggestions or no `confirm=true` preview for `huawei_configure_cce_hpa`.
- Node pool autoscaling min/max recommendations.
- request/limit adjustment suggestions.
- Fix suggestions for affinities, taints, tolerations, nodeSelector.
- Manual checklist for subnets, quotas, IAM.
- Verification steps and rollback paths before and after changes.

# # Actions that need to be transferred

When the customer explicitly requests rectification, transfer it to the `auto-remediation-runner` or manual change process:

- HPA configuration: Preview the manifest first and then confirm it by the customer.
- Node pool expansion or min/max adjustment: Business impact, costs, AZ/specifications, and rollback plan must be confirmed.
- request/limit adjustment: requires release window or rolling update schedule.
- Plug-in installation/upgrade: It is necessary to confirm the plug-in version, cluster version compatibility and rollback plan.