# Output Schema

```json
{
  "success": true,
  "action": "pod_failure_diagnose",
  "summary": {
    "diagnosis_status": "abnormal | no_known_failure_detected | no_matching_abnormal_pods",
    "diagnosed_pods": 1,
    "total_pods_seen": 12,
    "status_counts": {
      "Running": 8,
      "Pending": 1
    },
    "issue_counts": {
      "CrashLoopBackOff": 1
    }
  },
  "target": {
    "namespace": "default",
    "workload_name": "optional",
    "pod_name": "optional",
    "labels": "optional",
    "include_logs": true,
    "include_metrics": false
  },
  "pods": [
    {
      "pod": {
        "name": "demo-xxx",
        "namespace": "default",
        "status": "Running",
        "reason": null,
        "node": "192.168.0.10",
        "qos_class": "Burstable"
      },
      "issues": [
        {
          "type": "CrashLoopBackOff | ImagePullBackOff | OOMKilled | PendingScheduling | PendingStorage | Evicted | FrequentRestart | PodNotReady",
          "title": "human-readable diagnosis",
          "confidence": 0.92,
          "container": "app",
          "evidence": [],
          "recommendation": []
        }
      ],
      "events": [],
      "containers": [],
      "logs": {
        "container": "app",
        "current": {
          "success": true,
          "excerpt": "sanitized tail logs"
        },
        "previous": {
          "success": true,
          "excerpt": "sanitized previous logs"
        }
      },
      "metrics": {
        "success": true
      }
    }
  ],
  "top_causes": [
    {
      "rank": 1,
      "type": "CrashLoopBackOff",
      "title": "容器反复启动失败并进入退避重试",
      "confidence": 0.92,
      "affected_count": 1,
      "affected_pods": ["default/demo-xxx"],
      "evidence": [],
      "recommendation": []
    }
  ],
  "recommended_actions": [
    {
      "action": "读取 previous 日志并结合退出码定位应用启动失败点。",
      "source_cause": "CrashLoopBackOff",
      "requires_confirmation": false
    }
  ],
  "warnings": [],
  "next_skill": "auto-remediation-runner | null"
}
```
