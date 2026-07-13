# Output Schema

The final report may be Markdown, but it should map cleanly to this JSON shape. Include command evidence without secrets.

```json
{
  "success": true,
  "action": "node_failure_diagnose_cli",
  "execution_model": "hcloud CCE + kubectl",
  "target": {
    "region": "cn-north-4",
    "project_id": "optional",
    "cluster_id": "cluster uuid",
    "cluster_name": "optional",
    "node_name": "192.168.0.10",
    "node_ip": "192.168.0.10"
  },
  "cli_path": {
    "hcloud_commands": [
      "hcloud CCE ShowCluster ...",
      "hcloud CCE ListNodes ...",
      "hcloud CCE CreateKubernetesClusterCert ..."
    ],
    "kubectl_commands": [
      "kubectl --kubeconfig=<file> describe node ...",
      "kubectl --kubeconfig=<file> get lease ...",
      "kubectl --kubeconfig=<file> get pods -A --field-selector spec.nodeName=..."
    ],
    "mutating_commands_run": false
  },
  "summary": {
    "diagnosis_status": "abnormal | healthy | partial_evidence",
    "confidence": 0.9,
    "root_category": "ControlPlaneDisconnected | NodeNotReady | MemoryPressure | DiskPressure | PIDPressure | NetworkUnavailableOrCNI | KubeletOrRuntimeProblem | SchedulingDisabledOrTainted | HealthyOrNoNodeFault",
    "affected_pod_count": 5
  },
  "node": {
    "name": "192.168.0.10",
    "internal_ip": "192.168.0.10",
    "ready": "True | False | Unknown",
    "unschedulable": false,
    "taints": [],
    "conditions": [
      {
        "type": "Ready",
        "status": "True",
        "reason": "KubeletReady",
        "message": "kubelet is posting ready status",
        "last_transition_time": "2026-07-06T10:00:00Z"
      }
    ],
    "lease": {
      "available": true,
      "renew_time": "2026-07-06T10:00:00Z",
      "stale": false,
      "delay_seconds": 10
    }
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "NodeNotReady",
      "title": "Node is not ready",
      "confidence": 0.9,
      "interpretation": "Plain-language explanation of the evidence.",
      "evidence": [],
      "ruled_out": [],
      "follow_up_checks": [],
      "candidate_fix": [],
      "handoff": "huawei-cloud-cce-auto-remediation-runner"
    }
  ],
  "workload_impact": {
    "pods_on_node": 12,
    "symptomatic_pods": [],
    "evicted_pods": [],
    "not_ready_pods": []
  },
  "metrics": {
    "available": true,
    "source": "kubectl top",
    "notes": []
  },
  "verification_gaps": [],
  "recommended_actions": []
}
```

## Markdown Report Sections

Use these sections in the human-readable report, with action-driving sections first:

1. Executive summary: node status, confidence, root category, and one-line conclusion.
2. Root-cause analysis: top causes, evidence, and interpretation.
3. Recommended next steps and handoff recommendation.
4. Target and scope.
5. Node lifecycle and liveness funnel.
6. Workload impact on the node.
7. Negative evidence and ruled-out causes.
8. Node conditions and kube-node-lease.
9. Metrics, Events, and verification gaps.
10. Detailed supporting evidence.
11. CLI path used.
12. Explicit statement that no mutating command was run.

## Recommendation Requirements

Each top cause should include:

- `interpretation`: what the node signal means.
- `evidence`: direct condition, Event, lease, pod, or metric evidence.
- `ruled_out`: adjacent causes that are less likely and why.
- `follow_up_checks`: specific checks and expected confirming/refuting signals.
- `candidate_fix`: safe remediation options without executing them.
- `handoff`: owner or skill for actions outside this read-only diagnoser.
