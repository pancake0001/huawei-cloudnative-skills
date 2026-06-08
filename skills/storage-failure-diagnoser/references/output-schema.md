# Output Schema

`huawei_storage_failure_diagnose` returns structured JSON with the final customer report embedded in `report_markdown`.

```json
{
  "success": true,
  "action": "huawei_storage_failure_diagnose",
  "region": "cn-north-4",
  "cluster_id": "cluster-id",
  "namespace": "default",
  "conclusion": "high signal conclusion",
  "confidence": "High",
  "findings": [
    {
      "stage": "3. Failure during mounting period",
      "type": "EVSNodeAttachLimitExceeded",
      "title": "VolumeAttachment Attached=False, the error message points to the fact that the number of cloud disks attached to a single ECS node has reached the upper limit",
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
  "report_markdown": "# CCE storage fault automated diagnosis report\n..."
}
```

# # Markdown Sections

`report_markdown` must contain the following headers:

- `# CCE Storage Fault Automated Diagnosis Report`
- `## 1. Diagnosis Overview`
- `## 2. Troubleshooting process`
- `## 3. Key object relationships`
- `## 4. Evidence matrix`
- `## 5. Diagnostic conclusion`
- `## 6. Recommended actions and verification standards`
- `## 7. Data gaps and manual confirmation`

# # Finding Types

Common `type` values:

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