# Skill Functional Test Prompts

> 32 skills total: 25 CCE + 1 CCI + 4 SWR + 2 UCS
> Each skill has 3-5 test prompts covering different trigger scenarios.
> Prompts use bilingual Chinese+English to match Trigger keywords.
> Prerequisite: AK/SK configured (`HW_ACCESS_KEY/HW_SECRET_KEY` or `HUAWEI_AK/HUAWEI_SK`) + region set.

---

## CCE Skills (25)

### 1. huawei-cloud-cce-alarm-correlation-engine

**P1 - Alarm storm correlation:**
> 我的CCE集群最近出现了大量告警，帮我分析一下这些告警是否有关联，是否存在告警风暴。区域cn-north-4，集群ID请从列表中获取。

**P2 - Alarm rule management:**
> 查看当前AOM告警规则列表，帮我检查是否有通知断档（action rule或mute rule缺失）。区域cn-north-4。

**P3 - Alarm dedup & severity:**
> 帮我做一次CCE集群告警巡检，看看有哪些活跃告警，按严重程度分组，识别重复告警。区域cn-north-4。

**P4 - Create event alarm rule:**
> 创建一个事件告警规则，参考CCE事件列表，当出现NodeNotReady事件时触发告警通知。区域cn-north-4。

---

### 2. huawei-cloud-cce-auto-remediation-runner

**P1 - Node drain preview:**
> 我的CCE集群有个节点NotReady，帮我生成一个drain恢复预览方案，先不要执行，只看预览。集群区域cn-north-4。

**P2 - Deployment rollback:**
> 我的Deployment my-app在cn-north-4区域的production命名空间中发布失败，帮我生成回滚预览方案。

**P3 - Scale workload:**
> 帮我生成一个扩容预览方案，把production命名空间的Deployment my-app从3副本扩到5副本。区域cn-north-4。

**P4 - Node cordon:**
> 节点ip-10-0-1-5需要临时隔离，帮我生成cordon预览方案。区域cn-north-4。

---

### 3. huawei-cloud-cce-autoscaling-diagnoser

**P1 - HPA not scaling:**
> 我的HPA配置了CPU 80%阈值但Pod副本数一直没增加，帮我诊断弹性伸缩问题。区域cn-north-4。

**P2 - CA node not adding:**
> CCE集群有Pending Pod但Cluster Autoscaler没有自动添加节点，帮我诊断伸缩失败原因。区域cn-north-4。

**P3 - Full cascade diagnosis:**
> 帮我做一次HPA到CA的级联诊断，看看从工作负载层到节点层的伸缩链路哪里断了。区域cn-north-4。

---

### 4. huawei-cloud-cce-availability-risk-scanner

**P1 - Full availability scan:**
> 对我的CCE集群做一次可用性风险扫描，检查单副本、PDB缺失、AZ不均衡等问题。区域cn-north-4。

**P2 - Single point of failure:**
> 检查集群中是否存在单点故障风险，比如单副本Deployment、网关集中部署。区域cn-north-4。

**P3 - Resource overcommit:**
> 分析集群中资源request/limit超配情况，看看是否存在容量幻觉。区域cn-north-4。

---

### 5. huawei-cloud-cce-capacity-trend-forecaster

**P1 - Capacity forecast:**
> 对CCE集群做一次7天容量趋势预测，看看CPU和内存资源什么时候会耗尽。区域cn-north-4。

**P2 - HPA tuning simulation:**
> 模拟调整HPA配置对集群容量的影响，当前CPU阈值80%，如果调到60%会怎样？区域cn-north-4。

**P3 - Resource exhaustion alert:**
> 分析集群资源趋势，判断是否存在近期资源耗尽风险，给出容量规划建议。区域cn-north-4。

---

### 6. huawei-cloud-cce-cci-bursting-deployer

**P1 - Enable CCI bursting:**
> 我想启用CCE到CCI的弹性 bursting能力，帮我检查前置条件并安装virtual-kubelet插件。区域cn-north-4。

