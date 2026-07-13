---
id: huawei-cloud-cce-network-failure-diagnoser
name: huawei-cloud-cce-network-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE network failures with hcloud CLI for CCE cluster discovery, kubeconfig acquisition, and optional read-only ELB/VPC/EIP/NAT evidence, then kubectl for Kubernetes network objects. Use this skill for Service unreachable, DNS/CoreDNS errors, Ingress 502/504, NetworkPolicy blocks, EndpointSlice/backend readiness issues, ELB backend health, EIP/NAT/VPC/security-group/ACL concerns, and end-to-end network Markdown reports. Do not use the Python SDK dispatcher.
tags: [huawei-cloud, cce, hcloud, koocli, kubectl, network, elb, vpc, diagnosis]
---

# Huawei Cloud CCE Network Failure Diagnoser

This skill diagnoses CCE network failures through Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

Execution model:

```text
hcloud CCE -> short-lived kubeconfig -> kubectl network evidence -> optional hcloud ELB/VPC/EIP/NAT read-only evidence -> ranked diagnosis report
```

Use CCE hcloud commands for cluster discovery and kubeconfig:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`
- `hcloud CCE CreateKubernetesClusterCert`

Use `kubectl` for Kubernetes network objects: Nodes, Pods, Services, Endpoints, EndpointSlices, Ingresses, NetworkPolicies, Events, CoreDNS/kube-dns resources, and relevant controller logs when RBAC allows.

Use cloud network hcloud commands only for read-only north-south evidence when identifiers are available or can be safely correlated:

- `hcloud ELB ListLoadBalancers/v3`
- `hcloud ELB ListListeners/v3`
- `hcloud ELB ListPools/v3`
- `hcloud ELB ListMembers/v3`
- `hcloud ELB ListHealthMonitors/v3`
- `hcloud VPC ListSecurityGroups/v3`
- `hcloud VPC ListSecurityGroupRules/v3`
- `hcloud VPC ListVpcs/v3`
- `hcloud VPC ListSubnets`
- `hcloud EIP ListPublicips/v3`
- `hcloud NAT ListNatGateways`

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, old `huawei_network_*` actions, or Huawei Cloud SDK imports for this skill.

## When To Use

Use this skill for:

- Service unreachable, intermittent, or selector/EndpointSlice issues.
- DNS/CoreDNS failures such as NXDOMAIN, timeout, or missing kube-dns endpoints.
- Ingress 502/504, ingress controller upstream errors, or LoadBalancer provisioning issues.
- NetworkPolicy blocking east-west traffic.
- ELB backend unhealthy, listener/pool/member mismatch, EIP/NAT/VPC/security group/ACL questions.
- Network symptoms that require an end-to-end Markdown report with evidence and verification criteria.

Do not use this skill to mutate resources. Binding/unbinding EIP, changing security groups, updating ELB listeners, editing CoreDNS, creating NetworkPolicies, scaling workloads, or restarting components must be handed off as recommendations only.

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4` |
| `project_id` | Usually | Required by most hcloud operations |
| `cluster_id` | Preferred | Resolve by name with `ListClusters` if absent |
| `namespace` | Usually | Required for namespaced K8s objects |
| `failure_symptom` | Recommended | `dns_failure`, `service_unreachable`, `ingress_502_504`, `external_access_failed`, `network_policy_block`, `intermittent` |
| `service_name` | Optional | Target Service |
| `ingress_name` | Optional | Target Ingress |
| `source_pod` | Optional | Source Pod name or selector |
| `destination_pod` | Optional | Destination Pod name or selector |
| `domain` | Optional | Domain involved in DNS/Ingress failure |
| `elb_id` | Optional | ELB load balancer ID for north-south checks |

If the target is vague, start with a namespace scan and ask for the specific service, ingress, source, destination, or domain before drawing a strong conclusion.

## Prerequisites

1. `hcloud` is installed and available in `PATH`, or a platform-native binary has been located and validated with `hcloud version`.
2. `kubectl` is installed and compatible with the target Kubernetes version. Linux sandboxes must use Linux kubectl; Windows workstations use `kubectl.exe`.
3. hcloud credentials are available through a profile, environment, or one-off CLI parameters. Verify only masked configuration with:

