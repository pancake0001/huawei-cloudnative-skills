# kubectl-cce Usage

Use `kubectl cce` as the primary Kubernetes access path. Do not generate kubeconfig, patch kubeconfig server fields, call the Kubernetes SDK, or fall back to SDK dispatcher actions for Kubernetes evidence.

## Install

Use `huawei-cloud-kubectl-cce-installer` when `kubectl` or `kubectl-cce` is missing. That skill owns local installation planning, release selection, source-build fallback, and plugin discovery checks.

For manual verification:

```bash
kubectl version --client
kubectl plugin list
```

On Windows, use `kubectl.exe` and a Windows `kubectl-cce` executable on `PATH`. On Linux sandboxes, use Linux-compatible binaries. If multiple kubectl binaries exist, set or document `KUBECTL_BIN` and verify the selected binary.

## Credentials

The plugin needs Huawei Cloud credentials plus the target project ID. Configure credentials through an approved local provider, protected environment, or tool-provided values. Do not print AK/SK, security tokens, Authorization headers, kubeconfig content, or plugin credential material.

Always pass `--project-id <project-id>` when available instead of relying on implicit discovery.

## Use

Always pass cluster, region, and project explicitly:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
```

For CCE API Gateway endpoint issues, record the sanitized error and use an endpoint override only when the default endpoint is invalid for the region or runtime network.

## Limits

- Prefer read-only `get` and bounded query commands.
- Do not run mutating commands.
- Do not use interactive or streaming commands.

Do not bypass the plugin by generating kubeconfig or switching to SDK calls.
