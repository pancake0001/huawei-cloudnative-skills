---
id: huawei-cloud-cce-metric-analyzer
name: huawei-cloud-cce-metric-analyzer
description: |
  Huawei Cloud CCE Metric analysis skill using the Python dispatcher with hcloud-backed cloud service queries.
  Use this skill when the user wants to: (1) query Pod/Node/CoreDNS/nginx-ingress/autoscaler/control-plane CPU, memory, disk, QPS, latency, request, connection, certificate, scaling, or error-rate metrics, (2) get resource usage TopN rankings, (3) query ECS/ELB/EIP/NAT cloud resource metrics, (4) aggregate cluster monitoring data with anomaly detection, (5) detect threshold-based resource anomalies.
  Trigger: user mentions "metric analysis", "指标分析", "CCE metrics", "CCE 指标", "AOM metrics", "AOM 指标", "CoreDNS metrics", "CoreDNS 指标", "nginx ingress metrics", "nginx-ingress 指标", "autoscaler metrics", "autoscaler 指标", "HPA metrics", "HPA 指标", "apiserver metrics", "etcd metrics", "controller manager metrics", "scheduler metrics", "control plane metrics", "控制面指标", "certificate expiration", "证书过期", "resource metrics", "资源指标", "CPU usage", "CPU 使用率", "memory usage", "内存使用率", "performance monitoring", "性能监控", "TopN", "resource ranking", "资源排名"
tags: [cce, metrics, aom, observability, analysis]
---

# Huawei Cloud CCE Metric Analyzer

## Overview

Query and analyze metrics for CCE clusters (Pod/Node CPU/memory/disk) and cloud resources (ECS, ELB, EIP, NAT). Supports threshold-based anomaly detection, status classification (critical/warning/normal), and full-cluster monitoring aggregation.

**Architecture**: `python3 scripts/huawei-cloud.py` dispatcher → hcloud (KooCLI) cloud service queries + signed AOM Prometheus HTTP queries + Kubernetes client → Pod/Node metrics, ECS/ELB/EIP/NAT metrics → Threshold classification → Anomaly detection

> **Execution method**: Cloud service queries are executed through the local `hcloud` CLI. AOM Prometheus `query_range` calls are the only exception and use signed HTTPS requests because the required Prometheus range-query path is not compatible with hcloud. Do not call Huawei Cloud SDKs, curl IAM flows, openstack, or hand-written cloud APIs outside the bundled dispatcher.

**Related Skills**:
- `huawei-cloud-cce-pod-failure-diagnoser` - Pod CrashLoopBackOff, OOMKilled, restart storms
- `huawei-cloud-cce-node-failure-diagnoser` - Node health, resource pressure diagnosis
- `huawei-cloud-cce-kubernetes-event-analyzer` - Warning events, failure patterns
- `huawei-cloud-cce-capacity-trend-forecaster` - Capacity planning and trend forecasting
- `huawei-cloud-cce-cost-optimization-advisor` - Resource cost optimization
- `huawei-cloud-cce-auto-remediation-runner` - Remediation actions (scale, resize, drain)

**Capabilities**:
- Pod CPU/memory TopN ranking and single Pod time-series metrics
- Node CPU/memory/disk TopN ranking and single Node time-series metrics
- Node GPU and xGPU metrics, including GPU utilization, memory, temperature, power, schedule policy, xGPU allocation, usage, and health
- CoreDNS QPS, error rate excluding NXDOMAIN, NXDOMAIN rate, P95 latency, replica count, and per-Pod CPU/memory metrics
- nginx-ingress QPS, 4xx/5xx rate, success rate, P95 latency, active connections, per-Pod CPU/memory, and Ingress TLS certificate expiration status
- Autoscaler unschedulable Pods, node state count, scale-up/down events, errors, node groups, HPA current/desired replicas, and per-Pod CPU/memory metrics
- Kubernetes control-plane metrics for apiserver, etcd, controller-manager, and scheduler
- ECS instance CPU/memory/disk/network metrics
- ELB connection, bandwidth, QPS metrics
- EIP bandwidth, traffic, packet loss metrics
- NAT Gateway SNAT connection metrics
- Full-cluster monitoring aggregation with anomaly detection (80% threshold)
- Threshold-based status classification (critical/warning/normal/unknown)

