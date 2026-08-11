# kubectl-cce Usage

使用 `kubectl cce` 作为唯一 Kubernetes 访问路径。不要生成 kubeconfig，不要 patch kubeconfig server，不要调用 Kubernetes SDK，也不要回退到旧 dispatcher action。

## 检查

```bash
kubectl version --client
kubectl plugin list
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get ns
```

Windows 使用 `kubectl.exe` 和 Windows 版 `kubectl-cce`；Linux sandbox 需要 Linux 兼容二进制。如果真实 kubectl 不在 `PATH`，设置 `KUBECTL_BIN`。

## 命令模式

必须显式传入集群、区域和项目：

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get pods -A -o wide
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events -A --sort-by=.lastTimestamp
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs <pod-name> -n <namespace> --all-containers --tail=200
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> top pods -n <namespace>
```

不要使用 `exec`、`attach`、`port-forward`、`logs -f`、`watch` 或变更命令。
