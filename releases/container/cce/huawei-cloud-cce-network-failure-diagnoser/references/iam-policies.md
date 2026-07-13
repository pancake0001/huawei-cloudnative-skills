# IAM And RBAC Requirements

## Huawei Cloud IAM

Minimum cloud permissions for the base workflow:

| Service | Purpose |
| --- | --- |
| CCE cluster list/show | Locate and validate the target cluster |
| CCE cluster certificate creation | Generate short-lived kubeconfig for kubectl |

Optional cloud network read permissions:

| Service | Purpose |
| --- | --- |
| ELB list/show | Load balancer, listener, pool, member, and health monitor evidence |
| VPC list/show | VPC, subnet, security group, security group rule, and ACL evidence |
| EIP list/show | Public IP binding and status evidence |
| NAT list/show | NAT gateway and SNAT/DNAT evidence |

No cloud write permissions are required by this skill.

## Kubernetes RBAC

Minimum Kubernetes read permissions:

| Resource | Verbs | Purpose |
| --- | --- | --- |
| `nodes` | get, list | Node and CNI base-layer health |
| `services` | get, list | Service routing configuration |
| `endpoints` | get, list | Legacy backend endpoint state |
| `endpointslices.discovery.k8s.io` | get, list | Backend readiness and address mapping |
| `ingresses.networking.k8s.io` | get, list | Ingress routing |
| `networkpolicies.networking.k8s.io` | get, list | Policy allow/deny evidence |
| `pods` | get, list | Backend readiness, labels, and placement |
| `events` | get, list | Timeline and controller/kubelet evidence |
| `pods/log` | get | Controller/CoreDNS/backend logs when needed |

If a permission is missing, report it as a verification gap and continue with allowed evidence.
