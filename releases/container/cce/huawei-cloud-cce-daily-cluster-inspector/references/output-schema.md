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
      "priority": "P0 | P1 | P2 | P3 | P4 | P5, assigned from inspection evidence",
      "category": "Pod | Node | Event | AOM | ELB | Resource | Other",
      "title": "risk title",
      "impact": "affected scope",
      "evidence": "facts from tool output",
      "suggestion": "next step",
      "root_cause_handoff": {
        "skill": "huawei-cloud-cce-root-cause-analyzer",
        "required": true,
        "time_window": "optional",
        "target_objects": [],
        "symptoms": [],
        "evidence": [],
        "data_gaps": []
      },
      "remediation_handoff": {
        "skill": "huawei-cloud-cce-auto-remediation-runner",
        "requires_root_cause": true,
        "mode": "advice | preview | authorized_execution",
        "authorization_required": true,
        "remediation_hints": []
      }
    }
  ],
  "recommended_followups": [],
  "report_file": "optional"
}
```

## Quick Check Response

`huawei_cce_quick_check` is an anomaly-existence gate. Expected scope:

```json
{
  "success": true,
  "has_anomaly": true,
  "anomaly_details": [
    {
      "type": "aom_alarm | k8s_event_anomaly | pod_metric_topn_anomaly | node_metric_topn_anomaly",
      "message": "short symptom summary"
    }
  ],
  "normal_details": [],
  "metrics": {
    "alarms": {},
    "events": {},
    "pod_metrics_topn": {},
    "node_metrics_topn": {}
  }
}
```

Quick check must not include ELB/EIP/NAT diagnosis, application root cause, Deployment replica analysis, or remediation recommendations.

## Deep Diagnosis Response

`huawei_cce_deep_diagnosis` collects root-cause evidence but does not decide final root cause:

```json
{
  "success": true,
  "quick_check_anomalies": [],
  "diagnosis": {
    "alarm_analysis": {},
    "alarm_correlation": {
      "merged_alarm_groups": []
    },
    "pod_metrics_topn": {},
    "node_metrics_topn": {},
    "monitoring_windows": {
      "abnormal_windows": []
    },
    "events": {},
    "event_analysis": {
      "groups": []
    },
    "application_evidence": {
      "affected_objects": [],
      "pod_state_summary": {},
      "deployment_replica_mismatches": []
    },
    "peripheral_resources": {
      "checked": true,
      "associated_elb_ids": [],
      "elb": {},
      "eip": {},
      "nat": {},
      "data_gaps": []
    }
  },
  "root_cause_handoff": {
    "skill": "huawei-cloud-cce-root-cause-analyzer",
    "required": true,
    "symptoms": [],
    "evidence": {},
    "analysis_focus": [],
    "data_gaps": []
  },
  "remediation_handoff": {
    "skill": "huawei-cloud-cce-auto-remediation-runner",
    "requires_root_cause": true,
    "mode": "advice | preview | authorized_execution"
  }
}
```
