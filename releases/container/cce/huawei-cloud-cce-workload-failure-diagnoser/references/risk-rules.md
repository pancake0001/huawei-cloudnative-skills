# Risk Rules

This skill operates at R1: read-only observation and diagnosis.

## Allowed

- Run CCE read operations through `hcloud CCE ListClusters`, `ShowCluster`, and `ShowClusterEndpoints`.
- Run `hcloud CCE CreateKubernetesClusterCert` to acquire a short-lived kubeconfig for diagnosis.
- Run read-only `kubectl` commands: `get`, `describe`, `logs`, `rollout status`, `rollout history`, `auth can-i`, `cluster-info`, and optional `top`.
- Read Workload, ReplicaSet, Pod, Event, PVC, PV, Service, Endpoint, Ingress, HPA, Node, metric, and log evidence.
- Generate diagnosis summaries, timelines, Top causes, and handoff recommendations.
- Suggest remediation options only as proposals.

## Not Allowed

- Do not run Python SDK dispatcher commands or bundled SDK scripts.
- Do not run `scripts/huawei-cloud.py`, `skill action=exec`, or any `huawei_workload_*` action.
- Do not run `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `replace`, `rollout undo`, `cordon`, `uncordon`, `drain`, `taint`, or `label` unless the user explicitly switches to a remediation task and accepts the risk.
- Do not run hcloud create/update/delete operations except `CreateKubernetesClusterCert`.
- Do not cordon, uncordon, drain, reboot, delete nodes, or resize node pools.
- Do not treat all namespace Warning events as evidence; filter to workload, owned ReplicaSet, or selected Pod evidence.
- Do not fabricate diagnosis results without command evidence.
- Do not print AK/SK, tokens, kubeconfig certificates, or Authorization headers.
- Do not commit kubeconfig files or verification logs containing sensitive data.

## Handoff

| Diagnosis Direction | Target Skill | Reason |
| --- | --- | --- |
| Workload resource changes | `huawei-cloud-cce-auto-remediation-runner` | Scale, patch, rollback, recreate, delete, or restart actions |
| Node pressure or scheduling failures | `huawei-cloud-cce-node-failure-diagnoser` | NotReady, DiskPressure, MemoryPressure, taints, or scheduling |
| Service, Ingress, ELB, or dependency reachability | `huawei-cloud-cce-network-failure-diagnoser` | Service endpoints missing, readiness path fails, ingress/service mismatch |
| Storage mount or PVC/PV issues | `huawei-cloud-cce-storage-failure-diagnoser` | FailedMount, FailedAttachVolume, PVC Pending |
| Multi-domain uncertainty | `huawei-cloud-cce-root-cause-analyzer` | Cross-domain evidence convergence |
| Pod-level failures | `huawei-cloud-cce-pod-failure-diagnoser` | CrashLoop, ImagePull, OOM, Pending, probe, or log drilldown |
| Alarm correlation evidence | `huawei-cloud-cce-alarm-correlation-engine` | AOM alarm deduplication and severity grouping |

## Kubeconfig Handling

- Use a short duration, normally `--duration=1`.
- Store kubeconfig outside the repository or in an ignored temporary path.
- Restrict permissions where supported by the OS.
- Delete temporary kubeconfig files after verification unless the user asks to keep them.
- Never include kubeconfig content in the report.
