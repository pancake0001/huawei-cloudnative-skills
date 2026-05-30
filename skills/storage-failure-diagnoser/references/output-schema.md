# Output Schema

`huawei_storage_failure_diagnose` 返回结构化 JSON，并在 `report_markdown` 中内嵌最终客户报告。

```json
{
  "success": true,
  "action": "huawei_storage_failure_diagnose",
  "region": "cn-north-4",
  "cluster_id": "cluster-id",
  "namespace": "default",
  "conclusion": "high signal conclusion",
  "confidence": "高 (High)",
  "findings": [
    {
      "stage": "三、挂载期故障",
      "type": "EVSNodeAttachLimitExceeded",
      "title": "VolumeAttachment Attached=False，错误信息指向 ECS 单节点挂载云硬盘数量达到上限",
      "confidence": 0.94,
      "severity": "critical",
      "evidence": [],
      "recommendation": []
    }
  ],
  "top_causes": [],
  "snapshot": {
    "inputs": {},
    "pvcs": [],
    "pvs": [],
    "storage_classes": [],
    "pods": [],
    "nodes": [],
    "events": [],
    "volume_attachments": [],
    "network_policies": [],
    "node_stats": {},
    "pvc_volume_stats": [],
    "csi_logs": {},
    "cloud_storage": {}
  },
  "report_markdown": "# CCE 存储故障自动化诊断报告\n..."
}
```

## Markdown Sections

`report_markdown` 必须包含以下标题：

- `# CCE 存储故障自动化诊断报告`
- `## 1. 诊断总览`
- `## 2. 排查过程`
- `## 3. 关键对象关系`
- `## 4. 证据矩阵`
- `## 5. 诊断结论`
- `## 6. 建议动作与验证标准`
- `## 7. 数据缺口与人工确认`

## Finding Types

常见 `type` 值：

- `NormalWaitForFirstConsumer`
- `EVSQuotaExceeded`
- `SFSSubnetIPInsufficient`
- `OBSBucketNameInvalid`
- `EVSAvailabilityZoneSchedulingConflict`
- `LocalPVNodeOffline`
- `VolumeAttachmentNotCreated`
- `EVSNodeAttachLimitExceeded`
- `EVSResidualAttachmentLock`
- `EVSAttachFailed`
- `HostKernelMountFailed`
- `SFSNfsNetworkBlocked`
- `OBSCredentialInvalid`
- `StoragePermissionDenied`
- `PVCCapacityExhausted`
- `PVCInodeExhausted`
- `ReadOnlyFilesystemProtection`
- `ConfigMapSecretSubPathDeadlock`
- `PVCProtectionBlocked`
- `StorageIOError`
