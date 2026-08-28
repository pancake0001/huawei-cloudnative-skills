---
id: huawei-cloud-cce-pressure-test
name: huawei-cloud-cce-pressure-test
description: >
  Run and evaluate Huawei Cloud CCE workload pressure tests with hcloud CLI for CCE cluster discovery, `kubectl cce` plugin commands for Kubernetes
  route/client/job/metrics evidence, and k6 for traffic generation. Use this skill for CCE pressure test, load test, stress test, performance test, k6 test, ELB
  traffic test, end-to-end traffic path validation, elasticity evaluation, 压测, 负载测试, 性能测试, 全链路压测, 弹性评估, and traffic generation. Do not use
  the Python SDK dispatcher.
tags: [cce, hcloud, kubectl, k6, pressure-test]
version: 1.0.0
---

# Huawei Cloud CCE Pressure Test

## Overview

This skill plans, runs, and reports controlled CCE workload pressure tests through Huawei Cloud `hcloud` CLI, Kubernetes `kubectl`, and k6.

Execution model:

```text
hcloud CCE cluster discovery -> kubectl cce preflight/route/client evidence -> k6 traffic -> kubectl cce metrics/logs/events -> pressure-test report
```

Use CCE hcloud commands for cluster discovery and metadata. Use kubectl-cce for Kubernetes API access:

- `hcloud CCE ListClusters`
- `hcloud CCE ShowCluster`
- `hcloud CCE ShowClusterEndpoints`

Use `kubectl cce` through kubectl-cce plugin access for Kubernetes objects: Deployments, StatefulSets, DaemonSets, Pods, Services, EndpointSlices, Ingresses,
HPA, PDB, Events, Job logs, and metrics-server data.

Use cloud network hcloud commands only when north-south ELB/VPC context is needed:

- `hcloud ELB ListLoadBalancers/v3`
- `hcloud ELB ListListeners/v3`
- `hcloud ELB ListPools/v3`
- `hcloud ELB ListMembers/v3`
- `hcloud ELB ListHealthMonitors/v3`
- `hcloud VPC ListSubnets`
- `hcloud VPC ListSecurityGroups/v3`
- `hcloud VPC ListSecurityGroupRules/v3`
- `hcloud EIP ListPublicips/v3`
- `hcloud NAT ListNatGateways`

Do not use Python SDK dispatcher commands, `scripts/huawei-cloud.py`, `skill action=exec`, old `huawei_*pressure*` actions, or Huawei Cloud SDK imports for this
skill.

**Related prerequisite skill**: use `huawei-cloud-kubectl-cce-installer` to install or repair `kubectl`/`kubectl-cce`. Read `references/kubectl-cce.md` for the
plugin access contract.

## When To Use

Use this skill for:

- CCE workload pressure tests, k6 tests, load tests, stress tests, and performance baselines.
- End-to-end path checks such as k6 client -> ELB -> ingress controller -> Service -> Pod.
- Route readiness checks before sending traffic to an existing workload.
- Baseline vs scaled or HPA-driven elasticity comparisons.
- Investigation of latency, 4xx/5xx, connection errors, timeout, saturation, or HPA lag observed during a pressure test.
- Generating a Markdown report from traffic results and Kubernetes/cloud evidence.

Do not use this skill as a general read-only failure diagnoser when no pressure test is involved. Use the Pod, workload, node, or network diagnoser skills for
pure diagnosis.

## Parameters

### Input Parameter Validation
Required parameters must be provided before execution. A required `cluster_id`, or an optional `cluster_id` supplied by the user, must pass the following validation before any cluster-targeted request. Query tools may query the region globally only when their optional `cluster_id` is omitted:
1. Check whether `cluster_id` is a standard UUID:
   - UUID: call `hcloud CCE ShowCluster` to verify it.
   - Otherwise: call `hcloud CCE ListClusters`, perform an exact and unique name match, convert it to a UUID, then call `ShowCluster` to verify it.
If a required `cluster_id` is missing, or any supplied `cluster_id` is invalid, unmatched, or ambiguous, stop the operation and require the user to provide the correct region and cluster ID. A supplied invalid `cluster_id` must never fall back to a global query; never guess or select a cluster. For any other required resource identifier, first use the corresponding read-only query tool to list candidates when the user cannot provide an unambiguous value, then ask the user to choose; never select a candidate automatically.

