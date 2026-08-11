# Output Schema

```json
{
  "success": true,
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "time_range": "optional"
  },
  "summary": {
    "top_reason": "ImagePullBackOff",
    "total_events": 120,
    "warning_count": 42,
    "affected_objects": 8,
    "confidence": 0.78,
    "data_gaps": []
  },
  "top_reasons": [],
  "repeated_patterns": [],
  "namespace_breakdown": [],
  "affected_objects": [],
  "event_timeline": [],
  "next_steps": [],
  "report_markdown": "# CCE Kubernetes Event Analysis Report..."
}
```

Markdown section order:

1. `## Summary`
2. `## Event Patterns`
3. `## Next Actions`
4. `## Event Timeline`
5. `## Data Gaps`
6. `## Appendix`
