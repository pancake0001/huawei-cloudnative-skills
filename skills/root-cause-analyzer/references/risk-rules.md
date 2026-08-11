# Risk Rules

- 只允许只读发现、诊断、指标/日志/事件查询和报告生成。
- 不执行扩缩容、删除、patch、重启、drain、reboot、EIP 绑定/解绑、路由变更、安全组变更、NetworkPolicy/RBAC 修改、集群休眠/唤醒等动作。
- 不使用 Python SDK dispatcher、`scripts/huawei-cloud.py`、`skill action=exec`、`huawei_*` action、kubeconfig 生成、手写 IAM/API 或 Huawei Cloud SDK import。
- Kubernetes 证据使用 `kubectl cce`，云侧只读证据使用 `hcloud`；失败时写成脱敏数据缺口并降低置信度。
- 可观测上下文包是一轮证据输入；高风险或互相矛盾的发现必须复核后才能给高置信度根因。
- 不凭单一告警或孤立对象更新直接下根因结论，必须有时间线或证据链。
- 不暴露 AK/SK、token、kubeconfig、Authorization header、镜像仓库密钥、业务 Secret 或 kubectl-cce 凭据材料。
