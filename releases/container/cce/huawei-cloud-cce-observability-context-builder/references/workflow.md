# Workflow

## Collection Order

1. Record the user symptom, incident time, region, project ID, cluster, namespace, and target objects.
2. Resolve cluster context with `hcloud CCE ListClusters`, `ShowCluster`, and `ListNodes`.
3. Verify `kubectl cce` access and collect a broad current-state snapshot:
   - namespaces,
   - Pods,
   - workloads and ReplicaSets,
   - Services, Ingresses, Endpoints, and EndpointSlices,
   - Nodes,
   - PVCs, PVs, and StorageClasses,
   - Events sorted by timestamp.
4. Collect scoped evidence:
   - target Pod or workload describe output,
   - bounded current and previous Pod logs,
   - `top pods` and `top nodes` when Metrics API works.
5. Pull or request specialized read-only evidence:
   - alarms from `huawei-cloud-cce-alarm-correlation-engine`,
   - metrics from `huawei-cloud-cce-metric-analyzer`,
   - Event deep analysis from `huawei-cloud-cce-kubernetes-event-analyzer`,
   - logs from `huawei-cloud-cce-log-analyzer` or supported hcloud LTS read-only queries.
6. Normalize all evidence into a timeline with source, timestamp, object, severity, signal, and confidence.
7. Produce a context package and recommend the next diagnoser.

## Handoff Rules

| Dominant Signal | Handoff |
| --------------- | ------- |
| Image pull, restart, OOM, scheduling, probe, container logs | Pod or workload diagnoser |
| NodeNotReady, node pressure, taints, runtime/kubelet symptoms | Node diagnoser |
| Service, EndpointSlice, DNS, Ingress, ELB, EIP, NAT symptoms | Network diagnoser |
| PVC/PV/CSI attach or mount symptoms | Storage diagnoser |
| Multiple domains or conflicting signals | Root-cause analyzer |
| Mostly alarms | Alarm correlation engine |
| Mostly metrics | Metric analyzer |
| Mostly historical Events | Kubernetes event analyzer |
| Mostly log patterns | Log analyzer |

## Data Gap Handling

Record data gaps with:

- source,
- command category,
- object scope,
- sanitized error,
- impact on confidence,
- recommended next way to fill the gap.

Never fill gaps by inventing data or switching to SDK/kubeconfig paths.