**Typical Use Cases**:

- "Show Pods with the highest CPU usage in my cluster"
- "Get Node memory usage ranking"
- "Get GPU and xGPU metrics for a CCE node"
- "Check CoreDNS QPS, latency, and error rate"
- "Check nginx-ingress request latency, 5xx rate, and TLS certificate expiration"
- "Check autoscaler scaling activity and HPA replica gaps"
- "Check apiserver, etcd, controller-manager, and scheduler key metrics"
- "Check ECS instance resource metrics"
- "What is the ELB QPS for my load balancer?"
- "Show EIP bandwidth usage"
- "Aggregate all monitoring data for the cluster"
- "Which resources have exceeded critical thresholds?"
- "Detect resource anomalies in the last hour"

## Prerequisites

### 1. Runtime Dependencies

- Python 3.8+ for the dispatcher and result processing
- hcloud (KooCLI) 7.2.2+ for CCE/ECS/ELB/VPC/EIP/NAT/CES/IAM cloud service queries
- Kubernetes Python client for reading in-cluster Pod/Node/Service details after hcloud creates short-lived CCE cluster credentials
- AOM Prometheus range queries use signed HTTPS requests with AK/SK because the hcloud AOM Prometheus query path is not compatible with the required query_range API
- Controller-manager and scheduler metrics require the corresponding ServiceMonitor to be enabled separately in AOM; otherwise these tools may return empty metric series
- Run environment check before first use (see Verification section)

### 2. Credential Configuration

- Valid Huawei Cloud credentials via hcloud profile or AK/SK mode
- **Security Rules**:
  - 🚫 Never expose AK/SK values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_AK` or `echo $HUAWEI_SK` to check credentials
  - ✅ Credential priority for hcloud calls is: explicit tool parameters > local hcloud profile > environment variables
  - ✅ AOM Prometheus signed HTTP and Kubernetes certificate setup cannot use encrypted hcloud profile material, so they use explicit tool parameters first and environment variables as the signing fallback
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**Configuration Method**:

```bash
hcloud configure list

# Optional environment variable fallback
export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_REGION=cn-north-4
```

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 3. IAM Permission Requirements

| API Action                      | Permission          | Purpose                                    |
| ------------------------------- | ------------------- | ------------------------------------------ |
| `cce:cluster:get`               | Get cluster         | View CCE cluster details                   |
| `aom:instance:list`             | List AOM instances  | Discover AOM Prometheus instance for metrics |
| `aom:metricsData:get`           | Get metrics data    | Query Pod/Node CPU/memory/disk metrics     |
| `ces:metricsData:get`           | Get CES metrics     | Query ECS/ELB/EIP/NAT cloud resource metrics |
| `ecs:cloudServers:list`         | List ECS servers    | Correlate ECS instance IDs                 |
| `elb:loadbalancers:list`        | List ELB instances  | Correlate ELB IDs                          |
| `vpc:eips:list`                 | List EIPs           | Correlate EIP IDs                          |
| `nat:natGateways:list`          | List NAT Gateways   | Correlate NAT Gateway IDs                  |

**Permission Failure Handling**:

1. When any command fails due to IAM permission errors, display the required permission list
2. Guide the user to create a custom policy in the IAM console and grant authorization
3. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

All commands use the Python dispatcher script: `python3 scripts/huawei-cloud.py <action> <key=value>...`

### 1. CCE Pod Metrics

```bash
# Pod TopN — cluster-wide CPU/memory ranking
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=default top_n=10 hours=1

# Pod TopN with label selector
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=default label_selector="app=nginx,version=v1" top_n=10 hours=1

