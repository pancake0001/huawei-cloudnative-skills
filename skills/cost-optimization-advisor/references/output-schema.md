# Output Schema

```json
{
  "summary": "cost optimization summary",
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "optional",
    "excluded_namespaces": ["kube-system"],
    "windows": ["24h", "7d"]
  },
  "cluster_utilization": {
    "24h": {
      "cpu_avg_percent": 0,
      "memory_avg_percent": 0,
      "overall_low_utilization": false
    },
    "7d": {
      "cpu_avg_percent": 0,
      "memory_avg_percent": 0,
      "overall_low_utilization": false
    }
  },
  "low_utilization_nodes": [
    {
      "node": "node-name-or-ip",
      "window": "24h | 7d | both",
      "cpu_avg_percent": 0,
      "memory_avg_percent": 0,
      "reason": "below cluster average"
    }
  ],
  "oversized_requests": [
    {
      "namespace": "business",
      "workload": "deployment/name",
      "resource": "cpu | memory",
      "request": "optional",
      "actual_p95": "optional",
      "ratio": 0,
      "priority": "observe | optimize | high"
    }
  ],
  "elasticity": {
    "hpa": {
      "status": "not_configured | configured | unknown",
      "recommendations": [],
      "existing_hpas": [],
      "example_yaml": [],
      "preview_action": "huawei_configure_cce_hpa without confirm=true"
    },
    "node_autoscaler": {
      "status": "not_configured | configured | unknown",
      "recommendations": []
    }
  },
  "execution_plan": [],
  "risks": [],
  "data_gaps": [],
  "files": {
    "summary": "optional cost-optimization-summary.json path",
    "report": "optional cost-optimization-report.md path"
  }
}
```
