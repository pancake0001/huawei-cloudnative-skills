# Output Schema

The main tool `huawei_node_failure_diagnose` returns structured evidence and Markdown reports. Final user-facing output should preferably use `report_markdown`.

```json
{
  "success": true,
  "action": "huawei_node_failure_diagnose",
  "region": "cn-north-4",
  "cluster_id": "cluster-id",
  "node": {
    "name": "node-name",
    "internal_ip": "10.0.0.1",
    "ready": "True | False | Unknown",
    "conditions": [
      {
        "type": "Ready",
        "status": "Unknown",
        "reason": "NodeStatusUnknown",
        "message": "...",
        "last_heartbeat_time": "2026-05-30T10:00:00Z",
        "last_transition_time": "2026-05-30T10:01:00Z"
      }
    ]
  },
  "lease": {
    "found": true,
    "namespace": "kube-node-lease",
    "renew_time": "2026-05-30T10:00:00Z",
    "renew_delay_seconds": 72,
    "stale": true,
    "threshold_seconds": 40
  },
  "liveness": {
    "case": "A | B | C | D",
    "ready": "True | False | Unknown",
    "lease_stale": true,
    "conclusion": "Control surface and node lost contact",
    "inference": "Ready=Unknown and Lease renewal exceeds the threshold..."
  },
  "root_category": "ControlPlaneDisconnected | MemoryPressure | DiskPressure | Network | Kubelet | NotReady | Healthy",
  "conclusion": "The control plane loses contact with the node (network link or Kubelet/CRI heartbeat is interrupted, node-side verification is required)",
  "confidence": "High",
  "scores": {
    "ControlPlaneDisconnected": 8,
    "MemoryPressure": 11,
    "Kubelet": 4
  },
  "evidence": [
    {
      "category": "MemoryPressure",
      "severity": "critical",
      "signal": "SystemOOM",
      "source": "Event/kubelet",
      "detail": "System OOM encountered..."
    }
  ],
  "pod_summary": {
    "total": 24,
    "phase_counts": {
      "Running": 10,
      "Unknown": 14
    },
    "symptomatic": [],
    "observed": [
      {
        "namespace": "kube-system",
        "name": "node-local-dns-abc",
        "phase": "Running",
        "restart_total": 0,
        "core_daemon": true
      }
    ]
  },
  "health_items": [
    {
      "item": "Memory pressure",
      "status": "Undecidable",
      "detail": "MemoryPressure=Unknown; evidence_score=0"
    }
  ],
  "node_events": [],
  "pod_events": [],
  "metrics": {},
  "metric_error": null,
  "report_markdown": "# Kubernetes node automated diagnostic report\n..."
}
```

# # Markdown reports must contain

1. `# Kubernetes node automated diagnostic report`
2. `## 1. Diagnosis overview`: target node, diagnosis conclusion, confidence, explosion radius.
3. `## 2. Node status health`: NotReady, memory pressure, disk pressure, network status, Kubelet status, node scheduling taint; when the pressure condition changes to `Unknown` due to `NodeStatusUnknown` and there is no independent evidence, it is marked as "undecidable", do not write "normal".
4. `## 3. Key troubleshooting`: control plane survival status diversion, key event timing, node load abnormality observation, indicator snapshot, evidence matrix.
5. `## 4. Diagnostic conclusion`: deduce the evidence into a clear conclusion and point out the parts that still need to be confirmed by local logs.
6. `## 5. Operation and maintenance disposal suggestions`: only give suggestions and verification steps, and do not directly implement changes.