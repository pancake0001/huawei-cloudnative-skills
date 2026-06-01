# Skill Index

`skills/_catalog` 是人工查找用的总目录，不是可触发 Skill。Agent 通过各 Skill 的 `SKILL.md` 中的 `description` 自动匹配能力。

当前展示 **33 个业务 Skill**。`huawei-cloud` 是兼容历史调用的聚合入口，不作为独立业务 Skill 展示，也不计入数量。

## 1. 生命周期与资源管理

### CCE

| Skill | 能力说明 |
| --- | --- |
| `huawei-cloud-cce-cluster-management` | 管理 CCE 集群、节点池、节点、插件、EIP 和 kubeconfig 的全生命周期。 |
| `cce-cluster-upgrade-planner` | 规划 CCE Kubernetes 版本升级，检查升级路径、插件兼容性、差异项和升级窗口。 |
| `cce-workload-manager` | 管理 CCE 工作负载及 Kubernetes 资源，包括 Deployment、StatefulSet、DaemonSet、Job、CronJob、HPA、Service、Ingress 和配置资源。 |

### CCI

| Skill | 能力说明 |
| --- | --- |
| `huawei-cloud-cci-instance-management` | 管理 CCI 容器实例，包括 Namespace、网络、Deployment、StatefulSet、Pod、EIPPool、日志和指标。 |

### SWR

| Skill | 能力说明 |
| --- | --- |
| `huawei-cloud-swr-image-management` | 管理 SWR 命名空间、镜像仓库、标签、登录凭证和配额。 |
| `huawei-cloud-swr-image-governance` | 管理 SWR 权限、保留策略、共享策略、委托和不可变规则。 |
| `huawei-cloud-swr-image-automation` | 管理 SWR 镜像同步、触发器和自动部署流程。 |
| `huawei-cloud-swr-enterprise-instance` | 管理 SWR 企业实例、实例内命名空间、仓库、制品、凭证、端点和域名。 |

## 2. 可观测与智能告警

| Skill | 能力说明 |
| --- | --- |
| `observability-context-builder` | 汇聚 AOM 告警、指标、LTS 日志、Pod 日志和 Kubernetes 事件，形成诊断上下文。 |
| `alarm-correlation-engine` | 关联分析 AOM active/history 告警，完成去重归并、严重级别分组和告警规则核对。 |
| `log-analyzer` | 查询和分析 Pod 标准输出、CCE LogConfig 应用日志和 LTS 日志。 |
| `kubernetes-event-analyzer` | 查询和分析 Kubernetes Warning 事件、重复模式及 Pod、Node、Workload 异常。 |
| `metric-analyzer` | 查询和分析 CCE Pod、Node 及 ECS、ELB、EIP、NAT 指标，识别阈值异常。 |

## 3. 故障诊断与自愈恢复

| Skill | 能力说明 |
| --- | --- |
| `pod-failure-diagnoser` | 诊断 CrashLoopBackOff、ImagePullBackOff、OOMKilled、Pending、Evicted 和频繁重启等 Pod 故障。 |
| `workload-failure-diagnoser` | 诊断 Deployment、StatefulSet、DaemonSet 发布失败、滚动升级卡住、副本不足和探针异常。 |
| `node-failure-diagnoser` | 诊断 Node NotReady、资源压力、NPD、CNI、kubelet 和容器运行时异常。 |
| `autoscaling-diagnoser` | 诊断 HPA、Cluster Autoscaler 和 CCE 弹性引擎链路故障。 |
| `network-failure-diagnoser` | 诊断 Service、DNS、Ingress、NetworkPolicy、ELB、EIP、NAT 和 VPC 网络故障。 |
| `storage-failure-diagnoser` | 诊断 PVC、PV、EVS、SFS、OBS、挂载、容量和删除保护相关故障。 |
| `root-cause-analyzer` | 汇总跨域证据，输出 Top 根因、影响范围、置信度和恢复交接。 |
| `change-impact-analyzer` | 分析发布、配置、网络、安全策略和节点变更造成的故障影响。 |
| `dependency-impact-analyzer` | 基于 Service、Ingress、Pod 和 Node 拓扑分析故障传播路径和上下游影响。 |
| `auto-remediation-runner` | 生成并执行受控恢复动作，所有高风险变更默认预览并要求明确确认。 |

## 4. 巡检、治理与持续运维

