# kubectl-cce Usage

Use `kubectl cce` as the primary Kubernetes access path. Do not generate kubeconfig, patch kubeconfig server fields, call the Kubernetes SDK, or fall back to
SDK dispatcher actions for Kubernetes evidence.

## Install

Use `huawei-cloud-kubectl-cce-installer` when `kubectl` or `kubectl-cce` is missing. That skill owns local installation planning, release selection,
source-build fallback, and plugin discovery checks.

For manual verification:

```bash
kubectl version --client
kubectl plugin list
```

On Windows, use `kubectl.exe` and a Windows `kubectl-cce` executable on `PATH`. On Linux sandboxes, use Linux-compatible binaries. If multiple kubectl binaries
exist, set or document `KUBECTL_BIN` and verify the selected binary.

## Credentials

The plugin needs Huawei Cloud credentials plus the target project ID. Configure credentials through an approved local provider, protected environment, or
tool-provided values. Do not print AK/SK, security tokens, Authorization headers, kubeconfig content, or plugin credential material.

For environment-variable mode, use the published plugin contract: `HW_ACCESS_KEY`/`HW_SECRET_KEY`, optional `HW_SECURITY_TOKEN`, and
`HW_PROJECT_ID`/`HW_REGION`. In a sandboxed or agent runtime, pass `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token` per
invocation. Commands should always prefer explicit `--region <region>` and `--project-id <project-id>`.

Always pass `--project-id <project-id>` when available instead of relying on implicit discovery.

## Use

Always pass cluster, region, and project explicitly:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

For CCE API Gateway endpoint issues, first record the sanitized error. Use `CCE_ENDPOINT` or a documented plugin endpoint option only when the default endpoint
is invalid for the region or runtime network.

## Limits

- Prefer read-only `get`, `describe`, `top`, and bounded `logs` commands.
- Do not run mutating commands from diagnosis skills.
- Do not use interactive or streaming commands such as `exec`, `attach`, `port-forward`, or unbounded `logs -f`.
- Keep log reads bounded with `--tail` or a time window.

## Failure Handling

When plugin access fails, report:

1. Whether `kubectl plugin list` discovered `kubectl-cce`.
2. Cluster ID, region, and project ID used.
3. Endpoint override status if any.
4. Sanitized error message.
5. Whether the failure is likely missing binary, incompatible OS/arch, missing credentials, missing project ID, endpoint reachability, cluster state, or RBAC.

Do not bypass the plugin by generating kubeconfig or switching to SDK calls.


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.
