# Risk Rules

- 允许自动执行只读诊断动作。
- 禁止在本 skill 中调用扩缩容、删除工作负载、删除节点、drain、reboot。
- 如建议 `huawei_scale_cce_workload` 或 `huawei_resize_cce_workload`，必须转交 `auto-remediation-runner`。
- 不把应用日志中的疑似密钥原文复制到输出。