```bash
hcloud configure list
```

4. IAM allows CCE cluster read and kubeconfig certificate creation. ELB/VPC/EIP/NAT read permissions are needed only when diagnosing cloud-side network objects.
5. Kubernetes RBAC allows read access to Services, Endpoints, EndpointSlices, Ingresses, NetworkPolicies, Pods, Nodes, Events, and relevant logs.

Never print AK, SK, security tokens, kubeconfig certificates, Authorization headers, or registry/application secrets.

## CCE hcloud Setup Flow

### 1. Confirm CLI Tools

```bash
hcloud version
hcloud configure list
kubectl version --client
```

If a tool is not in `PATH`, locate or install a platform-native binary and validate the exact binary before using it. Keep examples platform-neutral as `hcloud` and `kubectl`.

### 2. Locate And Check The Cluster

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

If only a private API endpoint is available, run kubectl from a VPC/VPN/Direct Connect/Cloud Desktop environment that can reach the private endpoint.

### 3. Acquire A Short-Lived Kubeconfig

```bash
hcloud CCE CreateKubernetesClusterCert --cluster_id=<cluster-id> --project_id=<project-id> --duration=1 --cli-region=<region> --cli-output=json > <temp-kubeconfig-file>
chmod 600 <temp-kubeconfig-file>
```

Store kubeconfig outside the repository and delete it after diagnosis when no longer needed. If KooCLI times out on a recently awakened cluster, retry with `--cli-connect-timeout=20 --cli-read-timeout=90 --cli-retry-count=2`.

### 4. Verify Kubernetes Read Access

```bash
kubectl --kubeconfig=<kubeconfig-file> cluster-info
kubectl --kubeconfig=<kubeconfig-file> auth can-i list services -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list endpoints -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list endpointslices.discovery.k8s.io -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list networkpolicies.networking.k8s.io -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list ingresses.networking.k8s.io -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list pods -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> auth can-i list events -n <namespace>
```

If RBAC denies a read, report the missing verb/resource and continue only with allowed evidence.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence order and failure rules.

Start with the Kubernetes network baseline:

```bash
kubectl --kubeconfig=<kubeconfig-file> get nodes -o wide
kubectl --kubeconfig=<kubeconfig-file> get svc,endpoints,endpointslice,ingress,networkpolicy -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n <namespace> -o wide
kubectl --kubeconfig=<kubeconfig-file> get events -n <namespace> --sort-by=.lastTimestamp
```

For a Service:

```bash
kubectl --kubeconfig=<kubeconfig-file> get svc <service-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> get endpoints <service-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> get endpointslice -n <namespace> -l kubernetes.io/service-name=<service-name> -o yaml
```

For DNS:

```bash
kubectl --kubeconfig=<kubeconfig-file> get svc,endpoints,endpointslice -n kube-system -o wide
kubectl --kubeconfig=<kubeconfig-file> get pods -n kube-system -o wide | grep -E 'coredns|kube-dns|node-local-dns'
kubectl --kubeconfig=<kubeconfig-file> logs -n kube-system -l k8s-app=kube-dns --tail=200
```

On PowerShell, replace `grep` with `Select-String`.

For Ingress and LoadBalancer:

```bash
kubectl --kubeconfig=<kubeconfig-file> get ingress <ingress-name> -n <namespace> -o yaml
kubectl --kubeconfig=<kubeconfig-file> describe ingress <ingress-name> -n <namespace>
kubectl --kubeconfig=<kubeconfig-file> describe svc <service-name> -n <namespace>
```

Use hcloud cloud-network reads only when needed:

