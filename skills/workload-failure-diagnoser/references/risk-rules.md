# Risk Rules

## Allowed

- Read Workload, ReplicaSet, Pod, Event, PVC, PV, metric, log, node, and network diagnostic data.
- Generate diagnosis summaries, evidence timelines, Top causes, and handoff recommendations.
- Suggest remediation options only as proposals.

## Not Allowed

- Do not call `huawei_scale_cce_workload`, `huawei_resize_cce_workload`, or `huawei_delete_cce_workload`.
- Do not cordon, uncordon, drain, reboot, delete nodes, or resize node pools.
- Do not add `confirm=true` to any action.
- Do not treat all namespace Warning events as evidence; only use UID-filtered events.

## Handoff

- Workload resource changes go to `auto-remediation-runner`.
- Node pressure or scheduling failures go to `node-failure-diagnoser`.
- Service, Ingress, ELB, or dependency reachability issues go to `network-failure-diagnoser`.
- Multi-domain uncertainty goes to `root-cause-analyzer`.
