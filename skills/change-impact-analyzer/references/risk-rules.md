# RiskRules

# # Read only boundary

`change-impact-analyzer` only allows read-only querying and report generation:

- You can query audit logs, K8s events, AOM alarms, and the current status of Pod/Service/Ingress/Node/ConfigMap/Secret/NodePool/Security Group/VPC ACL.
- Workload, Network, and Node diagnostic actions can be called for read-only drill-down.
- `report_markdown` can be written to a user-specified `output_file`.

# # Prohibited actions

It is prohibited to execute within this skill:

- Roll back or republish the workload.
- Modify Deployment/StatefulSet/DaemonSet, ConfigMap, Secret, Service, Ingress, and Gateway.
- Modify NetworkPolicy, RBAC, Security Group, and VPC ACL.
- Scaling workloads or node pools.
- cordon, uncordon, drain, delete, reboot node or ECS.
- Modify HSS vulnerability status.

# # Resume action handover

When the report points to explicit recovery action:

1. Write recommended actions, risks and verification criteria in the report.
2. Perform any changes without `confirm=true`.
3. Hand over `auto-remediation-runner` to generate preview.
4. The skill can be resumed and executed only after explicit confirmation from the user.
5. After the change, run `huawei_change_impact_analyze` again or verify the corresponding diagnoser.

## Conclusion confidence

- `high`: At least three of the four types of evidence including audit changes, failure time proximity, event/alarm response, and topology impact surface are hit.
- `medium`: Hits audit changes and at least one type of response signal, or hits global core changes but insufficient response signals.
- `low`: only object writes or current snapshot, lack of time/response/topology evidence.

Low-confidence conclusions must include data gaps in the report, and do not write speculation as fact.