# Single Pod time-series
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  pod_name=my-app-xxx namespace=default hours=1
```

### 2. CCE Node Metrics

```bash
# Node TopN — cluster-wide CPU/memory/disk ranking
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN \
  region=cn-north-4 cluster_id=<cluster-id> \
  top_n=10 hours=1

# Single Node time-series
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  node_ip=10.0.0.1 hours=1

# Node GPU and xGPU metrics
python3 scripts/huawei-cloud.py huawei_get_cce_node_gpu_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  node_ip=10.0.0.1 hours=1
```

### 3. CCE CoreDNS Metrics

```bash
# CoreDNS key metrics: QPS, error rate excluding NXDOMAIN, NXDOMAIN rate, P95 latency, replicas, CPU, and memory
python3 scripts/huawei-cloud.py huawei_get_cce_coredns_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*coredns.*" hours=1
```

### 4. CCE nginx-ingress Metrics

```bash
# nginx-ingress request processing and Ingress TLS certificate expiration
python3 scripts/huawei-cloud.py huawei_get_cce_nginx_ingress_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*nginx.*ingress.*|.*ingress.*nginx.*" \
  ingress_namespace=default cert_expire_warning_days=30 hours=1
```

### 5. CCE Autoscaler Metrics

```bash
# Cluster Autoscaler and HPA metrics
python3 scripts/huawei-cloud.py huawei_get_cce_autoscaler_metrics \
  region=cn-north-4 cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*cluster.*autoscaler.*|.*autoscaler.*" \
  include_hpa=true hours=1
```

### 6. Kubernetes Control Plane Metrics

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

### 7. Cloud Resource Metrics

```bash
# ECS instance metrics
python3 scripts/huawei-cloud.py huawei_get_ecs_metrics \
  region=cn-north-4 instance_id=<instance-id>

# ELB metrics
python3 scripts/huawei-cloud.py huawei_get_elb_metrics \
  region=cn-north-4 elb_id=<loadbalancer-id> hours=1

# EIP metrics
python3 scripts/huawei-cloud.py huawei_get_eip_metrics \
  region=cn-north-4 eip_id=<eip-id> hours=1

# NAT Gateway metrics
python3 scripts/huawei-cloud.py huawei_get_nat_gateway_metrics \
  region=cn-north-4 nat_gateway_id=<nat-gateway-id> hours=1
```

### 8. Cluster Monitoring Aggregation

```bash
# Aggregate all monitoring data with anomaly detection
python3 scripts/huawei-cloud.py huawei_cce_cluster_monitoring_aggregation \
  region=cn-north-4 cluster_id=<cluster-id> \
  start_time="2026-05-30 00:00:00" end_time="2026-05-30 23:59:59" \
  namespace=default top_n=10