**P2 - Bursting smoke test:**
> 做一个CCI弹性bursting的冒烟测试，部署一个测试Pod到虚拟节点上。区域cn-north-4。

**P3 - Diagnose bursting failure:**
> 我配置了CCI bursting但Pod一直没到Running状态，帮我诊断问题。区域cn-north-4。

---

### 7. huawei-cloud-cce-change-impact-analyzer

**P1 - Recent change impact:**
> 我的CCE集群2小时前出现故障，帮我分析近期变更（Deployment发布、ConfigMap更新、网络策略变更）的影响。区域cn-north-4。

**P2 - Deployment release impact:**
> 分析昨天晚上做的一次Deployment发布对集群的爆炸半径和影响面。区域cn-north-4。

**P3 - Config change blast radius:**
> 分析最近一次ConfigMap/Secret变更的级联影响范围。区域cn-north-4。

---

### 8. huawei-cloud-cce-cluster-management

**P1 - List clusters:**
> 列出我账号下所有CCE集群，查看每个集群的版本、节点数和状态。区域cn-north-4。

**P2 - Create cluster:**
> 创建一个CCE集群，v1.28版本，3节点，集群名称test-cluster。区域cn-north-4。（注意：此为变更操作，仅做预览验证skill是否走确认流程）

**P3 - Node pool resize:**
> 把集群的nodepool-1从3节点扩到5节点。区域cn-north-4。（变更操作，验证确认流程）

**P4 - Get kubeconfig:**
> 获取CCE集群的kubeconfig文件，有效期1天。区域cn-north-4。

---

### 9. huawei-cloud-cce-cluster-upgrade-planner

**P1 - Full upgrade assessment:**
> 我的CCE集群当前是v1.23版本，想升级到v1.25，帮我做一次完整的升级评估（升级路径、前置检查、插件兼容性、窗口时间估算）。区域cn-north-4。

**P2 - Pre-upgrade checklist:**
> 帮我做CCE集群升级前的76项检查，看看当前集群是否满足升级条件。区域cn-north-4。

**P3 - Upgrade window estimation:**
> 我的集群有10个节点5个插件，从v1.23升级到v1.25，估算升级窗口需要多长时间。区域cn-north-4。

---

### 10. huawei-cloud-cce-container-migration-planner

**P1 - Migration inventory:**
> 我需要把CCE集群迁移到另一个区域，帮我盘点源集群的所有资源（工作负载、网络、存储、配置）。区域cn-north-4。

**P2 - Dependency mapping:**
> 分析源集群工作负载之间的依赖关系，生成依赖矩阵和迁移批次建议。区域cn-north-4。

**P3 - Migration risk assessment:**
> 评估迁移方案的风险，生成回滚策略和验证清单。区域cn-north-4。

---

### 11. huawei-cloud-cce-cost-optimization-advisor

**P1 - Full cost analysis:**
> 对CCE集群做一次成本优化分析，找出资源浪费、超配请求、低利用率节点。区域cn-north-4。

**P2 - Idle resource detection:**
> 检查集群中是否有空闲节点或闲置工作负载，给出降本建议。区域cn-north-4。

**P3 - HPA recommendation:**
> 分析当前HPA配置是否合理，给出优化建议和autoscaler策略调整方案。区域cn-north-4。

---

### 12. huawei-cloud-cce-daily-cluster-inspector

**P1 - Daily inspection:**
> 对CCE集群做一次日常巡检，快速检查集群健康状态。区域cn-north-4。

**P2 - Quick health check:**
> 帮我做一个CCE集群快检，看看有没有明显异常。区域cn-north-4。

**P3 - Cluster heartbeat:**
> 生成集群心跳摘要报告，包含关键指标和告警摘要。区域cn-north-4。

---

### 13. huawei-cloud-cce-dependency-impact-analyzer

**P1 - Service topology:**
> 分析CCE集群的服务拓扑，构建Service/Ingress/Pod的依赖关系图。区域cn-north-4。

