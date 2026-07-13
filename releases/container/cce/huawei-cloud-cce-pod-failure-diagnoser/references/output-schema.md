# Output Schema

The final user-facing report may be Markdown, but it should be easy to map to this JSON shape. Include command evidence without secrets.

```json
{
  "success": true,
  "action": "pod_failure_diagnose_cli",
  "execution_model": "hcloud CCE + kubectl",
  "target": {
    "region": "cn-north-4",
    "project_id": "optional",
    "cluster_id": "cluster uuid",
    "cluster_name": "optional",
    "namespace": "default",
    "pod_name": "optional",
    "workload_name": "optional",
    "selector": "optional"
  },
  "cli_path": {
    "hcloud_commands": [
      "hcloud CCE ShowCluster ...",
      "hcloud CCE CreateKubernetesClusterCert ..."
    ],
    "kubectl_commands": [
      "kubectl --kubeconfig=<file> describe pod ...",
      "kubectl --kubeconfig=<file> get events ..."
    ],
    "mutating_commands_run": false
  },
  "summary": {
    "diagnosis_status": "abnormal | no_known_failure_detected | no_matching_pods | partial_evidence",
    "confidence": 0.85,
    "diagnosed_pods": 1,
    "total_pods_seen": 3,
    "status_counts": {
      "Running": 2,
      "Pending": 1
    },
    "issue_counts": {
      "CrashLoopBackOff": 1
    }
  },
  "pods": [
    {
      "pod": {
        "name": "demo-xxx",
        "namespace": "default",
        "phase": "Running",
        "reason": null,
        "node": "192.168.0.10",
        "qos_class": "Burstable",
        "owner": "ReplicaSet/demo-abc"
      },
      "containers": [
        {
          "name": "app",
          "ready": false,
          "restart_count": 5,
          "state": "waiting",
          "state_reason": "CrashLoopBackOff",
          "last_state_reason": "Error",
          "last_exit_code": 1
        }
      ],
      "issues": [
        {
          "type": "CrashLoopBackOff | ImagePullBackOff | OOMKilled | PendingScheduling | PendingStorage | Evicted | FrequentRestart | ProbeFailure | SandboxOrCNIBlocked | PodNotReady",
          "title": "human-readable diagnosis",
          "confidence": 0.92,
          "container": "app",
          "scenario": "CrashLoopBackOff",
          "subtype": "app_startup_error",
          "root_cause_interpretation": "Explain what the failing signal means and why it is the most likely root cause.",
          "ruled_out": [
            "Scheduling is unlikely because PodScheduled=True and nodeName is set.",
            "OOM is unlikely because the container never started and restartCount is 0."
          ],
          "evidence": [
            "Previous logs show startup exception",
            "Event BackOff restarting failed container"
          ],
          "follow_up_checks": [
            {
              "check": "Verify the referenced image repository and tag exist.",
              "expected_signal": "Repository/tag is present and accessible from the intended registry.",
              "command_or_location": "Registry console, release manifest, or image build pipeline"
            }
          ],
          "recommendation": [
            "Fix application startup config and redeploy through the appropriate deployment workflow"
          ]
        }
      ],
      "events": [
        {
          "reason": "BackOff",
          "message": "Back-off restarting failed container",
          "last_timestamp": "2026-07-06T10:00:00Z",
          "count": 12
        }
      ],
      "logs": {
        "current": {
          "available": true,
          "excerpt": "sanitized tail logs"
        },
        "previous": {
          "available": true,
          "excerpt": "sanitized previous logs"
        }
      },
      "metrics": {
        "available": true,
        "source": "kubectl top",
        "notes": []
      }
    }
  ],
  "top_causes": [
    {
      "rank": 1,
      "type": "CrashLoopBackOff",
      "title": "Container repeatedly fails to start and enters back-off retry",
      "confidence": 0.92,
      "affected_count": 1,
      "affected_pods": ["default/demo-xxx"],
      "scenario": "CrashLoopBackOff",
      "subtype": "app_startup_error",
      "interpretation": "Explain the matched scenario in plain language using the relevant scenario guide.",
      "ruled_out": [],
      "evidence": [],
      "follow_up_checks": [],
      "recommendation": []
    }
  ],
  "verification_gaps": [
    {
      "area": "metrics",
      "detail": "metrics-server unavailable; kubectl top failed"
    }
  ],
  "recommended_actions": [
    {
      "action": "Read previous logs and combine with exit code to locate application startup failure point.",
      "source_cause": "CrashLoopBackOff",
      "requires_confirmation": false,
      "why": "Explains how this action validates or fixes the current hypothesis.",
      "handoff_skill": null
    }
  ],
  "next_skill": "huawei-cloud-cce-auto-remediation-runner | huawei-cloud-cce-node-failure-diagnoser | huawei-cloud-cce-storage-failure-diagnoser | null"
}
```

## Markdown Report Sections

When writing a human-readable report, put the action-driving sections first:

1. Executive summary: status, confidence, affected object, and one-line conclusion.
2. Root-cause analysis: top causes, direct evidence, and plain-language interpretation.
3. Recommended next steps: safe checks, candidate fix paths, and handoff skills.
4. Target and scope.
5. Pod lifecycle status.
6. Negative evidence and ruled-out causes.
7. Logs, Events, metrics, node/storage findings.
8. Verification gaps.
9. Detailed supporting evidence.
10. CLI path used.
11. Explicit statement that no mutating command was run.

## Scenario-Specific Recommendation Requirements

After identifying `top_causes[].type`, load `references/scenario-guides.md` and apply the matching scenario section. Do not reserve detailed recommendations for one special case; every concrete failure type should include scenario-specific interpretation, ruled-out causes, next checks, and candidate fix paths.

Each top cause should include:

- `scenario`: the matched scenario guide section, such as `ImagePullBackOff`, `CrashLoopBackOff`, `OOMKilled`, `Pending`, `StorageMountFailure`, `Evicted`, `ProbeFailure`, `SandboxOrCNIBlocked`, or `QuotaOrAdmissionRejected`.
- `subtype`: a more precise class derived from Events/logs/status, such as `repository_or_tag_missing`, `app_startup_error`, `memory_limit_too_low`, `failed_scheduling_taint`, or `pvc_pending`.
- `interpretation`: plain-language explanation of what the evidence means.
- `ruled_out`: adjacent causes that are less likely and why.
- `follow_up_checks`: concrete checks with expected confirming/refuting signals.
- `candidate_fix`: safe remediation options, without executing them.
- `handoff`: relevant skill or owner when remediation is outside this read-only diagnoser.
