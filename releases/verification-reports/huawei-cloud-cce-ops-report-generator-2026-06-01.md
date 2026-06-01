# huawei-cloud-cce-ops-report-generator 验证报告

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Skill | `huawei-cloud-cce-ops-report-generator` |
| 验证工具 | `aicli v1.0.0-beta.2` |
| 验证环境 | CCE 集群 `aicli` 命名空间，Pod `aicli-dcfcf5595-4gf22` |
| 验证时间 | 2026-06-01 |
| 区域 | `cn-north-4` |
| 集群 ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| 操作性质 | 只读报告生成 |

## 验证结果

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 触发 | 通过 | aicli 正确加载并识别该 skill |
| weekly 报告生成 | 通过 | `report_type=weekly` 成功生成综合报告，recommendations=14 |
| 只读安全 | 通过 | 仅查询数据并生成报告，无变更操作 |
| 凭证安全 | 通过 | 未输出 AK/SK/Token |

## 关键发现

| 编号 | 类型 | 问题 | 处理 |
| --- | --- | --- | --- |
| - | 参数 | 首次使用 `report_type=daily`，返回 `invalid report_type` | 改用文档支持的 `report_type=weekly` 后通过。初始调用使用了未注册的 `daily` 类型 |

## 修复记录

| 编号 | 类型 | 问题 | 修复 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 参数兼容性 | CLI dispatcher 仅支持 `key=value` 格式 | 增强 `_parse_cli_params` 支持多种格式 |

## 最终结论

**通过**。报告生成功能正常，使用合法 report_type 后输出完整。


## aicli 实际输出（Skill 生成的报告）

No report field found. Keys: ['success', 'action', 'generated_at', 'scope', 'report', 'summary', 'recommendations', 'recommendation_rows', 'data_gaps', 'data_gap_rows', 'sources', 'files']
{
  "success": true,
  "action": "generate_ops_report",
  "generated_at": "2026-06-01T11:44:09+00:00",
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "1d450236-5b28-11f1-a7f6-0255ac10026a",
    "excluded_namespaces": [
      "kube-system"
    ],
    "business_namespaces": [],
    "gateway_keywords": [
      "nginx",
      "gateway",
      "ingress",
      "kong",
      "apisix",
      "traefik",
      "envoy"
    ]
  },
  "report": {
    "type": "weekly",
    "hours": 168,
    "short_hours": 24,
    "long_hours": 168
  },
  "summary": {
    "daily_cluster_inspector": {
      "status": "anomaly",
      "has_anomaly": true,
      "anomaly_count": 1,
      "anomalies": [
        {
          "type": "replica_mismatch",
          "deployments": [
            {
              "name": "cceaddon-virtual-kubelet-resource-syncer",
              "ready": null,
              "desired": 2
            },
            {
              "name": "cceaddon-virtual-kubelet-virtual-kubelet",
              "ready": 1,
              "desired": 2
            }
          ],
          "message": "2 个 Deployment 副本不匹配: cceaddon-virtual-kubelet-resource-syncer(None/2), cceaddon-virtual-kubelet-virtual-kubelet(1/2)"
        }
      ],
      "normal_details": [
        "AOM 告警正常：0 firing, 0 resolved，无资源类严重告警",
        "ELB 正常：3 个 ELB 最近 5分钟内无异常"
      ],
      "recovery_plan_count": 1,
      "message": "🚨 CCE集群异常 - 自动诊断完成\n\n📊 异常摘要\n  - 2 个 Deployment 副本不匹配: cceaddon-virtual-kubelet-resource-syncer(None/2), cceaddon-virtual-kubelet-virtual-kubelet(1/2)\n\n🔍 根因：2 个 Deployment 副本不匹配: cceaddon-virtual-kubelet-resource-syncer(None/2), cceaddon-virtual-kubelet-virtual-kubelet(1/2)\n  链路: Pod 副本数不足 → 可能是节点资源不够或调度失败\n\n📋 恢复方案（待确认）\n  1. 恢复操作后等待 2-5 分钟，验证指标是否恢复正常\n     效果: 确认恢复效果 | 风险: none\n\n⏱️ 快检 38.54s + 诊断 28.22s"
    },
    "capacity_trend_forecaster": {
      "cpu_avg_percent": 34.87,
      "memory_avg_percent": 33.56,
      "cpu_p95_percent": 79.88,
      "memory_p95_percent": 70.0,
   
