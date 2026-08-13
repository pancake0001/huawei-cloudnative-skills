# Output Schema

```json
{
  "success": true,
  "analysis_trace_id": "STO-...",
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "default",
    "pvc_name": "optional",
    "pod_name": "optional",
    "volume_id": "optional"
  },
  "summary": {
    "headline": "storage diagnosis summary",
    "top_cause": {},
    "affected_objects": [],
    "confidence": 0.82,
    "data_gaps": []
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "FailedMount|FailedAttach|PVCPending|CapacityExhaustion|NfsTimeout|ObsCredentialError",
      "title": "cause title",
      "stage": "provisioning|binding|attach|mount|runtime|network|teardown",
      "confidence": 0.82,
      "evidence": [],
      "counter_evidence": [],
      "data_gaps": [],
      "next_verification": [],
      "recommendation": []
    }
  ],
  "evidence": {
    "pvc": [],
    "pv": [],
    "storageclass": [],
    "volumeattachments": [],
    "pods": [],
    "nodes": [],
    "events": [],
    "csi_logs": [],
    "cloud_storage": []
  },
  "report_markdown": "# CCE Storage Failure Diagnosis Report..."
}
```

Markdown section order:

1. `## Summary`
2. `## Root Cause Analysis`
3. `## Next Actions`
4. `## Evidence`
5. `## Data Gaps`
6. `## Appendix`
