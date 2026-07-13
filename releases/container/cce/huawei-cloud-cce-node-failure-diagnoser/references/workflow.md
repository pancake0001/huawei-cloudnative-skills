# Workflow

This workflow is read-only and uses only `hcloud CCE` plus `kubectl`.

## Evidence Order

1. Scope: confirm `region`, `project_id`, `cluster_id`, and one of `node_name` or `node_ip`.
2. CLI setup: verify hcloud, masked credentials, kubectl, cluster metadata, endpoint reachability, kubeconfig acquisition, and read RBAC.
3. Node inventory: list CCE nodes with hcloud when node ID metadata is useful; list Kubernetes nodes with kubectl for actual health state.
4. Node snapshot: inspect Ready condition, pressure conditions, NetworkUnavailable, taints, unschedulable state, labels, capacity, allocatable, and allocated resource summary.
5. Lease: inspect `kube-node-lease/<node-name>` and compare renew time with the current time. A stale lease plus Ready=Unknown is strong control-plane-to-node heartbeat evidence.
6. Events: collect Node-specific Events first, then cluster Events sorted by time. Preserve reason, message, count, source, and timestamp.
7. Workload impact: list all Pods on the node and classify Running, Pending, Failed, Evicted, Unknown, NotReady, and restart-heavy Pods.
8. Concentrated symptoms: look for node-local patterns such as `FailedCreatePodSandBox`, `ContainerStatusUnknown`, volume mount failures, CNI errors, image pull failures only on this node, or evictions.
9. Metrics: use `kubectl top node` and `kubectl top pods -A` when metrics-server is available. Record a verification gap when it is not.
10. Output: rank Top3 causes, cite evidence, describe impact, list safe next checks, and hand off any mutation.

## Baseline Commands

```bash
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ListNodes --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <kubeconfig-file>

kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> describe node <node-name>
kubectl --kubeconfig=<kubeconfig-file> get lease <node-name> -n kube-node-lease -o yaml
kubectl --kubeconfig=<kubeconfig-file> get events -A --field-selector involvedObject.kind=Node,involvedObject.name=<node-name> --sort-by=.lastTimestamp
kubectl --kubeconfig=<kubeconfig-file> get pods -A --field-selector spec.nodeName=<node-name> -o wide
kubectl --kubeconfig=<kubeconfig-file> top node <node-name>
```

## Failure Rules

### Control Plane Disconnected

- Signals: `Ready=Unknown`, reason `NodeStatusUnknown`, kube-node-lease renew time is stale, pressure conditions may also be `Unknown`.
- Interpretation: the control plane is no longer receiving node heartbeats. Do not label kubelet, network, or runtime as the single root cause unless Events or node-side evidence identify it.
- Next checks: node reachability from cluster network, kubelet status, container runtime status, CNI daemon state, and recent node maintenance or reboot events.

### Node NotReady

- Signals: `Ready=False`, kubelet reports node unhealthy, node problem detector Events, or repeated node condition transitions.
- Interpretation: the node is reachable enough to report state, but kubelet or node health is abnormal.
- Next checks: Node Events, kubelet/runtime/CNI conditions, pods on node, and whether symptoms affect multiple nodes.

### Resource Pressure

- Signals: `MemoryPressure=True`, `DiskPressure=True`, `PIDPressure=True`, evicted Pods, ephemeral-storage messages, or allocatable/request saturation.
- Interpretation: kubelet is protecting node stability or the node is near an operating limit.
- Next checks: node `describe` allocated resources, `kubectl top`, affected Pod QoS classes, eviction messages, image/container log disk usage, and recent workload changes.

### Network Or CNI Node Issue

- Signals: `NetworkUnavailable=True`, `CNIProblem`, `FailedCreatePodSandBox`, IP allocation errors, or CNI daemon issues concentrated on one node.
- Interpretation: Pods may schedule but cannot get a working sandbox or network.
- Next checks: CNI system Pods on the node, node conditions, Events mentioning IP allocation or plugin failure, and whether other nodes are healthy.

### Kubelet Or Runtime Problem

- Signals: `KUBELETProblem`, `CRIProblem`, frequent kubelet/containerd restarts, container status unknown, or kubelet not posting ready status.
- Interpretation: node agent or container runtime cannot manage Pods reliably.
- Next checks: node problem detector conditions, affected Pods, runtime restart Events, and handoff to node operations for host-side logs.

### Scheduling Disabled Or Tainted

- Signals: `SchedulingDisabled`, `spec.unschedulable=true`, taints without matching tolerations, or pods pending due to node selectors/taints.
- Interpretation: node may be intentionally excluded from scheduling or blocked by taints.
- Next checks: taints, tolerations, scheduler Events, node pool operation history, and maintenance window.

### Healthy Node Or Non-Node Root Cause

- Signals: Ready=True, lease fresh, no pressure or node problem conditions, other nodes show same app symptom.
- Interpretation: node is likely not the primary root cause; hand off to Pod, workload, storage, or network diagnoser based on failing workload evidence.

## Confidence Guidance

- High: direct Node condition/Event/lease evidence and matching workload impact.
- Medium: node symptoms are present but metrics or Events are incomplete.
- Low: RBAC or reachability gaps prevent key evidence collection.

## Handoff Guidance

- Auto-remediation runner: cordon/drain/reboot/scale only after user confirmation.
- Network failure diagnoser: CNI or node network evidence spans service connectivity.
- Pod failure diagnoser: one or a few Pods fail while the node is otherwise healthy.
- Storage failure diagnoser: node-local mount or volume attach errors dominate.
