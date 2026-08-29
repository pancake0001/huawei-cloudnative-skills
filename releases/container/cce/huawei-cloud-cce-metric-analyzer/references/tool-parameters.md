# Metric Tool Parameters

## Common Parameters

| Parameter | Required/Optional | Description | Default |
| --- | --- | --- | --- |
| `region` | Required | Region from request context or explicit user input | `HW_REGION_NAME`; otherwise prompt |
| `cluster_id` | Required for Pod And Node Metrics, Add-on Metrics, Kubernetes Control Plane Metrics, and Cluster Monitoring Aggregation | CCE cluster UUID, or an exact cluster name resolved by hcloud | N/A |
| `namespace` | Recommended | Kubernetes namespace | `default` |
| `ak` | Optional | Explicit AK; highest priority for all calls | profile/env fallback |
| `sk` | Optional | Explicit SK; highest priority for all calls | profile/env fallback |
| `project_id` | Optional | Explicit Project ID; hcloud uses profile before env fallback | Auto from IAM/profile |
| `security_token` | Optional | STS security token paired with temporary AK/SK | Environment fallback |
| `--cli-access-key` / `--cli-secret-key` | Optional | Explicit AK/SK for hcloud and `kubectl cce` | Overrides profile/environment |
| `--cli-security-token` | Optional | STS token paired with explicit CLI AK/SK | Passed to hcloud and `kubectl cce` |

## Pod And Node Metrics

### `huawei_get_cce_pod_metrics_topN`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `namespace` | No | Namespace filter | all |
| `label_selector` | No | Label selector, for example `app=web` | N/A |
| `top_n` | No | Number of top items | 10 |
| `hours` | No | Metrics lookback hours | 1 |
| `node_ip` | No | Filter Pods on a specific node | N/A |
| `cpu_query` / `memory_query` / `disk_query` | No | Custom PromQL | Auto |

### `huawei_get_cce_pod_metrics`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `pod_name` | Yes | Target Pod name | N/A |
| `namespace` | No | Namespace | `default` |
| `hours` | No | Metrics lookback hours | 1 |
| `cpu_query` / `memory_query` / `disk_query` | No | Custom PromQL | Auto |

### `huawei_get_cce_pod_gpu_metrics`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `pod_name` | Yes | Target Pod name | N/A |
| `namespace` | No | Target Pod namespace | all |
| `hours` | No | Metrics lookback hours | 1 |
| `gpu_selector` | No | Custom GPU metric label selector | `pod="<pod_name>",namespace="<namespace>"` |
| `utilization_query` / `memory_utilization_query` | No | Custom GPU utilization PromQL | Auto |
| `memory_used_query` / `memory_total_query` / `memory_free_query` | No | Custom GPU-memory PromQL | Auto |
| `schedule_policy_query` | No | Custom GPU schedule-policy PromQL | Auto |
| `xgpu_memory_total_query` / `xgpu_memory_used_query` | No | Custom xGPU memory PromQL | Auto |
| `xgpu_core_total_query` / `xgpu_core_used_query` / `xgpu_device_health_query` | No | Custom xGPU core and health PromQL | Auto |

Optional custom PromQL overrides are supported for GPU utilization, memory, schedule policy, xGPU allocation/usage, and xGPU health metrics.

### `huawei_get_cce_node_metrics_topN`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `top_n` | No | Number of top items | 10 |
| `hours` | No | Metrics lookback hours | 1 |

### `huawei_get_cce_node_metrics`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `node_ip` | Yes | Target Node IP | N/A |
| `hours` | No | Metrics lookback hours | 1 |

### `huawei_get_cce_node_gpu_metrics`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `node_ip` | Yes | Target Node IP or node name | N/A |
| `hours` | No | Metrics lookback hours | 1 |
| `gpu_selector` | No | Custom GPU metric label selector | `node=~"<node_ip>|<node_name>"` |
| `utilization_query` / `memory_utilization_query` | No | Custom GPU utilization PromQL | Auto |
| `memory_used_query` / `memory_total_query` / `memory_free_query` | No | Custom GPU-memory PromQL | Auto |
| `temperature_query` / `power_usage_query` | No | Custom GPU temperature and power PromQL | Auto |
| `schedule_policy_query` | No | Custom GPU schedule-policy PromQL | Auto |
| `xgpu_memory_total_query` / `xgpu_memory_used_query` | No | Custom xGPU memory PromQL | Auto |
| `xgpu_core_total_query` / `xgpu_core_used_query` / `xgpu_device_health_query` | No | Custom xGPU core and health PromQL | Auto |

Optional custom PromQL overrides are supported for GPU utilization, memory, temperature, power, schedule policy, xGPU allocation/usage, and xGPU health metrics.

## Add-on Metrics

### `huawei_get_cce_coredns_metrics`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `namespace` | No | CoreDNS namespace | `kube-system` |
| `pod_regex` | No | Regex used to match CoreDNS Pods | `.*coredns.*` |
| `hours` | No | Metrics lookback hours | 1 |
| `qps_query` / `error_rate_query` / `nxdomain_rate_query` | No | Custom QPS and error-rate PromQL | Auto |
| `latency_p95_query` | No | Custom P95 latency PromQL | Auto |
| `cpu_query` / `memory_query` / `replicas_query` | No | Custom CPU, memory, and replica-count PromQL | Auto |

Optional custom PromQL overrides are supported for QPS, error rate, NXDOMAIN rate, P95 latency, CPU, memory, and replica count.

