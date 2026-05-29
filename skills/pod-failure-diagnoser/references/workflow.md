# Workflow

1. 识别 Pod 状态：Running、Pending、Failed、CrashLoopBackOff、ImagePullBackOff、OOMKilled、Evicted。
2. 对 Pending 优先看调度事件、资源不足、亲和性、污点容忍、安全组或 PVC。
3. 对 CrashLoopBackOff 优先看 previous 日志、退出码、探针失败和配置变更。
4. 对 OOMKilled 优先看内存指标、limit/request、突增流量和历史告警。
5. 对 ImagePullBackOff 优先看镜像地址、密钥、网络、仓库权限。
6. 将 Events、Logs、Metrics 按时间线合并，给出 Top3 可能原因。
7. 需要动作时只输出建议，不自动执行。

