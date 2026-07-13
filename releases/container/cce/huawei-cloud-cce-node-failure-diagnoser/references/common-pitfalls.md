# Common Pitfalls And Solutions

## Pitfall 1: Treating Ready=Unknown As A Definite Kubelet Failure

`Ready=Unknown` plus stale kube-node-lease means the control plane has lost heartbeat visibility. It may be kubelet, node network, runtime, host, or maintenance. State the broader conclusion first, then list node-side checks.

## Pitfall 2: Marking Unknown Pressure Conditions As Normal

When the node is unreachable, pressure conditions may also be `Unknown`. Do not mark MemoryPressure or DiskPressure as healthy unless you have independent fresh evidence.

## Pitfall 3: Ignoring The Lease

Always inspect `kube-node-lease/<node-name>` for NotReady or Unknown nodes:

```bash
kubectl --kubeconfig=<kubeconfig-file> get lease <node-name> -n kube-node-lease -o yaml
```

Lease freshness is a strong liveness signal.

## Pitfall 4: Diagnosing Node Fault From One Pod

One Pod failing on a healthy node is often a Pod/workload/storage issue. Check whether symptoms are concentrated across many Pods on the node before calling it a node fault.

## Pitfall 5: Missing Node-Local CNI Patterns

`FailedCreatePodSandBox`, IP allocation errors, and CNI plugin errors concentrated on one node can indicate node-local network failure even when the node is Ready.

## Pitfall 6: Overusing Metrics

Metrics are supporting evidence, not mandatory truth. If `kubectl top` returns `Metrics API not available`, record the gap and rely on conditions, Events, and eviction messages.

## Pitfall 7: Running Remediation From The Diagnoser

This skill must not cordon, drain, taint, reboot, or delete anything. Recommend a safe action and hand it off.

## Quick Signal Table

| Signal | Likely Meaning | Recommended Action |
| --- | --- | --- |
| `Ready=Unknown` + stale lease | Control plane lost heartbeat | Check node reachability, kubelet, runtime, recent maintenance |
| `Ready=False` | Node reports unhealthy | Read Node Events and NPD/kubelet/CRI conditions |
| `MemoryPressure=True` | Memory pressure or eviction threshold | Check evicted Pods, QoS, memory requests/limits, metrics |
| `DiskPressure=True` | Disk or ephemeral-storage pressure | Check eviction messages, image/log disk usage, node disk condition |
| `PIDPressure=True` | PID exhaustion | Check workload process counts and node PID condition |
| `NetworkUnavailable=True` | Node network or CNI not ready | Hand off to network/node operations after Events review |
| Many Pods `ContainerStatusUnknown` | Node/runtime heartbeat disrupted | Correlate with Ready/lease/runtime conditions |
