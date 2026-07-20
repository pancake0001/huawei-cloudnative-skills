# kubectl-cce Plugin Usage

## Release Source

Use the [Gitee `pancake0001/kubectl-cce-plugin` Release `v0.1.0`](https://gitee.com/pancake0001/kubectl-cce-plugin/releases/tag/v0.1.0) when an asset exists. Its published assets support Linux and Windows amd64/arm64; it does not publish a macOS asset. The installer falls back to building the fixed `v0.1.0` source tag with Go when the asset is unavailable or its download fails.

## Plugin Credentials

The plugin obtains CCE access credentials from tool-provided values or environment variables. Never print these values.

```bash
export HW_ACCESS_KEY="<your-ak>"
export HW_SECRET_KEY="<your-sk>"
export HW_PROJECT_ID="<your-project-id>"
export HW_REGION="cn-north-4"
```

For temporary credentials, set `HW_SECURITY_TOKEN` as well.

## Read-only Test

Use a specific cluster ID and a read-only request:

```bash
kubectl cce --cluster-id <cluster-id> --region cn-north-4 get namespaces
```

Do not run write operations during installation verification.

## Windows Installation

Download the matching v0.1.0 ZIP asset, extract `kubectl-cce.exe`, place it in a directory on `PATH`, then verify:

```powershell
kubectl plugin list
```
