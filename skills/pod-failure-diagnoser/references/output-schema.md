# Output Schema

```json
{
  "summary": "pod diagnosis summary",
  "target": {
    "namespace": "default",
    "workload": "optional",
    "pod": "optional"
  },
  "pod_status": [],
  "events": [],
  "logs": {
    "current": [],
    "previous": []
  },
  "metrics": [],
  "top_causes": [],
  "recommended_actions": [],
  "needs_confirmation": false
}
```

