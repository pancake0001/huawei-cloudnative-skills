# CCE Pressure-Test Scenario Guides

After identifying a top finding, use the matching section to make the report specific and actionable.

## K6ClientImagePullFailure

Evidence:

- k6 Job Pod is `ImagePullBackOff` or `ErrImagePull`.
- Pod Events mention manifest errors, registry timeout, authentication, DNS, or `400 Bad Request`.
- No k6 summary exists.

Interpretation:

- The test client never started, so the result is a client setup failure, not target workload performance.

Next steps:

- Mirror the k6 image to regional SWR and update the Job image.
- Confirm image pull secret if using a private repository.
- Re-run smoke before baseline or ramp.

## RouteHostOrPathMismatch

Evidence:

- k6 receives 404/421/TLS host mismatch.
- Ingress has a Host rule or path that differs from `target_url`.
- Default backend handles the request.

Interpretation:

- Traffic reached ingress but did not match the intended route.

Next steps:

- Add the correct `Host` header in k6.
- Correct path/protocol.
- Re-run smoke and verify backend Service hit count/logs.

## ServiceNoReadyEndpoint

Evidence:

- Service exists, but Endpoints or EndpointSlices have no ready addresses.
- Pods are NotReady or Service selector matches no Pods.
- Ingress/ELB returns 502/503.

Interpretation:

- The route cannot forward to ready application Pods, so load testing capacity would be meaningless.

Next steps:

- Fix Pod readiness or Service selector.
- Check readiness probe failure Events.
- Re-run smoke after endpoints are ready.

## ApplicationLatencySaturation

Evidence:

- k6 p95/p99 latency rises with VUs or RPS.
- HTTP success may stay high at first, then errors appear near a load threshold.
- Pod CPU/memory or application logs show pressure, queueing, GC, or timeout evidence.

Interpretation:

- The application or its direct dependencies are likely the limiting factor at the tested load.

Next steps:

- Compare latency curve with Pod metrics and logs.
- Check request queue, thread pool, DB/cache dependency, and resource limits.
- Tune app or resource requests/limits, then rerun baseline.

## HpaScaleUpLag

Evidence:

- HPA metrics are available, but replicas increase late relative to latency or CPU pressure.
- HPA conditions show stabilization, cooldown, or maxReplicas reached.
- Latency improves after new replicas become Ready.

Interpretation:

- The workload can benefit from more replicas, but autoscaling timing or limits are constraining performance.

Next steps:

- Check HPA target utilization, maxReplicas, stabilization windows, and readiness delay.
- Consider pre-warming, higher minReplicas, or adjusted HPA behavior.
- Hand off to the autoscaling diagnoser for deeper HPA analysis.

## HpaMetricsUnavailable

Evidence:

- `kubectl cce ... top` or HPA status shows missing metrics.
- HPA does not scale while traffic increases.

Interpretation:

- Autoscaling cannot be evaluated reliably because the control signal is missing.

Next steps:

- Diagnose metrics-server or observability add-on health.
- Do not conclude application capacity from a failed HPA phase alone.
- Record the metrics gap and rerun after metrics recover.

## NodeOrClusterCapacitySaturation

Evidence:

- Pods are Pending or HPA cannot add ready replicas.
- Nodes are near CPU/memory allocatable waterlines.
- Events mention insufficient CPU, memory, ephemeral storage, or node pressure.

Interpretation:

- Cluster capacity, not just workload configuration, limits the pressure-test result.

Next steps:

- Check node allocatable vs requests.
- Review nodepool autoscaling limits and recent scale events.
- Hand off to node or autoscaling diagnosis depending on evidence.

## ELBBackendUnhealthy

Evidence:

- ELB member health is unhealthy or listener/pool/member mapping is inconsistent.
- Kubernetes endpoints are ready, but external traffic fails.
- k6 sees connection reset, 502/504, or timeout through ELB.

Interpretation:

- The north-south load-balancing layer may be the failing layer.

Next steps:

- Map ELB listener -> pool -> members to node/Pod route.
- Check health-monitor path, port, protocol, and security group rules.
- Hand off to the network diagnoser if cloud-side mapping is unresolved.

## ShortConnectionLimit

Evidence:

- Short-connection model fails earlier than keepalive.
- Errors are connection resets, timeouts, or connection refused.
- Application CPU is not the obvious limiting factor.

Interpretation:

- Connection churn, ELB/backend limits, application accept backlog, or NAT/ephemeral ports may be limiting.

Next steps:

- Compare keepalive and short-connection results.
- Check ELB connection metrics when available.
- Review backend server connection handling and OS/application connection limits.
