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
        "requires_root_cause": true,
        "input_source": "root-cause-analyzer.remediation_candidates",
        "policy": "execute R3 read-only candidates directly; execute R2 low-risk candidates only with customer authorization; advise only for R1/R0 candidates",
        "do_not_call": "huawei-cloud-cce-auto-remediation-runner"
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
      "type": "aom_alarm | k8s_event_anomaly | pod_metric_topn_anomaly | node_metric_topn_anomaly | coredns_metric_anomaly",
      "message": "short symptom summary"
    }
  ],
  "normal_details": [],
  "metrics": {
    "alarms": {},
    "events": {},
    "pod_metrics_topn": {},
    "node_metrics_topn": {},
    "coredns": {
      "metrics": {
        "cpu_usage_percent": {},
        "success_rate_percent": {},
        "p99_latency_ms": {}
      },
      "anomalies": [],
      "data_gaps": []
    }
  }
}
```

Quick check must not include ELB/EIP/NAT diagnosis, application root cause, Deployment replica analysis, or remediation recommendations.

## Deep Diagnosis Response

`huawei_cce_deep_diagnosis` merges abnormal signals and collects read-only monitoring evidence for related resources. It does not conclude root cause or choose recovery strategy:

```json
{
  "success": true,
  "quick_check_anomalies": [],
  "diagnosis": {
    "mode": "abnormal_signal_merge_and_monitoring_inspection",
    "inspection_boundary": "merge abnormal signals and collect read-only monitoring evidence; no root cause conclusion",
    "alarms": {},
    "alarm_merge": {
      "merged_alarm_groups": [],
      "quick_alarm_names": []
    },
    "pod_metrics_topn": {},
    "node_metrics_topn": {},
    "coredns": {
      "metrics": {
        "cpu_usage_percent": {},
        "success_rate_percent": {},
        "p99_latency_ms": {}
      },
      "anomalies": [],
      "data_gaps": []
    },
    "monitoring_windows": {
      "abnormal_windows": [],
      "count": 0
    },
    "events": {},
    "abnormal_events": [],
    "event_merge": {
      "groups": [],
      "total_abnormal_events": 0
    },
    "pods": {},
    "deployments": {},
    "nodes": {},
    "services": {},
    "ingresses": {},
    "peripheral_monitoring": {
      "checked": true,
      "associated_elb_ids": [],
      "elb": {},
      "eip": {},
      "nat": {},
      "ecs": {
        "checked": true,
        "target_node_names": [],
        "target_node_ips": [],
        "matched_instances": [],
        "metrics": {},
        "data_gaps": []
      },
      "data_gaps": []
    },
    "abnormal_object_analysis": {
      "abnormal_objects": [
        {
          "key": "Pod:default:example-pod",
          "kind": "Pod | Node | Deployment | Service | Ingress | Cluster | Unknown",
          "namespace": "default",
          "name": "example-pod",
          "symptoms": [
            {
              "source": "aom_alarm | kubernetes_event | pod_metric_topn | node_metric_topn | quick_metric_topn",
              "symptom": "short abnormal expression",
              "first_seen": "optional first abnormal timestamp",
              "last_seen": "optional last abnormal timestamp",
              "detail": {}
            }
          ],
          "first_seen": "first abnormal timestamp for this object",
          "last_seen": "last abnormal timestamp for this object",
          "relationships": {
            "node": "optional node name",
            "workload": {},
            "services": [],
            "ingresses": [],
            "elb_ids": [],
            "eip_addresses": []
          }
        }
      ],
      "object_count": 0,
      "timeline": {
        "first_seen": "global first abnormal timestamp",
        "last_seen": "global last abnormal timestamp",
        "objects_with_time_window": 0
      },
      "relationship_summary": {
        "service_count": 0,
        "ingress_count": 0,
        "associated_elb_ids": [],
        "associated_ecs_ids": [],
        "peripheral_checked": true
      },
      "data_gaps": [],
      "note": "inspection evidence only; downstream root-cause-analyzer owns root cause conclusion"
    },
    "abnormal_object_discovery": {
      "mode": "discovery_only",
      "abnormal_objects": [],
      "abnormal_events": [],
      "object_count": 0,
      "event_count": 0
    }
  },
  "root_cause_handoff": {
    "skill": "huawei-cloud-cce-root-cause-analyzer",
    "required": true,
    "symptoms": [],
    "evidence": {
      "handoff_policy": "Only abnormal inspection findings are included. Healthy/normal check items are excluded.",
      "quick_check_anomalies": [],
      "abnormal_object_analysis": {},
      "alarm_merge": {},
      "event_merge": {},
      "monitoring_windows": {},
      "coredns": {},
      "peripheral_monitoring": {},
      "data_gaps": []
    },
    "analysis_focus": [],
    "data_gaps": []
  },
  "remediation_handoff": {
    "requires_root_cause": true,
    "input_source": "root-cause-analyzer.remediation_candidates",
    "policy": "execute R3 read-only candidates directly; execute R2 low-risk candidates only with customer authorization; advise only for R1/R0 candidates",
    "do_not_call": "huawei-cloud-cce-auto-remediation-runner"
  }
}
```
