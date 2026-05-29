# Output Schema

```json
{
  "summary": "root cause summary",
  "incident": {
    "symptom": "optional",
    "impact": "optional",
    "time_window": "optional"
  },
  "evidence": {
    "alarms": [],
    "events": [],
    "workloads": [],
    "nodes": [],
    "network": []
  },
  "top_causes": [
    {
      "cause": "text",
      "confidence": "high | medium | low",
      "evidence": [],
      "counter_evidence": []
    }
  ],
  "recommended_actions": []
}
```