### Input Parameters

Collect these values before preparing any traffic:

| Input | Required | Notes |
| --- | --- | --- |
| `region` | Yes | Example: `cn-north-4`. |
| `project_id` | Usually | Required by most hcloud CCE operations. |
| `cluster_id` | Preferred | If absent, resolve by cluster name with `ListClusters`. |
| `cluster_name` | Optional | Use only to locate `cluster_id`. |
| `namespace` | Usually | Target workload namespace. |
| `workload_name` | Usually | Deployment, StatefulSet, or DaemonSet name. |
| `workload_kind` | Optional | Default to Deployment when not specified. |
| `target_url` | Required before traffic | External URL, Ingress URL, or Service URL from an approved route. |
| `target_port` | Optional | Container or Service target port. |
| `host_header` | Optional | Required when Ingress host rules are used. |
| `traffic_model` | Yes | `smoke`, `keepalive`, `short`, `ramp`, or a user-defined k6 script. |
| `vus`, `duration`, `rps` | Yes | Start small, then ramp only after smoke success. |
| `test_window` | Required for production-like targets | Include owner and stop conditions. |
| `output_dir` | Recommended | Store run summary, logs, evidence, and report. |

If any target, owner, or traffic limit is ambiguous, stop before sending traffic and ask for confirmation.

## Prerequisites

1. `hcloud` is installed and available in `PATH`, or a platform-native binary has been located and validated with `hcloud version`. Keep examples
   platform-neutral as `hcloud`, not an OS-specific absolute path.
2. `kubectl` is installed and compatible with the target Kubernetes minor version. Linux sandboxes must use Linux kubectl; Windows workstations use
   `kubectl.exe`. Do not hard-code `kubectl.exe` in the skill workflow.
3. k6 is available locally, or the test will use an approved in-cluster k6 Job image. If public image pulls are unreliable, mirror the k6 image to regional SWR
   before running the Job.
4. hcloud credentials are configured through a profile, environment, or one-off CLI parameters. Verify only masked configuration with:

   ```bash
   hcloud configure list
   ```

5. IAM allows CCE cluster read and kubectl-cce API Gateway access. ELB/VPC/EIP/NAT read permissions are needed only when cloud-side network evidence is
   collected.
6. Kubernetes RBAC allows read access to workload resources, Services, EndpointSlices, Ingresses, HPA, Events, Pods, Pod logs, Job logs, and metrics. Write
   permissions are needed only for user-approved route/client/scale changes.

Never print AK, SK, security tokens, kubectl-cce proxy credentials, Authorization headers, registry secrets, or application secrets. Do not write credentials
into reports or manifests.

## Core Commands And Setup Flow

### 1. Confirm CLI Tools

```bash
hcloud version
hcloud configure list
kubectl version --client
k6 version
```

If k6 is not installed locally, use an in-cluster Job only after the user approves the Job manifest and target. If hcloud or kubectl is missing, install or
locate the platform-native binary and validate the exact binary before continuing.

### 2. Locate And Check The Cluster

```bash
hcloud CCE ListClusters --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud CCE ShowCluster --cluster_id=<cluster-id> --project_id=<project-id> --detail=true --cli-region=<region> --cli-output=json
hcloud CCE ShowClusterEndpoints --cluster_id=<cluster-id> --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Confirm the cluster belongs to the expected region/project.

The kubectl-cce plugin normally talks to the CCE API Gateway endpoint `<cluster-id>.cce.<region>.myhuaweicloud.com`. If that endpoint is not valid for the
current environment, set `CCE_ENDPOINT` or pass `--endpoint`. If plugin/API Gateway access fails, report it as an access gap with the error text; do not fall
back to kubeconfig generation or SDK calls by default.

### 3. Configure kubectl-cce Plugin

Read `references/kubectl-cce.md` before running Kubernetes commands. Use the kubectl CCE plugin as the primary Kubernetes access path; do not generate
kubeconfig, patch kubeconfig server fields, call the Kubernetes SDK, or fall back to SDK dispatcher actions.

If `kubectl` or `kubectl-cce` is missing, use `huawei-cloud-kubectl-cce-installer` to install or repair local prerequisites. This diagnoser verifies and uses
the plugin; it does not own plugin installation policy.

Verify local tooling and plugin discovery:

```bash
kubectl version --client
kubectl plugin list
```

Configure plugin credentials through approved tool parameters, a protected shell environment, or an approved local credential provider without printing values.
Pass cluster, region, and project ID explicitly in diagnostic commands:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

Use `CCE_ENDPOINT` or `--endpoint` only when the default `<cluster-id>.cce.<region>.myhuaweicloud.com` endpoint is not valid for the current environment. If
plugin access fails, report the sanitized installation, credential, API Gateway reachability, or Kubernetes RBAC gap; do not switch to kubeconfig generation or
SDK calls.

The plugin intentionally blocks streaming commands such as `exec`, `attach`, and `port-forward`. `logs -f` and `watch` are not hardened, so use bounded
`logs --tail` and normal `get` commands in diagnosis reports.

### 4. Verify Kubernetes Access

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> cluster-info
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get deployments -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list pods -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list events -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i get pods/log -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i list jobs -n <client-namespace>
```