| Skill | 能力说明 |
| --- | --- |
| `daily-cluster-inspector` | 执行周期性 CCE 健康检查、快速巡检和持续运维摘要。 |
| `availability-risk-scanner` | 扫描高可用、AZ 分布、单副本、PDB、探针、亲和性、网关和资源超配风险。 |
| `capacity-trend-forecaster` | 分析周期性容量趋势，预测资源瓶颈，模拟 HPA 和节点弹性策略。 |
| `cost-optimization-advisor` | 分析空闲资源、过量 Request、低利用率节点和弹性策略优化机会。 |
| `ops-report-generator` | 汇总巡检、容量、可用性、成本和 on-call 上下文，生成周报、月报、SLA、容量和稳定性报告。 |

## 5. 解决方案与交付

| Skill | 能力说明 |
| --- | --- |
| `cce-cci-bursting-deployer` | 配置、部署并验证 CCE 到 CCI 2.0 的弹性扩容能力，包括 VPCEP、virtual-kubelet 和冒烟验证。 |
| `container-migration-planner` | 盘点容器平台资源和依赖，输出迁移批次、风险和验证方案，不执行真实迁移。 |
| `全链路压测` | 构建从 k6 客户端经 ELB、nginx-ingress 到业务 Pod 的压测链路，收集观测数据并输出性能报告。 |

## 6. 多云、多集群管理

| Skill | 能力说明 |
| --- | --- |
| `ucs-cluster-onboarding-manager` | 管理 UCS 集群纳管、生命周期、舰队分组、kubeconfig 和资源配额。 |
| `ucs-policy-governor` | 管理 UCS 策略实例、策略定义、启停操作、执行状态和舰队合规审计。 |

## 常见问题路由

| 用户问题 | 推荐 Skill |
| --- | --- |
| Pod 一直重启、Pending、OOMKilled | `pod-failure-diagnoser` |
| 发布失败、滚动升级卡住、副本不满足 | `workload-failure-diagnoser` |
| 节点 NotReady、资源压力、节点漏洞 | `node-failure-diagnoser` |
| HPA 不扩 Pod、CA 不扩节点 | `autoscaling-diagnoser` |
| Ingress 502、Service 不通、ELB 链路异常 | `network-failure-diagnoser` |
| PVC Pending、FailedMount、容量耗尽 | `storage-failure-diagnoser` |
| 告警很多，需要合并分析 | `alarm-correlation-engine` |
| 查询 Pod 标准输出或 LTS 应用日志 | `log-analyzer` |
| 分析 Kubernetes 事件趋势 | `kubernetes-event-analyzer` |
| 查询 Pod、Node 或云资源指标 | `metric-analyzer` |
| 汇聚日志、事件、指标和告警 | `observability-context-builder` |
| 业务不可用，需要综合根因分析 | `root-cause-analyzer` |
| 变更后出现故障 | `change-impact-analyzer` |
| 分析服务故障影响范围 | `dependency-impact-analyzer` |
| 执行扩容、重启、drain 或恢复动作 | `auto-remediation-runner` |
| 做每日巡检或周期性健康检查 | `daily-cluster-inspector` |
| 做成本优化分析 | `cost-optimization-advisor` |
| 做容量趋势预测和弹性模拟 | `capacity-trend-forecaster` |
| 做可用性风险扫描 | `availability-risk-scanner` |
| 生成周报、月报或 SLA 报告 | `ops-report-generator` |
| 做容器迁移方案和资源盘点 | `container-migration-planner` |
| 配置 CCE 到 CCI 弹性扩容 | `cce-cci-bursting-deployer` |
| 做全链路压测和性能评估 | `全链路压测` |
| 管理 CCE 集群生命周期 | `huawei-cloud-cce-cluster-management` |
| 规划 CCE 集群版本升级 | `cce-cluster-upgrade-planner` |
| 管理 CCE 工作负载 | `cce-workload-manager` |
| 管理 CCI 容器实例 | `huawei-cloud-cci-instance-management` |
| 管理 SWR 镜像生命周期 | `huawei-cloud-swr-image-management` |
| 管理 SWR 镜像治理策略 | `huawei-cloud-swr-image-governance` |
| 管理 SWR 镜像同步和触发器 | `huawei-cloud-swr-image-automation` |
| 管理 SWR 企业实例 | `huawei-cloud-swr-enterprise-instance` |
| 管理 UCS 集群纳管和舰队 | `ucs-cluster-onboarding-manager` |
| 管理 UCS 策略和合规审计 | `ucs-policy-governor` |
