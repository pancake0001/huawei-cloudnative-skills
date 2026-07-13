# Common Pitfalls And Solutions

## Pitfall 1: Starting At ELB Before Checking Endpoints

For Ingress or LoadBalancer symptoms, first confirm that the Service has ready EndpointSlices. If there are no ready backends, ELB 502/504 is usually downstream.

## Pitfall 2: Treating Service Existence As Service Health

A Service can exist and still route nowhere. Always check selector, Endpoints, EndpointSlices, and backend Pod readiness.

## Pitfall 3: Ignoring NetworkPolicy

When Service and endpoints are healthy but east-west traffic fails, inspect NetworkPolicies that select the destination Pod and policy types that imply default deny.

## Pitfall 4: Overusing Active Tests

`kubectl exec` curl tests, packet capture, and traffic generation can affect workloads or require extra permissions. This skill is passive by default. Use active tests only after explicit user request and risk acknowledgment.

## Pitfall 5: Confusing DNS And Service Routing

DNS failure means name resolution is broken; Service routing failure means a resolved Service has no healthy path. Report them separately.

## Pitfall 6: Missing Node/CNI Base-Layer Failure

If nodes are NotReady or CNI is broken, Service, DNS, and Ingress symptoms may be secondary. Prune upper-layer confidence until the node/CNI issue is explained.

## Pitfall 7: Assuming Cloud Security Policy Without Evidence

Security groups, ACLs, routes, EIP, and NAT should be cited with actual hcloud read evidence. If the command is not run or permission is missing, mark it as a verification gap.

## Quick Signal Table

| Signal | Likely Meaning | Recommended Action |
| --- | --- | --- |
| Service selector matches no Pods | Selector mismatch | Compare Service selector with Pod/workload labels |
| EndpointSlice has zero ready addresses | No healthy backend | Check backend Pod readiness and probes |
| NetworkPolicy selects destination with no allow rule | Policy block | Check source/destination labels, namespace labels, ports |
| CoreDNS has no endpoints or restarts | DNS layer failure | Inspect kube-system DNS resources and logs |
| Ingress backend service/port missing | Ingress mapping error | Fix Ingress backend or Service port through workload workflow |
| ELB member unhealthy | Cloud LB cannot reach backend or health check fails | Check member port, health monitor, SG/ACL, Pod readiness |
| EIP not associated | External ingress unavailable | Check EIP/LB binding and hand off for change |
