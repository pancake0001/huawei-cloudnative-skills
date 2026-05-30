# Output Schema

主工具 `huawei_node_failure_diagnose` 返回结构化证据和 Markdown 报告。最终面向用户的输出应优先使用 `report_markdown`。

```json
{
  "success": true,
  "action": "huawei_node_failure_diagnose",
  "region": "cn-north-4",
  "cluster_id": "cluster-id",
  "node": {
    "name": "node-name",
    "internal_ip": "10.0.0.1",
    "ready": "True | False | Unknown",
    "conditions": [
      {
        "type": "Ready",
        "status": "Unknown",
        "reason": "NodeStatusUnknown",
        "message": "...",
        "last_heartbeat_time": "2026-05-30T10:00:00Z",
        "last_transition_time": "2026-05-30T10:01:00Z"
      }
    ]
  },
  "lease": {
    "found": true,
    "namespace": "kube-node-lease",
    "renew_time": "2026-05-30T10:00:00Z",
    "renew_delay_seconds": 72,
    "stale": true,
    "threshold_seconds": 40
  },
  "liveness": {
    "case": "A | B | C | D",
    "ready": "True | False | Unknown",
    "lease_stale": true,
    "conclusion": "控制面与节点失联",
    "inference": "Ready=Unknown 且 Lease 续约超过阈值..."
  },
  "root_category": "ControlPlaneDisconnected | MemoryPressure | DiskPressure | Network | Kubelet | NotReady | Healthy",
  "conclusion": "控制面与节点失联（网络链路或 Kubelet/CRI 心跳中断，需节点侧验证）",
  "confidence": "高 (High)",
  "scores": {
    "ControlPlaneDisconnected": 8,
    "MemoryPressure": 11,
    "Kubelet": 4
  },
  "evidence": [
    {
      "category": "MemoryPressure",
      "severity": "critical",
      "signal": "SystemOOM",
      "source": "Event/kubelet",
      "detail": "System OOM encountered..."
    }
  ],
  "pod_summary": {
    "total": 24,
    "phase_counts": {
      "Running": 10,
      "Unknown": 14
    },
    "symptomatic": [],
    "observed": [
      {
        "namespace": "kube-system",
        "name": "node-local-dns-abc",
        "phase": "Running",
        "restart_total": 0,
        "core_daemon": true
      }
    ]
  },
  "health_items": [
    {
      "item": "内存压力",
      "status": "不可判定",
      "detail": "MemoryPressure=Unknown; evidence_score=0"
    }
  ],
  "node_events": [],
  "pod_events": [],
  "metrics": {},
  "metric_error": null,
  "report_markdown": "# Kubernetes 节点自动化诊断报告\n..."
}
```

## Markdown 报告必须包含

1. `# Kubernetes 节点自动化诊断报告`
2. `## 1. 诊断总览`：目标节点、诊断结论、置信度、爆炸半径。
3. `## 2. 节点状态健康度`：NotReady、内存压力、磁盘压力、网络状态、Kubelet 状态、节点调度污点；当压力条件因 `NodeStatusUnknown` 变为 `Unknown` 且无独立证据时标为“不可判定”，不要写成“正常”。
4. `## 3. 关键排查`：控制面存活状态分流、关键事件时序、节点负载异常观测、指标快照、证据矩阵。
5. `## 4. 诊断结论`：把证据推导成明确结论，并指出仍需本地日志确认的部分。
6. `## 5. 运维处置建议`：只给建议和验证步骤，不直接执行变更。
