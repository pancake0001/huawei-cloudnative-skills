# Output Schema

`huawei_change_impact_analyze` returns structured JSON and always includes `report_markdown`.

```json
{
  "success": true,
  "analysis_trace_id": "CIA-yyyymmddHHMMSS-xxxxxxxx",
  "analysis_window": {
    "start_time": "YYYY-MM-DD HH:MM:SS",
    "end_time": "YYYY-MM-DD HH:MM:SS",
    "hours": 1
  },
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "target_name": "optional"
  },
  "summary": {
    "core_change_count": 3,
    "top_risk_count": 3,
    "data_sources": {
      "CCE Audit Log": "Success",
      "K8s historical events": "Success",
      "AOM Alert": "Success",
      "Current resource snapshot": "Success"
    }
  },
  "top_changes": [
    {
      "time": "YYYY-MM-DD HH:MM:SS",
      "verb": "patch",
      "resource": "configmaps",
      "namespace": "kube-system",
      "name": "coredns",
      "object_key": "kube-system/coredns",
      "category": "global_config_change",
      "title": "Cluster basic configuration changes",
      "actor": "user or serviceAccount",
      "semantic_fields": ["data", "Corefile"],
      "blast_radius": "Full cluster",
      "impacted_entities": {
        "pods": [],
        "services": ["kube-system/kube-dns"],
        "ingresses": [],
        "nodes": ["node-a"]
      },
      "risk_score": 96,
      "risk_level": "Critical",
      "confidence": "high",
      "risk_reasons": [],
      "evidence": []
    }
  ],
  "changes": [],
  "report_markdown": "# CCE Change Impact Analysis Report\n...",
  "report_file": "/optional/path/report.md",
  "capture_metadata": {}
}
```

# # Markdown report structure

Customer delivery reports must contain the following sections:

1. `Analysis summary`: Trace ID, cluster, region, scope, target object, window, number of core changes, preliminary conclusion.
2. `Troubleshooting Process`: Description of the four-stage pipeline.
3. `Data source and collection status`: success/failure status of audit logs, K8s events, AOM alarms, and resource snapshots.
4. `Core Change Timeline`: A list of key changes arranged by time.
5. `Highest risk warning`: Top N changes, risk level, score, confidence, basis.
6. `Explosion radius and propagation path`: affects Pod/Service/Ingress/Node or global path.
7. `Evidence Matrix`: audit, event, and alarm evidence.
8. `Conclusion and verification suggestions': final judgment, read-only verification suggestions, recovery action handover instructions.
9. `Reused capabilities`: List the tools that have been reused this time.
10. `Capability Gaps and Strengthening Suggestions`: Explain the boundaries caused by incomplete data.