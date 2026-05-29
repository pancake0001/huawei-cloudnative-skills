# Risk Rules

- 巡检只允许 R1 只读动作。
- 不允许自动扩容、删除、drain、reboot、休眠、唤醒。
- 自动巡检报告不得包含 AK/SK、token、证书、完整 kubeconfig。
- 异常项只输出建议，恢复动作必须另行确认。

