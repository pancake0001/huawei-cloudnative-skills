# Workflow

1. 确认节点是否 Ready、是否存在 MemoryPressure、DiskPressure、PIDPressure、NetworkUnavailable。
2. 查看节点事件和 NPD 类事件，区分系统盘、容器运行时、kubelet、网络插件问题。
3. 查询节点 CPU、内存、磁盘、网络指标，找出高峰和持续时间。
4. 关联节点上的 Pod，判断是节点问题还是单个工作负载导致。
5. 涉及 NotReady 时核对安全组、网络 ACL、Master-Node 通信和节点 IP。
6. 涉及漏洞时查询 HSS 清单，区分需要重启生效的内核类漏洞。
7. 输出影响面、根因候选和验证步骤。

