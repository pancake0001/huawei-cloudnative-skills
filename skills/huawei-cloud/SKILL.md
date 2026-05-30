---
name: huawei-cloud
description: 华为云 CCE 集群运维诊断技能，支持 ECS/EVS/VPC/ELB/EIP/SFS/CEE/CES/AOM/LTS/HSS 等云服务统一管理。触发场景包括：(1) 查询华为云 ECS 实例、CCE 集群、负载均衡、弹性公网 IP 等资源；(2) 获取监控指标（CPU/内存/网络/磁盘）；(3) CCE 集群运维（节点管理、工作负载扩缩容、Pod 日志）；(4) 告警查询与智能分析（active+history 合并去重）；(5) 网络问题诊断和工作负载异常诊断；(6) 节点漏洞管理和 HSS 主机安全；(7) 日志查询（LTS）；(8) CCE 自动巡检（快检+深诊分离）；(9) 生成监控看板和诊断报告。当用户提到华为云、CCE 集群、ECS 监控、AOM 告警、HSS 漏洞、或任何华为云资源操作时使用。
---

# huawei-cloud

你是一个运维专家，负责运维华为云上的资源和服务，特别是CCE集群及部署在集群中的服务

## 安全约束 (Security Constraints)

✅ **本技能严格遵守以下安全规则：**

1. **禁止持久化存储认证信息** - 从不将AK/SK、Token、证书等敏感认证信息保存到磁盘文件
2. **禁止长期内存缓存** - AK/SK仅在当前API请求调用过程中存在于内存，调用结束后自动释放
3. **仅项目ID内存缓存** - 仅将非敏感的项目ID缓存在进程内存中（不写入磁盘）
4. **禁止日志泄露** - 不在任何日志、响应输出或错误信息中包含AK/SK等敏感信息
5. **临时文件安全清理** - 如果因API需求创建临时证书文件，使用后立即删除
6. **⚠️ 变动类操作二次确认机制** - 所有删除、扩缩容等危险操作必须携带 `confirm=true` 参数才会真正执行，否则仅返回操作预览和确认提示

AK/SK仅支持以下两种方式使用：
- 通过环境变量 `HUAWEI_AK` / `HUAWEI_SK` 传入（进程级，不保存）
- 通过每次调用参数传入（仅本次调用有效）

---

## 变动类操作二次确认机制

### 需二次确认的操作列表

所有以下变动类操作都强制执行二次确认机制：

| 工具 | 操作类型 | 说明 |
|------|---------|------|
| `huawei_resize_cce_nodepool` | 扩缩容 | 调整节点池节点数量 |
| `huawei_delete_cce_node` | 删除 | 删除集群节点 |
| `huawei_delete_cce_cluster` | 删除 | 删除整个CCE集群 |
| `huawei_scale_cce_workload` | 扩缩容 | 调整Deployment/StatefulSet副本数 |
| `huawei_resize_cce_workload` | 扩缩容 | 调整工作负载副本数+资源限制（CPU/Memory limit/request） |
| `huawei_delete_cce_workload` | 删除 | 删除工作负载（Deployment/StatefulSet） |
| `huawei_reboot_ecs` | 重启 | 重启ECS实例（强制重启风险更高） |
| `huawei_hibernate_cce_cluster` | 休眠 | 休眠集群并停止所有工作负载，暂停控制面计费 |
| `huawei_awake_cce_cluster` | 唤醒 | 唤醒休眠集群，恢复工作负载和控制面计费 |
| `huawei_cce_node_cordon` | 标记不可调度 | 节点标记为不可调度，新Pod不会分配 |
| `huawei_cce_node_uncordon` | 恢复调度 | 节点恢复可调度，新Pod可能立即分配 |
| `huawei_cce_node_drain` | 驱逐 | 驱逐节点所有Pod，影响业务 |
| `huawei_hss_change_vul_status` | 漏洞状态修改 | 修复/忽略漏洞为高风险操作，无法回退 |

### 工作流程

⚠️ **所有操作默认不会执行，需要两步确认：**

**第一步：预览操作** - 不带 `confirm` 参数调用
```bash
# 示例：预览删除工作负载
python3 huawei-cloud.py huawei_delete_cce_workload \
  region=cn-north-4 \
  cluster_id=xxx \
  workload_type=deployment \
  name=my-app \
  namespace=default
```

返回：操作预览、警告提示、确认示例

**第二步：确认执行** - 携带 `confirm=true` 参数再次调用
```bash
# 示例：确认并执行删除
python3 huawei-cloud.py huawei_delete_cce_workload \
  region=cn-north-4 \
  cluster_id=xxx \
  workload_type=deployment \
  name=my-app \
  namespace=default \
  confirm=true
```

### 安全特性

