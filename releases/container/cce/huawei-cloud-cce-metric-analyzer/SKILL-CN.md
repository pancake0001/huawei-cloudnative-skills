---
id: huawei-cloud-cce-metric-analyzer
name: huawei-cloud-cce-metric-analyzer
description: |
  基于 Python 调度器的华为云 CCE 指标分析技能，云服务查询通过 hcloud 执行。
  当用户需要以下能力时使用本技能：(1) 查询 Pod/Node/CoreDNS/nginx-ingress/autoscaler/control-plane 的 CPU、内存、磁盘、QPS、延迟、请求、连接、证书、扩缩容或错误率指标，(2) 获取资源使用率 TopN 排名，(3) 查询 ECS/ELB/EIP/NAT 云资源指标，(4) 聚合集群监控数据并做异常检测，(5) 基于阈值识别资源异常。
  触发词：用户提到 "metric analysis"、"指标分析"、"CCE metrics"、"CCE 指标"、"AOM metrics"、"AOM 指标"、"CoreDNS metrics"、"CoreDNS 指标"、"nginx ingress metrics"、"nginx-ingress 指标"、"autoscaler metrics"、"autoscaler 指标"、"HPA 指标"、"apiserver metrics"、"etcd metrics"、"controller manager metrics"、"scheduler metrics"、"control plane metrics"、"控制面指标"、"certificate expiration"、"证书过期"、"resource metrics"、"资源指标"、"CPU 使用率"、"内存使用率"、"TopN" 或 "资源排名"。
tags: [cce, metrics, aom, observability, analysis]
---

# 华为云 CCE 指标分析器

## 概览

查询并分析 CCE 集群指标（Pod/Node CPU、内存、磁盘）和云资源指标（ECS、ELB、EIP、NAT）。支持基于阈值的异常检测、状态分类（critical/warning/normal）和整集群监控聚合。

**架构**：`python3 scripts/huawei-cloud.py` 调度器 -> hcloud (KooCLI) 云服务查询 + AOM Prometheus 签名 HTTP 查询 + Kubernetes client -> Pod/Node 指标、ECS/ELB/EIP/NAT 指标 -> 阈值分类 -> 异常检测。

> **执行方式**：云服务查询通过本机 `hcloud` CLI 执行。AOM Prometheus `query_range` 是唯一例外，由于所需 Prometheus range-query 路径不兼容 hcloud，因此使用签名 HTTPS 请求。禁止在调度器之外直接调用华为云 SDK、curl IAM、openstack 或手写云 API。

**相关技能**：
- `huawei-cloud-cce-pod-failure-diagnoser` - Pod CrashLoopBackOff、OOMKilled、重启风暴
- `huawei-cloud-cce-node-failure-diagnoser` - 节点健康和资源压力诊断
- `huawei-cloud-cce-kubernetes-event-analyzer` - Warning 事件和失败模式
- `huawei-cloud-cce-capacity-trend-forecaster` - 容量规划和趋势预测
- `huawei-cloud-cce-cost-optimization-advisor` - 资源成本优化
- `huawei-cloud-cce-auto-remediation-runner` - 修复动作（扩缩容、规格调整、drain）

**能力范围**：
- Pod CPU/内存 TopN 排名和单 Pod 时序指标
- Node CPU/内存/磁盘 TopN 排名和单 Node 时序指标
- Node GPU 与 xGPU 指标，包括 GPU 使用率、显存、温度、功耗、调度策略、xGPU 分配、使用量和健康状态
- Pod GPU 与 xGPU 指标
- CoreDNS QPS、排除 NXDOMAIN 的错误率、NXDOMAIN 比例、P95 延迟、副本数和 Pod CPU/内存
- nginx-ingress QPS、4xx/5xx 速率、成功率、P95 延迟、活跃连接、Pod CPU/内存和 Ingress TLS 证书过期状态
- Autoscaler 不可调度 Pod、节点状态数量、扩/缩容事件、错误、节点组、HPA 当前/期望副本，以及 Pod CPU/内存
- Kubernetes 控制面指标：apiserver、etcd、controller-manager、scheduler
- ECS 实例 CPU/内存/磁盘/网络指标
- ELB 连接、带宽、QPS 指标
- EIP 带宽、流量、丢包率指标
- NAT Gateway SNAT 连接指标
- 整集群监控聚合和异常检测（80% 阈值）
- 阈值状态分类：critical/warning/normal/unknown