```bash
hcloud ELB ListLoadBalancers/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListListeners/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListPools/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListMembers/v3 --project_id=<project-id> --pool_id=<pool-id> --cli-region=<region> --cli-output=json
hcloud VPC ListSecurityGroups/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud VPC ListSecurityGroupRules/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud EIP ListPublicips/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud NAT ListNatGateways --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Use `hcloud <service> <operation> --help` when a filter parameter differs by API version.

## Active Test Boundary

By default, do not run `kubectl exec`, packet capture, stress tests, or synthetic traffic generation. If the user explicitly requests an active connectivity test, explain the scope and risk, then prefer the least invasive command and include it in the report.

## Cause Ranking

Rank causes by the first failing layer:

1. Cluster/API/RBAC reachability gap.
2. Node or CNI health that invalidates higher-layer diagnosis.
3. DNS/CoreDNS/kube-dns/node-local-dns.
4. Service selector and EndpointSlice readiness.
5. NetworkPolicy and namespace policy.
6. Ingress/controller/backend mapping.
7. Cloud ELB listener/pool/member/health monitor.
8. VPC/security group/ACL/EIP/NAT.
9. Application/backend readiness or overload.

Common cause labels:

| Cause | Evidence |
| --- | --- |
| `NodeOrCNIUnhealthy` | Node NotReady, CNIProblem, FailedCreatePodSandBox |
| `DnsCoreDNSFailure` | kube-dns/CoreDNS has no ready endpoints, restarting, timeout, NXDOMAIN evidence |
| `ServiceNoReadyEndpoint` | Service exists but EndpointSlice has no ready addresses |
| `ServiceSelectorMismatch` | Service selector matches no Pods |
| `NetworkPolicyBlocked` | NetworkPolicy selects destination and does not allow source/port |
| `IngressBackendMismatch` | Ingress routes to missing Service/port or unhealthy backend |
| `ELBBackendUnhealthy` | ELB member unhealthy while K8s object mapping is present |
| `SecurityPolicyBlocked` | Security group, ACL, or route evidence blocks traffic |
| `EgressNatOrEipIssue` | NAT/EIP missing or abnormal for external egress/ingress path |
| `BackendApplicationIssue` | Network path exists but backend Pods are not ready or logs show app errors |

## Report Format

Use `references/output-schema.md` as the detailed schema. Put decision-critical information first; topology, object snapshots, and command traces come after the conclusion and next steps.

The user-facing report should include, in this order:

- Executive summary: symptom status, confidence, root category, and one-line conclusion.
- Root-cause analysis: top causes ranked with direct evidence and interpretation.
- Recommended next steps: verification checks, candidate fix paths, and handoff owner/skill.
- Target: region, project, cluster, namespace, symptom, source/destination, Service/Ingress/domain/ELB.
- Network path funnel with checked, abnormal, skipped, and pruned stages.
- Negative evidence: layers checked and why they are less likely.
- Key object snapshot: Service, EndpointSlice, Pods, Ingress, NetworkPolicy, CoreDNS, ELB/VPC objects when relevant.
- Verification gaps.
- Evidence matrix and detailed supporting evidence.
- CLI path used: hcloud CCE, kubectl, and optional hcloud ELB/VPC/EIP/NAT reads.
- Explicit statement that no mutating command was run.

## Safety Rules

Read `references/risk-rules.md` before making recommendations. This skill is read-only. Do not run:

- `kubectl apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, or component restarts
- `kubectl exec`, packet capture, or traffic generation unless explicitly requested and acknowledged
- hcloud create/update/delete operations
- Any SDK dispatcher action

## Verification

Read `references/verification-method.md` for the CLI verification checklist. A valid implementation should pass these checks:

- `hcloud version`, `hcloud configure list`, and `kubectl version --client` work.
- `hcloud CCE ListClusters`, `ShowCluster`, and `CreateKubernetesClusterCert` work.
- `kubectl --kubeconfig=<file>` can read network objects in the target namespace.
- Optional hcloud ELB/VPC/EIP/NAT read operations work when cloud-side evidence is needed.
- Repository/package search finds no SDK dispatcher entrypoints in this skill package.

## References

- `references/workflow.md` - layered network evidence order and failure rules.
- `references/common-pitfalls.md` - network diagnosis traps and CLI examples.
- `references/output-schema.md` - Markdown and JSON report structure.
- `references/risk-rules.md` - read-only boundaries and handoff rules.
- `references/verification-method.md` - environment and CLI verification.
- `references/iam-policies.md` - IAM and Kubernetes RBAC requirements.
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/