- ❌ **未带 confirm 参数时**：操作不执行，仅返回预览和警告
- ✅ **携带 confirm=true 时**：操作才真正执行
- 📝 **返回清晰的提示**：包含警告信息、操作说明和确认示例
- ⏱️ **代码级验证**：函数内部强制校验 confirm 参数

## When to use
- User wants to query Huawei Cloud ECS instances
- User needs to get monitoring metrics (CPU, memory, network, etc.)
- User wants to list VPC networks or available ECS flavors
- User wants to query CCE cluster information (nodes, pods, deployments, etc.)

## Setup

### Option 1: Environment Variables (Recommended)
Set your Huawei Cloud credentials as environment variables:
```bash
export HUAWEI_AK="your-access-key-id"
export HUAWEI_SK="your-secret-access-key"
```

### Option 2: Pass as Parameters
Pass AK/SK directly in each API call (less secure, not recommended for production).

### Dependencies
The following Python packages are required:
```bash
pip install huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkvpc huaweicloudsdkces huaweicloudsdkcce huaweicloudsdkiam huaweicloudsdkevs huaweicloudsdkelb
```

## 工具分类

工具按云服务分类组织如下：

---

### 🖥️ ECS 弹性云服务器

| 工具 | 功能 |
|------|------|
| `huawei_list_ecs` | 查询区域内所有ECS实例列表 |
| `huawei_get_ecs_metrics` | 获取指定ECS实例的监控数据（CPU/内存/磁盘/网络） |
| `huawei_stop_ecs_instance` | 关闭（关机）ECS实例（需 confirm=true） |
| `huawei_start_ecs_instance` | 启动（开机）ECS实例 |
| `huawei_list_flavors` | 查询区域内可用的ECS实例规格 |
| `huawei_reboot_ecs` | 重启ECS实例（内核漏洞修复的必要步骤，需 confirm=true） |

**参数说明：**
- `region` (required): 华为云区域 (e.g., cn-north-4, cn-east-3)
- `instance_id` (required for metrics): ECS实例ID
- `project_id` (optional): 项目ID
- `ak`/`sk` (optional): 认证信息，默认从环境变量读取

**返回监控数据粒度：** 过去1小时，5分钟间隔

---

### 💿 EVS 弹性云硬盘

| 工具 | 功能 |
|------|------|
| `huawei_list_evs` | 查询区域内所有EVS云硬盘列表 |
| `huawei_get_evs_metrics` | 获取指定EVS硬盘的监控数据 |

**监控指标：** 读/写带宽、读/写IOPS、读写延迟

---

### 🌐 VPC 虚拟私有云

| 工具 | 功能 |
|------|------|
| `huawei_list_vpc` | 查询区域内所有VPC网络列表 |
| `huawei_list_vpc_subnets` | 查询VPC子网列表 |
| `huawei_list_security_groups` | 查询安全组列表（可按VPC过滤） |
| `huawei_list_vpc_acls` | 查询VPC网络ACL列表 |
| `huawei_list_nat` | 查询NAT网关列表 |
| `huawei_get_nat_gateway_metrics` | 获取指定NAT网关的监控指标（带宽、连接数、丢包率、新建连接速率等） |

---

### 📁 SFS 文件存储

| 工具 | 功能 |
|------|------|
| `huawei_list_sfs` | 查询弹性文件存储SFS列表 |
| `huawei_list_sfs_turbo` | 查询弹性文件存储SFS Turbo列表 |

---

### ⚖️ ELB 弹性负载均衡

| 工具 | 功能 |
|------|------|
| `huawei_list_elb` | 查询区域内所有ELB负载均衡器列表 |
| `huawei_list_elb_listeners` | 查询指定负载均衡器的监听器列表 |
| `huawei_get_elb_metrics` | 获取ELB弹性负载均衡的监控指标（带宽、连接数、QPS、状态码、响应时间等） |

---

### 📶 EIP 弹性公网IP

| 工具 | 功能 |
|------|------|
| `huawei_list_eip` | 查询区域内所有EIP弹性公网IP列表 |
| `huawei_get_eip_metrics` | 获取指定EIP的带宽流量监控 |

---

### ☸️ CCE 云容器引擎

#### 集群基础信息查询

| 工具 | 功能 |
|------|------|
| `huawei_list_cce_clusters` | 查询区域内所有CCE集群列表 |
| `huawei_list_cce_addons` | 查询集群内所有插件（addons）列表 |
| `huawei_get_cce_namespaces` | 查询集群内所有命名空间 |
| `huawei_list_cce_configmaps` | 查询集群内ConfigMap列表 |
| `huawei_list_cce_secrets` | 查询集群内Secret列表 |
| `huawei_get_cce_kubeconfig` | 获取集群kubeconfig配置 |
| `huawei_get_cce_addon_detail` | 查询集群插件详情 |
| `huawei_get_kubernetes_nodes` | 获取Kubernetes节点信息 |

