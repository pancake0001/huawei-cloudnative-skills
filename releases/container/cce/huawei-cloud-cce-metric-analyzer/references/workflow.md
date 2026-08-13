# Workflow

## Collection Lanes

1. Resolve context with `hcloud CCE ListClusters`, `ShowCluster`, and `ListNodes`.
2. Set the incident window from user input, Events, alarms, or change time. Keep the first pass small, usually 1 hour.
3. Choose one or more lanes:
   - Pod/workload: Pod TopN, target Pod time series, HPA/autoscaler, Events.
   - Node: Node TopN, target Node time series, disk/memory pressure, node Events.
   - DNS: CoreDNS QPS, NXDOMAIN, error rate, P95 latency, replicas, Pod CPU/memory.
   - Ingress: nginx-ingress QPS, 4xx/5xx, success rate, P95 latency, active connections, TLS certificate status.
   - External access: ELB, EIP, and NAT CES metrics plus Service/Ingress association through `kubectl cce`.
   - Control plane: apiserver, etcd, controller-manager, scheduler time series when AOM collection is enabled.
4. Use `kubectl cce` only for Kubernetes resource relationships and live Metrics API checks.
5. Correlate metric anomalies with Events, alarms, rollouts, and user symptom timestamps.
6. Put summary, root-cause signal, and next actions before raw evidence.

## Pod Metrics

For high Pod usage or suspected resource pressure:

1. Get Pod list and labels with `kubectl cce ... get pods -n <namespace> -o wide` or `-o json`.
2. Query AOM Pod CPU, memory, and disk time series scoped by `cluster`, `namespace`, and Pod name or selector.
3. Compare top consumers against affected workloads.
4. Check Events for OOMKilled, Evicted, BackOff, FailedScheduling, and readiness/liveness failures.
5. Hand off to the Pod or workload diagnoser when the anomaly maps to a concrete Pod or rollout.

## Node Metrics

For node pressure or noisy-neighbor suspicion:

1. Get node inventory with `hcloud CCE ListNodes` and `kubectl cce ... get nodes -o wide`.
2. Query AOM/CES node CPU, memory, disk, filesystem, and network series.
3. Compare affected Pods on the node against node-level spikes.
4. Check node Conditions, taints, and Events.
5. Hand off to the node diagnoser for node NotReady, pressure, runtime, or disk issues.

## Component Metrics

For DNS, Ingress, autoscaling, or control-plane symptoms:

1. Confirm component Pods and namespaces with `kubectl cce ... get pods -A`.
2. Query the matching AOM metric family.
3. Verify whether required PodMonitor or ServiceMonitor collection is enabled.
4. Record empty series as data gaps unless Events or logs prove the component is healthy.

## Cloud Resource Metrics

For external access or egress symptoms:

1. Map Kubernetes Services/Ingresses to ELB/EIP/NAT where possible.
2. Query CES with `hcloud CES ShowMetricData` for the matched resource IDs.
3. Compare QPS, latency, bandwidth, packet loss, and connection utilization with the incident window.
4. Do not claim traffic impact from topology alone; require CES, alarms, logs, or user symptoms.

## Thresholds

| Resource | Critical | Warning |
| -------- | -------- | ------- |
| CPU | >80% sustained or sharp incident-time spike | >50% sustained |
| Memory | >85% or OOM-adjacent trend | >50% sustained |
| Disk | >85% | >70% |
| EIP/NAT | saturation, packet loss, or connection drops matching symptoms | elevated sustained utilization |
| ELB | latency/error/QPS change matching symptoms | clear degradation versus baseline |

Thresholds are leads, not final root causes. Always correlate with at least one other evidence type before giving high confidence.
