# Output Schema

```json
{
  "summary": "one paragraph context summary",
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "optional",
    "namespace": "optional",
    "workload": "optional",
    "time_window": "optional"
  },
  "signals": {
    "alarms": [],
    "events": [],
    "metrics": [],
    "logs": []
  },
  "timeline": [],
  "gaps": [],
  "next_skill": "pod-failure-diagnoser | node-failure-diagnoser | network-failure-diagnoser | root-cause-analyzer"
}
```

