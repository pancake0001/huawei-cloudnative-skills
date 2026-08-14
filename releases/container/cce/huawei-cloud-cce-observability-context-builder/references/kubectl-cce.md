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

Common non-secret context variables include `HW_REGION`, `HUAWEI_REGION`, `HW_PROJECT_ID`, `HUAWEI_PROJECT_ID`, and `CCE_PROJECT_ID`. Credential aliases may
include `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK`, `HW_ACCESS_KEY`/`HW_SECRET_KEY`, and temporary-token variables such as
`HUAWEICLOUD_SECURITY_TOKEN` or `HUAWEI_IAM_TOKEN`.

## Command Pattern

Always pass cluster, region, and project explicitly:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
```

Prefer bounded read-only commands:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
```

Do not use `exec`, `attach`, `port-forward`, `logs -f`, `watch`, or mutation commands.
