---
id: huawei-cloud-cce-metric-analyzer
name: huawei-cloud-cce-metric-analyzer
description: |
  Huawei Cloud CCE Metric analysis skill using the Python dispatcher with hcloud-backed cloud service queries.
  Use this skill when the user wants to: (1) query Pod/Node/CoreDNS/nginx-ingress/autoscaler/control-plane CPU, memory, disk, QPS, latency, request, connection, certificate, scaling, or error-rate metrics, (2) get resource usage TopN rankings, (3) query ECS/ELB/EIP/NAT cloud resource metrics, (4) aggregate cluster monitoring data with anomaly detection, (5) detect threshold-based resource anomalies.
  Trigger: user mentions "metric analysis", "指标分析", "CCE metrics", "CCE 指标", "AOM metrics", "AOM 指标", "CoreDNS metrics", "CoreDNS 指标", "nginx ingress metrics", "nginx-ingress 指标", "autoscaler metrics", "autoscaler 指标", "HPA metrics", "HPA 指标", "apiserver metrics", "etcd metrics", "controller manager metrics", "scheduler metrics", "control plane metrics", "控制面指标", "certificate expiration", "证书过期", "resource metrics", "资源指标", "CPU usage", "CPU 使用率", "memory usage", "内存使用率", "performance monitoring", "性能监控", "TopN", "resource ranking", "资源排名"
tags: [cce, metrics, aom, observability, analysis]
version: 1.0.0
---

# Huawei Cloud CCE Metric Analyzer

## Overview

Query and analyze metrics for CCE clusters (Pod/Node CPU/memory/disk) and cloud resources (ECS, ELB, EIP, NAT). Supports threshold-based anomaly detection,
status classification (critical/warning/normal), and full-cluster monitoring aggregation.

**Architecture**: `python3 scripts/huawei-cloud.py` dispatcher → hcloud (KooCLI) cloud service queries + signed AOM Prometheus HTTP queries + limited kubectl
reads only when Kubernetes resource relationships are required → Pod/Node metrics, ECS/ELB/EIP/NAT metrics → Threshold classification → Anomaly detection

> **Execution method**: Cloud service queries are executed through the local `hcloud` CLI. AOM Prometheus `query_range` calls are the only exception and use
> signed HTTPS requests because the required Prometheus range-query path is not compatible with hcloud. Do not call Huawei Cloud SDKs, curl IAM flows,
> openstack, or hand-written cloud APIs outside the bundled dispatcher.
> For AOM Prometheus range queries in `cn-north-7`, the dispatcher uses `aomperform.cn-north-7.myhuaweicloud.com`; other regions use
> `aom.<region>.myhuaweicloud.com`.

**Related Skills**: use pod/node diagnosers, Kubernetes event analyzer, capacity/cost skills, or auto-remediation runner for follow-up diagnosis or explicitly
requested remediation.

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

**Typical Use Cases**: query Pod/Node TopN, GPU/xGPU, CoreDNS, nginx-ingress, autoscaler, control-plane, ECS/ELB/EIP/NAT metrics, full-cluster aggregation, and
threshold-based anomaly detection.

## Prerequisites

### 1. Runtime Dependencies

- Python 3.8+ for the dispatcher and result processing
- hcloud (KooCLI) 7.2.2+ for CCE/ECS/ELB/VPC/EIP/NAT/CES/IAM cloud service queries
- `kubectl` only for Kubernetes resource reads that cannot be derived from AOM/hcloud, such as Pod `label_selector` filtering, Ingress TLS certificate checks,
  and LoadBalancer Service discovery for ELB/EIP association; clusters without external EIP require `kubectl cce`.
- Prometheus-related monitoring data is queried from AOM Prometheus with signed HTTPS requests; the cluster must have the Prometheus add-on integrated with AOM,
  otherwise these tools may return empty metric series
- Controller-manager, scheduler, and etcd metrics require the `kube-controller-manager`, `kube-scheduler`, and `etcd-server` ServiceMonitors to be enabled
  separately in AOM; otherwise these tools may return empty metric series
