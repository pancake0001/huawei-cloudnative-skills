# Output Schema

```json
{
  "success": true,
  "analysis_trace_id": "RCA-...",
  "scope": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "namespace": "optional",
    "target_name": "optional"
  },
  "summary": {
    "headline": "一句话总结",
    "top_cause": {},
    "impact_scope": "namespace/service/workload/node/cluster",
    "confidence": 0.86,
    "data_gaps": []
  },
  "observability_context": {
    "source": "huawei-cloud-cce-observability-context-builder",
    "high_signal_findings": [],
    "timeline": [],
    "data_gaps": []
  },
  "top_causes": [],
  "evidence_timeline": [],
  "investigation_steps": [],
  "dependent_skill_findings": [],
  "report_markdown": "# CCE 综合根因分析报告...",
  "report_file": "optional"
}
```

Markdown 顺序：

1. `## 总结`
2. `## 根因分析`
3. `## 下一步措施`
4. `## 可观测上下文`
5. `## 证据时间线`
6. `## 影响面`
7. `## 排查步骤`
8. `## 数据缺口和置信度限制`
9. `## 附录`
