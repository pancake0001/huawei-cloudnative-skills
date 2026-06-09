# Inspection To Remediation Cases

Use these cases when a CCE inspection result needs to be converted into a preview-first recovery plan. The inspection phase remains read-only. Any action that changes workload, node, node pool, cluster, or traffic state must follow the risk rules and must not add `confirm=true` automatically.

## Case Selection Rules

- Prefer a low-impact recovery action before disruptive actions.
- Always include diagnosis evidence, target object, impact scope, rollback idea, and verification method.
- Use `huawei_auto_remediation_run` when the recovery can be expressed as a standard orchestration plan.
- Use specific CCE actions when the remediation target is clear, such as workload rollback, workload scale, node cordon, node uncordon, node drain, ECS reboot, or node pool resize.
- If the evidence is incomplete, output a remediation candidate list and request confirmation for the exact object and action.

## Case 1: Node NotReady Isolation And Replacement

Inspection evidence:

- Node remains `NotReady` beyond the configured tolerance window.
- Kubelet heartbeat is missing.
- Pods on the node are `Unknown`, stuck `Terminating`, or repeatedly rescheduled.

Preview remediation:

1. `huawei_cce_node_cordon` the affected node.
2. Diagnose kubelet, container runtime, network, and ECS status.
3. If the node recovers, `huawei_cce_node_uncordon`.
4. If the node does not recover, propose `huawei_cce_node_drain`, `huawei_reboot_ecs`, or `huawei_resize_cce_nodepool` to replace capacity.

Verification:

- `huawei_get_kubernetes_nodes`
- `huawei_node_diagnose`
- Workload available replicas after rescheduling

Risk:

- Cordon and uncordon are R1 when the target node is covered by explicit customer automatic-action authorization.
- Drain is R2.
- Reboot and destructive replacement are R3.

## Case 2: CoreDNS Degradation Recovery

Inspection evidence:

- CoreDNS Pod is `CrashLoopBackOff`, `Pending`, or unavailable.
- CoreDNS Deployment available replicas are below desired replicas.
- DNS resolution check fails for `kubernetes.default`.
- AOM alarms or events show DNS latency or query failure.

Preview remediation:

1. Diagnose CoreDNS Pods, ConfigMap, events, and scheduling conditions.
2. Restart unhealthy CoreDNS Pods by deleting only the failed replicas when the cause is transient.
3. Scale CoreDNS Deployment when replicas are insufficient for cluster size.
4. If a recent configuration change caused failure, propose rollback of the CoreDNS configuration or addon update plan.

Verification:

- CoreDNS Pod status
- CoreDNS Deployment available replicas
- In-cluster DNS query check
- Workload recovery for Pods that were blocked by DNS

Risk:

- Scaling or restarting Pods affects running state and must be previewed.
- Addon uninstall or disruptive addon change is high risk and must be confirmed explicitly.

## Case 3: Workload Replica Shortage Recovery

Inspection evidence:

- Deployment or StatefulSet available replicas are lower than desired replicas.
- Pods are `Pending`, `CrashLoopBackOff`, `ImagePullBackOff`, or blocked by failed probes.
- Events identify scheduling, image, probe, quota, or storage causes.

Preview remediation:

1. Diagnose the failed Pods and recent rollout state.
2. If the new revision is unavailable because of image, command, probe, or startup failure, prefer `huawei_rollback_cce_workload`.
3. If the cause is insufficient capacity, propose `huawei_resize_cce_nodepool` or HPA limit adjustment.
4. If only a small number of Pods are stuck, propose deleting failed Pods to trigger recreation.

Verification:

- `huawei_workload_diagnose`
- `huawei_workload_rollout_diagnose`
- Available replicas and Pod events

Risk:

- Customer-authorized workload scale-out, node pool scale-out, cordon, and uncordon can be R1.
- HPA changes can be R1 only when the current Pod count is known, `minReplicas >= currentPodCount`, and `maxReplicas > currentPodCount`.
- Workload resize, rollback, scale-in, node pool resize with unknown direction, and HPA changes outside the R1 condition are R2.
- Workload deletion is R3.

## Case 4: ImagePullBackOff Secret Refresh

Inspection evidence:

- Pods are `ImagePullBackOff` or `ErrImagePull`.
- Events mention authentication failure, missing secret, repository not found, or network timeout.
- Related imagePullSecret is missing, expired, or not attached to the ServiceAccount.

Preview remediation:

1. Verify image name, tag, namespace, and imagePullSecret reference.
2. Refresh or recreate the imagePullSecret if the credentials are known and approved.
3. Patch the target workload or ServiceAccount when the secret reference is missing.
4. Delete failed Pods to trigger a new image pull.

Verification:

- Pod status changes from `ImagePullBackOff` to `Running`.
- Events show successful image pull.
- Workload available replicas recover.

Risk:

- Secret refresh and workload patch are state-changing and require preview.
- Do not create credentials from guessed values.

## Case 5: PVC Capacity Exhaustion Expansion

Inspection evidence:

- PVC usage exceeds threshold.
- Pod logs or events show `no space left on device`.
- Inode usage is close to exhaustion.
- StorageClass supports volume expansion.

Preview remediation:

1. Confirm StorageClass expansion support and target PVC.
2. Patch PVC requested storage to the approved size.
3. Wait for volume and filesystem expansion.
4. If expansion is unsupported, propose cleanup, workload migration, or storage replacement.

Verification:

- PVC capacity and conditions
- Pod filesystem usage
- Application health or readiness

Risk:

- PVC resize is state-changing and must be previewed.
- Avoid automatic expansion when the namespace has quota or cost constraints.

## Case 6: ELB Or Ingress Backend Recovery

Inspection evidence:

- ELB backend health check fails.
- Service Endpoints or EndpointSlices are empty.
- Backend Pods are not Ready.
- Ingress routes to a Service with no healthy backends.

Preview remediation:

1. Diagnose Ingress, Service selector, Endpoints, Pods, and readiness probe.
2. If backend Pods are unhealthy, recover the workload using the workload replica shortage case.
3. If selector drift is detected after a change, propose Service selector correction or workload label rollback.
4. If the issue follows a rollout, propose workload rollback.

Verification:

- Service Endpoints are populated.
- ELB backend health returns to healthy.
- External request probe succeeds.

Risk:

- Selector changes, rollback, and Pod recreation are state-changing and must be previewed.

## Case 7: Namespace Quota Exhaustion Relief

Inspection evidence:

- Events show `exceeded quota`.
- ResourceQuota CPU, memory, Pod count, or PVC count is exhausted.
- New Pods are stuck `Pending` or workload rollout cannot create replicas.

Preview remediation:

1. Identify the quota dimension and top consumers.
2. Clean completed Jobs or failed Pods if they are safe to remove.
3. Propose quota adjustment only when the target namespace and new limits are explicit.
4. If quota cannot change, propose scaling down non-critical workloads or scheduling release.

Verification:

- ResourceQuota usage falls below hard limit.
- Pending Pods can be created.
- Target workload reaches desired replicas.

Risk:

- Quota changes and workload scale-down are state-changing and must be previewed.
- Deleting workloads or batch resources can be R3 depending on scope.