**典型场景**：
- “查询集群 CPU 使用率最高的 Pod”
- “获取 Node 内存使用率排名”
- “获取 CCE 节点 GPU 和 xGPU 指标”
- “检查 CoreDNS QPS、延迟和错误率”
- “检查 nginx-ingress 请求延迟、5xx 率和 TLS 证书过期”
- “检查 autoscaler 扩缩容活动和 HPA 副本差异”
- “检查 apiserver、etcd、controller-manager、scheduler 关键指标”
- “检查 ECS 实例资源指标”
- “查看某个 ELB 的 QPS”
- “查看 EIP 带宽使用”
- “聚合集群全部监控数据”
- “哪些资源超过了 critical 阈值”
- “检测最近一小时资源异常”

## 前置条件

### 1. 运行依赖

- Python 3.8+，用于调度器和结果处理
- hcloud (KooCLI) 7.2.2+，用于 CCE/ECS/ELB/VPC/EIP/NAT/CES/IAM 云服务查询
- Kubernetes Python client，用于 hcloud 创建短期 CCE 集群凭据后读取集群内 Pod/Node/Service 详情
- 普罗相关监控数据从 AOM Prometheus 获取，使用 AK/SK 签名 HTTPS 请求；目标集群必须已安装普罗插件并对接 AOM，否则相关工具可能返回空指标序列
- controller-manager、scheduler 和 etcd 指标需要在 AOM 中单独开启 `kube-controller-manager`、`kube-scheduler`、`etcd-server` ServiceMonitor，否则工具可能返回空指标序列
- autoscaler、ingress-controller 和 NVIDIA GPU 指标需要在 AOM 中单独开启对应的 `autoscaler`、`ingress-controller`、`nvidia-gpu-device-plugin` PodMonitor；ingress 请求指标还需要在 ingress-controller PodMonitor 中单独放通 `nginx_ingress_controller_requests`
- 首次使用前请运行验证章节中的检查命令

### 2. 认证配置

- 支持通过 hcloud profile 或 AK/SK 模式提供华为云认证
- **安全规则**：
  - 禁止在代码、对话或命令中暴露 AK/SK
  - 禁止使用 `echo $HUAWEI_AK` 或 `echo $HUAWEI_SK` 检查凭据
  - hcloud 调用认证优先级：显式工具参数 > 本机 hcloud profile > 环境变量
  - AOM Prometheus 签名 HTTP 和 Kubernetes 证书创建无法使用加密 hcloud profile 中的密钥材料，因此使用显式工具参数优先、环境变量作为签名 fallback
  - 优先使用 IAM 用户而不是根账号
  - 对敏感操作启用 MFA

**配置方式**：

```bash
hcloud configure list

export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_REGION=cn-north-4
```

### 3. IAM 权限要求

| API Action | 权限用途 |
| ---------- | -------- |
| `cce:cluster:get` | 查看 CCE 集群详情 |
| `aom:instance:list` | 发现用于指标查询的 AOM Prometheus 实例 |
| `aom:metricsData:get` | 查询 Pod/Node CPU、内存、磁盘等 AOM 指标 |
| `ces:metricsData:get` | 查询 ECS/ELB/EIP/NAT 云资源指标 |
| `ecs:cloudServers:list` | 关联 ECS 实例 ID |
| `elb:loadbalancers:list` | 关联 ELB ID |
| `vpc:eips:list` | 关联 EIP ID |
| `nat:natGateways:list` | 关联 NAT Gateway ID |

**权限失败处理**：

1. 命令因 IAM 权限失败时，展示需要的权限列表。
2. 引导用户在 IAM 控制台创建自定义策略并授权。
3. 暂停执行，等待用户确认权限已补齐。

## 核心命令

所有命令都使用 Python 调度器脚本：

```bash
python3 scripts/huawei-cloud.py <action> <key=value>...
```

## KooCLI命令格式标准

不要要求用户直接执行原始 `hcloud` 命令，统一使用调度器格式：

```bash
python3 scripts/huawei-cloud.py <tool-name> key=value key=value
```

