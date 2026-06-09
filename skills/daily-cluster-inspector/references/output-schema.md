# Output Schema

```json
{
  "summary": "daily inspection summary",
  "status": "HEALTHY | WARNING | CRITICAL",
  "cluster": {
    "region": "cn-north-4",
    "cluster_id": "optional"
  },
  "checks": [],
  "risks": [
    {
      "priority": "P0 | P1 | P2 | P3 | P4 | P5, assigned by AI from inspection evidence",
      "category": "Pod | Node | Event | AOM | ELB | Resource | Other",
      "title": "risk title",
      "impact": "affected scope",
      "evidence": "facts from tool output",
      "suggestion": "next step",
      "root_cause_handoff": {
        "skill": "root-cause-analyzer",
        "required": true,
        "time_window": "optional",
        "target_objects": [],
        "symptoms": [],
        "evidence": [],
        "data_gaps": []
      }
    }
  ],
  "recommended_followups": [],
  "report_file": "optional"
}
```
