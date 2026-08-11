# Event Query Workflow

## Event Query Sequence

1. Identify `region`, `project_id`, `cluster_id`, and optional `namespace`.
2. Read `references/kubectl-cce.md`, then query current Events through `kubectl cce`.
3. Filter Warning Events first unless the user explicitly asks for all Events.
4. Apply follow-up filters:
   - reason patterns such as FailedScheduling, FailedMount, ImagePullBackOff;
   - involved object kind/name;
   - namespace;
   - incident time window.
5. Group by reason, type, namespace, and affected object.
6. Summarize top reasons, repeated patterns, affected resources, and likely diagnosis handoff.
7. For historical windows, discover Event-to-LTS LogConfig through `kubectl cce` and use hcloud LTS only when the log group/stream and time window are known.

## Event Pattern Recognition

| Pattern | Likely Cause | Handoff Target |
| --- | --- | --- |
| `ImagePullBackOff` / `ErrImagePull` | Wrong image, registry access, missing pull secret, or image tag not found | `huawei-cloud-cce-pod-failure-diagnoser` |
| `FailedScheduling` + `insufficient` | Resource pressure, constraints, taints, or node unavailability | `huawei-cloud-cce-workload-failure-diagnoser` / `huawei-cloud-cce-node-failure-diagnoser` |
| `FailedMount` / `FailedAttachVolume` | PVC/PV/CSI/EVS/SFS storage issue | `huawei-cloud-cce-storage-failure-diagnoser` |
| `Evicted` | Node pressure or kubelet eviction thresholds | `huawei-cloud-cce-pod-failure-diagnoser` / `huawei-cloud-cce-node-failure-diagnoser` |
| `NodeNotReady` | Node agent, runtime, network, or infrastructure issue | `huawei-cloud-cce-node-failure-diagnoser` |
| `Unhealthy` + readiness/liveness probe | Application startup, probe, or dependency issue | `huawei-cloud-cce-pod-failure-diagnoser` |
| `FailedCreatePodSandBox` | CNI, network plugin, IPAM, or sandbox issue | `huawei-cloud-cce-network-failure-diagnoser` |
| `OOMKilled` | Memory limit exceeded | `huawei-cloud-cce-pod-failure-diagnoser` |

## Time-Window Analysis

1. Compare firstTimestamp, lastTimestamp, eventTime, and count around the incident window.
2. Flag Events that started or peaked during the incident.
3. Separate symptoms that happen after a recovery action from initial trigger Events.
4. If current Events no longer cover the incident window, use LTS if configured; otherwise mark the retention gap.

## LTS Selection Guide

| Need | Current Events via `kubectl cce` | Historical Events via hcloud LTS |
| --- | --- | --- |
| Recent current state | Primary | Not needed |
| Precise historical time range | Limited by Event retention | Preferred if LogConfig exists |
| Keyword search over historical records | Client-side only | Preferred |
| No `default-event` LogConfig | Current only | Not available; record gap |
