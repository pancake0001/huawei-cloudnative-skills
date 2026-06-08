# Output Schema

```json
{
  "success": false,
  "requires_confirmation": true,
  "remediation_trace_id": "ARR-...",
  "strategy": "rollback_previous_revision",
  "diagnosis": {},
  "action_result": {},
  "verification": {},
  "summary": "remediation plan or execution result",
  "action": "huawei_auto_remediation_run | huawei_rollback_cce_workload | huawei_scale_cce_workload",
  "risk_level": "R1 | R2 | R3",
  "target": {
    "region": "cn-north-4",
    "cluster_id": "optional",
    "resource": "optional"
  },
  "preview": {},
  "requires_confirmation": true,
  "confirmation_received": false,
  "execution": {},
  "verification": [],
  "rollback_notes": [],
  "report_markdown": "# CCE automatic recovery execution report...",
  "report_file": "optional"
}
```