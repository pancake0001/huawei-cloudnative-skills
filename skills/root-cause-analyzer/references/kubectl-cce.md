# kubectl-cce Usage

Use `kubectl cce` as the primary Kubernetes access path. Do not generate kubeconfig, patch kubeconfig server fields, call the Kubernetes SDK, or fall back to SDK dispatcher actions for Kubernetes evidence.

## Install

Use `huawei-cloud-kubectl-cce-installer` when `kubectl` or `kubectl-cce` is missing. Verify:

```bash
kubectl version --client
kubectl plugin list
```

Windows uses `kubectl.exe` and a Windows `kubectl-cce` executable. Linux sandboxes require Linux-compatible binaries.

## Use

Always pass cluster, region, and project explicitly:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get namespaces
```

Do not print AK/SK, security tokens, Authorization headers, kubeconfig content, or plugin credential material. Keep commands read-only and bounded.
