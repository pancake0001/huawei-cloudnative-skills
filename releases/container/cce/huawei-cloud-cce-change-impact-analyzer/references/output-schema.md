# Output Schema

```json
{
  "success": true,
  "analysis_trace_id": "CHG-...",
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "target_name": "optional",
    "fault_time": "optional"
  },
  "summary": {
    "headline": "most likely change and confidence",
    "top_change": {},
    "confidence": 0.75,
    "evidence_sufficient": true,
    "data_gaps": []
  },
  "top_changes": [
    {
      "rank": 1,
      "category": "workload|config|network|security|infrastructure",
      "title": "change title",
      "time": "change time",
      "affected_objects": [],
      "risk_score": 82,
      "confidence": 0.78,
      "evidence": [],
      "counter_evidence": [],
      "data_gaps": [],
      "next_verification": []
    }
  ],
  "evidence_timeline": [],
  "blast_radius": [],
  "next_actions": [],
  "report_markdown": "# CCE Change Impact Report..."
}
```

Markdown section order:

1. `## Summary`
2. `## Change Impact Analysis`
3. `## Next Actions`
4. `## Evidence Timeline`
5. `## Blast Radius`
6. `## Data Gaps`
7. `## Appendix`
