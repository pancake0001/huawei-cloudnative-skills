---
name: metric-analyzer
description: Use this skill to query and analyze metrics for CCE clusters and cloud resources, including Pod, Node, ECS, ELB, EIP, and NAT usage, plus threshold-based anomaly detection and status classification.
---

# Metric Analyzer

Query and analyze metrics for CCE clusters (Pod/Node) and cloud resources (ECS, ELB, EIP, NAT). Supports threshold-based anomaly detection and status classification.

Runtime note: the user-facing entry remains `python3 scripts/huawei-cloud.py`. CCE/ECS/ELB/VPC/EIP/NAT/CES/IAM cloud service queries are executed through hcloud (KooCLI). AOM Prometheus range queries use signed HTTPS requests with AK/SK because the hcloud AOM Prometheus query path is not compatible with the required query_range API. Configure credentials with `hcloud configure` or supported AK/SK environment variables.

> **执行方式**：云服务查询统一通过本机 `hcloud` CLI 执行。AOM Prometheus `query_range` 是唯一例外，因为所需的 Prometheus range-query 路径当前不兼容 hcloud，所以使用 AK/SK 签名 HTTPS 请求。禁止在 dispatcher 外绕过工具直接调用 SDK、curl IAM、openstack 或手写云服务 API。

> **认证优先级**：hcloud 调用使用 `工具入参 > 本机 hcloud profile > 环境变量`。AOM Prometheus signed HTTP 和 Kubernetes 证书创建无法直接使用加密的 hcloud profile 凭证材料，因此签名类调用使用 `工具入参 > 环境变量`。

> **采集依赖**：controller-manager 和 scheduler 指标需要在 AOM 中单独开启对应的 ServiceMonitor；如果未开启，工具可以正常执行，但可能返回空指标序列。

## Scope

Use this skill when the user asks to:

- Get Pod CPU/memory usage ranking in a CCE cluster
- Get Node CPU/memory/disk usage ranking in a CCE cluster
- Query specific Pod or Node metrics time-series
- Check which Pods/Nodes are consuming the most resources
- Get ECS instance CPU/memory/disk/network metrics
- Get ELB connection, bandwidth, QPS metrics
- Get EIP bandwidth and traffic metrics
- Get NAT Gateway SNAT connection metrics
- Detect resource anomalies via threshold-based classification

This skill is read-only. It does not modify resources or configurations.

## 风险等级

当前技能全部工具都是只读查询或本地分析，不创建、修改、删除、重启、扩缩容任何华为云或 Kubernetes 资源。

| 等级 | 含义 | 执行建议 |
|------|------|---------|
| R3 | 无风险只读查询或本地分析 | 可自动执行 |
| R2 | 低风险变更，例如创建监控配置，不删除资源、不扩容、不直接增加费用 | 当前工具未使用 |
| R1 | 有风险操作，例如类似重启影响、停用保护、可能增加费用或降低可观测性的变更 | 当前工具未使用 |
| R0 | 致命级别操作，例如删除集群、应用，或删除影响面较大的监控保护 | 当前工具未使用 |