云服务查询由调度器转换为 KooCLI 调用。AOM Prometheus range 查询因路径不兼容 hcloud，使用签名 HTTPS 请求。包含空格、`>`、`<`、`|`、JSON 或 PromQL 的值需要加引号；禁止打印或持久化 AK/SK、security token、kubeconfig 或临时载荷；Kubernetes/AOM PromQL 必须保留 `cluster="<cluster_id>"` 过滤。

### 1. CCE Pod 指标

```bash
# Pod TopN，集群级 CPU/内存排名
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=default top_n=10 hours=1

# 带 label selector 的 Pod TopN
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=default label_selector="app=nginx,version=v1" top_n=10 hours=1

# 单 Pod 时序指标
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  pod_name=my-app-xxx namespace=default hours=1

# 单 Pod GPU 和 xGPU 指标
python3 scripts/huawei-cloud.py huawei_get_cce_pod_gpu_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  pod_name=my-gpu-app-xxx namespace=default hours=1
```

### 2. CCE Node 指标

```bash
# Node TopN，集群级 CPU/内存/磁盘排名
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN \
  region=cn-north-4 cluster_id=<cluster-id> \
  top_n=10 hours=1

# 单 Node 时序指标
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  node_ip=10.0.0.1 hours=1

# Node GPU 和 xGPU 指标
python3 scripts/huawei-cloud.py huawei_get_cce_node_gpu_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  node_ip=10.0.0.1 hours=1
```

### 3. CCE CoreDNS 指标

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_coredns_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*coredns.*" hours=1
```

### 4. CCE nginx-ingress 指标

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_nginx_ingress_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*nginx.*ingress.*|.*ingress.*nginx.*" \
  ingress_namespace=default cert_expire_warning_days=30 hours=1
```

### 5. CCE Autoscaler 指标

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_autoscaler_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*cluster.*autoscaler.*|.*autoscaler.*" \
  include_hpa=true hours=1
```

### 6. Kubernetes 控制面指标

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_apiserver_metrics \
  region=cn-north-4 cluster_id=<cluster-id> hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_etcd_metrics \
  region=cn-north-4 cluster_id=<cluster-id> hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_controller_manager_metrics \
  region=cn-north-4 cluster_id=<cluster-id> namespace=kube-system hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_scheduler_metrics \
  region=cn-north-4 cluster_id=<cluster-id> namespace=kube-system hours=1
```

### 7. 云资源指标

```bash
# ECS 实例指标
python3 scripts/huawei-cloud.py huawei_get_ecs_metrics \
  region=cn-north-4 instance_id=<instance-id>

# ELB 指标
python3 scripts/huawei-cloud.py huawei_get_elb_metrics \
  region=cn-north-4 elb_id=<loadbalancer-id> hours=1

# EIP 指标
python3 scripts/huawei-cloud.py huawei_get_eip_metrics \
  region=cn-north-4 eip_id=<eip-id> hours=1

# NAT Gateway 指标
python3 scripts/huawei-cloud.py huawei_get_nat_gateway_metrics \
  region=cn-north-4 nat_gateway_id=<nat-gateway-id> hours=1
```

### 8. 集群监控聚合

```bash
python3 scripts/huawei-cloud.py huawei_cce_cluster_monitoring_aggregation \
  region=cn-north-4 cluster_id=<cluster-id> \
  start_time="2026-05-30 00:00:00" end_time="2026-05-30 23:59:59" \
  namespace=default top_n=10
```

该工具聚合 Pod TopN CPU/内存、Node TopN CPU/内存/磁盘、ELB 指标（带 LoadBalancer Service 关联）、NAT Gateway 指标、EIP 指标（带宽、丢包率），并基于 80% 阈值做异常检测。

它也包含 CoreDNS、nginx-ingress 和 autoscaler 摘要。云资源仅在可证明与当前集群有关时纳入：ELB 通过 LoadBalancer Service IP/EIP 匹配，NAT Gateway 通过集群 VPC 过滤，EIP 限定为关联 ELB/NAT/Service IP 的地址。

## 风险等级

本技能是只读技能，不创建、更新、删除、重启、扩容或修改华为云和 Kubernetes 资源。

