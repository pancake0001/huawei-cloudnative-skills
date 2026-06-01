

## aicli 实际输出（Skill 生成的报告）

{
  "success": true,
  "action": "pod_failure_diagnose",
  "region": "cn-north-4",
  "cluster_id": "1d450236-5b28-11f1-a7f6-0255ac10026a",
  "target": {
    "namespace": "default",
    "pod_name": "abclient-57c4fbb6f6-22gc7",
    "workload_name": null,
    "labels": null
  },
  "summary": {
    "diagnosis_status": "no_matching_abnormal_pods",
    "message": "未找到匹配的异常 Pod；如果要诊断正常或指定 Pod，请提供 pod_name/workload_name/labels。",
    "total_pods_seen": 1019
  },
  "pods": [],
  "top_causes": [],
  "recommended_actions": [],
  "warnings": []
}
