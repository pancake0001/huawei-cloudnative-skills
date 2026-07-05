# Output Schema

Produce a concise Markdown report for users, and optionally include the JSON-compatible structure below for automation.

## Markdown Report

```markdown
# CCE Workload Diagnosis

## Target
- Region:
- Project ID:
- Cluster:
- Namespace:
- Kind:
- Name:

## CLI Path
- hcloud:
- kubeconfig:
- kubectl:
- Mutating commands run: No

## Summary
- Status:
- Confidence:
- Headline:

## Rollout Funnel
| Layer | Expected | Actual | Status | Evidence |
| --- | --- | --- | --- | --- |

## Top Causes
1. Cause:
   - Confidence:
   - Evidence:
   - Recommendation:

## Events And Logs
- Relevant events:
- Pod logs checked:
- Previous logs checked:

## Handoffs
- Skill:
- Reason:

## Gaps
- Missing permissions:
- Missing data:
- Tooling/network issues:
```

## JSON-Compatible Structure

```json
{
  "success": true,
  "execution_model": "hcloud_cce_cli_plus_kubectl",
  "target": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-id",
    "cluster_name": "cluster-name",
    "namespace": "default",
    "kind": "Deployment",
    "name": "api"
  },
  "commands": {
    "hcloud": [
      "hcloud CCE ListClusters ...",
      "hcloud CCE ShowCluster ...",
      "hcloud CCE CreateKubernetesClusterCert ..."
    ],
    "kubectl": [
      "kubectl --kubeconfig=<file> get deployment ...",
      "kubectl --kubeconfig=<file> get pods ..."
    ],
    "mutating_commands_run": false
  },
  "selector": {
    "value": "app=api",
    "source": "spec.selector.matchLabels"
  },
  "summary": {
    "status": "healthy | control_plane_not_observed | new_version_not_created | rollout_blocked | replicas_unavailable | probe_failure | insufficient_evidence",
    "headline": "human-readable diagnosis",
    "expected_replicas": 3,
    "updated_replicas": 3,
    "ready_replicas": 1,
    "available_replicas": 1,
    "top_cause": "ProbeFailure"
  },
  "generation_check": {
    "generation": 5,
    "observed_generation": 5,
    "observed": true
  },
  "workload": {
    "uid": "workload-uid",
    "conditions": [],
    "strategy": {}
  },
  "version": {
    "strategy": "DeploymentReplicaSet | StatefulSet | DaemonSet",
    "new_revision": "7",
    "new_owner": {},
    "old_owners": []
  },
  "funnel": [
    {
      "layer": "new_pods_ready",
      "expected": 3,
      "actual": 1,
      "status": "fail",
      "evidence": "2 selected new-version pods are not Ready"
    }
  ],
  "events": {
    "source": "kubectl get events",
    "filtered_count": 5,
    "filter_basis": "workload/replicaset/pod UID or selected object names",
    "timeline": []
  },
  "pod_drilldown": {
    "diagnosed_pods": 1,
    "pods": []
  },
  "top_causes": [
    {
      "rank": 1,
      "type": "ProbeFailure",
      "title": "New version Pods are Running but readiness checks fail",
      "confidence": 0.88,
      "evidence": [],
      "recommendations": []
    }
  ],
  "handoff": [
    {
      "skill": "huawei-cloud-cce-pod-failure-diagnoser",
      "reason": "Probe failure requires Pod log and health check analysis"
    }
  ],
  "gaps": [],
  "warnings": []
}
```

## Field Notes

| Field | Description |
| --- | --- |
| `execution_model` | Must be `hcloud_cce_cli_plus_kubectl` |
| `commands.mutating_commands_run` | Must remain `false` for this skill |
| `summary.status` | Diagnosis status based on the first failing funnel layer |
| `events.filter_basis` | Explain how namespace events were narrowed to workload-related evidence |
| `top_causes[].confidence` | 0.0-1.0 confidence based on direct evidence strength |
| `gaps` | Missing RBAC, missing metrics-server, missing logs, unavailable tools, or network limits |

## Handoff Skill Reference

| Direction | Skill |
| --- | --- |
| Pod runtime/log/probe | `huawei-cloud-cce-pod-failure-diagnoser` |
| Node pressure/scheduling | `huawei-cloud-cce-node-failure-diagnoser` |
| Storage/PVC/PV | `huawei-cloud-cce-storage-failure-diagnoser` |
| Service/Ingress/ELB/dependency | `huawei-cloud-cce-network-failure-diagnoser` |
| Multi-domain evidence | `huawei-cloud-cce-root-cause-analyzer` |
| Remediation execution | `huawei-cloud-cce-auto-remediation-runner` |
| Alarm correlation | `huawei-cloud-cce-alarm-correlation-engine` |