| 等级 | 含义 | 执行要求 |
| ---- | ---- | -------- |
| R3 | 无风险只读查询或本地分析 | 可自动执行 |
| R2 | 低风险变更，例如创建监控配置，不删除资源、不扩容、不直接增加费用 | 当前工具未使用 |
| R1 | 有风险操作，例如类似重启影响、停用保护、可能增加费用或降低可观测性的变更 | 当前工具未使用 |
| R0 | 致命级别操作，例如删除集群、应用或大范围监控保护 | 当前工具未使用 |

| 工具 | 操作类型 | 风险等级 | 说明 |
| ---- | -------- | -------- | ---- |
| `huawei_get_cce_pod_metrics_topN` | 查询 | R3 | 从 AOM Prometheus 读取 Pod CPU/内存/磁盘 TopN 指标 |
| `huawei_get_cce_pod_metrics` | 查询 | R3 | 读取单个 Pod CPU/内存/磁盘时序指标 |
| `huawei_get_cce_pod_gpu_metrics` | 查询 | R3 | 读取单个 Pod GPU 和 xGPU 指标 |
| `huawei_get_cce_node_metrics_topN` | 查询 | R3 | 从 AOM Prometheus 读取 Node CPU/内存/磁盘 TopN 指标 |
| `huawei_get_cce_node_metrics` | 查询 | R3 | 读取单个 Node CPU/内存/磁盘时序指标 |
| `huawei_get_cce_node_gpu_metrics` | 查询 | R3 | 读取单个 Node GPU 和 xGPU 指标 |
| `huawei_get_cce_coredns_metrics` | 查询 | R3 | 读取 CoreDNS QPS、排除 NXDOMAIN 的错误率、NXDOMAIN 比例、P95 延迟、副本数和 Pod CPU/内存 |
| `huawei_get_cce_nginx_ingress_metrics` | 查询 | R3 | 读取 nginx-ingress 请求处理指标和 Ingress TLS 证书过期状态；缺少请求维度指标时 QPS 回退到 nginx process 请求计数 |
| `huawei_get_cce_autoscaler_metrics` | 查询 | R3 | 读取 Cluster Autoscaler 扩缩容指标、HPA 副本状态和 autoscaler Pod CPU/内存 |
| `huawei_get_cce_apiserver_metrics` | 查询 | R3 | 读取 kube-apiserver QPS、错误率、延迟和 inflight 请求 |
| `huawei_get_cce_etcd_metrics` | 查询 | R3 | 读取 etcd leader、proposal、DB 大小、磁盘延迟、CPU 和内存 |
| `huawei_get_cce_controller_manager_metrics` | 查询 | R3 | 读取控制面 workqueue 深度、adds、retries、排队延迟和处理耗时 |
| `huawei_get_cce_scheduler_metrics` | 查询 | R3 | 读取 scheduler 调度尝试、待调度 Pod、调度延迟和队列指标 |
| `huawei_get_ecs_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 ECS 监控数据 |
| `huawei_get_elb_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 ELB 监控数据 |
| `huawei_get_eip_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 EIP 监控数据 |
| `huawei_get_nat_gateway_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 NAT Gateway 监控数据 |
| `huawei_cce_cluster_monitoring_aggregation` | 查询 + 本地分析 | R3 | 聚合 Pod/Node/云资源指标并在本地分类异常 |

## 参数参考

### 通用参数

| 参数 | 必填/可选 | 说明 | 默认值 |
| ---- | --------- | ---- | ------ |
| `region` | 必填 | 华为云区域 | `HUAWEI_REGION` |
| `cluster_id` | 必填 | CCE 集群 ID | N/A |
| `namespace` | 推荐 | Kubernetes 命名空间 | `default` |
| `ak` | 可选 | 显式 AK；所有调用最高优先级 | profile/env fallback |
| `sk` | 可选 | 显式 SK；所有调用最高优先级 | profile/env fallback |
| `project_id` | 可选 | 显式 Project ID；hcloud 使用 profile 后再环境变量 fallback | IAM/profile 自动解析 |