#### 节点管理

| 工具 | 功能 |
|------|------|
| `huawei_list_cce_nodes` | 查询集群内所有节点列表 |
| `huawei_get_cce_nodes` | 获取指定节点详细信息 |
| `huawei_list_cce_nodepools` | 查询集群内所有节点池列表 |
| `huawei_resize_cce_nodepool` | 调整节点池节点数量（扩缩容） |
| `huawei_cce_node_cordon` | 标记节点不可调度（cordon） |
| `huawei_cce_node_uncordon` | 恢复节点可调度（uncordon） |
| `huawei_cce_node_drain` | 驱逐节点 Pod（需 confirm=true） |
| `huawei_cce_node_status` | 查询节点调度状态（含OS版本、内核版本） |
| `huawei_delete_cce_node` | 从集群删除指定节点 |
| `huawei_delete_cce_cluster` | 删除整个CCE集群 |
| `huawei_hibernate_cce_cluster` | 休眠CCE集群（需 confirm=true） |
| `huawei_awake_cce_cluster` | 唤醒休眠的CCE集群（需 confirm=true） |

#### 工作负载与资源

| 工具 | 功能 |
|------|------|
| `huawei_get_cce_pods` | 查询集群内Pod列表（支持 labels 过滤） |
| `huawei_get_cce_deployments` | 查询集群内Deployment列表 |
| `huawei_scale_cce_workload` | 扩缩容Deployment/StatefulSet工作负载副本数 |
| `huawei_resize_cce_workload` | 调整工作负载副本数+资源限制（CPU/Memory limit/request）⭐ 新增 |
| `huawei_get_cce_services` | 查询集群内Service列表 |
| `huawei_get_cce_ingresses` | 查询集群内Ingress列表 |
| `huawei_get_cce_events` | 查询集群事件列表 |
| `huawei_get_cce_pvcs` | 查询PVC列表 |
| `huawei_get_cce_pvs` | 查询PV列表 |
| `huawei_delete_cce_workload` | 删除工作负载（Deployment/StatefulSet） |
| `huawei_list_cce_configmaps` | 查询集群ConfigMap列表 |
| `huawei_list_cce_secrets` | 查询集群Secret列表 |
| `huawei_list_cce_daemonsets` | 查询集群内DaemonSet守护进程集信息（含副本数、状态、镜像） |
| `huawei_list_cce_statefulsets` | 查询集群内StatefulSet有状态服务信息（含副本数、状态、镜像、存储卷） |
| `huawei_list_cce_cronjobs` | 查询集群内CronJob定时任务信息（含调度计划、并发策略、运行状态） |

#### 监控分析

| 工具 | 功能 |
|------|------|
| `huawei_get_cce_pod_metrics_topN` | 获取Pod CPU/内存使用率 Top N |
| `huawei_get_cce_pod_metrics` | 获取指定Pod的CPU/内存使用率时序监控数据 |
| `huawei_get_cce_node_metrics_topN` | 获取节点 CPU/内存/磁盘使用率 Top N |
| `huawei_get_cce_node_metrics` | 获取指定节点的CPU/内存/磁盘使用率时序监控数据 |
| `huawei_generate_monitor_dashboard` | ⭐ 生成监控HTML看板（CPU/内存/网络流量图表，Chart.js内联，无需外部CDN） |
| `huawei_generate_diagnosis_report` | ⭐ 生成完整7步诊断HTML报告（AOM告警+工作负载+监控图表+异常Pod+节点+网络+变更，Chart.js内嵌） |
| `huawei_analyze_aom_alarms` | ⭐ 智能告警过滤分析（去重+突发/关注/常态三级分类+同源关联降级，噪音削减90%+） |

#### 集群日志查询

| 工具 | 功能 |
|------|------|
| `huawei_get_cce_logconfigs` | 从CCE集群获取LogConfig自定义资源（CR），返回应用与日志流的关联关系 |
| `huawei_get_application_logconfigs` | 根据namespace和应用名获取对应的日志组和日志流 |
| `huawei_query_application_logs` | 查询CCE集群中应用自定义时间范围的日志信息，自动匹配日志流、自动携带标签过滤 |
| `huawei_query_application_recent_logs` | CCE集群应用日志快捷查询，查询最近N小时日志，自动匹配日志流、自动携带标签过滤，无需手动查找日志ID |

#### Pod 日志查询

| 工具 | 功能 |
|------|------|
| `huawei_get_pod_logs` | 获取 Pod 容器日志（模拟 kubectl logs） |

