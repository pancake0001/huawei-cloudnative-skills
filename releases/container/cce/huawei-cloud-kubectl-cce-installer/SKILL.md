---
name: huawei-cloud-kubectl-cce-installer
description: >
  Query specific Kubernetes resources in Huawei Cloud CCE clusters through kubectl cce. Trigger when users ask to get, describe, inspect, or view a Pod,
  workload, Service, ConfigMap, node, namespace, or other CCE Kubernetes resource, or when they ask to install or repair the local kubectl-cce
  prerequisites. Install kubectl and kubectl-cce only when they are missing locally.
tags: [kubectl, kubectl-cce, cce, huawei-cloud, kubernetes, resource-query]
---

# Huawei Cloud CCE Kubectl Resource Query

Use this skill to retrieve specific CCE Kubernetes resources through `kubectl cce`. Resource access is the primary task. Local installation is only a
prerequisite recovery step when `kubectl` or the `kubectl-cce` plugin is unavailable.

## Scope And Safety

- Use `kubectl cce`; do not use a direct Kubernetes API client.
- Read-only commands only: `get`, `describe`, and `logs`.
- Never use `-A`, `--all-namespaces`, or another whole-cluster resource query.
- For namespaced resources, require `--namespace <namespace>` and, where feasible, a specific resource name.
- For cluster-scoped resources such as `node`, `namespace`, `persistentvolume`, and `storageclass`, require an exact resource name. Do not list every
  instance.
- Never run `apply`, `create`, `delete`, `edit`, `patch`, `replace`, `scale`, `rollout`, `cordon`, `drain`, or `exec`.
- Do not print credentials, tokens, kubeconfig content, or Secret data.

## Required Context

| Input | Requirement |
| --- | --- |
| `cluster_id` | Required standard UUID. If the user gives a name, resolve it with `hcloud CCE ListClusters` before running kubectl. |
| `region` | Required. Use an explicit value, then `HW_REGION_NAME`; otherwise ask the user. |
| Resource kind | Required, for example `pod`, `deployment`, `service`, `configmap`, or `node`. |
| Namespace or exact name | At least one is required. Namespaced resources require a namespace; cluster-scoped resources require an exact name. |

Credentials follow the plugin rules in [plugin-usage.md](references/plugin-usage.md). Use explicit `--cli-access-key`, `--cli-secret-key`, and optional
`--cli-security-token` only when the caller supplies them. Do not fall back to other credentials in that case.

## Workflow

1. Confirm the target cluster UUID, region, resource kind, namespace, and exact resource name when required.
2. Check local prerequisites:

   ```bash
   bash scripts/install_kubectl_cce.sh --check
   ```

3. When both `kubectl` and `kubectl-cce` are available, query the requested resource.
4. When either executable is missing, show the installer plan. Installation or replacement is an R1 local change and requires explicit confirmation:

   ```bash
   bash scripts/install_kubectl_cce.sh --bin-dir <directory>
   sudo bash scripts/install_kubectl_cce.sh --execute --bin-dir <directory>
   ```

5. Verify installation with `kubectl version --client` and `kubectl plugin list`, then run only the requested read-only resource query.

## Core Commands

Use one explicit namespace per namespaced query:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> \
  get pod <pod-name> --namespace <namespace> -o yaml

kubectl cce --cluster-id <cluster-id> --region <region> \
  describe deployment <deployment-name> --namespace <namespace>

kubectl cce --cluster-id <cluster-id> --region <region> \
  get service <service-name> --namespace <namespace> -o yaml
```

For a cluster-scoped resource, use an exact name:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> \
  get node <node-name> -o yaml
```

For credential modes, Windows usage, installation fallbacks, and x509 retry behavior, read [plugin-usage.md](references/plugin-usage.md). If a command fails
with an x509 upstream TLS validation error, retry that same command once with `--cce-insecure-upstream-tls=true` immediately after `cce`.

## Risk Levels

| Operation | Level | Guidance |
| --- | --- | --- |
| Resource query and local prerequisite check | R3 | May run automatically. |
| Local binary installation, source build, or plugin replacement | R1 | Preview first and require explicit confirmation before `--execute`. |

## Output

Return the cluster ID, region, resource kind, namespace when applicable, resource name, and requested status or fields. State clearly whether the resource is
not found, access is denied, prerequisites are missing, or an installation confirmation is needed.

## References

| Document | Use |
| --- | --- |
| [Plugin Usage](references/plugin-usage.md) | Credentials, command forms, x509 retry, Windows installation, and installer fallback. |
| [Acceptance Criteria](references/acceptance-criteria.md) | Resource-query and installation acceptance checks. |