```

This tool aggregates: Pod TopN CPU/memory, Node TopN CPU/memory/disk, ELB metrics (with LoadBalancer service association), NAT Gateway metrics, EIP metrics (bandwidth, packet loss), and anomaly detection using 80% threshold.

## Risk Levels

This skill is read-only. It does not create, update, delete, restart, scale, or modify Huawei Cloud or Kubernetes resources.

| Level | Meaning | Execution Guidance |
| ----- | ------- | ------------------ |
| R3 | No-risk read-only query or local analysis | May run automatically |
| R2 | Low-risk change, such as creating monitoring configuration without deleting resources or increasing service capacity/cost | Not used by current tools |
| R1 | Risky operation, such as restart-like impact, disabling protection, or changes that may increase cost or reduce observability | Not used by current tools |
| R0 | Critical operation, such as deleting clusters, applications, or broad-impact monitoring protections | Not used by current tools |

| Tool | Operation Type | Risk Level | Description |
| ---- | -------------- | ---------- | ----------- |
| `huawei_get_cce_pod_metrics_topN` | Query | R3 | Read Pod CPU/memory/disk TopN metrics from AOM Prometheus |
| `huawei_get_cce_pod_metrics` | Query | R3 | Read single Pod CPU/memory/disk time-series metrics |
| `huawei_get_cce_node_metrics_topN` | Query | R3 | Read Node CPU/memory/disk TopN metrics from AOM Prometheus |
| `huawei_get_cce_node_metrics` | Query | R3 | Read single Node CPU/memory/disk time-series metrics |
| `huawei_get_cce_node_gpu_metrics` | Query | R3 | Read single Node GPU and xGPU metrics from AOM Prometheus |
| `huawei_get_cce_coredns_metrics` | Query | R3 | Read CoreDNS QPS, error rate excluding NXDOMAIN, NXDOMAIN rate, P95 latency, replicas, and per-Pod CPU/memory metrics |
| `huawei_get_cce_nginx_ingress_metrics` | Query | R3 | Read nginx-ingress request-processing metrics and Ingress TLS certificate expiration status |
| `huawei_get_cce_autoscaler_metrics` | Query | R3 | Read Cluster Autoscaler scaling metrics, HPA replica state, and autoscaler Pod CPU/memory metrics |
| `huawei_get_cce_apiserver_metrics` | Query | R3 | Read kube-apiserver QPS, error rate, latency, and inflight request metrics |
| `huawei_get_cce_etcd_metrics` | Query | R3 | Read etcd leader, proposal, DB size, disk latency, CPU, and memory metrics |
| `huawei_get_cce_controller_manager_metrics` | Query | R3 | Read control-plane workqueue depth, adds, retries, queue latency, and work duration metrics |
| `huawei_get_cce_scheduler_metrics` | Query | R3 | Read scheduler attempts, pending Pods, scheduling latency, and queue metrics |
| `huawei_get_ecs_metrics` | Query | R3 | Read ECS monitoring data through hcloud/CES |
| `huawei_get_elb_metrics` | Query | R3 | Read ELB monitoring data through hcloud/CES |
| `huawei_get_eip_metrics` | Query | R3 | Read EIP monitoring data through hcloud/CES |
| `huawei_get_nat_gateway_metrics` | Query | R3 | Read NAT Gateway monitoring data through hcloud/CES |
| `huawei_cce_cluster_monitoring_aggregation` | Query + local analysis | R3 | Aggregate Pod/Node/cloud-resource metrics and classify anomalies locally |

## Parameter Reference

### Common Parameters

| Parameter    | Required/Optional | Description          | Default         |
| ------------ | ----------------- | -------------------- | --------------- |
| `region`     | Required          | Huawei Cloud region  | `HUAWEI_REGION` |
| `cluster_id` | Required          | CCE cluster ID       | N/A             |
| `namespace`  | Recommended       | Kubernetes namespace | `default`       |
| `ak`         | Optional          | Explicit AK; highest priority for all calls | profile/env fallback |
| `sk`         | Optional          | Explicit SK; highest priority for all calls | profile/env fallback |
| `project_id` | Optional          | Explicit Project ID; hcloud uses profile before env fallback | Auto from IAM/profile |

### `huawei_get_cce_pod_metrics_topN` Parameters

| Parameter       | Required | Description                     | Default  |
| --------------- | -------- | ------------------------------- | -------- |
| `namespace`     | No       | Namespace filter                | all      |
| `label_selector`| No       | Label selector (e.g. app=web)  | N/A      |
| `top_n`         | No       | Number of top items             | 10       |
| `hours`         | No       | Metrics lookback hours          | 1        |
| `node_ip`       | No       | Filter Pods on specific node    | N/A      |
| `cpu_query`     | No       | Custom CPU PromQL               | Auto     |
| `memory_query`  | No       | Custom memory PromQL            | Auto     |
| `disk_query`    | No       | Custom disk PromQL              | Auto     |

### `huawei_get_cce_pod_metrics` Parameters

| Parameter    | Required | Description                | Default  |
| ------------ | -------- | -------------------------- | -------- |
| `pod_name`   | Yes      | Target Pod name            | N/A      |
| `namespace`  | No       | Namespace                  | `default`|
| `hours`      | No       | Metrics lookback hours     | 1        |
| `cpu_query`  | No       | Custom CPU PromQL          | Auto     |
| `memory_query` | No     | Custom memory PromQL       | Auto     |
| `disk_query` | No       | Custom disk PromQL         | Auto     |

### `huawei_get_cce_node_metrics_topN` Parameters

| Parameter   | Required | Description                 | Default  |
| ----------- | -------- | --------------------------- | -------- |
| `top_n`     | No       | Number of top items         | 10       |
| `hours`     | No       | Metrics lookback hours      | 1        |

### `huawei_get_cce_node_metrics` Parameters

| Parameter  | Required | Description                 | Default  |
| ---------- | -------- | --------------------------- | -------- |
| `node_ip`  | Yes      | Target Node IP              | N/A      |
| `hours`    | No       | Metrics lookback hours      | 1        |

### `huawei_get_cce_node_gpu_metrics` Parameters

| Parameter | Required | Description | Default |
| --------- | -------- | ----------- | ------- |
| `node_ip` | Yes | Target Node IP or node name | N/A |
| `hours` | No | Metrics lookback hours | 1 |
| `gpu_selector` | No | Custom GPU metric label selector. Use this when GPU metrics do not use the `node` label | `node=~"<node_ip>|<node_name>"` |
| `utilization_query` | No | Custom `cce_gpu_utilization` PromQL | Auto |
| `memory_utilization_query` | No | Custom `cce_gpu_memory_utilization` PromQL | Auto |
| `memory_used_query` | No | Custom `cce_gpu_memory_used` PromQL | Auto |
| `memory_total_query` | No | Custom `cce_gpu_memory_total` PromQL | Auto |
| `memory_free_query` | No | Custom `cce_gpu_memory_free` PromQL | Auto |
| `temperature_query` | No | Custom `cce_gpu_temperature` PromQL | Auto |
| `power_usage_query` | No | Custom `cce_gpu_power_usage` PromQL | Auto |
| `schedule_policy_query` | No | Custom `gpu_schedule_policy` PromQL for xGPU mode detection | Auto |
| `xgpu_memory_total_query` | No | Custom `xgpu_memory_total` PromQL | Auto |
| `xgpu_memory_used_query` | No | Custom `xgpu_memory_used` PromQL | Auto |
| `xgpu_core_total_query` | No | Custom `xgpu_core_percentage_total` PromQL | Auto |
| `xgpu_core_used_query` | No | Custom `xgpu_core_percentage_used` PromQL | Auto |
| `xgpu_device_health_query` | No | Custom `xgpu_device_health` PromQL | Auto |

### `huawei_get_cce_coredns_metrics` Parameters

| Parameter | Required | Description | Default |
| --------- | -------- | ----------- | ------- |
| `namespace` | No | CoreDNS namespace | `kube-system` |
| `pod_regex` | No | Regex used to match CoreDNS Pods | `.*coredns.*` |
| `hours` | No | Metrics lookback hours | 1 |
| `qps_query` | No | Custom CoreDNS QPS PromQL | Auto |
| `error_rate_query` | No | Custom CoreDNS error-rate PromQL. The default excludes NXDOMAIN because Kubernetes search domains commonly generate NXDOMAIN responses | Auto |
| `nxdomain_rate_query` | No | Custom CoreDNS NXDOMAIN-rate PromQL for reference only | Auto |
| `latency_p95_query` | No | Custom CoreDNS P95 latency PromQL | Auto |
| `cpu_query` | No | Custom CoreDNS CPU PromQL | Auto |
| `memory_query` | No | Custom CoreDNS memory PromQL | Auto |
| `replicas_query` | No | Custom CoreDNS replica-count PromQL | Auto |

### `huawei_get_cce_nginx_ingress_metrics` Parameters

| Parameter | Required | Description | Default |
| --------- | -------- | ----------- | ------- |
| `namespace` | No | Namespace of nginx-ingress controller Pods. Use an empty value to query all namespaces | `kube-system` |
| `pod_regex` | No | Regex used to match nginx-ingress controller Pods | `.*nginx.*ingress.*|.*ingress.*nginx.*` |
| `ingress_namespace` | No | Namespace filter for Ingress TLS certificate checks | all |
| `hours` | No | Metrics lookback hours | 1 |
| `cert_expire_warning_days` | No | Days before expiry to mark certificates as warning | 30 |
| `check_certificates` | No | Whether to inspect Ingress TLS Secrets for expiration status | true |
| `qps_query` | No | Custom nginx-ingress QPS PromQL | Auto |
| `http_4xx_query` | No | Custom nginx-ingress 4xx QPS PromQL | Auto |
| `http_5xx_query` | No | Custom nginx-ingress 5xx QPS PromQL | Auto |
| `success_rate_query` | No | Custom nginx-ingress success-rate PromQL | Auto |
| `latency_p95_query` | No | Custom nginx-ingress P95 latency PromQL | Auto |
| `active_connections_query` | No | Custom nginx active-connections PromQL | Auto |
| `cpu_query` | No | Custom nginx-ingress CPU PromQL | Auto |
| `memory_query` | No | Custom nginx-ingress memory PromQL | Auto |

### `huawei_get_cce_autoscaler_metrics` Parameters

| Parameter | Required | Description | Default |
| --------- | -------- | ----------- | ------- |
| `namespace` | No | Namespace of Cluster Autoscaler Pods. Use an empty value to query all namespaces | `kube-system` |
| `pod_regex` | No | Regex used to match autoscaler Pods | `.*cluster.*autoscaler.*|.*autoscaler.*` |
| `hpa_namespace` | No | Namespace filter for HPA replica metrics | all |
| `hours` | No | Metrics lookback hours | 1 |
| `include_hpa` | No | Whether to query HPA current/desired replica metrics | true |
| `unschedulable_pods_query` | No | Custom unschedulable Pods PromQL | Auto |
| `nodes_count_query` | No | Custom autoscaler node-state count PromQL | Auto |
| `scale_up_query` | No | Custom scale-up event PromQL | Auto |
| `scale_down_query` | No | Custom scale-down event PromQL | Auto |
| `errors_query` | No | Custom autoscaler error PromQL | Auto |
| `node_groups_query` | No | Custom autoscaler node-group PromQL | Auto |
| `hpa_current_replicas_query` | No | Custom HPA current replicas PromQL | Auto |
| `hpa_desired_replicas_query` | No | Custom HPA desired replicas PromQL | Auto |
| `cpu_query` | No | Custom autoscaler Pod CPU PromQL | Auto |
| `memory_query` | No | Custom autoscaler Pod memory PromQL | Auto |

### Kubernetes Control Plane Tool Parameters

Applies to `huawei_get_cce_apiserver_metrics`, `huawei_get_cce_etcd_metrics`, `huawei_get_cce_controller_manager_metrics`, and `huawei_get_cce_scheduler_metrics`.

`huawei_get_cce_apiserver_metrics` defaults to `cluster="<cluster_id>",component="apiserver"` and does not add namespace or Pod labels. Its default P95 latency excludes `WATCH|CONNECT` requests and also returns `latency_p95_by_verb_ms` for diagnosis. Use `metric_selector` only when the Prometheus labels differ.

`huawei_get_cce_controller_manager_metrics` defaults to `cluster="<cluster_id>"` because CCE AOM workqueue metrics may not expose stable controller-manager Pod labels. It returns both aggregate workqueue metrics and per-queue `name` breakdowns.

`huawei_get_cce_scheduler_metrics` defaults to `cluster="<cluster_id>"` and returns aggregate metrics plus `result`, `profile/result`, and `queue` breakdowns.

Controller-manager and scheduler metrics depend on AOM ServiceMonitor collection being enabled for those control-plane endpoints. If ServiceMonitor is not enabled, the tools can run successfully but return empty series.

| Parameter | Required | Description | Default |
| --------- | -------- | ----------- | ------- |
| `namespace` | No | Namespace of control-plane Pods. Use an empty value to query all namespaces | `kube-system` |
| `pod_regex` | No | Regex used to match target component Pods | component-specific |
| `metric_selector` | No | Custom apiserver/controller-manager/scheduler metric label selector | apiserver: `cluster="<cluster_id>",component="apiserver"`; controller-manager/scheduler: `cluster="<cluster_id>"` |
| `hours` | No | Metrics lookback hours | 1 |

### `huawei_get_ecs_metrics` Parameters

| Parameter     | Required | Description                | Default  |
| ------------- | -------- | -------------------------- | -------- |
| `instance_id` | Yes      | ECS instance ID            | N/A      |

### `huawei_get_elb_metrics` Parameters

| Parameter | Required | Description                | Default  |
| --------- | -------- | -------------------------- | -------- |
| `elb_id`  | Yes      | ELB loadbalancer ID        | N/A      |
| `hours`   | No       | Metrics lookback hours     | 1        |

### `huawei_get_eip_metrics` Parameters

| Parameter | Required | Description                | Default  |
| --------- | -------- | -------------------------- | -------- |
| `eip_id`  | Yes      | EIP ID                     | N/A      |
| `hours`   | No       | Metrics lookback hours     | 1        |

### `huawei_get_nat_gateway_metrics` Parameters

| Parameter        | Required | Description                | Default  |
| ---------------- | -------- | -------------------------- | -------- |
| `nat_gateway_id` | Yes      | NAT Gateway ID             | N/A      |
| `hours`          | No       | Metrics lookback hours     | 1        |

### `huawei_cce_cluster_monitoring_aggregation` Parameters

| Parameter     | Required | Description                     | Default  |
| ------------- | -------- | ------------------------------- | -------- |
| `start_time`  | Yes      | Start time (YYYY-MM-DD HH:MM:SS)| N/A      |
| `end_time`    | Yes      | End time (YYYY-MM-DD HH:MM:SS)  | N/A      |
| `namespace`   | No       | Namespace filter                | `default`|
| `top_n`       | No       | Number of top items             | 10       |

## Output Format

See [Output Schema](references/output-schema.md) for the complete JSON response structure.

**Key output fields**:
- `success` — boolean, true if query completed
- `region` — Huawei Cloud region
- `cluster_id` / `cluster_name` — CCE cluster identity
- `aom_instance_id` — AOM Prometheus instance used for metric queries
- `metrics` — Dict with cpu/memory/disk data per resource, including status classification
- `certificate_check` — nginx-ingress Ingress TLS certificate expiration summary when certificate checking is enabled
- `time_series` — Historical data points with `timestamp`, `time`, `average`, `min`, `max`
- `status` — Threshold classification: `critical` (>80% CPU, >85% memory/disk), `warning` (>50% CPU/memory, >70% disk), `normal` (below warning), `unknown` (no data)

**Cloud resource metric fields** (ECS/ELB/EIP/NAT):
- ECS: `cpu_util`, `mem_util`, `disk_util`, `network_incoming/outgoing_bytes_rate`, `disk_read/write_bytes_rate`
- ELB: `m1_cps`, `m14_l7_rt`, `mb_l7_qps`, `mc-me-mf_l7_http_2xx-5xx`
- EIP: `upstream/downstream_bandwidth`, `upstream/downstream_bandwidth_usage`, `upstream/downstream_traffic`, `packet_loss_rate`
- NAT: `snat_connection`, `inbound/outbound_bandwidth`, `snat_connection_ratio`

## Verification

1. Run `python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN region=cn-north-4 cluster_id=<cluster-id> namespace=default top_n=5` to verify Pod metric queries
2. Run `python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN region=cn-north-4 cluster_id=<cluster-id> top_n=5` to verify Node metric queries
3. Run `python3 scripts/huawei-cloud.py huawei_get_ecs_metrics region=cn-north-4 instance_id=<instance-id>` to verify CES metric connectivity

## Best Practices

1. **Start with TopN for cluster-wide overview** — use Pod/Node TopN before drilling into individual resources
2. **Time-bound queries** — keep `hours` small (1-4) for recent analysis; cap at 24 hours for historical reviews
3. **Use namespace filtering** — always provide `namespace` to reduce noise in Pod TopN results
4. **Check status classification** — focus on `critical` and `warning` resources first; `normal` resources can be skipped
5. **Use aggregation for full-cluster health checks** — `huawei_cce_cluster_monitoring_aggregation` gives a one-shot overview of all resource metrics with anomaly detection
6. **Correlate with events** — if metrics show anomalies, check `huawei-cloud-cce-kubernetes-event-analyzer` for related warning events
7. **Hand off, don't remediate** — this skill is read-only; hand off to diagnosis skills for root cause analysis
8. **Sanitize output** — do not expose production pod names, node IPs, or cluster IDs in public summaries; use redacted examples

## Reference Documents

| Document                                | Description                              |
| --------------------------------------- | ---------------------------------------- |
| [Workflow](references/workflow.md)      | Metric query sequence, Pod/Node workflows, threshold detection, next-step handoff |
| [Risk Rules](references/risk-rules.md)  | Read-only constraints, data redaction rules, time-bounding, threshold caveats |
| [Output Schema](references/output-schema.md) | JSON response format for CCE metrics, cloud resource metrics, time-series, status values |

## Notes

- This skill is **strictly read-only** — it only queries and analyzes metrics; no modifications are made to resources or configurations
- Thresholds (CPU >80%, Memory >85%, Disk >85%) are **predefined baselines** — actual thresholds may vary by workload SLO; recommend users customize thresholds based on their specific requirements
- AK/SK must **never** be hardcoded — use explicit parameters only for one-off debugging, hcloud profiles for normal hcloud calls, or environment variables as fallback for signed AOM Prometheus/Kubernetes certificate calls
- The Python dispatcher script (`scripts/huawei-cloud.py`) is still the **only user-facing execution method**; metric cloud service calls inside the dispatcher use hcloud rather than direct Python SDK/API calls
- AOM Prometheus instance is **auto-discovered** — no need to manually specify `aom_instance_id`
- Cloud resource metrics (ECS/ELB/EIP/NAT) use CES (Cloud Eye Service), not AOM
- Do not make automatic scaling or remediation decisions based solely on metric analysis — forward to `huawei-cloud-cce-auto-remediation-runner` only if explicitly requested and validated

## Common Pitfalls

| Pitfall                                    | Symptom                               | Quick Fix                                    |
| ------------------------------------------ | ------------------------------------- | -------------------------------------------- |
| Missing `cluster_id`                       | Action fails immediately              | Provide `cluster_id` from cluster listing    |
| AOM Prometheus instance not found          | Metric queries return empty results   | Ensure AOM Prom instance is created for the cluster; check `aom:instance:list` permission |
| Large time window without namespace filter | Slow response, too many results       | Narrow `hours` to 1-4 and add `namespace` filter |
| Cloud resource ID not found                | ECS/ELB/EIP/NAT query returns error   | Verify resource ID exists; check CES IAM permission |
| Custom PromQL syntax error                 | `cpu_query` / `memory_query` returns empty | Use default auto-generated PromQL; only customize if familiar with AOM PromQL syntax |
| Permission denied on CES metrics           | Cloud resource metrics fail           | Verify `ces:metricsData:get` IAM permission |
| Aggregation missing time range             | `start_time` / `end_time` required but not provided | Always specify both time boundaries for aggregation queries |
| Node IP format mismatch                    | Single Node metrics fail              | Use the exact node IP as shown in cluster node listing (e.g. `10.0.0.1`) |