### `huawei_get_cce_nginx_ingress_metrics`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `namespace` | No | Namespace of nginx-ingress controller Pods; empty queries all namespaces | `kube-system` |
| `pod_regex` | No | Regex used to match nginx-ingress controller Pods | `.*nginx.*ingress.*|.*ingress.*nginx.*` |
| `ingress_namespace` | No | Namespace filter for Ingress TLS certificate checks | all |
| `hours` | No | Metrics lookback hours | 1 |
| `cert_expire_warning_days` | No | Days before expiry to mark certificates as warning | 30 |
| `check_certificates` | No | Inspect Ingress TLS Secrets for expiration status | true |
| `qps_query` / `http_4xx_query` / `http_5xx_query` | No | Custom request-rate PromQL | Auto |
| `success_rate_query` / `latency_p95_query` | No | Custom success-rate and P95 latency PromQL | Auto |
| `active_connections_query` / `cpu_query` / `memory_query` | No | Custom connection, CPU, and memory PromQL | Auto |

Ingress-controller metrics depend on the corresponding AOM PodMonitor. The `nginx_ingress_controller_requests` metric must be explicitly allowed in the PodMonitor; otherwise request-dimension metrics can be empty and QPS may use the `nginx_ingress_controller_nginx_process_requests_total` fallback.

Optional custom PromQL overrides are supported for QPS, 4xx/5xx, success rate, P95 latency, active connections, CPU, and memory.

### `huawei_get_cce_autoscaler_metrics`

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `namespace` | No | Namespace of Cluster Autoscaler Pods; empty queries all namespaces | `kube-system` |
| `pod_regex` | No | Regex used to match autoscaler Pods | `.*cluster.*autoscaler.*|.*autoscaler.*` |
| `hpa_namespace` | No | Namespace filter for HPA replica metrics | all |
| `hours` | No | Metrics lookback hours | 1 |
| `include_hpa` | No | Query HPA current/desired replica metrics | true |
| `unschedulable_pods_query` / `nodes_count_query` | No | Custom unschedulable-Pod and node-count PromQL | Auto |
| `scale_up_query` / `scale_down_query` / `errors_query` | No | Custom scaling-event and error PromQL | Auto |
| `node_groups_query` | No | Custom node-group PromQL | Auto |
| `hpa_current_replicas_query` / `hpa_desired_replicas_query` | No | Custom HPA replica PromQL | Auto |
| `cpu_query` / `memory_query` | No | Custom autoscaler Pod CPU and memory PromQL | Auto |

Optional custom PromQL overrides are supported for unschedulable Pods, node states, scale events, errors, node groups, HPA replicas, CPU, and memory.

## Kubernetes Control Plane Metrics

Applies to `huawei_get_cce_apiserver_metrics`, `huawei_get_cce_etcd_metrics`, `huawei_get_cce_controller_manager_metrics`, and `huawei_get_cce_scheduler_metrics`.

- Apiserver defaults to `cluster="<cluster_id>",component="apiserver"`, excludes `WATCH|CONNECT` from default P95 latency, and returns `latency_p95_by_verb_ms`.
- Etcd defaults to `cluster="<cluster_id>"` without namespace or Pod labels.
- Controller-manager defaults to `cluster="<cluster_id>"` and returns aggregate plus per-queue `name` breakdowns.
- Scheduler defaults to `cluster="<cluster_id>"` and returns aggregate plus `result`, `profile/result`, and `queue` breakdowns.
- Controller-manager, scheduler, and etcd require their AOM ServiceMonitor collection to be enabled; otherwise a successful query can return empty series.

| Tool | `pod_regex` default | `metric_selector` default |
| --- | --- | --- |
| `huawei_get_cce_apiserver_metrics` | `.*kube-apiserver.*|.*apiserver.*` | `cluster="<cluster_id>",component="apiserver"` |
| `huawei_get_cce_etcd_metrics` | `.*etcd.*` | `cluster="<cluster_id>"` |
| `huawei_get_cce_controller_manager_metrics` | `.*kube-controller-manager.*|.*controller-manager.*` | `cluster="<cluster_id>"` |
| `huawei_get_cce_scheduler_metrics` | `.*kube-scheduler.*|.*scheduler.*` | `cluster="<cluster_id>"` |

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `namespace` | No | Control-plane Pod namespace; an empty value queries all namespaces. | `kube-system` |
| `pod_regex` | No | Regex for the target component Pods. | Tool-specific value above |
| `metric_selector` | No | Custom Prometheus label selector. | Tool-specific value above |
| `hours` | No | Metrics lookback hours. | `1` |

## Cloud Resource Metrics

| Tool | Required ID | Optional parameters |
| --- | --- | --- |
| `huawei_get_ecs_metrics` | `instance_id` | None |
| `huawei_get_elb_metrics` | `elb_id` | `hours` (default `1`), `period` (default `300` seconds) |
| `huawei_get_eip_metrics` | `eip_id` | `hours` (default `1`), `period` (default `300` seconds) |
| `huawei_get_nat_gateway_metrics` | `nat_gateway_id` | `hours` (default `1`), `period` (default `300` seconds) |

## Cluster Monitoring Aggregation

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `start_time` | Yes | UTC start time, `YYYY-MM-DD HH:MM:SS`. | N/A |
| `end_time` | Yes | UTC end time, `YYYY-MM-DD HH:MM:SS`. | N/A |
| `namespace` | No | Namespace filter. | `default` |
| `top_n` | No | Number of top items. | `10` |
