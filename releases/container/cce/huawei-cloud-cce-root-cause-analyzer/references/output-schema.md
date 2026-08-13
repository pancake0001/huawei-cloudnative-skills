# Output Schema

```json
{
  "success": true,
  "analysis_trace_id": "RCA-...",
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "target_name": "optional workload/app/service/pod/node"
  },
  "summary": {
    "headline": "one sentence summary",
    "top_cause": {},
    "impact_scope": "namespace/service/workload/node/cluster",
    "confidence": 0.86,
    "data_gaps": []
  },
  "observability_context": {
    "source": "huawei-cloud-cce-observability-context-builder",
    "high_signal_findings": [],
    "timeline": [],
    "data_gaps": []
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "ImagePullBackOff",
      "title": "image manifest cannot be pulled from the resolved registry",
      "domain": "pod",
      "confidence": 0.9,
      "impact_scope": [],
      "evidence": [],
      "counter_evidence": [],
      "data_gaps": [],
      "next_verification": [],
      "recommendation": [],
      "handoff": {
        "skill": "huawei-cloud-cce-auto-remediation-runner",
        "requires_confirmation": true
      }
    }
  ],
  "evidence_timeline": [],
  "investigation_steps": [],
  "dependent_skill_findings": [],
  "report_markdown": "# CCE Comprehensive Root Cause Analysis Report...",
  "report_file": "optional"
}
```

Markdown section order:

1. `## Summary`
2. `## Root Cause Analysis`
3. `## Next Actions`
4. `## Observability Context`
5. `## Evidence Timeline`
6. `## Impact Scope`
7. `## Investigation Steps`
8. `## Data Gaps And Confidence Limits`
9. `## Appendix`
