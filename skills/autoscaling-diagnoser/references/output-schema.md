# Output Schema

The main tool `huawei_autoscaling_diagnose` returns structured evidence and Markdown reports. The final customer-facing output preferentially uses `report_markdown`.

```json
{
  "success": true,
  "action": "huawei_autoscaling_diagnose",
  "generated_at": "2026-05-30T00:00:00+00:00",
  "region": "cn-north-4",
  "cluster_id": "cluster-id",
  "intent": {
    "target": "WORKLOAD | NODE | UNKNOWN",
    "scale_direction": "scale_up | scale_down | unknown",
    "question": "Why can't it automatically expand?"
  },
  "scope": {
    "namespace": "default",
    "workload_name": "api",
    "workload_type": "Deployment"
  },
  "route": "A | B | C | BLOCKED",
  "discovery": {
    "has_hpa": true,
    "hpa_count": 1,
    "selected_hpa_count": 1,
    "has_ca": true,
    "ca_addon_installed": true,
    "nodepool_autoscaling_enabled": true,
    "nodepool_max_reached": [],
    "metric_addon_detected": true
  },
  "issues": [
    {
      "code": "HPA_CONTAINER_REQUEST_MISSING",
      "title": "The container sampled by HPA lacks resources request",
      "severity": "critical",
      "layer": "HPA",
      "evidence": "default/api-abc:app missing cpu",
      "recommendation": "Set resources.requests corresponding to HPA metrics for all target Pod containers."
    }
  ],
  "evidence": [
    {
      "layer": "CA-Log",
      "source": "Pod/cce-cluster-autoscaler-abc123 logs (tail=200)",
      "summary": "CA Pod=kube-system/cce-cluster-autoscaler-abc123, container=autoscaler, log_signals=3, snippet=\\\"NoExpansionOptions: ... subnet ip exhausted...\\\""
    },
    {
      "layer": "HPA",
      "source": "HorizontalPodAutoscaler/status",
      "summary": "default/api-hpa -> Deployment/api, min=2, max=10, current=2, desired=2"
    }
  ],
  "data_gaps": [],
  "conclusion": "The container sampled by HPA lacks resources request: default/api-abc:app missing cpu",
  "confidence": "High",
  "report_markdown": "# CCE Auto Scaling Automated Diagnosis Report\n..."
}
```

# # Markdown reports must contain

1. `# CCE Auto Scaling Automated Diagnosis Report`
2. `## 1. Diagnosis overview`: area, cluster, semantic intention, scaling direction, diagnosis path, conclusion, confidence level.
3. `## 2. Capability discovery and routing`: Has_HPA, Has_CA, indicator link and routing basis.
4. `## 3. Troubleshooting process`: Actual execution steps of Gateway and path A/B/C.
5. `## 4. Key evidence`: HPA status, node pool/plug-in, Pending Pod, FailedScheduling and other evidence.
6. `## 5. Problem and root cause convergence`: Arrange problems, evidence, and suggestions by severity level.
7. `## 6. Next step suggestions`: Read-only verification and rectification suggestions, do not directly implement changes.
8. `## 7. Data gap`: The part where the acquisition failed and the current atomic capability cannot be confirmed.

# # Severity level meaning

- `critical`: Blocking items that are sufficient to independently explain the non-scalability, such as no HPA, missing request, CA not installed, scaling of the node pool is not enabled, maxReplicas/max_nodes reaches the upper limit.
- `high`: Strong correlation blocking evidence, such as FailedScheduling insufficient resources, affinity/taint conflicts, cloud resource quotas or permission signals.
- `medium`: Suspicious items that need to be reviewed, such as the indicator plug-in is not recognized, the safe-to-evict key exists but the value is missing.
- `info`: The current behavior may not be triggered normally, such as the indicator does not exceed the threshold and there is no Pending Pod.