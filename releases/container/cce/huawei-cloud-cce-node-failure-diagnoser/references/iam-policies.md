# IAM And RBAC Requirements

## Huawei Cloud IAM

Minimum cloud permissions for this CLI workflow:

| Service | Purpose |
| --- | --- |
| CCE cluster list/show | Locate and validate the target cluster |
| CCE node list/show | Correlate CCE node metadata when needed |
| CCE cluster certificate creation | Generate short-lived kubeconfig for kubectl |

The skill does not require AOM, HSS, ECS write, VPC write, or CCE mutation permissions.

## Kubernetes RBAC

Minimum Kubernetes read permissions:

| Resource | Verbs | Purpose |
| --- | --- | --- |
| `nodes` | get, list | Node status, conditions, capacity |
| `leases` in `kube-node-lease` | get, list | Node heartbeat freshness |
| `events` | get, list | Node and workload event timeline |
| `pods` | get, list | Workload impact on the node |
| `pods/log` | get | Logs for affected Pods when needed |
| `metrics.k8s.io` | get, list | Optional `kubectl top` evidence |

If a permission is missing, report it as a verification gap and continue with allowed evidence.