Check write permissions only when the user has approved a mutating step:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i create jobs -n <client-namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i create services -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i patch services -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i patch ingress -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> auth can-i update deployments/scale -n <namespace>
```

If RBAC denies a read, report the missing verb/resource and continue only with allowed evidence. If RBAC denies a requested mutation, do not work around it with
SDK or direct API calls.

## Pressure Test Workflow

Read `references/workflow.md` before running a test. The standard flow is:

1. Define the target, owner, traffic model, limits, and stop conditions.
2. Configure kubectl-cce plugin credentials and verify Kubernetes access.
3. Run read-only preflight with `kubectl`.
4. Choose traffic mode: local k6 against an external URL, or approved in-cluster k6 Job.
5. Preview every manifest and command that creates, patches, scales, or sends traffic.
6. Run a low-volume smoke test.
7. Run the approved baseline or ramp phase.
8. Collect k6 summary, Job logs, Events, HPA state, Pod metrics, and optional ELB/VPC evidence.
9. Generate the report with summary, findings, root/bottleneck analysis, and next steps first.
10. For elasticity evaluation, compare baseline vs scaled/HPA phases and include data gaps.

## Read-Only Preflight

Start with Kubernetes object and health evidence:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get nodes -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get deploy,sts,ds,svc,endpoints,endpointslice,ingress,hpa,pdb -n <namespace> -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -n <namespace> -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -n <namespace> --sort-by=.lastTimestamp
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top nodes
```

If `kubectl cce ... top` is unavailable, record a metrics gap and do not invent resource trends.

For north-south traffic, inspect known ELB context when identifiers are available:

```bash
hcloud ELB ListLoadBalancers/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListListeners/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
hcloud ELB ListPools/v3 --project_id=<project-id> --cli-region=<region> --cli-output=json
```

Use `hcloud <service> <operation> --help` before adding filters that differ by API version.

## Traffic Generation Modes

### Local k6

Use local k6 when the current runtime can reach `target_url`. This avoids creating Kubernetes resources and is preferred for simple external URL tests.

```bash
k6 run --vus <vus> --duration <duration> <script.js>
```

Record the target URL, Host header, VUs, duration, thresholds, and the exact script path. Do not include credentials or bearer tokens in the script.

### In-Cluster k6 Job

Use an in-cluster Job when the target is cluster-internal or the user's runtime cannot reach the target. This creates Kubernetes resources and sends traffic, so
it requires explicit approval after the manifest is shown.

Read `references/manifest-templates.md` for the ConfigMap and Job template. Apply only after approval:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> apply -f <approved-k6-manifest.yaml>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> wait --for=condition=complete job/<job-name> -n <client-namespace> --timeout=<timeout>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs job/<job-name> -n <client-namespace> --all-containers
```

If the Job fails with `ImagePullBackOff` or `ErrImagePull`, diagnose it with Pod Events and recommend mirroring the k6 image to regional SWR.

## Route And Scaling Changes

Service, Ingress, sample workload, ELB creation, workload scaling, HPA changes, and cleanup are not automatic. Preview the exact YAML or command, explain risk
and rollback, and run it only after explicit user approval in the conversation.

For Kubernetes route manifests, read `references/manifest-templates.md`.

For manual scale elasticity tests, apply only after approval:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> scale deployment/<workload-name> -n <namespace> --replicas=<replicas>
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> rollout status deployment/<workload-name> -n <namespace> --timeout=180s
```

