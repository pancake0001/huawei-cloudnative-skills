# kubectl-cce Plugin Usage

## Release Source

Use the [Gitee `pancake0001/kubectl-cce-plugin` Release `v0.2.1`](https://gitee.com/pancake0001/kubectl-cce-plugin/releases/tag/v0.2.1) when an asset exists.
Its published assets support Linux and Windows amd64/arm64; it does not publish a macOS asset. The installer falls back to building the fixed `v0.2.1` source
tag with Go when the asset is unavailable or its download fails.

## Credential Options

The plugin accepts two credential modes. Name the mechanism **names** below (public plugin docs); never show, print, log, or persist credential **values**.

### Mode 1 — Environment variables (default; ordinary interactive environments)

For users whose environment cannot inject CLI args. The plugin reads credentials from the process environment. Set them through an approved local credential
provider (protected shell rc, systemd environment file, or secrets manager) before invoking the plugin:

- `HW_ACCESS_KEY` / `HW_SECRET_KEY` — permanent AK/SK
- `HW_SECURITY_TOKEN` — required when using temporary AK/SK
- `HW_PROJECT_ID` / `HW_REGION` — target project and region

### Mode 2 — CLI flags (v0.2.1+; sandboxed/agent runtimes)

For trusted sandbox/agent runtimes that inject credentials per invocation and control process visibility. Pass:

- `--cli-access-key <ak>` / `--cli-secret-key <sk>`
- `--cli-security-token <token>` — for temporary credentials

> ⚠️ Do **not** use Mode 2 in ordinary multi-user environments: CLI args are visible in `ps aux` and leak credentials. Prefer Mode 1 there. Mode 2 is safe only
> where the runtime controls process visibility (sandbox).

## Read-only Test

```bash
# Mode 1 (env vars)
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region "${HW_REGION}" get namespaces

# Mode 2 (runtime injection — runtime supplies the real values; never log them)
kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> --region <region> \
  --cli-access-key <access-key> --cli-secret-key <secret-key> \
  [--cli-security-token <token>] get namespaces
```

Do not run write operations during installation verification.

## Windows Installation

Do not run `install_kubectl_cce.sh` on Windows. Download the matching Windows `kubectl.exe` from the
[official Kubernetes release site](https://kubernetes.io/releases/download/), then download the matching `kubectl-cce` v0.2.1 ZIP asset from the
[Gitee Release](https://gitee.com/pancake0001/kubectl-cce-plugin/releases/tag/v0.2.1). Extract both executables, place them in a user-selected directory on
`PATH`, then verify:

```powershell
kubectl plugin list
```


## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.