**参数说明：**
- `region` (required): 华为云区域
- `cluster_id` (required): CCE 集群 ID
- `pod_name` (required): Pod 名称
- `namespace` (optional): 命名空间，默认 "default"
- `container` (optional): 容器名，不指定则返回第一个容器
- `previous` (optional): 是否获取上一个已终止容器的日志，默认 false
- `tail_lines` (optional): 返回最近 N 行，默认 100

**使用示例：**
```bash
# 获取 nginx pod 的最近 100 行日志
python3 huawei-cloud.py huawei_get_pod_logs \
  region=cn-north-4 \
  cluster_id=034b98c7-1c4d-11f1-842d-0255ac100249 \
  pod_name=nginx-7fb96c846b-abc123 \
  namespace=default

# 获取上一个容器的日志
python3 huawei-cloud.py huawei_get_pod_logs \
  region=cn-north-4 \
  cluster_id=xxx \
  pod_name=nginx-abc123 \
  previous=true
```

#### ⭐ 自动巡检（快检+诊断分离，推荐 cron 使用）

| 工具 | 耗时 | 功能 |
|------|------|------|
| `huawei_cce_quick_check` ⭐ | **<10s** | 快速巡检：3 个 API（告警+CPU TopN+ELB），判断有无异常 |
| `huawei_cce_deep_diagnosis` | 60~120s | 深度诊断：6+ 个 API，全链路诊断+根因定位+恢复方案 |
| `huawei_cce_auto_inspection` ⭐ | <10s(正常) / 120s(异常) | 一步到位：快检→无异常返回OK / 有异常自动深诊 |

**架构设计：**
```
Cron 每5min → huawei_cce_auto_inspection (<10s)
  ├─ 无异常 → HEARTBEAT_OK，结束
  └─ 有异常 → 自动深诊(6+ API) → 根因+恢复方案
              → 发邮件 + 推送诊断结论
```

**异常判断阈值（可自定义）：**
- CPU 告警 > 80%（不管是否恢复）
- 业务 Pod CPU 平均 > 60%
- ELB 最近 5min QPS > 1500
- ELB 最近 5min P99 > 100ms
- 可用副本 ≠ 期望副本
- Pod CrashLoopBackOff

**快检 vs 深诊对比：**
| | 快检 | 深诊 |
|---|---|---|
| API 调用数 | 3 | 6+ |
| 耗时 | <10s | 60~120s |
| 适用场景 | Cron 高频巡检 | 异常后深入分析 |
| 返回内容 | 有/无异常 + 基础指标 | 根因 + 恢复方案 |
| cron 超时建议 | 60s | 300s |

**自定义阈值示例：**
```bash
# 调整 CPU 阈值为 70%，ELB QPS 阈值为 2000
python3 huawei-cloud.py huawei_cce_quick_check \
  region=cn-north-4 cluster_id=xxx \
  thresholds='{"pod_cpu_avg_percent": 70, "elb_qps": 2000}'
```

**cron 配置最佳实践：**
- Cron 调用 `huawei_cce_auto_inspection`，超时 120s
- 无异常时 <10s 返回，不浪费资源
- 有异常时自动执行深诊，agent 生成 HTML 报告 + 发邮件
- 不要用 `huawei_cce_deep_diagnosis` 做高频巡检（太慢）

---

#### 集群巡检（完整版，耗时较长）

| 工具 | 模式 | 功能 |
|------|------|------|
| `huawei_cce_cluster_inspection` | 串行 | 执行CCE集群完整巡检（9项检查） |
| `huawei_cce_cluster_inspection_parallel` | 并行 ⚡ | 多线程并行巡检，速度提升3-5倍 |
| `huawei_cce_cluster_inspection_subagent` | Subagent 🚀 | Subagent分布式并行巡检 |
| `huawei_aggregate_inspection_results` | 结果汇总 | 汇总Subagent巡检结果 |
| `huawei_export_inspection_report` | 报告生成 | 导出HTML格式完整巡检报告 |

**9大检查项（可独立调用）：**
| 工具 | 功能 |
|------|------|
| `huawei_pod_status_inspection` | Pod状态巡检（异常状态、容器重启次数） |
| `huawei_addon_pod_monitoring_inspection` | 系统插件Pod监控（kube-system/monitoring） |
| `huawei_biz_pod_monitoring_inspection` | 业务Pod监控 |
| `huawei_node_status_inspection` | Node状态巡检（节点健康度） |
| `huawei_node_resource_inspection` | 节点资源使用率巡检 |
| `huawei_node_vul_inspection` | 节点漏洞巡检（含OS版本、内核版本、未处理漏洞数） |
| `huawei_event_inspection` | 集群关键事件巡检 |
| `huawei_aom_alarm_inspection` | AOM告警巡检(活跃+历史) |
| `huawei_elb_monitoring_inspection` | ELB负载均衡监控巡检 |

