# CCE Pressure-Test Risk Rules

Pressure tests can change cluster state, create billable resources, and affect real traffic. Treat safety boundaries as part of the test design.

## R0 Read-Only And Planning

These actions may run without additional approval after credentials and target are known:

- `hcloud version`, `hcloud configure list`, and `kubectl version --client`.
- `hcloud CCE ListClusters`, `ShowCluster`, and `ShowClusterEndpoints`; Kubernetes evidence uses `kubectl cce ...`.
- `kubectl cce ... get`, `describe`, `logs`, `top`, and `auth can-i` read-only checks.
- Read-only hcloud ELB/VPC/EIP/NAT list operations.
- Generate local scripts, YAML manifests, runbooks, and reports.

Still redact credentials, tokens, certificates, registry secrets, and application secrets.

## R1 Local Or Manifest Preparation

These are low risk but must be shown to the user:

- Create a local k6 script.
- Create a local Kubernetes YAML manifest file.
- Prepare route, Job, ConfigMap, sample workload, or cleanup manifests.
- Prepare report artifacts.

Do not apply manifests or send traffic in R1.

## R2 Approved Traffic Or Kubernetes Mutation

These require explicit user approval in the conversation:

- Run local `k6 run` against a real target.
- Apply an in-cluster k6 ConfigMap or Job.
- Create or patch Service or Ingress for the test route.
- Create a sample workload for a lab test.
- Scale a workload for an elasticity phase.
- Delete test Jobs or ConfigMaps.

Before approval, show:

- Exact command or YAML.
- Target namespace and resource names.
- Traffic model, VUs, duration, RPS cap, and thresholds.
- Expected impact and stop conditions.
- Rollback or cleanup command.

## R3 High-Risk Or Billable Changes

These require extra confirmation and should be avoided unless necessary:

- Create, update, or delete ELB, EIP, NAT, security group, or VPC resources.
- Modify HPA behavior, workload resource requests/limits, nodepool size, or cluster autoscaler settings.
- Run high-volume traffic against production or customer-facing targets.
- Use short-connection mode at high VU counts, which can amplify connection churn.
- Run tests without an approved time window or owner.

Show cost impact, blast radius, rollback, and validation checks before executing any R3 command.

## Stop Conditions

Stop the test or avoid escalation when any of these occur:

- Smoke test fails.
- Success rate falls below the agreed threshold.
- 5xx, timeout, or connection errors rise sharply.
- p95 or p99 latency exceeds the agreed limit.
- Pods restart, become NotReady, or enter CrashLoopBackOff/ImagePullBackOff.
- HPA cannot read metrics while the test depends on autoscaling.
- CPU, memory, or node capacity reaches the agreed waterline.
- The target, Host header, namespace, or route mapping is uncertain.

## Prohibited Defaults

Do not run these by default:

- `kubectl cce ... apply`, `create`, `patch`, `edit`, `delete`, `scale`, `rollout restart`, or `rollout undo`.
- Any local or in-cluster k6 traffic against a real target.
- hcloud create/update/delete operations.
- Python SDK dispatcher actions, direct IAM/API calls, or handwritten cloud API calls.
- Commands that print AK/SK, kubectl-cce proxy credentials, Authorization headers, or secrets.

## Cleanup Rules

Cleanup is a mutation and must be approved. Only delete resources that were created for this test and are named in the report. Never automatically delete:

- User workloads.
- Existing Services or Ingresses.
- ELB, EIP, NAT, security groups, or VPC resources.
- Namespaces that may contain resources not created by the test.
