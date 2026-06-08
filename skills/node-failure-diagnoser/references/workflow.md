# Workflow

# # Reusability and gaps

- There are reusable tools: `huawei_get_kubernetes_nodes` checks Node Ready/stress conditions, `huawei_get_cce_events` checks Kubernetes Events, `huawei_get_cce_pods` checks Pod phase/reason/lastState, `huawei_get_cce_node_metrics` and `huawei_get_cce_pod_metrics_topN` Check AOM indicators, `huawei_node_diagnose`/`huawei_node_batch_diagnose` to check node monitoring, NPD and workload summary.
- The external huawei-cloud skill also emphasizes the CCE node, Pod, Event, monitoring, inspection, and diagnostic report tool families. You can directly use these read-only tools and the output habit of "list tasks first, and then output the complete report".
- Original gaps: lack of `kube-node-lease` renewal evidence, lack of Node condition full timestamp, lack of Pod symptom aggregation on the node, lack of deterministic actions to synthesize NotReady/stress/CNI/kubelet evidence into Markdown reports.
- The main tool has been supplemented: `huawei_node_failure_diagnose` outputs structured evidence and `report_markdown` at once.

# # Main process

1. Input must contain `region`, `cluster_id`, and `node_name` or `node_ip`.
2. Call `huawei_node_failure_diagnose`, default `lease_timeout_seconds=40`, `event_limit=500`, `hours=1`, `include_metrics=true`.
3. If the main tool returns `report_markdown`, use this Markdown directly as the final report body. Only add explanations that the user cares about, and do not discard the evidence table.
4. If the main tool fails, follow the manual process below.

# # 1. Control plane survival status offloading

Collection:

- `Ready`, `MemoryPressure`, `DiskPressure`, `PIDPressure`, `NetworkUnavailable` in `v1.Node.status.conditions`.
- `spec.renewTime` of `kube-node-lease/<node_name>`, calculates the difference between the current time and renewTime.

Judgment:

- Case A: `Ready=Unknown` and Lease renewal delay exceeds 40 seconds. The inference is that the control plane is disconnected from the node. If there is no stronger evidence such as `SystemOOM`, `EvictionThresholdMet`, `FailedCreatePodSandBox/CNI`, `ContainerRuntimeNotReady`, etc., the conclusion should be written as "the control plane lost contact with the node (the network link or Kubelet/CRI heartbeat is interrupted, node-side verification is required)", and do not bet on kubelet or the network prematurely.
- Case B: `Ready=False` and the Lease is renewed normally. The corollary is that the kubelet survives and proactively reports that the node or infrastructure is unhealthy.
- Case C: `Ready=True`. It is inferred that the basic communication is normal, and we continue to troubleshoot local resource pressure, CNI and workload symptoms.
- Case D: Other combinations. Marked as insufficient evidence, continue to converge using Event, Pod and node local logs.

# # 2. Node event timing traceback

Filter events with `involvedObject.kind=Node` and `involvedObject.name=<node_name>` and sort them in descending order of `lastTimestamp/eventTime/firstTimestamp`.

Strong signal:

- `SystemOOM`: Strong evidence of memory pressure.
- `EvictionThresholdMet` and message contains `imagefs`, `nodefs`, `DiskPressure`, `ephemeral-storage`: strong evidence of disk pressure.
- `KubeletSetupFailed`, `ContainerRuntimeNotReady`, `PLEG`, runtime not ready: strong evidence of kubelet/CRI anomaly.
- `NodeNotReady`: NotReady result evidence, you must continue to find the root cause.

# # 3. Drill down on load side symptoms

Query all Pods with `spec.nodeName=<node_name>` and aggregate `phase`, `reason`, `message`, container `state` and `lastState`.

Judgment:

- Disk Pressure: Multiple Pods with `phase=Failed`, `reason=Evicted`, message indicating `DiskPressure`, `nodefs`, `imagefs` or `ephemeral-storage`.
- Memory pressure: `lastState.terminated.reason=OOMKilled` of the business Pod, especially the exit code `137`; if there is `SystemOOM` at the same time, the confidence level is high.
- Network exception: The new Pod has a long-term `ContainerCreating`, the corresponding Pod Event has `FailedCreatePodSandBox`, and the message includes `CNI`, `network plugin returns error`, `timeout waiting for DHCP`, etc.
- kubelet/CRI exception: A large number of Pods become `Unknown`/`NodeLost`, or `kube-system` core DaemonSet (kube-proxy, CNI plug-in, CSI plug-in, etc.) is abnormal, restarts frequently, or is `Unhealthy`.

# # 4. Indicators and cloud-side certificate supplementation

- Use `huawei_get_cce_node_metrics` to verify CPU, memory, and disk trends, and do not directly regard single-point peaks as the root cause.
- Use `huawei_get_cce_pod_metrics_topN node_ip=<node_ip>` to check the high memory/high CPU Pods on the node.
- When NotReady or the network candidate is strong, additional security group, network ACL, and Master-Node communication link checks are added.
- When it comes to kernel vulnerabilities and problems that take effect after reboot, add the HSS host and vulnerability list, but do not perform repairs in this skill.

# # 5. Conclusion synthesis

Priority is not a fixed order, but strength of evidence:

1. Strong Event + Pod symptoms are consistent: high confidence and can fall directly into the memory, disk, network or kubelet/CRI categories.
2. `Ready=Unknown` + Lease timeout: The "node lost connection" itself is a high confidence level; for the underlying root cause, usually only medium and low confidence candidates can be given, unless there is independent strong evidence.
3. The pressure condition is `Unknown` and reason is `NodeStatusUnknown`: This only means that the kubelet will no longer report it, which is not equivalent to whether MemoryPressure/DiskPressure is normal or abnormal; the report should be marked as "undecidable" and indicate the lack of independent evidence.
4. Only NotReady or only indicator exceptions: medium to low confidence, local log verification is required.

The conclusion must include: root cause category, confidence level, key evidence, impact area, unconfirmed risks, and next step verification.