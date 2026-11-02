# CLI Installation

The skill requires `hcloud`, `kubectl`, and the `kubectl-cce` plugin. Install or repair `kubectl` and `kubectl-cce` with the
`huawei-cloud-kubectl-cce-installer` skill. Confirm availability before diagnosis:

```bash
hcloud version
kubectl version --client
kubectl plugin list
```

The diagnoser does not download or alter local CLI installations.