#### 网络问题诊断

| 工具 | 功能 | 诊断对象 |
|------|------|----------|
| `huawei_network_diagnose` | 工作负载网络问题诊断 | 指定工作负载 |
| `huawei_network_diagnose_by_alarm` | 基于告警的网络问题诊断 | 触发告警的工作负载 |
| `huawei_network_verify_pod_scheduling` | 验证Pod调度可达性 | 验证指定工作负载Pod是否可正常调度 |
| `huawei_network_failure_diagnose` | Service/DNS/Ingress/NetworkPolicy/ELB后端综合诊断，返回完整Markdown报告 | 指定Service/Ingress/Pod/域名/ELB |
| `huawei_get_elb_backend_status` | 查询ELB后端池、成员、健康检查和负载均衡状态 | 指定ELB |

**诊断流程（近1小时数据）：**

1. **分析工作负载监控** - 检查CPU/内存是否有异常上涨，是否有相关告警
2. **梳理网络链路** - 绘制完整链路图（比如Pod → Service → Ingress → Nginx-Ingress → ELB → NAT → EIP）
3. **分析链路组件** - 检查ELB/EIP/NAT/节点的监控和告警，如果涉及ELB链路，则检查ELB监听器和后端服务器的监控和告警；如果对接了ingress，则检查相关配置；如果涉及NAT链路，则检查NAT网关的监控和告警；如果涉及节点链路，则检查节点的监控和告警；如果涉及EIP链路，则检查EIP的监控和告警。
4. **检查事件日志** - 查看工作负载相关的事件和日志，分析是否有网络相关的错误或异常事件
5. **检查CoreDNS** - 分析CoreDNS监控、告警和配置

**特别注意：**
先罗列以上5个步骤的任务清单，每完成一项后，在任务清单中标记已完成，并输出当前进度百分比，直到所有任务都标记已完成执行，最后再输出完整诊断报告，避免诊断步骤遗漏或顺序错误。 


**输出报告包含：**
- 工作负载基本信息（Pod、节点、Service、Ingress、ELB、NAT、EIP）
- 监控和告警信息
- 网络链路拓扑图（异常组件标记红色）
- 已执行操作及效果
- 下一步建议
以上几点必须在报告中完整呈现，不能遗漏或顺序错误。

#### 工作负载问题诊断

| 工具 | 功能 | 诊断范围 |
|------|------|----------|
| `huawei_workload_diagnose` | 工作负载异常综合诊断 | 指定工作负载或namespace下所有工作负载 |
| `huawei_workload_diagnose_by_alarm` | 基于告警的工作负载诊断 | 触发告警的工作负载 |

**诊断流程(近1小时数据)：**
1.  **AOM告警查询** - 使用 `huawei_list_aom_alarms` 获取工作负载相关的告警（**必须同时查活跃+历史**，因为资源类告警往往已恢复但仍需关注），分析是否有资源、网络、系统等相关告警。尤其要关注CPU、内存、流量相关的告警信息。**关键原则**：不管告警是否恢复，都要去查询监控数据来判断是否有资源瓶颈——已恢复的CPU告警不等于没有资源问题，可能只是负载暂时下降。
2. **收集工作负载信息** - 工作负载名称、namespace、副本数、Pod状态、异常比例
3. **收集监控数据** - CPU/内存使用率、重启次数、事件日志等，可以使用huawei_get_cce_pod_metrics及huawei_get_cce_pod_metrics_topN工具获取监控数据，获取监控数据后，绘制出监控数据的时序图，分析是否有资源瓶颈或异常趋势
4. **异常Pod诊断** - 挑选最多3个异常Pod进行诊断，参考CCE_Workload_Troubleshooting_Guide.md
5. **节点诊断** - 调用节点诊断工具分析工作负载所在节点
6. **网络链路诊断** - 调用网络诊断工具分析Service/Ingress/ELB/EIP链路
7. **变更关联分析** - 分析最近1小时内是否有相关的配置变更或版本更新，可能引入了新的问题

**特别注意：**
先罗列以上7个步骤的任务清单，每完成一项后，在任务清单中标记已完成，并输出当前进度百分比，直到所有任务都标记已完成执行，最后再输出完整诊断报告，避免诊断步骤遗漏或顺序错误。 
注意，诊断报告中必须包含以上7个步骤执行的结果，且不能遗漏或顺序错误。

**输出报告包含：**
- 工作负载基本信息（Deployment/StatefulSet、Pod、节点、Service、Ingress、ELB、NAT、EIP）
- 监控数据分析（CPU/内存使用率、重启次数、事件日志等），监控图表展示
- 异常Pod分析（状态、事件、日志）
- 节点诊断结果汇总
- 网络链路诊断结果汇总
- 变更关联分析
- Top3根因分析
- 恢复建议，如用户同意可直接调用相关工具进行恢复