For chargeable ELB creation, use hcloud only after reviewing subnet, AZ, flavor, public/private exposure, and cost impact. Prefer reusing an existing
ingress-controller ELB when possible.

## Analysis And Scenario Guidance

Rank findings by direct evidence and the first failing layer:

1. Target reachability and DNS/TLS/Host header correctness.
2. Kubernetes route: Ingress -> Service -> EndpointSlice -> ready Pods.
3. k6 client health and image pull/log evidence.
4. Application response code, timeout, and latency behavior.
5. Pod CPU/memory/restart/probe/resource pressure.
6. HPA metrics and scale-up timing.
7. Node and cluster capacity.
8. ELB/listener/pool/member health and cloud network constraints.

After identifying the top finding, read `references/scenario-guides.md` and apply the matching scenario. Reports should include concrete next checks and
candidate fixes for every material finding, not just a generic phrase such as "pressure test failed" or "image pull failed".

## Output Format

Use `references/output-schema.md` as the detailed schema. Put decision-critical information first; raw commands and supporting tables come after the conclusion.

The user-facing report should include, in this order:

- Executive summary: test status, confidence, target, traffic phase, and one-line conclusion.
- Root or bottleneck analysis: top findings ranked with direct evidence and plain-language interpretation.
- Recommended next steps: safe immediate checks, candidate fixes, rollback or stop actions, and owner/skill handoff.
- Test scope: region, project, cluster, namespace, workload, URL, traffic model, time window, and approvals.
- Traffic results: requests, RPS, success rate, latency percentiles, thresholds, and k6 errors.
- Route and workload health: Ingress, Service, EndpointSlice, Pods, Events, HPA, metrics.
- Cloud-side evidence when collected: ELB/listener/pool/member/VPC/EIP/NAT context.
- Negative evidence and verification gaps.
- CLI path used: hcloud CCE operations, kubectl commands, k6 command or Job manifest.
- Explicit statement of which mutating or traffic-generating operations were approved and run.

## Safety Rules

Read `references/risk-rules.md` before applying manifests or sending traffic. This skill may run read-only checks and create report content, but it must not
automatically run:

- `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout restart`, or `rollout undo`
- Local `k6 run` or in-cluster k6 Job traffic against a real target
- hcloud create/update/delete operations, including ELB creation
- HPA, nodepool, NAT, security group, or EIP changes
- Any SDK dispatcher action

## Verification

Read `references/verification-method.md` for the CLI verification checklist. A valid implementation should pass these checks:

- `hcloud version`, `hcloud configure list`, `kubectl version --client`, and either `k6 version` or approved in-cluster Job image validation work.
- `hcloud CCE ListClusters`, `ShowCluster`, and `ShowClusterEndpoints` work, and `kubectl cce ...` can reach the cluster through the CCE API Gateway.
- `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id>` can read the target namespace and workload.
- Smoke traffic is run before larger traffic.
- Repository/package search finds no SDK dispatcher entrypoints in this skill package.

## Best Practices

Use a staged traffic plan, verify smoke traffic first, and stop immediately when an approved safety threshold is exceeded.

## Notes

Collected evidence indicates the test environment only and does not prove production capacity without equivalent workload, network, and scaling conditions.

## References

- `references/workflow.md` - staged pressure-test workflow and evidence order.
- `references/manifest-templates.md` - local k6, in-cluster k6 Job, Service, and Ingress templates.
- `references/scenario-guides.md` - scenario-specific analysis and next-step guidance.
- `references/common-pitfalls.md` - pressure-test traps and CLI examples.
- `references/output-schema.md` - Markdown and JSON report structure.
- `references/risk-rules.md` - traffic, mutation, and chargeable-resource boundaries.
- `references/verification-method.md` - environment and CLI verification.
- `references/iam-policies.md` - IAM and Kubernetes RBAC requirements.
- Huawei Cloud KooCLI documentation: https://support.huaweicloud.com/hcli/
- Huawei Cloud CCE documentation: https://support.huaweicloud.com/cce/
- Kubernetes kubectl reference: https://kubernetes.io/docs/reference/kubectl/


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.


## Cluster ID Input

`cluster_id` must use a standard UUID. If the input is not a standard UUID, first list CCE clusters and perform an exact cluster-name match; convert the name to its UUID only when there is one match. If there is no match or more than one match, require the user to provide a UUID. Never guess or arbitrarily select a cluster.