### `huawei_get_cce_pod_metrics_topN` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `namespace` | 否 | 命名空间过滤 | all |
| `label_selector` | 否 | 标签选择器，例如 app=web | N/A |
| `top_n` | 否 | TopN 数量 | 10 |
| `hours` | 否 | 指标回溯小时数 | 1 |
| `node_ip` | 否 | 过滤指定节点上的 Pod | N/A |
| `cpu_query` | 否 | 自定义 CPU PromQL | Auto |
| `memory_query` | 否 | 自定义内存 PromQL | Auto |
| `disk_query` | 否 | 自定义磁盘 PromQL | Auto |

### `huawei_get_cce_pod_metrics` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `pod_name` | 是 | 目标 Pod 名称 | N/A |
| `namespace` | 否 | 命名空间 | `default` |
| `hours` | 否 | 指标回溯小时数 | 1 |
| `cpu_query` | 否 | 自定义 CPU PromQL | Auto |
| `memory_query` | 否 | 自定义内存 PromQL | Auto |
| `disk_query` | 否 | 自定义磁盘 PromQL | Auto |

### `huawei_get_cce_pod_gpu_metrics` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `pod_name` | 是 | 目标 Pod 名称 | N/A |
| `namespace` | 否 | 目标 Pod 命名空间 | all |
| `hours` | 否 | 指标回溯小时数 | 1 |
| `gpu_selector` | 否 | 自定义 GPU 指标 label selector；当 GPU 指标不使用 `pod` 或 `namespace` 标签时使用 | `pod="<pod_name>",namespace="<namespace>"` |

支持可选自定义 PromQL 覆盖 GPU 使用率、显存、调度策略、xGPU 分配/使用量和 xGPU 健康指标。

### `huawei_get_cce_node_metrics_topN` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `top_n` | 否 | TopN 数量 | 10 |
| `hours` | 否 | 指标回溯小时数 | 1 |

### `huawei_get_cce_node_metrics` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `node_ip` | 是 | 目标 Node IP | N/A |
| `hours` | 否 | 指标回溯小时数 | 1 |

### `huawei_get_cce_node_gpu_metrics` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `node_ip` | 是 | 目标 Node IP 或节点名 | N/A |
| `hours` | 否 | 指标回溯小时数 | 1 |
| `gpu_selector` | 否 | 自定义 GPU 指标 label selector；当 GPU 指标不使用 `node` 标签时使用 | `node=~"<node_ip>|<node_name>"` |

支持可选自定义 PromQL 覆盖 GPU 使用率、显存、温度、功耗、调度策略、xGPU 分配/使用量和 xGPU 健康指标。

### `huawei_get_cce_coredns_metrics` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `namespace` | 否 | CoreDNS 命名空间 | `kube-system` |
| `pod_regex` | 否 | 匹配 CoreDNS Pod 的正则 | `.*coredns.*` |
| `hours` | 否 | 指标回溯小时数 | 1 |

支持可选自定义 PromQL 覆盖 QPS、错误率、NXDOMAIN 比例、P95 延迟、CPU、内存和副本数。

### `huawei_get_cce_nginx_ingress_metrics` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `namespace` | 否 | nginx-ingress controller Pod 所在命名空间；传空值可查全部命名空间 | `kube-system` |
| `pod_regex` | 否 | 匹配 nginx-ingress controller Pod 的正则 | `.*nginx.*ingress.*|.*ingress.*nginx.*` |
| `ingress_namespace` | 否 | Ingress TLS 证书检查的命名空间过滤 | all |
| `hours` | 否 | 指标回溯小时数 | 1 |
| `cert_expire_warning_days` | 否 | 证书到期前多少天标记为 warning | 30 |
| `check_certificates` | 否 | 是否检查 Ingress TLS Secret 证书过期状态 | true |

ingress-controller 指标依赖对应的 AOM PodMonitor。`nginx_ingress_controller_requests` 指标需要在 ingress-controller PodMonitor 中单独放通；否则 4xx/5xx QPS、成功率、延迟等请求维度指标可能为空，QPS 只能在存在 `nginx_ingress_controller_nginx_process_requests_total` 时使用该指标兜底。

支持可选自定义 PromQL 覆盖 QPS、4xx/5xx、成功率、P95 延迟、活跃连接、CPU 和内存。

