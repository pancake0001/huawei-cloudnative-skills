# CCE Pressure-Test IAM And RBAC Requirements

Use least privilege. Pressure testing should not require broad admin credentials unless the user explicitly asks to create or modify infrastructure.

## Huawei Cloud IAM

Minimum cloud-side permissions:

- CCE cluster list/show.
- CCE cluster endpoint show.
- CCE kubectl-cce API Gateway access.

Optional read-only permissions for north-south checks:

- ELB load balancer/listener/pool/member/health-monitor list.
- VPC subnet/security group/security group rule list.
- EIP public IP list.
- NAT gateway list.

Optional high-risk permissions, only when explicitly approved:

- ELB create/update/delete.
- EIP bind/unbind.
- NAT/security group/VPC updates.
- CCE nodepool or cluster autoscaler changes.

Do not request write permissions when the task is only to run local k6 against an existing URL.

## Kubernetes RBAC

Read-only preflight usually needs:

```text
get/list/watch nodes
get/list/watch deployments,statefulsets,daemonsets,replicasets
get/list/watch pods,pods/log
get/list/watch services,endpoints,endpointslices
get/list/watch ingresses
get/list/watch horizontalpodautoscalers
get/list/watch poddisruptionbudgets
get/list/watch events
get/list/watch jobs
get/list/watch configmaps
```

Metrics require access to `metrics.k8s.io` resources when metrics-server is installed.

Approved in-cluster k6 Job mode may need:

```text
create/update/patch/delete jobs
create/update/patch/delete configmaps
create/get/list namespaces only if a dedicated client namespace is created
```

Approved route preparation may need:

```text
create/update/patch services
create/update/patch ingresses
```

Approved elasticity tests may need:

```text
update deployments/scale
get/watch deployments
```

## Handling Permission Errors

When a command is denied:

1. Quote the denied verb/resource/scope from the error.
2. Continue with other allowed evidence.
3. Add the missing permission to data gaps.
4. Do not switch to SDK, direct API calls, or admin credentials without user approval.

Never print credentials, kubectl-cce proxy credentials, or tokens while troubleshooting permissions.
