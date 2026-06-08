# Output Schema

Primary action: `huawei_workload_rollout_diagnose`.

```json
{
  "success": true,
  "action": "workload_rollout_diagnose",
  "target": {
    "namespace": "default",
    "kind": "Deployment",
    "name": "api"
  },
  "selector": {
    "value": "app=api",
    "source": "matchLabels"
  },
  "summary": {
    "status": "control_plane_not_observed | new_version_not_created | rollout_blocked | replicas_unavailable | probe_failure | healthy",
    "headline": "human-readable diagnosis; may note when old-version replicas remain available",
    "expected_replicas": 3,
    "ready_replicas": 1,
    "available_replicas": 1,
    "top_cause": "ProbeFailure | ContainerCommandNotFound | CrashLoopOrAppExit | ..."
  },
  "generation_check": {
    "generation": 5,
    "observed_generation": 5,
    "observed": true
  },
  "workload": {
    "kind": "Deployment",
    "uid": "workload-uid",
    "desired_replicas": 3,
    "updated_replicas": 3,
    "ready_replicas": 1,
    "available_replicas": 1,
    "conditions": []
  },
  "version": {
    "strategy": "DeploymentReplicaSet",
    "new_rs": {},
    "old_rs": []
  },
  "funnel": [
    {"layer": "workload_current", "expected": 3, "actual": 3, "status": "pass"},
    {"layer": "new_pods_ready", "expected": 3, "actual": 1, "status": "fail"}
  ],
  "events": {
    "filtered_count": 5,
    "timeline": [],
    "filter": {
      "uid_count": 6,
      "before_count": 40,
      "after_count": 5,
      "events_without_involved_uid": 0
    }
  },
  "pod_diagnosis": {
    "diagnosed_pods": 1,
    "pods": []
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "ProbeFailure",
      "title": "The new version of Pod is running but the probe fails or is not ready",
      "confidence": 0.88,
      "evidence": [],
      "recommendation": []
    }
  ],
  "handoff": [
    {
      "skill": "pod-failure-diagnoser",
      "reason": "Probe failure requires combination of Pod log and health check configuration"
    }
  ],
  "warnings": []
}
```

Context-only action: `huawei_get_workload_rollout_context`.

```json
{
  "success": true,
  "action": "get_workload_rollout_context",
  "workload": {},
  "replicasets": [],
  "pods": [],
  "events": [],
  "event_filter": {},
  "warnings": []
}
```