### `huawei_get_cce_autoscaler_metrics` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `namespace` | 否 | Cluster Autoscaler Pod 所在命名空间；传空值可查全部命名空间 | `kube-system` |
| `pod_regex` | 否 | 匹配 autoscaler Pod 的正则 | `.*cluster.*autoscaler.*|.*autoscaler.*` |
| `hpa_namespace` | 否 | HPA 副本指标的命名空间过滤 | all |
| `hours` | 否 | 指标回溯小时数 | 1 |
| `include_hpa` | 否 | 是否查询 HPA 当前/期望副本指标 | true |

支持可选自定义 PromQL 覆盖不可调度 Pod、节点状态、扩缩容事件、错误、节点组、HPA 副本、CPU 和内存。

### Kubernetes 控制面工具参数

适用于 `huawei_get_cce_apiserver_metrics`、`huawei_get_cce_etcd_metrics`、`huawei_get_cce_controller_manager_metrics` 和 `huawei_get_cce_scheduler_metrics`。

`huawei_get_cce_apiserver_metrics` 默认使用 `cluster="<cluster_id>",component="apiserver"`，不追加 namespace 或 Pod 标签。默认 P95 延迟排除 `WATCH|CONNECT` 请求，并返回 `latency_p95_by_verb_ms` 用于诊断。Prometheus 标签不一致时再使用 `metric_selector`。

`huawei_get_cce_etcd_metrics` 默认使用 `cluster="<cluster_id>"`，不附加 namespace 或 Pod 标签。只有 Prometheus 标签和默认假设不一致时才使用 `metric_selector`。

`huawei_get_cce_controller_manager_metrics` 默认使用 `cluster="<cluster_id>"`，因为 CCE AOM workqueue 指标可能没有稳定的 controller-manager Pod 标签。它返回聚合 workqueue 指标和按 queue `name` 拆分的指标。

`huawei_get_cce_scheduler_metrics` 默认使用 `cluster="<cluster_id>"`，返回聚合指标以及按 `result`、`profile/result` 和 `queue` 拆分的指标。

controller-manager、scheduler 和 etcd 指标依赖 AOM 对对应的 `kube-controller-manager`、`kube-scheduler`、`etcd-server` 端点启用 ServiceMonitor。如果未启用，工具可以执行成功但可能返回空序列。

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `namespace` | 否 | 控制面 Pod 命名空间；传空值可查全部命名空间 | `kube-system` |
| `pod_regex` | 否 | 匹配目标组件 Pod 的正则 | 组件相关 |
| `metric_selector` | 否 | 自定义 apiserver/etcd/controller-manager/scheduler 指标 label selector | apiserver: `cluster="<cluster_id>",component="apiserver"`；etcd/controller-manager/scheduler: `cluster="<cluster_id>"` |
| `hours` | 否 | 指标回溯小时数 | 1 |

### 云资源工具参数

| 工具 | 必填 ID 参数 | 可选参数 |
| ---- | ------------ | -------- |
| `huawei_get_ecs_metrics` | `instance_id` | 无 |
| `huawei_get_elb_metrics` | `elb_id` | `hours` |
| `huawei_get_eip_metrics` | `eip_id` | `hours` |
| `huawei_get_nat_gateway_metrics` | `nat_gateway_id` | `hours` |

### `huawei_cce_cluster_monitoring_aggregation` 参数

| 参数 | 必填 | 说明 | 默认值 |
| ---- | ---- | ---- | ------ |
| `start_time` | 是 | 开始时间，格式 YYYY-MM-DD HH:MM:SS | N/A |
| `end_time` | 是 | 结束时间，格式 YYYY-MM-DD HH:MM:SS | N/A |
| `namespace` | 否 | 命名空间过滤 | `default` |
| `top_n` | 否 | TopN 数量 | 10 |
| `security_token` | 否 | AK/SK 临时会话凭据的 security token | env fallback |

## 输出格式

完整 JSON 响应结构见 [Output Schema](references/output-schema.md)。

**关键输出字段**：
- `success` - 查询是否完成
- `region` - 华为云区域
- `cluster_id` / `cluster_name` - CCE 集群标识
- `aom_instance_id` - 指标查询使用的 AOM Prometheus 实例
- `metrics` - 每个资源的 CPU/内存/磁盘数据和状态分类
- `certificate_check` - nginx-ingress 启用证书检查时的 Ingress TLS 证书过期摘要
- `time_series` - 历史数据点，包含 `timestamp`、`time`、`average`、`min`、`max`
- `status` - 阈值分类：`critical`、`warning`、`normal`、`unknown`