- Autoscaler, ingress-controller, and NVIDIA GPU metrics require the corresponding `autoscaler`, `ingress-controller`, and `nvidia-gpu-device-plugin`
  PodMonitors to be enabled separately in AOM; ingress request metrics also require `nginx_ingress_controller_requests` to be explicitly allowed in the
  ingress-controller PodMonitor
- Run environment check before first use (see Verification section)
- **kubectl cce dependency:** Use [huawei-cloud-kubectl-cce-installer](../huawei-cloud-kubectl-cce-installer/SKILL.md) for plugin availability, installation,
  credential handling, and command usage. Follow its [plugin usage](references/kubectl-cce.md) contract.

### 2. Credential Configuration

- Valid Huawei Cloud credentials via hcloud profile or AK/SK mode
- CLI callers may pass `--cli-access-key`, `--cli-secret-key`, and optional `--cli-security-token`. AK/SK must be supplied together, and a token requires
  that pair. They are passed explicitly to hcloud and `kubectl cce`; profile and authentication environment-variable fallback are disabled for the request.
  Do not combine them with conflicting `ak`, `sk`, or `security_token` values.
- **Security Rules**:
  - 🚫 Never expose AK/SK values in code, conversation, or commands
  - 🚫 Never use `echo $HW_ACCESS_KEY` or `echo $HW_SECRET_KEY` to check credentials
  - ✅ Credential priority for hcloud calls is: explicit tool parameters > local hcloud profile > environment variables
  - ✅ AOM Prometheus signed HTTP and Kubernetes certificate setup use explicit tool parameters first; when explicit AK/SK is supplied, no authentication
    environment variable is used as a signing fallback
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**Configuration Method**:

```bash
hcloud configure list

export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
export HW_REGION_NAME=<region>
```

### 3. Region Selection

- Use `region=<region>` from the current user request or established task context when it is available.
- If no `region` parameter is supplied, use `HW_REGION_NAME`.
- If neither source provides a region, return an error asking the user to provide `region` or set `HW_REGION_NAME`. Do not infer a target region from an hcloud profile or any other environment variable.

### 4. IAM Permission Requirements

| API Action               | Permission         | Purpose                                      |
| ------------------------ | ------------------ | -------------------------------------------- |
| `cce:cluster:get`        | Get cluster        | View CCE cluster details                     |
| `aom:instance:list`      | List AOM instances | Discover AOM Prometheus instance for metrics |
| `aom:metricsData:get`    | Get metrics data   | Query Pod/Node CPU/memory/disk metrics       |
| `ces:metricsData:get`    | Get CES metrics    | Query ECS/ELB/EIP/NAT cloud resource metrics |
| `ecs:cloudServers:list`  | List ECS servers   | Correlate ECS instance IDs                   |
| `elb:loadbalancers:list` | List ELB instances | Correlate ELB IDs                            |
| `vpc:eips:list`          | List EIPs          | Correlate EIP IDs                            |
| `nat:natGateways:list`   | List NAT Gateways  | Correlate NAT Gateway IDs                    |

**Permission Failure Handling**:

1. When any command fails due to IAM permission errors, display the required permission list
2. Guide the user to create a custom policy in the IAM console and grant authorization
3. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

All commands use the Python dispatcher script: `python3 scripts/huawei-cloud.py <action> <key=value>...`

## KooCLI命令格式标准

Do not ask users to run raw `hcloud` commands directly. Use the dispatcher format:

```bash
python3 scripts/huawei-cloud.py <tool-name> key=value key=value
```

The dispatcher converts cloud service queries to KooCLI calls. AOM Prometheus range queries use signed HTTPS requests because that path is not compatible with
hcloud. Avoid Kubernetes resource reads unless the tool explicitly needs Pod labels, Ingress TLS Secrets, or LoadBalancer Services. Quote values containing
spaces, `>`, `<`, `|`, JSON, or PromQL; never print or persist AK/SK, security tokens, kubeconfig files, or temporary payloads; keep Kubernetes/AOM PromQL
scoped with `cluster="<cluster_id>"`.

### 1. CCE Pod Metrics

