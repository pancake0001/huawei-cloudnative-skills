# Output Schema

## Optional Scope Hint Input

When available, pass `abnormal_object_analysis` from `huawei-cloud-cce-daily-cluster-inspector` as an RCA scope hint:

```json
{
  "abnormal_object_analysis": {
    "abnormal_objects": [
      {
        "kind": "Pod | Node | Deployment | Service | Ingress | Cluster",
        "namespace": "optional",
        "name": "object-name",
        "symptoms": [],
        "first_seen": "optional",
        "last_seen": "optional",
        "relationships": {}
      }
    ],
    "timeline": {},
    "relationship_summary": {},
    "data_gaps": []
  }
}
```

RCA may use these objects to choose target namespace, workload, node, related resources, and query time window. RCA must not rank root causes directly from this payload; it must collect its own Events, metrics, topology, change, alarm, and domain diagnosis evidence.

```json
{
  "success": true,
  "analysis_trace_id": "RCA-...",
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "target_name": "optional workload/app/service"
  },
  "summary": {
    "top_cause": {},
    "cause_count": 3,
    "remediation_candidate_count": 2,
    "supporting_finding_count": 2,
    "scope_hint_input": "abnormal_object_analysis | null",
    "root_cause_evidence_policy": "Root cause is ranked from RCA-collected evidence and domain analyzers, not from inspector output alone.",
    "data_sources": {
      "scope_hints": true,
      "runtime_evidence": true,
      "rollout": true,
      "dependency": true,
      "change": true,
      "alarms": true
    }
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "ContainerCommandNotFound | DnsPerformanceBottleneck",
      "title": "New version container startup command or entry file does not exist",
      "domain": "workload | dns",
      "confidence": 0.94,
      "evidence": [],
      "counter_evidence": [],
      "recommendation": [],
      "remediation_hint": {
        "skill": "huawei-cloud-cce-auto-remediation-runner",
        "action": "huawei_auto_remediation_run",
        "strategy": "rollback_previous_revision",
        "requires_confirmation": true
      }
    }
  ],
  "supporting_findings": [
    {
      "type": "DependencyImpactScope | AlarmEvidence",
      "title": "Impact scope or evidence correlation, not a ranked root cause",
      "domain": "dependency | alarm",
      "confidence": 0.5,
      "evidence": [],
      "counter_evidence": [],
      "recommendation": []
    }
  ],
  "remediation_candidates": [
    {
      "skill": "huawei-cloud-cce-auto-remediation-runner",
      "strategy": "rollback_previous_revision | scale_workload_out | scale_coredns_out | configure_hpa | resize_workload | fix_image_or_pull_secret_preview | cordon_node | drain_node_after_cordon | node_cordon_drain_or_scale_nodepool_preview | resize_peripheral_resource_preview",
      "action": "huawei_rollback_cce_workload | huawei_scale_cce_workload | huawei_configure_cce_hpa | huawei_resize_cce_workload | huawei_cce_node_cordon | huawei_cce_node_drain | manual_review_image_pull_secret | manual_select_node_or_nodepool_action | manual_resize_peripheral_resource",
      "risk_level": "R0 | R1 | R2 | R3",
      "target": {
        "region": "cn-north-4",
        "cluster_id": "cluster-id",
        "namespace": "optional",
        "workload_type": "deployment",
        "name": "optional",
        "node_name": "optional",
        "nodepool_id": "optional"
      },
      "params": {},
      "reason": "why this recovery candidate is suitable",
      "verification": [],
      "requires_confirmation": true
    }
  ],
  "remediation_handoff": {
    "skill": "huawei-cloud-cce-auto-remediation-runner",
    "input_field": "remediation_candidates",
    "mode": "advice | preview | authorized_execution"
  },
  "report_markdown": "# CCE Comprehensive Root Cause Analysis Report...",
  "report_file": "optional"
}
```
