# Risk Rules

- 允许自动执行 R1 只读查询：节点、Pod、Deployment、StatefulSet、DaemonSet、Service、Ingress、PDB、ReplicaSet、节点指标和报告生成。
- 禁止 scanner 自动修改副本数、PDB、探针、亲和性、拓扑分散、request/limit、节点池、master 或插件配置。
- 任何真实整改都必须由客户明确授权，并说明影响范围、回滚方式和验证指标。
- `kube-system` 普通工作负载默认不作为业务风险处理，但 CoreDNS、nginx-ingress、ingress-nginx 等核心插件需要检查反亲和和分布风险。
- 托管控制面 master 不可见时，不得臆测 master 高可用；必须标记数据缺口并建议到 CCE 控制台/API 复核。
- 单副本、有状态服务、网关服务的整改要先确认业务可多副本运行、会话保持、存储绑定和流量入口策略。
- 修改健康检查前必须确认探测路径、端口、超时、初始延迟和失败阈值，避免错误探针导致批量重启。
- 修改亲和性或拓扑分散前必须确认节点池容量、AZ 资源、存储 AZ 绑定、污点和容忍配置。