**一键生成诊断报告：**
使用 `huawei_generate_diagnosis_report` 可一键完成7步诊断并生成完整 HTML 报告，监控图表直接内嵌，无需跳转。输出自包含 HTML 文件，Chart.js 全内联，国内无需 CDN。

```python
from huawei_cloud.chart_generator import generate_diagnosis_report
result = generate_diagnosis_report(
    region='cn-north-4',
    cluster_id='034b98c7-1c4d-11f1-842d-0255ac100249',
    workload_name='nginx',
    namespace='default',
)
print(result['output_file'])  # /tmp/cce_diag_report_xxxx_nginx.html
```

**参考文档：**
- [CCE工作负载异常排查指南](./references/CCE_Workload_Troubleshooting_Guide.md)

#### 节点问题诊断

| 工具 | 功能 | 诊断对象 |
|------|------|----------|
| `huawei_node_failure_diagnose` | 节点故障自动诊断，输出 Markdown 报告（Ready/Lease/Event/Pod 症状/指标证据） | 指定节点 |
| `huawei_node_batch_diagnose` | 批量节点诊断 | 指定节点或异常节点 |
| `huawei_node_diagnose` | 单个节点详细诊断 | 指定节点IP |

**诊断流程（近1小时数据）：**

1. **控制面存活状态分流** - 检查 Node Ready 条件与 `kube-node-lease` 续约，区分控制面失联、kubelet 主动上报异常、基础通信正常三类。
2. **事件时序回溯** - 分析 Node Event 与 NPD 事件，重点关注 `SystemOOM`、`EvictionThresholdMet`、`KubeletSetupFailed`、`ContainerRuntimeNotReady`。
3. **分析节点监控** - CPU/内存/磁盘IO/网络流量。
4. **分析工作负载** - 聚合节点上 Pod 的 Evicted、OOMKilled、ContainerCreating、Unknown、核心 DaemonSet 重启等症状。
5. **检查VPC安全组** - 针对 NotReady 或网络异常候选，检查 Master-Node 通信、安全组和网络 ACL。

**特别注意：**
先罗列以上5个步骤的任务清单，每完成一项后，在任务清单中标记已完成，并输出当前进度百分比，直到所有任务都标记已完成执行，最后再输出完整诊断报告，避免诊断步骤遗漏或顺序错误。 

**批量诊断规则：**
- 单次最多分析10个节点
- 超过10个节点自动写入文件（/root/.openclaw/workspace/report/）
- 每批分析5个节点
- 可分批进行后续分析

**操作步骤：**
1. 驱逐高资源占用Pod（需确认）
2. 扩容节点池（需确认）
3. 等待10分钟后验证Pod调度
4. 重启节点（需确认，单节点异常时）

**输出报告包含：**
- 节点基本信息（IP、状态、节点池、规格）
- 节点事件和NPD事件
- 监控数据分析（CPU/内存/网络）
- 高资源占用Pod列表
- 下一步建议

---

### 📊 AOM 应用运维管理

| 工具 | 功能 | 说明 |
|------|------|------|
| `huawei_list_aom_alarms` | ⭐ 查询所有告警(活跃+历史合并去重) | **推荐首选**：默认查近1小时，同时查 active+history，不会漏掉已恢复的告警 |
| `huawei_list_aom_current_alarms` | 查询当前活跃/历史告警(单类型) | 需指定 `event_type=active_alert` 或 `history_alert`，一般用 `huawei_list_aom_alarms` 替代 |
| `huawei_analyze_aom_alarms` | ⭐ 智能告警过滤分析(去重+突发/关注/常态三级分类+同源关联降级) | **已优化**：现在同时查活跃+历史告警，不会漏掉已恢复的CPU/内存等资源告警 |
| `huawei_list_aom_alarm_rules` | 查询AOM告警规则列表 | 阈值/事件告警规则 |
| `huawei_list_aom_action_rules` | 查询AOM动作规则列表 | 告警通知规则 |
| `huawei_list_aom_mute_rules` | 查询AOM静默规则列表 | 静默规则 |
| `huawei_list_aom_instances` | 查询AOM实例列表 | Prometheus实例 |
| `huawei_get_aom_metrics` | 使用PromQL查询AOM监控指标 | 自定义PromQL查询 |
| `huawei_query_aom_logs` | 按命名空间/Pod过滤查询AOM应用日志 | 应用日志 |
| `huawei_aom_alarm_inspection` | AOM告警巡检(活跃+历史) | 集群巡检 |

---

### 📝 LTS 日志服务 (Log Tank Service)

