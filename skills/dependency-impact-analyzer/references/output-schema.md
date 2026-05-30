# Output Schema

```json
{
  "success": true,
  "analysis_trace_id": "DIA-...",
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "cluster-id",
    "namespace": "default",
    "target_name": "api",
    "match_reason": "target_name=api"
  },
  "summary": {
    "risk_level": "High | Medium | Low | Unknown",
    "risk_score": 88,
    "risk_reason": "target pods unavailable and exposed by Service/Ingress",
    "pod_health": {
      "total": 2,
      "ready": 0,
      "unready": 2,
      "availability": "unavailable"
    },
    "service_count": 1,
    "ingress_count": 1,
    "path_count": 2
  },
  "target": {
    "pods": [],
    "services": [],
    "ingresses": []
  },
  "propagation_paths": [],
  "report_markdown": "# CCE 依赖影响面分析报告...",
  "report_file": "optional"
}
```