**P2 - Cascade failure blast radius:**
> 如果Service A挂了，帮我分析级联故障的爆炸半径和上下游影响面。区域cn-north-4。

**P3 - Dependency mapping:**
> 构建集群依赖映射，标注关键传播路径和入口点。区域cn-north-4。

---

### 14. huawei-cloud-cce-kubernetes-event-analyzer

**P1 - Event query:**
> 查询CCE集群最近的Kubernetes事件，重点关注FailedScheduling和FailedMount事件。区域cn-north-4。

**P2 - Warning event analysis:**
> 分析集群中所有Warning类型的事件，按类别分组统计。区域cn-north-4。

**P3 - LTS event search:**
> 通过LTS日志流查询CCE集群事件，搜索最近1小时的异常事件模式。区域cn-north-4。

---

### 15. huawei-cloud-cce-log-analyzer

**P1 - Pod log query:**
> 查询production命名空间中Pod my-app-xxx的最近100行日志。区域cn-north-4。

**P2 - LTS log search:**
> 在LTS中搜索CCE集群应用日志，查找最近30分钟内包含"error"关键词的日志。区域cn-north-4。

**P3 - LogConfig management:**
> 列出当前CCE集群的LogConfig采集规则，帮我创建一个新的采集规则（预览模式）。区域cn-north-4。

**P4 - Audit log analysis:**
> 查询CCE集群审计日志，分析最近1小时的Pod删除和配置变更事件。区域cn-north-4。

---

### 16. huawei-cloud-cce-metric-analyzer

**P1 - Pod metric query:**
> 查询CCE集群Pod的CPU和内存使用率指标，区域cn-north-4。

**P2 - TopN ranking:**
> 获取集群中CPU使用率Top10的Pod排名。区域cn-north-4。

**P3 - Anomaly detection:**
> 检测集群中是否存在资源指标异常（超过阈值），给出异常分类。区域cn-north-4。

**P4 - Cloud resource metrics:**
> 查询集群关联的ECS/ELB/EIP/NAT云资源指标。区域cn-north-4。

---

### 17. huawei-cloud-cce-network-failure-diagnoser

**P1 - Service unreachable:**
> 我的Service在CCE集群中无法访问，帮我诊断网络连通性问题。区域cn-north-4。

**P2 - Ingress 502 diagnosis:**
> Ingress返回502错误，帮我分析ELB配置和后端Pod状态。区域cn-north-4。

**P3 - DNS resolution failure:**
> 集群内DNS解析失败，帮我诊断CoreDNS配置和网络策略。区域cn-north-4。

---

### 18. huawei-cloud-cce-node-failure-diagnoser

**P1 - Node NotReady:**
> 我的CCE集群有个节点变成NotReady了，帮我诊断节点故障原因。区域cn-north-4。

**P2 - Node disk/memory pressure:**
> 检查集群节点是否存在磁盘压力或内存压力。区域cn-north-4。

**P3 - Node event analysis:**
> 查看异常节点的Kubernetes事件和AOM指标。区域cn-north-4。

---

### 19. huawei-cloud-cce-observability-context-builder

**P1 - Full context package:**
> 为CCE集群构建一个完整的可观测性上下文包（告警+指标+日志+事件），用于后续诊断。区域cn-north-4。

**P2 - Metric+log+event correlation:**
> 收集集群的指标、日志和事件数据，建立关联关系。区域cn-north-4。

**P3 - Diagnosis context for handoff:**
> 构建诊断上下文，包含异常告警和相关日志事件，准备交接给根因分析skill。区域cn-north-4。

---

### 20. huawei-cloud-cce-ops-report-generator

**P1 - Weekly ops report:**
> 生成CCE集群本周运维报告，整合巡检、容量、可用性、成本等数据。区域cn-north-4。

**P2 - Monthly capacity report:**
> 生成月度容量报告，包含资源趋势和容量预测。区域cn-north-4。