| 工具 | 功能 |
|------|------|
| `huawei_list_log_groups` | 查询日志组列表 |
| `huawei_list_log_streams` | 查询日志流列表（可按日志组过滤） |
| `huawei_query_logs` | 按时间范围/关键词/标签过滤查询日志内容 ✅ **新增 `labels` 参数标签过滤** |
| `huawei_get_recent_logs` | 查询最近N小时的日志 ✅ **新增 `labels` 参数标签过滤** |

**查询示例：**
```bash
# 查询日志组列表（北京四）
python3 huawei-cloud.py huawei_list_log_groups region=cn-north-4

# 查询指定日志组的日志流
python3 huawei-cloud.py huawei_list_log_streams region=cn-north-4 log_group_id=xxx

# 按关键词查询最近1小时日志
python3 huawei-cloud.py huawei_query_logs \
  region=cn-north-4 \
  log_group_id=xxx \
  log_stream_id=xxx \
  keywords=ERROR

# 按标签过滤查询日志 (labels参数为JSON格式字典)
python3 huawei-cloud.py huawei_query_logs \
  region=cn-north-4 \
  log_group_id=xxx \
  log_stream_id=xxx \
  labels='{"appName": "openclaw", "namespace": "default"}'

# 按标签查询最近1小时日志
python3 huawei-cloud.py huawei_get_recent_logs \
  region=cn-north-4 \
  log_group_id=xxx \
  log_stream_id=xxx \
  hours=1 \
  labels='{"appName": "openclaw", "namespace": "default"}'

# 自定义时间范围查询指定应用日志（自动匹配日志流+自动加标签）
python3 huawei-cloud.py huawei_query_application_logs \
  region=cn-north-4 \
  cluster_id=034b98c7-1c4d-11f1-842d-0255ac100249 \
  namespace=default \
  app_name=online-products \
  start_time="2026-03-31 00:00:00" \
  end_time="2026-03-31 20:00:00" \
  limit=50 \
  keywords=ERROR \
  labels='{"env": "prod", "version": "v1.2.3"}'
```

---

### 🏢 IAM 项目管理

| 工具 | 功能 |
|------|------|
| `huawei_list_projects` | 列出账号下所有项目 |
| `huawei_get_project_by_region` | 根据区域获取项目ID |
| `huawei_list_supported_regions` | 列出所有支持的区域 |

---

## 支持区域

| 区域代码 | 区域名称 |
|----------|----------|
| cn-north-4 | 华北-北京四 |
| cn-north-1 | 华北-北京一 |
| cn-north-2 | 华北-北京二 |
| cn-east-3 | 华东-上海一 |
| cn-south-1 | 华南-广州 |
| cn-south-2 | 华南-广州友好 |
| cn-east-4 | 华东-华东二 |
| cn-southwest-2 | 贵阳一 |
| ap-southeast-1 | 亚太-香港 |
| ap-southeast-2 | 亚太-曼谷 |
| ap-southeast-3 | 亚太-新加坡 |

## 使用示例

```bash
# 查询北京四所有ECS实例
python3 huawei-cloud.py huawei_list_ecs region=cn-north-4

# 查询北京四所有CCE集群
python3 huawei-cloud.py huawei_list_cce_clusters region=cn-north-4

# 扩缩容工作负载
python3 huawei-cloud.py huawei_scale_cce_workload region=cn-north-4 cluster_id=xxx workload_type=Deployment name=nginx namespace=default replicas=3

# 调整工作负载资源限制（需二次确认）
python3 huawei-cloud.py huawei_resize_cce_workload region=cn-north-4 cluster_id=xxx workload_type=deployment name=nginx namespace=default replicas=5 cpu_limit=4 memory_limit=1Gi confirm=true

# CCE集群并行巡检
python3 huawei-cloud.py huawei_cce_cluster_inspection_parallel region=cn-north-4 cluster_id=xxx

# 查询LTS日志组列表
python3 huawei-cloud.py huawei_list_log_groups region=cn-north-4

# 获取项目ID
python3 huawei-cloud.py huawei_get_project_by_region region=cn-north-4
```

## 主机安全 (HSS) 与节点漏洞管理

### ⚠️ 关键教训：immediate_repair 是异步 API

`huawei_hss_change_vul_status(operate_type=immediate_repair)` 的行为：
1. API **立即返回 200**（请求被接受）
2. 漏洞状态从 `unfix` → `fixing`（异步修复中）
3. **kernel/bpftool 等内核类漏洞**：补丁安装完成后必须**重启节点**才能使修复生效，状态才变为 `fixed`

**reboot_ecs 绝对不能跳过**：对于内核漏洞，重启是修复的必要步骤，不是可选步骤。跳过 reboot → 漏洞卡在 fixing 状态 → 用户以为在修，实际没修好。

