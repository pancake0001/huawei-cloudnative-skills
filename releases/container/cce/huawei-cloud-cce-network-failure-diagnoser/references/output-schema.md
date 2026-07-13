# Output Schema

The final report may be Markdown, but it should map cleanly to this JSON shape. Include command evidence without secrets.

```json
{
  "success": true,
  "action": "network_failure_diagnose_cli",
  "execution_model": "hcloud CCE + kubectl + optional hcloud ELB/VPC/EIP/NAT",
  "target": {
    "region": "cn-north-4",
    "project_id": "optional",
    "cluster_id": "cluster uuid",
    "cluster_name": "optional",
    "namespace": "default",
    "failure_symptom": "service_unreachable",
    "service_name": "api",
    "ingress_name": "optional",
    "source": "optional",
    "destination": "optional",
    "domain": "optional",
    "elb_id": "optional"
  },
  "cli_path": {
    "hcloud_cce_commands": [],
    "kubectl_commands": [],
    "hcloud_network_commands": [],
    "mutating_commands_run": false,
    "active_tests_run": false
  },
  "summary": {
    "diagnosis_status": "abnormal | no_known_failure_detected | partial_evidence",
    "confidence": 0.88,
    "root_category": "ServiceNoReadyEndpoint",
    "pipeline_pruned": false
  },
  "path_funnel": [
    {
      "stage": "Service",
      "status": "checked | abnormal | skipped | pruned",
      "finding": "EndpointSlice has no ready addresses"
    }
  ],
  "object_snapshot": {
    "nodes": [],
    "services": [],
    "endpoints": [],
    "endpoint_slices": [],
    "ingresses": [],
    "network_policies": [],
    "dns": [],
    "cloud": {
      "elb": [],
      "vpc": [],
      "eip": [],
      "nat": []
    }
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "ServiceNoReadyEndpoint",
      "title": "Service has no ready backend endpoint",
      "confidence": 0.92,
      "interpretation": "Plain-language explanation of the evidence.",
      "evidence": [],
      "ruled_out": [],
      "follow_up_checks": [],
      "candidate_fix": [],
      "handoff": "huawei-cloud-cce-pod-failure-diagnoser"
    }
  ],
  "verification_gaps": [],
  "recommended_actions": []
}
```

## Markdown Report Sections

Use these sections in the human-readable report, with action-driving sections first:

1. Executive summary: symptom status, confidence, root category, and one-line conclusion.
2. Root-cause analysis: top causes, evidence, and interpretation.
3. Recommended next steps and handoff recommendation.
4. Target and symptom.
5. Network path funnel.
6. Negative evidence and ruled-out layers.
7. Key object snapshot.
8. Verification gaps.
9. Evidence matrix and detailed supporting evidence.
10. CLI path used.
11. Explicit statement that no mutating command was run.

## Recommendation Requirements

Each top cause should include:

- `interpretation`: what the failing network layer means.
- `evidence`: direct K8s or hcloud network evidence.
- `ruled_out`: adjacent layers that were checked and are less likely.
- `follow_up_checks`: concrete checks with expected confirming/refuting signals.
- `candidate_fix`: safe remediation options without executing them.
- `handoff`: relevant skill or owner for actions outside this read-only diagnoser.
