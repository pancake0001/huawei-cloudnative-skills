# RiskRules

- Allows automatic execution of node read-only queries, Lease queries, Event queries, Pod queries, indicator queries, inspections and HSS queries.
- `huawei_node_failure_diagnose` is a read-only diagnostic tool that only generates structured evidence and Markdown reports and does not perform recovery actions.
- This skill is prohibited from directly calling cordon, uncordon, drain, reboot, and vulnerability status modification.
- It is recommended that the business impact, Pods on the node, rollback method and verification steps must be explained before restarting or draining.
- HSS repair actions must state that `confirm=true` can only be passed in after the user explicitly confirms it.