**P3 - SLA stability report:**
> 生成SLA稳定性报告，统计故障次数和恢复时间。区域cn-north-4。

---

### 21. huawei-cloud-cce-pod-failure-diagnoser

**P1 - CrashLoopBackOff:**
> 我的Pod处于CrashLoopBackOff状态，帮我诊断容器启动失败原因。区域cn-north-4，命名空间production。

**P2 - ImagePullBackOff:**
> Pod出现ImagePullBackOff，帮我分析镜像拉取失败原因。区域cn-north-4。

**P3 - OOMKilled:**
> Pod被OOMKilled了，帮我查看内存使用情况和资源限制配置。区域cn-north-4。

**P4 - Pod Pending:**
> Pod一直Pending无法调度，帮我分析调度失败原因。区域cn-north-4。

---

### 22. huawei-cloud-cce-root-cause-analyzer

**P1 - Cross-domain RCA:**
> CCE集群同时出现告警风暴、Pod故障和节点异常，帮我做跨域根因分析。区域cn-north-4。

**P2 - Multi-failure correlation:**
> 多类告警同时触发，帮我找出根本原因和影响范围。区域cn-north-4。

**P3 - Change correlation RCA:**
> 故障发生前有配置变更，帮我关联变更和故障的因果关系。区域cn-north-4。

---

### 23. huawei-cloud-cce-storage-failure-diagnoser

**P1 - PVC Pending:**
> PVC一直Pending无法绑定PV，帮我诊断存储问题。区域cn-north-4。

**P2 - Volume mount failure:**
> Pod出现FailedMount错误，帮我分析卷挂载失败原因。区域cn-north-4。

**P3 - EVS disk issue:**
> 检查集群关联的EVS云硬盘状态，看是否有异常。区域cn-north-4。

---

### 24. huawei-cloud-cce-workload-failure-diagnoser

**P1 - Deployment rollout stuck:**
> Deployment发布卡住了，replicas一直unavailable，帮我诊断发布失败原因。区域cn-north-4。

**P2 - Probe failure:**
> 工作负载readinessProbe一直失败，帮我分析探针配置和Pod状态。区域cn-north-4。

**P3 - ReplicaSet blocked:**
> ReplicaSet创建被阻住了，可能是quota或webhook拒绝，帮我排查。区域cn-north-4。

---

### 25. huawei-cloud-cce-workload-manager

**P1 - Get kubeconfig + deploy:**
> 获取CCE集群kubeconfig，然后部署一个nginx Deployment到production命名空间。区域cn-north-4。

**P2 - Scale + rollout check:**
> 把Deployment my-app扩容到5副本，然后检查rollout状态。区域cn-north-4。

**P3 - HPA setup:**
> 为Deployment my-app配置HPA，最小2副本最大10副本，CPU阈值80%。区域cn-north-4。

**P4 - Service + Ingress:**
> 创建Service和Ingress暴露Deployment my-app。区域cn-north-4。

---

## CCI Skills (1)

### 26. huawei-cloud-cci-instance-management

**P1 - Create namespace + deploy:**
> 在CCI中创建一个namespace并部署一个简单Deployment。区域cn-north-4。（变更操作，验证确认流程）

**P2 - Query CCI instances:**
> 查看我的CCI容器实例状态和Pod列表。区域cn-north-4。

**P3 - EIPPool management:**
> 为CCI Pod配置EIPPool以获取公网IP访问能力。区域cn-north-4。

---

## SWR Skills (4)

### 27. huawei-cloud-swr-enterprise-instance

**P1 - Create enterprise instance:**
> 创建一个SWR企业版实例。区域cn-north-4。（变更操作，验证确认流程）

**P2 - Namespace + repository:**
> 在SWR企业实例中创建namespace和repository。区域cn-north-4。

**P3 - Credential + endpoint:**
> 获取SWR企业实例的长效登录凭证，并配置VPC终端节点。区域cn-north-4。

---

### 28. huawei-cloud-swr-image-automation

