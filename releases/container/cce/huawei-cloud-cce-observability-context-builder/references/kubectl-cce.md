# kubectl-cce Usage

Use the `kubectl cce` plugin as the only Kubernetes access path for this skill. Do not generate or patch kubeconfig, call the Kubernetes SDK, or fall back to
SDK dispatcher actions.

## Setup

Use `huawei-cloud-kubectl-cce-installer` when `kubectl` or `kubectl-cce` is missing. Verify:

```bash
kubectl version --client
kubectl plugin list
```

The executable must be named `kubectl-cce` so kubectl discovers it as `kubectl cce`. Windows uses `kubectl-cce.exe`; Linux sandboxes require Linux-compatible
binaries. If kubectl is not in `PATH`, set `KUBECTL_BIN` to the platform-native path.

## Credentials

Configure credentials through an approved local provider, protected environment, or tool-provided values. Do not print AK/SK, security tokens, Authorization
headers, kubeconfig content, or plugin credential material.

For environment-variable mode, use the published plugin contract: `HW_ACCESS_KEY`/`HW_SECRET_KEY`, optional `HW_SECURITY_TOKEN`, and
`HW_PROJECT_ID`/`HW_REGION`. In a sandboxed or agent runtime, pass `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token` per
invocation. Commands should always prefer explicit `--region <region>` and `--project-id <project-id>`.

## Command Pattern

Always pass cluster, region, and project explicitly:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
```

Prefer bounded read-only commands:

```bash
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
```

Do not use `exec`, `attach`, `port-forward`, `logs -f`, `watch`, or mutation commands.


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.
