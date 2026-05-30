# Risk Rules

- 允许自动执行只读诊断动作。
- 禁止在本 skill 中调用扩缩容、删除工作负载、删除节点、drain、reboot。
- 如建议 `huawei_scale_cce_workload` 或 `huawei_resize_cce_workload`，必须转交 `auto-remediation-runner`。
- 日志只能输出经过脱敏的尾部片段；不要把应用日志中的疑似密码、token、AK/SK、Authorization 原文复制到输出。
- ImagePullBackOff 优先看 Events，不反复请求不存在的容器日志。
- 对 OOMKilled、PendingScheduling、Evicted 给出的扩容、隔离、删除重建等建议只能是恢复预案，不在本 skill 执行。