**P1 - Cross-region sync:**
> 配置SWR镜像跨区域自动同步，把cn-north-4的镜像同步到cn-east-3。区域cn-north-4。

**P2 - Trigger auto-deploy:**
> 创建一个SWR触发器，当镜像推送到指定仓库时自动部署到CCE工作负载。区域cn-north-4。

**P3 - Sync job status:**
> 查看镜像同步任务的状态和进度。区域cn-north-4。

---

### 29. huawei-cloud-swr-image-governance

**P1 - Permission management:**
> 查看SWR namespace的权限配置，帮我给某个用户授予读取权限。区域cn-north-4。

**P2 - Retention policy:**
> 创建镜像保留策略，自动清理超过30天的旧版本镜像。区域cn-north-4。

**P3 - Share & agency:**
> 配置SWR共享下载域名，并检查委托配置。区域cn-north-4。

---

### 30. huawei-cloud-swr-image-management

**P1 - Namespace + docker login:**
> 创建SWR namespace，然后获取docker login临时凭证登录镜像仓库。区域cn-north-4。

**P2 - Repository + tag management:**
> 查看SWR仓库的镜像版本列表，帮我清理过期tag。区域cn-north-4。

**P3 - Quota check:**
> 查看SWR资源配额使用情况。区域cn-north-4。

---

## UCS Skills (2)

### 31. ucs-cluster-onboarding-manager

**P1 - Register cluster to UCS:**
> 把我的CCE集群注册到UCS进行纳管。区域cn-north-4。（变更操作，验证确认流程）

**P2 - Fleet group management:**
> 创建一个UCS舰队集群组，并把已纳管的集群加入舰队。区域cn-north-4。

**P3 - Get federation kubeconfig:**
> 获取UCS舰队联邦kubeconfig用于多集群操作。区域cn-north-4。

---

### 32. ucs-policy-governor

**P1 - Enable policy:**
> 在UCS舰队上启用一个合规策略（如资源配额策略）。区域cn-north-4。（变更操作，验证确认流程）

**P2 - Compliance audit:**
> 检查UCS舰队中所有集群的策略合规状态，生成合规审计报告。区域cn-north-4。

**P3 - Policy instance management:**
> 查看当前策略实例列表，帮我更新一个策略的配置参数。区域cn-north-4。

---

## Test Execution Notes

1. **AK/SK prerequisite**: All skills require Huawei Cloud credentials. Set environment variables before testing:
   ```bash
   export HW_ACCESS_KEY=<your-ak>
   export HW_SECRET_KEY=<your-sk>
   export HW_REGION_NAME=cn-north-4
   ```
   Or equivalently: `HUAWEI_AK`, `HUAWEI_SK`, `HUAWEI_CLOUD_REGION`

2. **Mutation skills (change operations)**: Skills marked as "变更操作" should be tested in preview mode first. Verify the skill:
   - Generates a preview before execution
   - Requires explicit `confirm=true` before actual mutation
   - Never auto-adds `confirm=true`

3. **Read-only diagnosis skills**: These skills should be tested for:
   - Correct API query execution
   - Structured diagnosis report output (Markdown)
   - Evidence chain with source data
   - Confidence rating and recommendations
   - Proper handoff to related skills

4. **Cross-skill handoff verification**: Some prompts intentionally invoke scenarios that should trigger skill handoff:
   - Alarm correlation → Root cause analyzer
   - Daily inspector → Specific failure diagnoser
   - Observability context → Diagnosis skills
   - Pod failure → Workload failure or Node failure

5. **Dispatcher pattern skills**: Skills using `scripts/huawei-cloud.py` dispatcher should verify:
   - The skill uses `skill action=exec` to run scripts
   - Does NOT attempt hcloud/kubectl/curl directly
   - Environment check runs before main action

6. **Cluster ID**: Most prompts leave cluster_id as "从列表中获取" — the skill should first call ListClusters to discover the ID, then proceed with the specific operation.