| 工具 | 操作类型 | 风险等级 | 说明 |
|------|---------|---------|------|
| `huawei_get_cce_pod_metrics_topN` | 查询 | R3 | 从 AOM Prometheus 读取 Pod CPU/内存/磁盘 TopN 指标 |
| `huawei_get_cce_pod_metrics` | 查询 | R3 | 读取单个 Pod CPU/内存/磁盘时序指标 |
| `huawei_get_cce_node_metrics_topN` | 查询 | R3 | 从 AOM Prometheus 读取 Node CPU/内存/磁盘 TopN 指标 |
| `huawei_get_cce_node_metrics` | 查询 | R3 | 读取单个 Node CPU/内存/磁盘时序指标 |
| `huawei_get_cce_node_gpu_metrics` | 查询 | R3 | 读取单个 Node GPU 和 xGPU 监控指标 |
| `huawei_get_cce_pod_gpu_metrics` | 查询 | R3 | 读取单个 Pod GPU 和 xGPU 监控指标 |
| `huawei_get_cce_coredns_metrics` | 查询 | R3 | 读取 CoreDNS QPS、排除 NXDOMAIN 的错误率、NXDOMAIN 比例、P95 延迟、副本数以及 Pod CPU/内存指标 |
| `huawei_get_cce_nginx_ingress_metrics` | 查询 | R3 | 读取 nginx-ingress 请求处理指标和 Ingress TLS 证书过期状态 |
| `huawei_get_cce_autoscaler_metrics` | 查询 | R3 | 读取 Cluster Autoscaler 扩缩容指标、HPA 副本状态以及 autoscaler Pod CPU/内存指标 |
| `huawei_get_cce_apiserver_metrics` | 查询 | R3 | 读取 kube-apiserver QPS、错误率、延迟和 inflight 请求指标 |
| `huawei_get_cce_etcd_metrics` | 查询 | R3 | 读取 etcd leader、proposal、DB 大小、磁盘延迟、CPU 和内存指标 |
| `huawei_get_cce_controller_manager_metrics` | 查询 | R3 | 读取控制面 workqueue 深度、adds、retries、排队延迟和处理耗时指标 |
| `huawei_get_cce_scheduler_metrics` | 查询 | R3 | 读取 scheduler 调度尝试、待调度 Pod、调度延迟和队列指标 |
| `huawei_get_ecs_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 ECS 监控指标 |
| `huawei_get_elb_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 ELB 监控指标 |
| `huawei_get_eip_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 EIP 监控指标 |
| `huawei_get_nat_gateway_metrics` | 查询 | R3 | 通过 hcloud/CES 读取 NAT Gateway 监控指标 |
| `huawei_cce_cluster_monitoring_aggregation` | 查询 + 本地分析 | R3 | 汇总 Pod/Node/云资源监控并在本地做异常分类 |

## Tools

### CCE Metrics

| Tool | Purpose | Required parameters |
|------|---------|---------------------|
| `huawei_get_cce_pod_metrics_topN` | Get Pod CPU/memory/disk TopN | `region`, `cluster_id` |
| `huawei_get_cce_pod_metrics` | Get single Pod CPU/memory/disk time-series | `region`, `cluster_id`, `pod_name` |
| `huawei_get_cce_node_metrics_topN` | Get Node CPU/memory/disk TopN | `region`, `cluster_id` |
| `huawei_get_cce_node_metrics` | Get single Node time-series | `region`, `cluster_id`, `node_ip` |
| `huawei_get_cce_node_gpu_metrics` | Get single Node GPU and xGPU metrics | `region`, `cluster_id`, `node_ip` |
| `huawei_get_cce_pod_gpu_metrics` | Get single Pod GPU and xGPU metrics | `region`, `cluster_id`, `pod_name` |
| `huawei_get_cce_coredns_metrics` | Get CoreDNS QPS/error-rate excluding NXDOMAIN/NXDOMAIN-rate/P95/replicas/CPU/memory | `region`, `cluster_id` |
| `huawei_get_cce_nginx_ingress_metrics` | Get nginx-ingress request metrics and TLS certificate expiration | `region`, `cluster_id` |
| `huawei_get_cce_autoscaler_metrics` | Get Cluster Autoscaler and HPA metrics | `region`, `cluster_id` |
| `huawei_get_cce_apiserver_metrics` | Get kube-apiserver key metrics | `region`, `cluster_id` |
| `huawei_get_cce_etcd_metrics` | Get etcd key metrics | `region`, `cluster_id` |
| `huawei_get_cce_controller_manager_metrics` | Get controller-manager key metrics | `region`, `cluster_id` |
| `huawei_get_cce_scheduler_metrics` | Get scheduler key metrics | `region`, `cluster_id` |

### Cloud Resource Metrics

| Tool | Purpose | Required parameters |
|------|---------|---------------------|
| `huawei_get_ecs_metrics` | Get ECS CPU/memory/disk/network metrics | `region`, `instance_id` |
| `huawei_get_elb_metrics` | Get ELB connections, bandwidth, QPS | `region`, `elb_id` |
| `huawei_get_eip_metrics` | Get EIP bandwidth, traffic, packet rate | `region`, `eip_id` |
| `huawei_get_nat_gateway_metrics` | Get NAT SNAT connections, bandwidth | `region`, `nat_gateway_id` |

### Aggregation Tool

| Tool | Purpose | Required parameters |
|------|---------|---------------------|
| `huawei_cce_cluster_monitoring_aggregation` | Aggregate all cluster monitoring with anomaly detection | `region`, `cluster_id`, `start_time`, `end_time` |

## Usage

### CCE Pod Metrics

```bash
# Pod TopN
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=default \
  top_n=10 \
  hours=1

