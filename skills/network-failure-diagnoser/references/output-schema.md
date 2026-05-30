# Output Schema

`huawei_network_failure_diagnose` 返回结构化 JSON，并在 `report_markdown` 中内嵌最终报告。

```json
{
  "success": true,
  "action": "huawei_network_failure_diagnose",
  "region": "cn-north-4",
  "cluster_id": "cluster-id",
  "namespace": "default",
  "conclusion": "high signal conclusion",
  "confidence": "高 (High)",
  "pipeline_pruned": false,
  "findings": [
    {
      "stage": "第三阶段：东西向路由与策略层诊断",
      "type": "NetworkPolicyBlocked",
      "title": "NetworkPolicy 选择了目标 Pod，但未放行源 Pod 标签或目标端口",
      "confidence": 1.0,
      "severity": "critical",
      "evidence": [],
      "recommendation": [],
      "prune": false
    }
  ],
  "top_causes": [],
  "snapshot": {
    "inputs": {},
    "nodes": [],
    "pods": [],
    "services": [],
    "ingresses": [],
    "endpoint_slices": [],
    "network_policies": [],
    "events": [],
    "logs": {},
    "cloud": {
      "elb_ids": [],
      "elbs": {},
      "eips": {},
      "nat": {},
      "security_groups": {},
      "vpc_acls": {}
    }
  },
  "report_markdown": "# CCE 网络故障自动化诊断报告\n..."
}
```

## Markdown Sections

`report_markdown` 必须包含以下标题：

- `# CCE 网络故障自动化诊断报告`
- `## 1. 诊断总览`
- `## 2. 排查过程`
- `## 3. 链路拓扑`
- `## 4. 关键对象快照`
- `## 5. 证据矩阵`
- `## 6. 诊断结论`
- `## 7. 建议动作与验证标准`

## Finding Types

常见 `type` 值：

- `NodeUnhealthy`
- `NodePressure`
- `PodDNSConfigMissing`
- `KubeDnsNoEndpoint`
- `CoreDNSRestarting`
- `CoreDNSNxDomain`
- `CoreDNSUpstreamTimeout`
- `NetworkPolicyBlocked`
- `ServiceNoReadyEndpoint`
- `ServiceSelectorMismatch`
- `ReadinessFlapping`
- `BackendOverloaded`
- `LoadBalancerProvisioningFailed`
- `ELBBackendUnhealthy`
- `IngressUpstreamError`
