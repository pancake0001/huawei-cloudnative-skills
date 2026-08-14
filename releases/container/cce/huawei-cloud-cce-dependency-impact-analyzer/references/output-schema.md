# Output Schema

```json
{
  "success": true,
  "analysis_trace_id": "DEP-...",
  "execution_model": "hcloud CCE + kubectl-cce + delegated observability skills",
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "default",
    "target_name": "app-or-service",
    "label_selector": "app=demo"
  },
  "summary": {
    "headline": "impact summary",
    "risk_level": "High|Medium|Low|Unknown",
    "impact_status": "observed|possible|not_observed|unknown",
    "affected_entrypoints": [],
    "affected_backends": [],
    "confidence": 0.78,
    "data_gaps": []
  },
  "propagation_paths": [
    {
      "direction": "external|internal",
      "path": ["Ingress", "Service", "EndpointSlice", "Pod", "Node"],
      "impact": "what can fail or degrade",
      "evidence": []
    }
  ],
  "pod_health": {},
  "service_mapping": [],
  "ingress_mapping": [],
  "node_distribution": [],
  "next_actions": [],
  "commands": {
    "read_only_commands": [],
    "mutating_commands_run": false,
    "collection_errors": []
  },
  "report_markdown": "# CCE Dependency Impact Report..."
}
```

Markdown section order:

1. `## Summary`
2. `## Impact Paths`
3. `## Next Actions`
4. `## Evidence`
5. `## Confidence Limits`
6. `## Appendix`