```bash
# Pod TopN — cluster-wide CPU/memory ranking
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=<region> cluster_id=<cluster-id> \
  namespace=default top_n=10 hours=1

# Pod TopN with label selector
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=<region> cluster_id=<cluster-id> \
  namespace=default label_selector="app=nginx,version=v1" top_n=10 hours=1

# Single Pod time-series
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics \
  region=<region> cluster_id=<cluster-id> \
  pod_name=my-app-xxx namespace=default hours=1

# Single Pod GPU and xGPU metrics
python3 scripts/huawei-cloud.py huawei_get_cce_pod_gpu_metrics \
  region=<region> cluster_id=<cluster-id> \
  pod_name=my-gpu-app-xxx namespace=default hours=1
```

### 2. CCE Node Metrics

```bash
# Node TopN — cluster-wide CPU/memory/disk ranking
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN \
  region=<region> cluster_id=<cluster-id> \
  top_n=10 hours=1

# Single Node time-series
python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics \
  region=<region> cluster_id=<cluster-id> \
  node_ip=10.0.0.1 hours=1

# Node GPU and xGPU metrics
python3 scripts/huawei-cloud.py huawei_get_cce_node_gpu_metrics \
  region=<region> cluster_id=<cluster-id> \
  node_ip=10.0.0.1 hours=1
```

### 3. CCE CoreDNS Metrics

```bash
# CoreDNS key metrics: QPS, error rate excluding NXDOMAIN, NXDOMAIN rate, P95 latency, replicas, CPU, and memory
python3 scripts/huawei-cloud.py huawei_get_cce_coredns_metrics \
  region=<region> cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*coredns.*" hours=1
```

### 4. CCE nginx-ingress Metrics

```bash
# nginx-ingress request processing and Ingress TLS certificate expiration
python3 scripts/huawei-cloud.py huawei_get_cce_nginx_ingress_metrics \
  region=<region> cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*nginx.*ingress.*|.*ingress.*nginx.*" \
  ingress_namespace=default cert_expire_warning_days=30 hours=1
```

### 5. CCE Autoscaler Metrics

```bash
# Cluster Autoscaler and HPA metrics
python3 scripts/huawei-cloud.py huawei_get_cce_autoscaler_metrics \
  region=<region> cluster_id=<cluster-id> \
  namespace=kube-system pod_regex=".*cluster.*autoscaler.*|.*autoscaler.*" \
  include_hpa=true hours=1
```

### 6. Kubernetes Control Plane Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_apiserver_metrics \
  region=<region> cluster_id=<cluster-id> hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_etcd_metrics \
  region=<region> cluster_id=<cluster-id> hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_controller_manager_metrics \
  region=<region> cluster_id=<cluster-id> namespace=kube-system hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_scheduler_metrics \
  region=<region> cluster_id=<cluster-id> namespace=kube-system hours=1
```

### 7. Cloud Resource Metrics

```bash
# ECS instance metrics
python3 scripts/huawei-cloud.py huawei_get_ecs_metrics \
  region=<region> instance_id=<instance-id>

# ELB metrics
python3 scripts/huawei-cloud.py huawei_get_elb_metrics \
  region=<region> elb_id=<loadbalancer-id> hours=1

# EIP metrics
python3 scripts/huawei-cloud.py huawei_get_eip_metrics \
  region=<region> eip_id=<eip-id> hours=1

# NAT Gateway metrics
python3 scripts/huawei-cloud.py huawei_get_nat_gateway_metrics \
  region=<region> nat_gateway_id=<nat-gateway-id> hours=1
```

### 8. Cluster Monitoring Aggregation

```bash
# Aggregate all monitoring data with anomaly detection
python3 scripts/huawei-cloud.py huawei_cce_cluster_monitoring_aggregation \
  region=<region> cluster_id=<cluster-id> \
  start_time="2026-05-30 00:00:00" end_time="2026-05-30 23:59:59" \
  namespace=default top_n=10
