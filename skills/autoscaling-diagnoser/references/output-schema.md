# Output Schema

主工具 `huawei_autoscaling_diagnose` 返回结构化证据和 Markdown 报告。最终面向客户的输出优先使用 `report_markdown`。

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
    "question": "为什么不能自动扩容了"
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
      "title": "被 HPA 采样的容器缺少资源 request",
      "severity": "critical",
      "layer": "HPA",
      "evidence": "default/api-abc:app missing cpu",
      "recommendation": "为所有目标 Pod 容器设置 HPA 指标对应的 resources.requests。"
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
  "conclusion": "被 HPA 采样的容器缺少资源 request：default/api-abc:app missing cpu",
  "confidence": "高 (High)",
  "report_markdown": "# CCE 弹性伸缩自动化诊断报告\n..."
}
```

## Markdown 报告必须包含

1. `# CCE 弹性伸缩自动化诊断报告`
2. `## 1. 诊断总览`：区域、集群、语义意图、伸缩方向、诊断路径、结论、置信度。
3. `## 2. 能力发现与路由`：Has_HPA、Has_CA、指标链路和路由依据。
4. `## 3. 排查过程`：Gateway、路径 A/B/C 的实际执行步骤。
5. `## 4. 关键证据`：HPA status、节点池/插件、Pending Pod、FailedScheduling 等证据。
6. `## 5. 问题与根因收敛`：按严重级别排列问题、证据、建议。
7. `## 6. 下一步建议`：只读验证和整改建议，不直接执行变更。
8. `## 7. 数据缺口`：采集失败、当前原子能力无法确认的部分。

## 严重级别含义

- `critical`：足以单独解释不扩缩容的阻断项，如无 HPA、缺 request、CA 未安装、节点池未开启伸缩、maxReplicas/max_nodes 达上限。
- `high`：强相关阻断证据，如 FailedScheduling 资源不足、亲和性/污点冲突、云资源配额或权限信号。
- `medium`：需要复核的可疑项，如指标插件未识别、safe-to-evict key 存在但缺少 value。
- `info`：当前行为可能是正常不触发，如指标未超过阈值、无 Pending Pod。
