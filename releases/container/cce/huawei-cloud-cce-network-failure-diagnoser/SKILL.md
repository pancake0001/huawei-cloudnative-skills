---
name: huawei-cloud-cce-network-failure-diagnoser
description: >
  Diagnose Huawei Cloud CCE network failures using hcloud for cluster and cloud-network metadata plus read-only kubectl-cce evidence. Use this skill whenever
  the user mentions unreachable Services, DNS or CoreDNS errors, Ingress 502/504, NetworkPolicy blocks, EndpointSlice or backend readiness, ELB health, EIP,
  NAT, VPC, security-group, or ACL issues.
version: 1.0.0
tags: [huawei-cloud, cce, kubectl, network, diagnosis]
---

# Huawei Cloud CCE Network Failure Diagnoser

## Overview

This skill diagnoses CCE network failures through Huawei Cloud `hcloud` CLI and Kubernetes `kubectl`.

Execution model:

```text
hcloud CCE cluster discovery -> kubectl cce network evidence -> optional hcloud ELB/VPC/EIP/NAT read-only evidence -> ranked diagnosis report
```

Use CCE hcloud commands for cluster discovery and metadata. Use kubectl-cce for Kubernetes API access:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

Use `kubectl cce` through the kubectl-cce plugin for Kubernetes network objects: Nodes, Pods, Services, Endpoints, EndpointSlices, Ingresses, NetworkPolicies,
Events, CoreDNS/kube-dns resources, and relevant controller logs when RBAC allows.

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

Do not use Python SDK dispatchers, legacy skill execution actions, old Huawei network actions, or Huawei Cloud SDK imports for this skill.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` for the
plugin access contract.

## When To Use

Use this skill for:

- Service unreachable, intermittent, or selector/EndpointSlice issues.
- DNS/CoreDNS failures such as NXDOMAIN, timeout, or missing kube-dns endpoints.
- Ingress 502/504, ingress controller upstream errors, or LoadBalancer provisioning issues.
- NetworkPolicy blocking east-west traffic.
- ELB backend unhealthy, listener/pool/member mismatch, EIP/NAT/VPC/security group/ACL questions.
- Network symptoms that require an end-to-end Markdown report with evidence and verification criteria.

Do not use this skill to mutate resources. Binding/unbinding EIP, changing security groups, updating ELB listeners, editing CoreDNS, creating NetworkPolicies,
scaling workloads, or restarting components must be handed off as recommendations only.

## Parameters

| Input             | Required    | Notes                                                                                                                     |
| ----------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------- |
| `region`          | Yes         | Request context or `HUAWEI_REGION`; otherwise ask the user                                                                                                     |
| `project_id`      | Usually     | Required by most hcloud operations                                                                                        |
| `cluster_id`      | Preferred   | Resolve by name with `ListClusters` if absent                                                                             |
| `namespace`       | Usually     | Required for namespaced K8s objects                                                                                       |
| `failure_symptom` | Recommended | `dns_failure`, `service_unreachable`, `ingress_502_504`, `external_access_failed`, `network_policy_block`, `intermittent` |
| `service_name`    | Optional    | Target Service                                                                                                            |
| `ingress_name`    | Optional    | Target Ingress                                                                                                            |
| `source_pod`      | Optional    | Source Pod name or selector                                                                                               |
| `destination_pod` | Optional    | Destination Pod name or selector                                                                                          |
| `domain`          | Optional    | Domain involved in DNS/Ingress failure                                                                                    |
| `elb_id`          | Optional    | ELB load balancer ID for north-south checks                                                                               |

If the target is vague, start with a namespace scan and ask for the specific service, ingress, source, destination, or domain before drawing a strong
conclusion.

## Region Selection

Use the region supplied by the current request or established task context. If it is absent, use `HUAWEI_REGION`. If neither source provides a region, stop and ask the user to provide `region` or set `HUAWEI_REGION`; never infer it from an hcloud profile.

## Explicit Credential Propagation

Accept `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token`. AK and SK must be supplied together; a token requires that pair. When
provided, append all supplied options to every `hcloud` and `kubectl cce` command, pass them unchanged to delegated skills, and do not use an hcloud profile
or authentication environment variables. Never print credential values.

## Prerequisites

1. `hcloud` is installed and available in `PATH`, or a platform-native binary has been located and validated with `hcloud version`.
2. `kubectl` is installed and compatible with the target Kubernetes version. Linux sandboxes must use Linux kubectl; Windows workstations use `kubectl.exe`.
3. hcloud credentials are available through a profile, environment, or one-off CLI parameters. Verify only masked configuration with `hcloud configure list`.
4. IAM allows CCE cluster read and kubectl-cce API Gateway access. ELB/VPC/EIP/NAT read permissions are needed only for cloud-side network objects.
5. Kubernetes RBAC allows read access to Services, Endpoints, EndpointSlices, Ingresses, NetworkPolicies, Pods, Nodes, Events, and relevant logs.

Never print AK, SK, security tokens, kubectl-cce proxy credentials, Authorization headers, or registry/application secrets.

## Core Commands And Setup

### 1. Confirm CLI Tools

```bash
hcloud version
hcloud configure list
kubectl version --client
```

If a tool is missing, stop this diagnosis flow and use `huawei-cloud-kubectl-cce-installer` or an approved platform-specific procedure. This diagnoser must not
download or execute installer scripts. Pin an approved version, verify its published checksum or signature, and then rerun the checks.

### 2. Locate And Check The Cluster

```bash
hcloud CCE ListClusters --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

