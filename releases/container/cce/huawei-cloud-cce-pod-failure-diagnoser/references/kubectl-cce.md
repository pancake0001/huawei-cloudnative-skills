# kubectl-cce Usage

This skill uses the `kubectl cce` plugin as the primary Kubernetes access path. Do not generate kubeconfig, patch kubeconfig server fields, call the Kubernetes
SDK, or fall back to SDK dispatcher actions for Kubernetes evidence.

## Install

Use `huawei-cloud-kubectl-cce-installer` when `kubectl` or `kubectl-cce` is missing. That skill owns local installation planning, release selection,
source-build fallback, and plugin discovery checks.

For manual setup, install a platform-native `kubectl`, install or build a platform-native `kubectl-cce`, and verify plugin discovery:

```bash
kubectl version --client
kubectl plugin list
```

The executable must be named `kubectl-cce` so kubectl discovers it as `kubectl cce`. On Windows the executable is usually `kubectl-cce.exe`. If the real kubectl
binary is not in `PATH`, set `KUBECTL_BIN` to the platform-native kubectl path before invoking the plugin.

## Credentials

The plugin requires AK/SK or an IAM token plus the target project ID. Configure credentials through approved tool parameters, a protected shell environment, or
an approved local credential provider. Do not print credential values, tokens, Authorization headers, or proxy details.

Supported credential names depend on the plugin version; common aliases include:

- AK/SK: `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK`, `HW_ACCESS_KEY`/`HW_SECRET_KEY`, or equivalent plugin-supported aliases.
- Temporary AK/SK: include the matching security token such as `HUAWEICLOUD_SECURITY_TOKEN`.
- Project ID: pass `--project-id <project-id>` explicitly; environment aliases such as `CCE_PROJECT_ID` or `HW_PROJECT_ID` may be used only when already
  configured.

## Use

Always pass cluster, region, and project ID explicitly in diagnostic examples:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

Use the default CCE API Gateway endpoint first. Set `CCE_ENDPOINT` or pass `--endpoint` only when `<cluster-id>.cce.<region>.myhuaweicloud.com` is not valid for
the current environment.

## Limits

The plugin intentionally blocks streaming commands such as `exec`, `attach`, and `port-forward`. `logs -f` and `watch` are not hardened. Use bounded
`logs --tail` and ordinary `get`/`describe` commands for reports.

## Failure Handling

If plugin access fails, report:

- whether `kubectl plugin list` discovers `kubectl-cce`;
- the cluster ID, region, and project ID used, without secrets;
- whether a custom `CCE_ENDPOINT` or `--endpoint` was used;
- the sanitized error text;
- whether the gap is plugin installation, credential, API Gateway reachability, or Kubernetes RBAC.

Do not switch to kubeconfig generation or SDK calls to bypass the failure.