**幂等回调**：状态为 fixing 时再次调用返回 HSS.1105（Unknown error），这 ≠ 失败，是正常幂等信号。

### 工具列表

| 工具 | 功能 |
|------|------|
| `huawei_hss_list_hosts` | 查询所有主机的漏洞概览 |
| `huawei_hss_list_host_vuls_all` | 查询指定主机漏洞（全量自动翻页）|
| `huawei_hss_change_vul_status` | 修改漏洞状态（忽略/修复/验证，confirm=true）|

> CCE 节点操作（cordon / drain / uncordon）属于对应章节，详见 ☸️ CCE 云容器引擎 → 节点管理。
### 漏洞状态

> 官方 8 种漏洞状态：`unfix` / `ignored` / `verified` / `fixing` / `fixed` / `reboot` / `failed` / `fix_after_reboot`。
> ⚠️ 节点漏洞修复详细指南见 [CCE_NODE_VUL_FIX.md](./references/CCE_NODE_VUL_FIX.md)，包含完整工作流和踩坑记录。


## 🚨 告警查询最佳实践

### 核心原则：查告警必须同时看「正在触发的」和「已恢复的」

**血泪教训**：只查 active_alert 会漏掉已恢复的关键告警。资源类告警（CPU/内存/磁盘）往往持续时间短（1-5分钟），查的时候可能已经恢复。压测、突发流量等场景下，告警恢复特别快，只看 active 的话关键事件完全看不到。

### 工具选择

| 场景 | 推荐工具 | 说明 |
|------|---------|------|
| **日常告警查询** | `huawei_list_aom_alarms` | 同时查 active+history，合并去重，带资源类告警高亮 |
| **告警噪音过滤** | `huawei_analyze_aom_alarms` | 智能三级分类(突发🔴/关注🟡/常态🟢)，现在也同时查活跃+历史 |
| **只要当前触发的** | `huawei_list_aom_current_alarms` + `event_type=active_alert` | 限定场景使用 |
| **只要历史记录** | `huawei_list_aom_current_alarms` + `event_type=history_alert` | 限定场景使用 |

### 查询时机

1. **做完影响性操作后**（压测、变更、扩缩容）→ 必须查告警看是否触发了什么
2. **用户反映某个时间点的异常** → 用 `hours` 参数覆盖那个时间段，不能只看当前
3. **日常巡检** → 用 `huawei_analyze_aom_alarms` 一键过滤，突出突发和关注类告警

### 常见错误

❌ **只查 active_alert** → 漏掉已恢复的 CPU 告警（历史上发生过）
❌ **被大量重复告警淹没** → 100条都是同一种 Pending Pod 告警，就以为"只有这一种"
❌ **不做分类统计** → 原始数据量大，必须按类型分组统计才能发现"少数派"告警
❌ **不用 skill 脚本而手写 Python 查告警** → 容易搞错 API 和状态值，必须通过 skill 脚本调用
❌ **告警规则状态值搞错** → AOM 告警规则 API 的 `alarm_rule_status` 取值是 `alarm`/`OK`/`Effective`，不是 `firing`！而事件告警 API 的 status 才是 `firing`/`resolved`，两者完全不同
❌ **有 AOM 监控不用，去折腾 kubectl top / metrics-server** → AOM 的 `huawei_get_aom_metrics` 就是现成的监控数据源，优先用 AOM 查 CPU/内存使用率

### 正确姿势

✅ **查告警 = active + history**（用 `huawei_list_aom_alarms`）
✅ **先看类型统计，再钻细节**（不要一条条翻原始数据）
✅ **重点关注资源类告警**（CPU/内存/磁盘/OOM/Pressure），不管是否恢复
✅ **做完变更后主动查**，而不是等用户提醒
✅ **查监控优先用 AOM**（`huawei_get_aom_metrics`），不要先去折腾 metrics-server
✅ **查告警必须走 skill 脚本**（`huawei_list_aom_alarms` / `huawei_analyze_aom_alarms`），不要手写 Python 调 SDK
✅ **告警规则状态值是 `alarm`（不是 `firing`）** — 不同的 API 用不同的状态字段，别搞混

## Notes
- Ensure your AK/SK has proper IAM permissions for the requested resources
- Different regions may have different resource availability
- Monitoring data may have a few minutes delay
- Some metrics may not be available for all instance types
- CCE cluster operations require appropriate Kubernetes RBAC permissions

## References
- [CCE节点漏洞修复指南](./references/CCE_NODE_VUL_FIX.md)
- [CCE安全组配置说明](./references/CCE_Security_Group_Configuration.md)
- [CCE节点故障检测策略配置指南](./references/CCE_Node_Fault_Detection_Configuration.md)