The kubectl-cce plugin normally talks to `<cluster-id>.cce.<region>.myhuaweicloud.com`. If that CCE API Gateway endpoint is invalid for the current environment,
set `CCE_ENDPOINT` or pass `--endpoint`. If access fails, report the error as an access gap; do not fall back to kubeconfig generation or SDK calls.

### 3. Configure kubectl-cce Plugin

Read `references/kubectl-cce.md` before running Kubernetes commands. Use the kubectl CCE plugin as the primary Kubernetes access path. Do not generate or patch
kubeconfig, call the Kubernetes SDK, or fall back to SDK dispatcher actions.

If `kubectl` or `kubectl-cce` is missing, use `huawei-cloud-kubectl-cce-installer` to install or repair local prerequisites. This diagnoser only verifies and
uses the plugin; it does not own plugin installation policy.

Verify local tooling and plugin discovery:

```bash
kubectl version --client
kubectl plugin list
```

Configure plugin credentials through approved tool parameters, a protected shell environment, or an approved local credential provider without printing values.
Pass cluster, region, and project ID explicitly in diagnostic commands:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

Use `CCE_ENDPOINT` or `--endpoint` only when the default `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is invalid. If plugin access fails, report the
sanitized installation, credential, API Gateway reachability, or Kubernetes RBAC gap; do not switch to kubeconfig generation or SDK calls.

The plugin blocks streaming commands such as `exec`, `attach`, and `port-forward`. `logs -f` and `watch` are not hardened, so use bounded `logs --tail` and
normal `get` commands in diagnosis reports.

### 4. Verify Kubernetes Read Access

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list services -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list endpoints -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list endpointslices.discovery.k8s.io -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list networkpolicies.networking.k8s.io -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list ingresses.networking.k8s.io -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
```

If RBAC denies a read, report the missing verb/resource and continue only with allowed evidence.

## Diagnosis Workflow

Read `references/workflow.md` for detailed evidence order and failure rules.

Start with the Kubernetes network baseline:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,endpointslice,ingress,networkpolicy -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
```

For a Service:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc <service-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get endpoints <service-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get endpointslice -n <namespace> -l kubernetes.io/service-name=<service-name> -o yaml
```

For DNS:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,endpoints,endpointslice -n kube-system -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n kube-system -o wide | grep -E 'coredns|kube-dns|node-local-dns'
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs -n kube-system -l k8s-app=kube-dns --tail=200
```

On PowerShell, replace `grep` with `Select-String`.

For Ingress and LoadBalancer:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ingress <ingress-name> -n <namespace> -o yaml
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe ingress <ingress-name> -n <namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> describe svc <service-name> -n <namespace>
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

The kubectl-cce plugin blocks `exec`, `attach`, and `port-forward`; this read-only skill must not bypass that boundary with kubeconfig, SDK, packet capture,
stress tests, or synthetic traffic generation. If the user requests an active connectivity test, record the source, destination, scope, risk, and expected
signal, then hand it off to an approved test path after explicit authorization.

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

| Cause                     | Evidence                                                                        |
| ------------------------- | ------------------------------------------------------------------------------- |
| `NodeOrCNIUnhealthy`      | Node NotReady, CNIProblem, FailedCreatePodSandBox                               |
| `DnsCoreDNSFailure`       | kube-dns/CoreDNS has no ready endpoints, restarting, timeout, NXDOMAIN evidence |
| `ServiceNoReadyEndpoint`  | Service exists but EndpointSlice has no ready addresses                         |
| `ServiceSelectorMismatch` | Service selector matches no Pods                                                |
| `NetworkPolicyBlocked`    | NetworkPolicy selects destination and does not allow source/port                |
| `IngressBackendMismatch`  | Ingress routes to missing Service/port or unhealthy backend                     |
| `ELBBackendUnhealthy`     | ELB member unhealthy while K8s object mapping is present                        |
| `SecurityPolicyBlocked`   | Security group, ACL, or route evidence blocks traffic                           |
| `EgressNatOrEipIssue`     | NAT/EIP missing or abnormal for external egress/ingress path                    |
| `BackendApplicationIssue` | Network path exists but backend Pods are not ready or logs show app errors      |

## Output Format

Use `references/output-schema.md` as the detailed schema. Put decision-critical information first; topology, object snapshots, and command traces come after the
conclusion and next steps.

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
- CLI path used: hcloud CCE, kubectl-cce, and optional hcloud ELB/VPC/EIP/NAT reads.
- Explicit statement that no mutating command was run.

## Best Practices

- Trace the path from client entrypoint to ready backend and stop at the first failed hop.
- Correlate selectors, endpoints, policies, DNS, Ingress, and cloud network identifiers.
- Treat active connectivity testing as a separate authorized handoff and record its scope, risk, and expected signal.
- Separate read-only diagnosis from network or workload changes and name the handoff.

## Notes And Safety Rules

Read `references/risk-rules.md` before making recommendations. This skill is read-only. Do not run:

- `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout undo`, or component restarts
- `kubectl exec`, packet capture, stress tests, or active traffic generation
- hcloud create/update/delete operations
- Any SDK dispatcher action

## Verification

Read `references/verification-method.md` for the CLI verification checklist. A valid implementation should pass these checks:

- `hcloud version`, `hcloud configure list`, and `kubectl version --client` work.
- `hcloud CCE ListClusters` and `ShowCluster` work, and `kubectl cce ...` can reach the cluster through the CCE API Gateway.
- `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id>` can read network objects in the target namespace.
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
