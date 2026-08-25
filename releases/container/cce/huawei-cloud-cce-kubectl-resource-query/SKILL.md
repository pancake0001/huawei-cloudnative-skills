---
name: huawei-cloud-cce-kubectl-resource-query
description: Query resource information from Huawei Cloud CCE clusters with kubectl cce. Trigger when users ask to get, describe, inspect, or view a specific Kubernetes resource, Pod, workload, Service, ConfigMap, node, or namespace in a CCE cluster.
tags: [CCE, Kubernetes, kubectl-cce, resource-query]
---

# CCE Kubectl Resource Query

Use this skill for read-only Kubernetes resource queries in a Huawei Cloud CCE cluster. Use `kubectl cce`, not direct Kubernetes API clients.

## Prerequisites

- `kubectl` and the `kubectl-cce` plugin are installed. Use `huawei-cloud-kubectl-cce-installer` when installation is required.
- Require `cluster_id` and `region`. `cluster_id` must be a UUID; resolve a user-supplied cluster name with `hcloud CCE ListClusters` before running `kubectl cce`.
- Require `project_id` when AK/SK credentials are used.
- Prefer explicit credentials when supplied: `--cli-access-key`, `--cli-secret-key`, and, for temporary credentials, `--cli-security-token`.

## Parameter Confirmation

Before executing a command, identify all of the following:

| Parameter | Requirement |
|---|---|
| `cluster_id` | Required CCE cluster UUID. |
| `region` | Required target region. |
| Resource kind | Required, for example `pod`, `deployment`, `service`, `configmap`, or `node`. |
| Namespace or resource name | At least one is required. Namespaced resources must use a namespace unless an exact resource name already includes a namespace in the user request. Cluster-scoped resources require an exact resource name. |

## Safety Constraints

1. Read-only commands only: `get`, `describe`, and `logs`.
2. Never use `-A`, `--all-namespaces`, or any equivalent whole-cluster resource query.
3. For namespaced resources, pass `--namespace <namespace>` when listing or querying. Do not list the same resource across all namespaces.
4. For cluster-scoped resources such as `node`, `namespace`, `persistentvolume`, and `storageclass`, require an exact resource name. Do not list all instances of a cluster-scoped resource.
5. Do not run mutation commands such as `apply`, `create`, `delete`, `edit`, `patch`, `replace`, `scale`, `rollout`, `cordon`, `drain`, or `exec`.
6. Do not expose credentials, bearer tokens, Secret data, or kubeconfig contents in command output.

## Core Commands

Set the common arguments once per command:

```bash
kubectl cce \
  --cluster-id <cluster-id> \
  --region <region> \
  --project-id <project-id> \
  --cli-access-key <ak> \
  --cli-secret-key <sk> \
  [--cli-security-token <security-token>]
```

Query a resource in one namespace:

```bash
kubectl cce <common-arguments> get pods --namespace <namespace>
kubectl cce <common-arguments> get pod <pod-name> --namespace <namespace> -o yaml
kubectl cce <common-arguments> describe deployment <deployment-name> --namespace <namespace>
kubectl cce <common-arguments> get service <service-name> --namespace <namespace> -o yaml
kubectl cce <common-arguments> get configmap <configmap-name> --namespace <namespace> -o yaml
```

Query a named cluster-scoped resource:

```bash
kubectl cce <common-arguments> get node <node-name> -o yaml
kubectl cce <common-arguments> describe namespace <namespace-name>
```

If a command returns an `x509` upstream TLS validation error, retry the same command once with `--cce-insecure-upstream-tls=true` immediately after `cce`. Do not add this flag preemptively.

## Output

Return the exact cluster, namespace when applicable, resource kind, resource name, and the requested status or fields. State clearly when a resource is not found or access is denied.
