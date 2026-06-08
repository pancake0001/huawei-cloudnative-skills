# Output Schema

`huawei_network_failure_diagnose` returns structured JSON with the final report embedded in `report_markdown`.

```json
{
  "success": true,
  "action": "huawei_network_failure_diagnose",
  "region": "cn-north-4",
  "cluster_id": "cluster-id",
  "namespace": "default",
  "conclusion": "high signal conclusion",
  "confidence": "High",
  "pipeline_pruned": false,
  "findings": [
    {
      "stage": "The third stage: east-west routing and policy layer diagnosis",
      "type": "NetworkPolicyBlocked",
      "title": "NetworkPolicy selected the target Pod but did not allow the source Pod label or target port",
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
  "report_markdown": "# CCE network fault automatic diagnosis report\n..."
}
```

# # Markdown Sections

`report_markdown` must contain the following headers:

- `# CCE network fault automated diagnosis report`
- `## 1. Diagnosis Overview`
- `## 2. Troubleshooting process`
- `## 3. Link topology`
- `## 4. Key object snapshot`
- `## 5. Evidence Matrix`
- `## 6. Diagnostic conclusion`
- `## 7. Recommended actions and verification standards`

# # Finding Types

Common `type` values:

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