```

This tool aggregates: Pod TopN CPU/memory, Node TopN CPU/memory/disk, ELB metrics (matched through LoadBalancer Services fetched by `kubectl`), NAT Gateway
metrics, EIP metrics (bandwidth, packet loss), and anomaly detection using 80% threshold.

It also includes CoreDNS, nginx-ingress, and autoscaler summaries. Cloud resources are scoped to the current cluster when an association can be proven: ELB is
matched through LoadBalancer Service IP/EIP, NAT Gateway is filtered by the cluster VPC, and EIP is limited to associated ELB/NAT/Service IPs.

LoadBalancer Service discovery uses `kubectl` with generated kubeconfig through the cluster EIP when external access is available. If the cluster has no EIP, it
uses the `kubectl cce` plugin. If neither path works, aggregation fails.

## Risk Levels

This skill is read-only. It does not create, update, delete, restart, scale, or modify Huawei Cloud or Kubernetes resources.

| Level | Meaning                                                                                                                       | Execution Guidance        |
| ----- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| R3    | No-risk read-only query or local analysis                                                                                     | May run automatically     |
| R2    | Low-risk change, such as creating monitoring configuration without deleting resources or increasing service capacity/cost     | Not used by current tools |
| R1    | Risky operation, such as restart-like impact, disabling protection, or changes that may increase cost or reduce observability | Not used by current tools |
| R0    | Critical operation, such as deleting clusters, applications, or broad-impact monitoring protections                           | Not used by current tools |

| Tool                                        | Operation Type         | Risk Level | Description                                                                                                                                                                             |
| ------------------------------------------- | ---------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `huawei_get_cce_pod_metrics_topN`           | Query                  | R3         | Read Pod CPU/memory/disk TopN metrics from AOM Prometheus                                                                                                                               |
| `huawei_get_cce_pod_metrics`                | Query                  | R3         | Read single Pod CPU/memory/disk time-series metrics                                                                                                                                     |
| `huawei_get_cce_node_metrics_topN`          | Query                  | R3         | Read Node CPU/memory/disk TopN metrics from AOM Prometheus                                                                                                                              |
| `huawei_get_cce_node_metrics`               | Query                  | R3         | Read single Node CPU/memory/disk time-series metrics                                                                                                                                    |
| `huawei_get_cce_node_gpu_metrics`           | Query                  | R3         | Read single Node GPU and xGPU metrics from AOM Prometheus                                                                                                                               |
| `huawei_get_cce_pod_gpu_metrics`            | Query                  | R3         | Read single Pod GPU and xGPU metrics from AOM Prometheus                                                                                                                                |
| `huawei_get_cce_coredns_metrics`            | Query                  | R3         | Read CoreDNS QPS, error rate excluding NXDOMAIN, NXDOMAIN rate, P95 latency, replicas, and per-Pod CPU/memory metrics                                                                   |
| `huawei_get_cce_nginx_ingress_metrics`      | Query                  | R3         | Read nginx-ingress request-processing metrics and Ingress TLS certificate expiration status; QPS falls back to nginx process request counters when request-dimension metrics are absent |
| `huawei_get_cce_autoscaler_metrics`         | Query                  | R3         | Read Cluster Autoscaler scaling metrics, HPA replica state, and autoscaler Pod CPU/memory metrics                                                                                       |
| `huawei_get_cce_apiserver_metrics`          | Query                  | R3         | Read kube-apiserver QPS, error rate, latency, and inflight request metrics                                                                                                              |
| `huawei_get_cce_etcd_metrics`               | Query                  | R3         | Read etcd leader, proposal, DB size, disk latency, CPU, and memory metrics                                                                                                              |
| `huawei_get_cce_controller_manager_metrics` | Query                  | R3         | Read control-plane workqueue depth, adds, retries, queue latency, and work duration metrics                                                                                             |
| `huawei_get_cce_scheduler_metrics`          | Query                  | R3         | Read scheduler attempts, pending Pods, scheduling latency, and queue metrics                                                                                                            |
| `huawei_get_ecs_metrics`                    | Query                  | R3         | Read ECS monitoring data through hcloud/CES                                                                                                                                             |
| `huawei_get_elb_metrics`                    | Query                  | R3         | Read ELB monitoring data through hcloud/CES                                                                                                                                             |
| `huawei_get_eip_metrics`                    | Query                  | R3         | Read EIP monitoring data through hcloud/CES                                                                                                                                             |
| `huawei_get_nat_gateway_metrics`            | Query                  | R3         | Read NAT Gateway monitoring data through hcloud/CES                                                                                                                                     |
| `huawei_cce_cluster_monitoring_aggregation` | Query + local analysis | R3         | Aggregate Pod/Node/cloud-resource metrics and classify anomalies locally                                                                                                                |

## Parameter Reference

### Input Parameter Validation

1. **Cluster-scoped metrics:** `huawei_get_cce_pod_metrics_topN`, `huawei_get_cce_pod_metrics`, `huawei_get_cce_pod_gpu_metrics`, `huawei_get_cce_node_metrics_topN`, `huawei_get_cce_node_metrics`, `huawei_get_cce_node_gpu_metrics`, `huawei_get_cce_coredns_metrics`, `huawei_get_cce_nginx_ingress_metrics`, `huawei_get_cce_autoscaler_metrics`, `huawei_get_cce_apiserver_metrics`, `huawei_get_cce_etcd_metrics`, `huawei_get_cce_controller_manager_metrics`, `huawei_get_cce_scheduler_metrics`, and `huawei_cce_cluster_monitoring_aggregation` require `region` and `cluster_id`, plus their tool-specific inputs. Validate `cluster_id` before any downstream query. When it is missing, stop and require the user to provide a cluster ID or cluster name; do not continue with an unscoped query. When a cluster value is supplied:
   - Standard UUID: call `hcloud CCE ShowCluster` to verify it; non-UUID value: call `hcloud CCE ListClusters`, perform an exact and unique cluster-name match, convert the match to its UUID, and then call `ShowCluster` to verify it.
   - Invalid, unmatched, or ambiguous value: stop and require the user to provide the correct region and cluster ID; never guess or select a cluster automatically.
2. **Cloud CES metrics:** `huawei_get_ecs_metrics` requires an explicit `instance_id`; `huawei_get_elb_metrics` requires an explicit `elb_id`; `huawei_get_eip_metrics` requires an explicit `eip_id`; and `huawei_get_nat_gateway_metrics` requires an explicit `nat_gateway_id`. Each also requires `region`, but does not require `cluster_id`. If the required resource ID is missing or invalid, stop and ask the user to provide the correct ID. Never use `hcloud list` to enumerate all cloud resources or poll metrics across resources as a fallback.
3. **Direct Pod and Node metrics:** `huawei_get_cce_pod_metrics` requires an explicit `pod_name`, and `huawei_get_cce_node_metrics` requires an explicit `node_ip`. If the target is missing, stop and ask the user to provide it. Query the supplied target directly through AOM PromQL; never enumerate Pods or nodes with `kubectl cce` and then poll their metrics. TopN tools are the explicit exception: they rank a cluster-scoped PromQL result in one query and do not poll resources individually.

See [Metric Tool Parameters](references/tool-parameters.md) for common parameters and every tool's parameters.

## Output Format

See [Output Schema](references/output-schema.md) for the JSON response structure.

**Key output fields**:

- `success` — boolean, true if query completed
- `region` — Huawei Cloud region
- `cluster_id` / `cluster_name` — CCE cluster identity
- `aom_instance_id` — AOM Prometheus instance used for metric queries
- `metrics` — Dict with cpu/memory/disk data per resource, including status classification
- `certificate_check` — nginx-ingress Ingress TLS certificate expiration summary when certificate checking is enabled
- `time_series` — Historical data points with `timestamp`, `time`, `average`, `min`, `max`
- `status` — Threshold classification: `critical` (>80% CPU, >85% memory/disk), `warning` (>50% CPU/memory, >70% disk), `normal` (below warning), `unknown` (no
  data)

## Workflow

1. Resolve region, cluster ID, and credentials using the documented priority.
2. Discover the AOM Prometheus instance from the CCE cluster add-on binding.
3. Start with Pod/Node TopN or aggregation, then drill into a Pod, Node, component, or cloud resource.
4. Keep PromQL scoped by `cluster="<cluster_id>"`; add namespace, pod, or resource filters only to reduce noise.
5. Use status classification as an investigation lead, then correlate anomalies with events or alarm history.

## Verification

1. Run `python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN region=<region> cluster_id=<cluster-id> namespace=default top_n=5` to verify Pod
   metric queries
2. Run `python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN region=<region> cluster_id=<cluster-id> top_n=5` to verify Node metric queries
3. Run `python3 scripts/huawei-cloud.py huawei_get_ecs_metrics region=<region> instance_id=<instance-id>` to verify CES metric connectivity

## Best Practices

1. Start with Pod/Node TopN before drilling into individual resources.
2. Keep `hours` small (1-4) for recent analysis; cap historical reviews at 24 hours.
3. Provide `namespace` to reduce Pod noise while preserving the cluster filter.
4. Focus on `critical` and `warning` resources first.
5. Use `huawei_cce_cluster_monitoring_aggregation` for full-cluster health checks.
6. Correlate metric anomalies with `huawei-cloud-cce-kubernetes-event-analyzer`.
7. Do not expose production Pod names, node IPs, or cluster IDs in public summaries.

## Notes

- This skill is strictly read-only and never modifies resources or configurations.
- Thresholds are predefined baselines; tune them against workload SLOs before making operational decisions.
- AK/SK must never be hardcoded; use hcloud profile for normal hcloud calls or environment fallback for signed AOM/Kubernetes calls.
- `scripts/huawei-cloud.py` is the only user-facing execution method
- AOM Prometheus instance is auto-discovered; no need to manually specify `aom_instance_id`
- Cloud resource metrics (ECS/ELB/EIP/NAT) use CES (Cloud Eye Service), not AOM
- Do not make automatic scaling or remediation decisions based solely on metric analysis.

## Troubleshooting

| Pitfall                                    | Symptom                             | Quick Fix                                                                                 |
| ------------------------------------------ | ----------------------------------- | ----------------------------------------------------------------------------------------- |
| Missing `cluster_id`                       | Action fails immediately            | Provide `cluster_id` from cluster listing                                                 |
| AOM Prometheus instance not found          | Metric queries return empty results | Ensure AOM Prom instance is created for the cluster; check `aom:instance:list` permission |
| Large time window without namespace filter | Slow response, too many results     | Narrow `hours` to 1-4 and add `namespace` filter                                          |
| Cloud resource ID not found                | ECS/ELB/EIP/NAT query returns error | Verify resource ID and CES IAM permission                                                 |
| Custom PromQL syntax error                 | Custom query returns empty          | Use default PromQL unless familiar with AOM PromQL                                        |
| Aggregation missing time range             | `start_time` / `end_time` missing   | Provide both time boundaries                                                              |

## Limitations

- AOM Prometheus data requires the cluster Prometheus add-on to be integrated with AOM.
- Control-plane ServiceMonitors and component PodMonitors must be enabled before related metrics appear.
- Query results reflect collected monitoring data only; missing series are not proof that the workload is healthy.
- This skill does not remediate, scale, restart, create, update, or delete cloud or Kubernetes resources.

## References

| Document                                                       | Description                                                             |
| -------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [Workflow](references/workflow.md)                             | Metric query sequence, threshold detection, next-step handoff           |
| [Risk Rules](references/risk-rules.md)                         | Read-only constraints, data redaction, time-bounding, threshold caveats |
| [Output Schema](references/output-schema.md)                   | JSON response schema for metric and status output                       |
| [CLI Installation Guide](references/cli-installation-guide.md) | hcloud, kubectl, kubectl-cce, and dispatcher setup                      |
| [IAM Policies](references/iam-policies.md)                     | Required read-only Huawei Cloud and Kubernetes permissions              |
| [Verification Method](references/verification-method.md)       | Static checks and smoke tests                                           |
| [Acceptance Criteria](references/acceptance-criteria.md)       | Functional, security, documentation, and quality gates                  |