# Single Pod
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  pod_name=<pod-name> \
  namespace=default \
  hours=1

# Single Pod GPU and xGPU metrics
python3 scripts/huawei-cloud.py huawei_get_cce_pod_gpu_metrics \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  pod_name=<pod-name> \
  namespace=default \
  hours=1
```

### CCE Node Metrics

```bash
# Node TopN
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  top_n=10 \
  hours=1

# Single Node
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  node_ip=<node-ip> \
  hours=1

# Node GPU and xGPU metrics
python3 scripts/huawei-cloud.py huawei_get_cce_node_gpu_metrics \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  node_ip=<node-ip> \
  hours=1
```

### CoreDNS Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_coredns_metrics \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=kube-system \
  pod_regex=".*coredns.*" \
  hours=1
```

### nginx-ingress Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_nginx_ingress_metrics \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=kube-system \
  pod_regex=".*nginx.*ingress.*|.*ingress.*nginx.*" \
  ingress_namespace=default \
  cert_expire_warning_days=30 \
  hours=1
```

### Autoscaler Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_autoscaler_metrics \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  namespace=kube-system \
  pod_regex=".*cluster.*autoscaler.*|.*autoscaler.*" \
  include_hpa=true \
  hours=1
```

### Control Plane Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_apiserver_metrics \
  region=cn-north-4 cluster_id=<cluster-id> hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_etcd_metrics \
  region=cn-north-4 cluster_id=<cluster-id> namespace=kube-system hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_controller_manager_metrics \
  region=cn-north-4 cluster_id=<cluster-id> namespace=kube-system hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_scheduler_metrics \
  region=cn-north-4 cluster_id=<cluster-id> namespace=kube-system hours=1
```

### ECS Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_ecs_metrics \
  region=cn-north-4 \
  instance_id=<instance-id>
```

### ELB Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_elb_metrics \
  region=cn-north-4 \
  elb_id=<loadbalancer-id> \
  hours=1
```

### EIP Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_eip_metrics \
  region=cn-north-4 \
  eip_id=<eip-id> \
  hours=1
```

### NAT Gateway Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_nat_gateway_metrics \
  region=cn-north-4 \
  nat_gateway_id=<nat-gateway-id> \
  hours=1
```

### Cluster Monitoring Aggregation

```bash
# Aggregate all monitoring data for a cluster with anomaly detection
python3 scripts/huawei-cloud.py huawei_cce_cluster_monitoring_aggregation \
  region=cn-north-4 \
  cluster_id=<cluster-id> \
  start_time="2026-05-30 00:00:00" \
  end_time="2026-05-30 23:59:59" \
  namespace=default \
  top_n=10
```

This tool aggregates:
- Pod metrics (TopN CPU/memory)
- Node metrics (TopN CPU/memory/disk)
- ELB metrics (with LoadBalancer service association)
- NAT Gateway metrics
- EIP metrics (bandwidth, packet loss)
- Anomaly detection using 80% threshold

## Analysis Guidance

1. **Review results**: Focus on resources with high utilization or abnormal patterns
2. **Check thresholds**: CPU >80%, Memory >85% typically marked as critical
3. **Identify affected workloads**: Correlate high resource usage with application issues
4. **Correlate with events**: If metrics show anomalies, check `kubernetes-event-analyzer`

## Output Format

| Field | Description |
|-------|-------------|
| `success` | Query success status |
| `region` | Cloud region |
| `metrics` | Resource-specific metrics with values and units |
| `time_series` | Historical data points (where available) |

## References

- Workflow: `references/workflow.md`
- Risk rules: `references/risk-rules.md`
- Output schema: `references/output-schema.md`
