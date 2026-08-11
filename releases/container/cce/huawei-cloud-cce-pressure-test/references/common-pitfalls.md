# CCE Pressure-Test Common Pitfalls

Use these checks before treating a pressure-test result as an application bottleneck.

## k6 Client Image Pull Failure

Symptoms:

- In-cluster k6 Job Pod is `ImagePullBackOff` or `ErrImagePull`.
- Job has no k6 summary.
- Events mention manifest, registry, timeout, unauthorized, or DNS.

What it means:

- No meaningful traffic reached the target from this Job.

Next steps:

- Inspect Job Pod Events with `kubectl describe pod`.
- Mirror the k6 image to regional SWR or use local k6.
- Re-run smoke before any larger phase.

## Wrong Target URL Or Host Header

Symptoms:

- 404 from ingress.
- TLS mismatch.
- Requests succeed only with a specific Host header.
- k6 connects but routes to default backend.

Next steps:

- Check Ingress rules and `spec.rules[].host`.
- Pass `Host` in the k6 script when required.
- Verify URL path and protocol before load.

## Service Has No Ready Endpoint

Symptoms:

- Service exists but EndpointSlice has no ready addresses.
- Ingress returns 502/503.
- Pods are NotReady or selector does not match Pods.

Next steps:

- Compare Service selector with Pod labels.
- Inspect readiness probe Events.
- Fix workload readiness or Service selector before pressure testing.

## Metrics API Unavailable

Symptoms:

- `kubectl top` returns `Metrics API not available`.
- HPA cannot read CPU or memory metrics.

Next steps:

- Record a metrics data gap.
- Check metrics-server/addon health with the relevant cluster operations.
- Do not invent CPU or memory trends.

## HPA Does Not Scale

Symptoms:

- Traffic increases, Pods saturate, but replicas remain unchanged.
- HPA condition says metrics unavailable, not enough data, or maxReplicas reached.

Next steps:

- Inspect `kubectl get hpa -o yaml`.
- Check target utilization, current metrics, min/max replicas, and stabilization windows.
- Hand off to the autoscaling diagnoser when HPA behavior is the main issue.

## Public Endpoint Or Kubeconfig Reachability

Symptoms:

- `CreateKubernetesClusterCert` succeeds, but kubectl cannot connect.
- kubeconfig server points to a private IP.
- Cluster was just awakened or EIP was just bound.

Next steps:

- Check `ShowClusterEndpoints`.
- Use a runtime that can reach the private API endpoint, or carefully replace only the kubeconfig `server` field with the public endpoint when available.
- Retry certificate creation with explicit hcloud timeouts after wake-up.

## ELB Evidence Missing

Symptoms:

- k6 sees 5xx or timeouts, but there is no ELB ID or listener/pool/member evidence.
- External traffic path cannot be correlated with Kubernetes objects.

Next steps:

- Collect read-only ELB list data when permitted.
- Map Ingress LoadBalancer address to ELB, listener, pool, and member.
- Record a confidence gap if cloud-side evidence is unavailable.

## Short-Connection Amplification

Symptoms:

- Short-connection model fails earlier than keepalive.
- Connection errors rise while application CPU is not saturated.

Next steps:

- Compare keepalive vs short-connection results.
- Check ELB connection limits, backend accept backlog, application connection pool, and NAT/ephemeral port behavior.
- Do not conclude application CPU bottleneck without resource evidence.

## Cleanup Assumptions

Symptoms:

- Test resources are left behind, or cleanup might delete user resources.

Next steps:

- List only resources created for the test.
- Show explicit delete commands.
- Get approval before cleanup.
