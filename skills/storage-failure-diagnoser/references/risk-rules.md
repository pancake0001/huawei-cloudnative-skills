# Risk Rules

- 允许自动执行 PVC、PV、StorageClass、Pod、Node、Event、VolumeAttachment、NetworkPolicy、Kubelet `/stats/summary`、Everest CSI 日志、EVS/SFS/SFS Turbo、安全组和 VPC ACL 的只读查询。
- 允许生成 Markdown 诊断报告、只读验证命令建议和恢复预案。
- 不删除 PVC/PV/Pod，不 patch finalizer，不强制 detach/attach EVS，不修改 StorageClass、StorageClass 参数、PV reclaim policy、IAM 委托、AK/SK Secret、安全组、ACL 或 VPC 路由。
- 不执行 `kubectl exec`、节点 SSH、抓包、压测、fsck、dmesg 采集或主动 NFS/OBS 读写探测，除非用户明确要求并确认风险。
- 任何会改变数据面或控制面的动作必须转交 `auto-remediation-runner`，并先输出影响范围、回滚方式、数据一致性风险和验证标准。
- PVC Terminating 时不要直接建议移除 `kubernetes.io/pvc-protection` finalizer；必须先证明没有 Pod 引用和业务数据风险。
- EVS 残留挂载或只读文件系统场景下，不建议在未确认文件系统一致性前做强制卸载、强制挂载或直接重启数据库类工作负载。
