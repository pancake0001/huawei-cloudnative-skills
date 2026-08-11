# Risk Rules

- 只读：允许查询、汇总、报告，不允许变更。
- 云侧上下文使用 `hcloud`。
- Kubernetes 上下文使用 `kubectl cce`。
- 不使用 Huawei Cloud SDK、Kubernetes SDK、kubeconfig 生成、旧 dispatcher action、手写 IAM/curl。
- 禁止 `apply`、`create`、`patch`、`edit`、`delete`、`scale`、`rollout restart`、`rollout undo`、`cordon`、`drain`、云侧绑定/解绑、休眠、唤醒、启停、重启。
- 禁止 `exec`、`attach`、`port-forward`、`logs -f`、`watch`。
- 日志必须有界，优先 `--tail=200` 和明确 Pod/container 范围。
- 日志命中疑似密钥时只报告位置并脱敏，不复制原值。
- 缺少 AOM/LTS/Metrics API/RBAC/日志源时写入数据缺口，不把“没查到”当作健康。
