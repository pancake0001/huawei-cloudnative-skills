# kubectl-cce Usage

`huawei_get_cce_events` uses `kubectl` to read Events. It first uses a temporary kubeconfig through the cluster external endpoint. When no external endpoint is available, it falls back to the `kubectl cce` plugin.

## Install

Install `kubectl` with the system package manager and verify it:

```bash
kubectl version --client
```

Install `kubectl-cce` v0.1.0 from the GitHub release that matches the local OS and architecture:

```bash
curl -LO https://github.com/pancake0001/kubectl-cce-plugin/releases/download/v0.1.0/kubectl-cce_0.1.0_linux_amd64.tar.gz
tar -xzf kubectl-cce_0.1.0_linux_amd64.tar.gz
chmod +x kubectl-cce && mv kubectl-cce /usr/local/bin/
kubectl plugin list
```

The executable must be named `kubectl-cce` so that kubectl discovers it as `kubectl cce`.

## Plugin Credentials

The plugin requires AK/SK as tool parameters or environment variables. For temporary credentials, also provide a security token.

```bash
export HW_ACCESS_KEY="<your-ak>"
export HW_SECRET_KEY="<your-sk>"
export HW_PROJECT_ID="<your-project-id>"
export HW_REGION="cn-north-4"
export HW_SECURITY_TOKEN="<your-security-token>"
```

## Example

```bash
kubectl cce --cluster-id <cluster-id> --region cn-north-4 get events -A
```
