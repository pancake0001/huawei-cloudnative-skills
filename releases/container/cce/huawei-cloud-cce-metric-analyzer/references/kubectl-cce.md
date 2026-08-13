# kubectl-cce Usage

Use `kubectl cce` only when the metric analyzer must read Kubernetes resources that AOM and hcloud cannot derive, such as Pod label filtering, Ingress TLS Secrets, or LoadBalancer Services. Do not generate kubeconfig, patch kubeconfig server fields, call the Kubernetes SDK, or fall back to SDK dispatcher actions for Kubernetes evidence.

## Install

Use `huawei-cloud-kubectl-cce-installer` when `kubectl` or `kubectl-cce` is missing. Verify:

```bash
kubectl version --client
kubectl plugin list
```

Windows uses `kubectl.exe` and a Windows `kubectl-cce` executable. Linux sandboxes require Linux-compatible binaries.

## Credentials

Configure plugin credentials through an approved local provider, protected environment, or tool-provided values. Do not print AK/SK, security tokens, Authorization headers, kubeconfig content, or plugin credential material.

Always pass `--project-id <project-id>` when available.

## Use

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get svc,ingress -A
```

Keep Kubernetes reads read-only and bounded. If plugin access fails, report a metric relationship data gap instead of bypassing the plugin.
