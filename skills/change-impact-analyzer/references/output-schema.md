# Output Schema

`huawei_change_impact_analyze` 返回结构化 JSON，并始终包含 `report_markdown`。

```json
{
  "success": true,
  "analysis_trace_id": "CIA-yyyymmddHHMMSS-xxxxxxxx",
  "analysis_window": {
    "start_time": "YYYY-MM-DD HH:MM:SS",
    "end_time": "YYYY-MM-DD HH:MM:SS",
    "hours": 1
  },
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "target_name": "optional"
  },
  "summary": {
    "core_change_count": 3,
    "top_risk_count": 3,
    "data_sources": {
      "CCE 审计日志": "成功",
      "K8s 历史事件": "成功",
      "AOM 告警": "成功",
      "当前资源快照": "成功"
    }
  },
  "top_changes": [
    {
      "time": "YYYY-MM-DD HH:MM:SS",
      "verb": "patch",
      "resource": "configmaps",
      "namespace": "kube-system",
      "name": "coredns",
      "object_key": "kube-system/coredns",
      "category": "global_config_change",
      "title": "集群基础配置变更",
      "actor": "user or serviceAccount",
      "semantic_fields": ["data", "Corefile"],
      "blast_radius": "全集群",
      "impacted_entities": {
        "pods": [],
        "services": ["kube-system/kube-dns"],
        "ingresses": [],
        "nodes": ["node-a"]
      },
      "risk_score": 96,
      "risk_level": "Critical",
      "confidence": "high",
      "risk_reasons": [],
      "evidence": []
    }
  ],
  "changes": [],
  "report_markdown": "# CCE 变更影响分析报告\n...",
  "report_file": "/optional/path/report.md",
  "capture_metadata": {}
}
```

## Markdown 报告结构

客户交付报告必须包含以下章节：

1. `分析摘要`：Trace ID、集群、区域、范围、目标对象、窗口、核心变更数、初步结论。
2. `排查过程`：四阶段流水线说明。
3. `数据源与采集状态`：审计日志、K8s 事件、AOM 告警、资源快照的成功/失败状态。
4. `核心变更时间线`：按时间排列的关键变更表。
5. `最高风险预警`：Top N 变更、风险等级、评分、置信度、依据。
6. `爆炸半径与传播路径`：影响 Pod/Service/Ingress/Node 或全局路径。
7. `证据矩阵`：审计、事件、告警证据。
8. `结论与验证建议`：最终判断、只读验证建议、恢复动作交接说明。
9. `已复用能力`：列出本次复用的工具。
10. `能力缺口与补强建议`：说明数据不完整带来的边界。
