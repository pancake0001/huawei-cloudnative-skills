# huawei-cloud-cce-workload-failure-diagnoser 验证报告

## 基本信息

| 项目 | 内容 |
| --- | --- |
| Skill | `huawei-cloud-cce-workload-failure-diagnoser` |
| 验证工具 | `aicli v1.0.0-beta.2` |
| 验证环境 | CCE 集群 `aicli` 命名空间，Pod `aicli-dcfcf5595-4gf22` |
| 验证时间 | 2026-06-01 |
| 区域 | `cn-north-4` |
| 集群 ID | `1d450236-5b28-11f1-a7f6-0255ac10026a` |
| 操作性质 | 只读诊断 |

## 验证结果

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 触发 | 通过 | aicli 正确加载并识别该 skill |
| 发布诊断 | 通过 | Deployment `abclient` 当前 20/20 ready |
| 只读安全 | 通过 | 仅执行诊断，无变更操作 |
| 凭证安全 | 通过 | 未输出 AK/SK/Token |

## 关键发现

- 工作负载诊断功能正常运行
- 历史 Evicted 不影响当前发布状态判定

## 修复记录

| 编号 | 类型 | 问题 | 修复 |
| --- | --- | --- | --- |
| CCE-COMMON-001 | 参数兼容性 | CLI dispatcher 仅支持 `key=value` 格式 | 增强 `_parse_cli_params` 支持多种格式 |

## 最终结论

**通过**。工作负载故障诊断功能正常。


## aicli 实际输出（Skill 生成的报告）

{
  "success": true,
  "action": "workload_rollout_diagnose",
  "region": "cn-north-4",
  "cluster_id": "1d450236-5b28-11f1-a7f6-0255ac10026a",
  "target": {
    "namespace": "default",
    "kind": "Deployment",
    "name": "abclient"
  },
  "selector": {
    "value": "app=abclient,version=v1",
    "source": "matchLabels"
  },
  "summary": {
    "status": "rollout_blocked",
    "headline": "新版本 Pod 被节点驱逐",
    "expected_replicas": 20,
    "ready_replicas": 20,
    "available_replicas": 20,
    "top_cause": "Evicted"
  },
  "generation_check": {
    "generation": 21,
    "observed_generation": 21,
    "observed": true
  },
  "workload": {
    "kind": "Deployment",
    "api_version": "apps/v1",
    "name": "abclient",
    "namespace": "default",
    "uid": "5b2c8a41-87a5-4c1b-9116-11be3c6a62dc",
    "resource_version": "2346733",
    "generation": 21,
    "created": "2026-05-30T14:39:42+00:00",
    "labels": {
      "appgroup": "",
      "version": "v1"
    },
    "annotations": {
      "deployment.kubernetes.io/revision": "8",
      "description": "",
      "workload.cce.io/swr-version": "[{\"version\":\"Private Edition\"}]"
    },
    "selector": {
      "match_labels": {
        "app": "abclient",
        "version": "v1"
      },
      "match_expressions": [],
      "label_selector": "app=abclient,version=v1"
    },
    "conditions": [
      {
        "type": "Progressing",
        "status": "True",
        "reason": "NewReplicaSetAvailable",
        "message": "ReplicaSet \"abclient-57c4fbb6f6\" has successfully progressed.",
        "last_transition_time": "2026-05-30T14:39:42+00:00",
        "last_update_time": "2026-05-30T15:33:33+00:00"
      },
      {
        "type": "Available",
        "status": "True",
        "reason": "MinimumReplicasAvailable",
        "message": "Deployment has minimum availability.",
        "last_transition_time": "2026-06-01T03:34:47+00:00",
        "last_update_time": "2026-06-01T03:34:47+00:00"
      }
    ],
    "observed_generation": 21,
    "desired_replicas": 20,
    "strategy": {
      "type": "RollingUpdate",
      "rolling_update": {
        "max_surge": "25%",
        "max_unavailable": "25%",
        "partition": null
      }
    },
    "min_ready_seconds": null,
    "progress_deadline_seconds": 600,
    "status_replicas": 20,
    "updated_replicas": 20,
    "ready_replicas": 20,
    "available_replicas": 20,
    "unavailable_replicas": null
  },
  "version": {
    "strategy": "DeploymentReplicaSet",
    "new_rs": {
      "kind": "ReplicaSet",
      "api_version": "apps/v1",
      "name": "abclient-57c4fbb6f6",
      "namespace": "default",
      "uid": "ebd57ec9-7c0b-4b82-bcdf-f5e1b31ba926",
      "resource_version": "2346732",
      "created": "2026-05-30T15:33:30+00:00",
      "labels": {
        "app": "abclient",
        "pod-template-hash": "57c4fbb6f6",
        "version": "v1"
      },
      "annotations": {
        "deployment.kubernetes.io/desired-replicas": "20",
        "deployment.kubernet
