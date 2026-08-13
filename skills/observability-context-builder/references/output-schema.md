# Output Schema

输出 Markdown 上下文包，关键信息放前面：

1. `## 总结`：范围、时间窗口、最强信号、置信度。
2. `## 范围`：region、project_id、cluster、namespace、目标对象和默认假设。
3. `## 高信号发现`：按价值排序的告警、事件、指标、日志、状态摘要。
4. `## 时间线`：用户现象、告警、Event、指标峰值、日志错误、发布/变更线索、恢复尝试。
5. `## 分来源证据`：Kubernetes 状态、Events、Logs、Alarms、Metrics、Cloud Metadata。
6. `## 数据缺口`：缺失来源、失败原因、对置信度影响、补齐方式。
7. `## 建议交接`：下一个 skill、原因和传入范围。
8. `## 使用命令`：脱敏后的 `hcloud` / `kubectl cce` 命令。

结构化上下文可按以下形状：

```json
{
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "targets": []
  },
  "time_window": {
    "start": "optional",
    "end": "optional",
    "assumption": "last 1 hour if unspecified"
  },
  "signals": {
    "kubernetes_state": [],
    "events": [],
    "logs": [],
    "alarms": [],
    "metrics": [],
    "cloud_metadata": []
  },
  "timeline": [],
  "data_gaps": [],
  "recommended_handoff": {
    "skill": "huawei-cloud-cce-root-cause-analyzer",
    "reason": "multiple domains need synthesis",
    "scope": {}
  }
}
```
