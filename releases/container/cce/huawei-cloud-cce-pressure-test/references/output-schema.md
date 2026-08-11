# CCE Pressure-Test Output Schema

Use this schema for both manual Markdown reports and any saved JSON evidence.

## Markdown Report Order

Put decision-critical information first.

```markdown
# CCE Pressure Test Report

## Executive Summary
- Status:
- Confidence:
- Target:
- Traffic phase:
- One-line conclusion:

## Root Or Bottleneck Analysis
| Rank | Finding | Evidence | Interpretation | Confidence |
| --- | --- | --- | --- | --- |

## Recommended Next Steps
| Priority | Action | Why | Owner/Handoff | Risk |
| --- | --- | --- | --- | --- |

## Test Scope And Approvals
| Field | Value |
| --- | --- |

## Traffic Results
| Phase | VUs/RPS | Duration | Requests | Success Rate | p50 | p95 | p99 | Errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Route And Workload Health
- Ingress:
- Service:
- EndpointSlice:
- Pods:
- Events:
- HPA:
- Metrics:

## Cloud-Side Evidence
- ELB:
- Listener/pool/member:
- VPC/EIP/NAT:

## Negative Evidence
- Checked and less likely:

## Verification Gaps
- Missing data:
- Impact on confidence:

## Evidence And Command Trace
- hcloud CCE commands:
- kubectl commands:
- k6 command or Job manifest:
- Mutating/traffic operations approved and executed:
```

For pressure tests, "root cause" may be a bottleneck or limiting factor rather than a failure. Name it precisely, for example `RouteHostMismatch`, `K6ClientImagePullFailure`, `ServiceNoReadyEndpoint`, `ApplicationLatencySaturation`, `HpaScaleUpLag`, `NodeCapacitySaturation`, or `ELBBackendUnhealthy`.

## JSON Evidence Shape

When saving structured evidence, use this shape:

```json
{
  "target": {
    "region": "",
    "project_id": "",
    "cluster_id": "",
    "cluster_name": "",
    "namespace": "",
    "workload_kind": "",
    "workload_name": "",
    "target_url": "",
    "host_header": ""
  },
  "approvals": [
    {
      "time": "",
      "scope": "",
      "approved_by": "",
      "command_or_manifest": "",
      "risk_level": ""
    }
  ],
  "preflight": {
    "cluster": {},
    "endpoints": {},
    "kubernetes_objects": {},
    "rbac": {},
    "metrics_available": null,
    "data_gaps": []
  },
  "traffic_runs": [
    {
      "phase": "",
      "mode": "local-k6|in-cluster-job",
      "start_time": "",
      "end_time": "",
      "vus": null,
      "duration": "",
      "rps_cap": null,
      "script_path": "",
      "job_name": "",
      "k6_summary": {
        "requests": null,
        "rps": null,
        "success_rate": null,
        "http_req_failed": null,
        "p50_ms": null,
        "p95_ms": null,
        "p99_ms": null,
        "errors": []
      },
      "workload_samples": [],
      "hpa_samples": [],
      "events": [],
      "logs": []
    }
  ],
  "cloud_evidence": {
    "elb": {},
    "vpc": {},
    "eip": {},
    "nat": {}
  },
  "findings": [
    {
      "rank": 1,
      "label": "",
      "evidence": [],
      "interpretation": "",
      "confidence": "",
      "next_steps": []
    }
  ],
  "negative_evidence": [],
  "data_gaps": [],
  "commands": []
}
```

## Finding Requirements

Each finding must include:

- Direct evidence: command output, Event, k6 summary, log line, or object field.
- Interpretation: what the evidence means for the traffic path or capacity.
- Confidence: high, medium, or low, based on evidence coverage.
- Next steps: at least one verification and one candidate fix or handoff.

Avoid vague conclusions:

- Weak: "Image pull failed."
- Strong: "The in-cluster k6 Job did not start because the k6 image could not be pulled. Pod Events show `ImagePullBackOff`; no HTTP traffic reached the target. Mirror the k6 image to regional SWR or use local k6 before rerunning."

- Weak: "Latency is high."
- Strong: "p95 latency crossed 2s only after HPA reached its current maxReplicas, while Pod CPU was near the agreed waterline. Next check HPA maxReplicas, CPU requests/limits, and node headroom before increasing traffic."

## Data Gap Requirements

A data gap is not a failure by itself. Include:

- What was unavailable.
- Why it was unavailable, if known.
- How it affects confidence.
- What command or permission would close the gap.

Examples:

- `kubectl top` returned Metrics API unavailable, so Pod CPU/memory trends could not be confirmed.
- ELB ID was not provided, so listener/pool/member health was not correlated.
- RBAC denied Job logs, so the k6 summary is unavailable.
