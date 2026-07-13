# Workflow

This workflow is read-only and uses `hcloud CCE`, `kubectl`, and optional read-only `hcloud` cloud-network commands.

## Evidence Order

1. Scope: confirm `region`, `project_id`, `cluster_id`, `namespace`, `failure_symptom`, and the target object or path.
2. CLI setup: verify hcloud, masked credentials, kubectl, cluster metadata, endpoint reachability, kubeconfig acquisition, and read RBAC.
3. Node base layer: check nodes and CNI-related conditions before interpreting Service or Ingress failures.
4. DNS layer: inspect kube-dns/CoreDNS Service, EndpointSlices, Pods, Events, and logs when the symptom involves DNS.
5. Service layer: inspect Service type, selector, ports, Endpoints, EndpointSlices, and backend Pod readiness.
6. Policy layer: inspect NetworkPolicies in the namespace and determine whether they select the destination and allow the source/port.
7. Ingress layer: inspect Ingress rules, class, annotations, backend Service/port, status address, controller Events, and related logs when available.
8. Cloud north-south layer: inspect ELB, listener, pool, member health, EIP, NAT, VPC, security group, subnet, and ACL only when the symptom requires it.
9. Application backend layer: inspect backend Pod readiness, restarts, Events, and sanitized logs when the network path is otherwise present.
10. Output: rank Top3 causes, cite evidence, list verification gaps, and provide safe handoff recommendations.

## Baseline Commands

```bash
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <kubeconfig-file>

kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> get svc,endpoints,endpointslice,ingress,networkpolicy -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
```

## Failure Rules

### Node Or CNI Unhealthy

- Signals: Node NotReady, NetworkUnavailable, CNIProblem, CNI Pods unhealthy, or `FailedCreatePodSandBox` concentrated on nodes.
- Interpretation: higher network layers may be symptoms; diagnose node/CNI first.
- Next checks: affected nodes, CNI daemon Pods, Events, and handoff to node/network operations.

### DNS/CoreDNS Failure

- Signals: kube-dns/CoreDNS Service has no ready endpoints, CoreDNS Pods restarting, node-local-dns unhealthy, logs show upstream timeout or NXDOMAIN for expected domains.
- Interpretation: service name or external domain resolution may fail before traffic reaches Service routing.
- Next checks: kube-system DNS resources, CoreDNS logs, node-local-dns injection, upstream DNS config, and whether only one namespace/node is affected.

### Service No Ready Endpoint

- Signals: Service exists but EndpointSlice has zero ready addresses, backend Pods are not Ready, or EndpointSlice address does not match expected Pods.
- Interpretation: Service routing has no healthy backend.
- Next checks: Service selector, backend Pod labels, readiness probes, Pod Events, and recent rollout.

### Service Selector Mismatch

- Signals: Service selector matches no Pods or wrong Pods.
- Interpretation: Kubernetes cannot build correct endpoints for the Service.
- Next checks: compare `spec.selector` with Pod labels and workload template labels.

### NetworkPolicy Blocked

- Signals: NetworkPolicy selects destination Pods and no ingress/egress rule allows the source labels, namespace labels, port, or protocol.
- Interpretation: policy is the likely blocking layer when Service and endpoints are otherwise healthy.
- Next checks: source Pod labels, destination Pod labels, namespace labels, policy types, ports, and default-deny policies.

### Ingress Backend Mismatch

- Signals: Ingress backend points to missing Service/port, empty address, controller Events, or 502/504 upstream errors while Service mapping is wrong or backends are not ready.
- Interpretation: north-south HTTP route cannot reach a healthy backend.
- Next checks: Ingress rules, class, annotations, Service port names/numbers, EndpointSlices, and ingress controller logs.

### ELB Backend Unhealthy

- Signals: Kubernetes LoadBalancer/Ingress object exists, but ELB member health is unhealthy or listener/pool/member mapping is inconsistent.
- Interpretation: cloud load balancer cannot reach backend members or health checks fail.
- Next checks: ELB listener, pool, members, health monitor, backend port, subnet, security group, and backend Pod readiness.

### Security Policy Blocked

- Signals: Security group or ACL rules do not allow required source/destination/port/protocol, or route/subnet evidence blocks the path.
- Interpretation: cloud-side policy may block north-south or node-to-ELB traffic.
- Next checks: effective security group rules, VPC ACLs, subnet route table, ELB subnet, and expected source CIDR.

### EIP/NAT Issue

- Signals: EIP not bound to expected load balancer, NAT gateway missing for egress, SNAT rules absent, or EIP status abnormal.
- Interpretation: external ingress or egress path may be missing cloud-side network attachment.
- Next checks: EIP association, NAT gateway/SNAT rules, route table, and workload subnet.

### Backend Application Issue

- Signals: Service, endpoints, policy, ingress, and ELB look healthy, but backend Pods are not Ready or logs show application errors.
- Interpretation: network path is likely present; the backend application is failing health checks or requests.
- Next checks: Pod failure diagnoser and workload owner.

## Pruning Rules

- If node/CNI is unhealthy, report upper network layers as pruned or low-confidence until node health is restored.
- If DNS is the symptom and DNS layer is abnormal, do not over-investigate ELB unless the target is an external DNS name tied to ELB.
- If Service has no ready endpoints, Ingress/ELB failures are downstream symptoms until backend readiness is fixed.

## Handoff Guidance

- Node failure diagnoser for node/CNI base-layer faults.
- Pod or workload failure diagnoser for backend Pods not Ready.
- Auto-remediation runner for confirmed, user-approved changes.
- Platform/network owner for ELB, security group, ACL, NAT, EIP, or route changes.