## 工作流

1. 按文档优先级解析 region、cluster ID 和认证凭据。
2. 从 CCE 集群插件绑定中发现 AOM Prometheus 实例。
3. 先使用 Pod/Node TopN 或聚合工具获取概览，再下钻 Pod、Node、组件或云资源。
4. PromQL 保持 `cluster="<cluster_id>"` 集群过滤；namespace、pod 或资源过滤只用于降噪。
5. 将状态分类作为排查线索，再结合事件或告警历史做关联分析。

## 验证

1. 运行 `python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN region=cn-north-4 cluster_id=<cluster-id> namespace=default top_n=5` 验证 Pod 指标查询
2. 运行 `python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN region=cn-north-4 cluster_id=<cluster-id> top_n=5` 验证 Node 指标查询
3. 运行 `python3 scripts/huawei-cloud.py huawei_get_ecs_metrics region=cn-north-4 instance_id=<instance-id>` 验证 CES 指标连通性

## 最佳实践

1. 先看 Pod/Node TopN，再钻取单个资源。
2. 最近分析建议 `hours` 保持 1-4；历史回顾最多 24 小时。
3. Pod TopN 尽量提供 `namespace` 以减少噪声，但不能移除 cluster 过滤。
4. 优先关注 `critical` 和 `warning` 资源。
5. 使用 `huawei_cce_cluster_monitoring_aggregation` 做集群健康概览。
6. 指标异常时，结合 `huawei-cloud-cce-kubernetes-event-analyzer` 查看事件。
7. 对外摘要不要暴露生产 Pod 名、节点 IP 或集群 ID。

## 注意事项

- 本技能严格只读，不修改资源或配置。
- 阈值是预设基线，实际阈值应结合业务 SLO 调整。
- AK/SK 禁止硬编码；常规 hcloud 调用优先使用 hcloud profile，AOM/Kubernetes 签名调用可使用环境变量 fallback。
- `scripts/huawei-cloud.py` 是唯一面向用户的执行入口。
- AOM Prometheus 实例会自动发现，无需手动指定 `aom_instance_id`。
- 云资源指标（ECS/ELB/EIP/NAT）使用 CES（Cloud Eye Service），不是 AOM。
- 不要仅凭指标分析自动做扩缩容或修复决策。

## 排障

| 问题 | 表现 | 处理方式 |
| ---- | ---- | -------- |
| 缺少 `cluster_id` | action 立即失败 | 使用集群列表中的 `cluster_id` |
| 找不到 AOM Prometheus 实例 | 指标查询为空 | 确保集群已创建 AOM Prom 实例；检查 `aom:instance:list` 权限 |
| 时间窗口过大且没有 namespace 过滤 | 响应慢、结果过多 | 将 `hours` 缩小到 1-4，并添加 `namespace` |
| 云资源 ID 不存在 | ECS/ELB/EIP/NAT 查询报错 | 确认资源 ID 存在并具备 CES 权限 |
| 自定义 PromQL 语法错误 | 查询返回空 | 优先使用默认 PromQL |
| 聚合缺少时间范围 | 缺少 `start_time` / `end_time` | 聚合查询必须同时提供开始和结束时间 |

## 限制

- AOM Prometheus 数据要求集群普罗插件已对接 AOM。
- 控制面 ServiceMonitor 和组件 PodMonitor 需要开启后才会有相关指标。
- 查询结果只反映已采集的监控数据；指标序列缺失不代表工作负载健康。
- 本技能不修复、扩缩容、重启、创建、更新或删除云资源和 Kubernetes 资源。

## 参考文档
| 文档 | 说明 |
| ---- | ---- |
| [Workflow](references/workflow.md) | 指标查询顺序、阈值检测和后续交接 |
| [Risk Rules](references/risk-rules.md) | 只读约束、数据脱敏、时间范围约束、阈值注意事项 |
| [Output Schema](references/output-schema.md) | 指标和状态输出的 JSON 响应结构 |
