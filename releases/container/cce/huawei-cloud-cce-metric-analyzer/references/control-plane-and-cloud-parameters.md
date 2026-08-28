# Control Plane And Cloud Parameters

## Kubernetes Control Plane Metrics

Applies to `huawei_get_cce_apiserver_metrics`, `huawei_get_cce_etcd_metrics`, `huawei_get_cce_controller_manager_metrics`, and `huawei_get_cce_scheduler_metrics`.

- Apiserver defaults to `cluster="<cluster_id>",component="apiserver"`, excludes `WATCH|CONNECT` from default P95 latency, and returns `latency_p95_by_verb_ms`.
- Etcd defaults to `cluster="<cluster_id>"` without namespace or Pod labels.
- Controller-manager defaults to `cluster="<cluster_id>"` and returns aggregate plus per-queue `name` breakdowns.
- Scheduler defaults to `cluster="<cluster_id>"` and returns aggregate plus `result`, `profile/result`, and `queue` breakdowns.
- Controller-manager, scheduler, and etcd require their AOM ServiceMonitor collection to be enabled; otherwise a successful query can return empty series.

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `namespace` | No | Control-plane Pod namespace; an empty value queries all namespaces. | `kube-system` |
| `pod_regex` | No | Regex for the target component Pods. | Component-specific |
| `metric_selector` | No | Custom Prometheus label selector. | Apiserver: `cluster="<cluster_id>",component="apiserver"`; others: `cluster="<cluster_id>"` |
| `hours` | No | Metrics lookback hours. | `1` |

## Cloud Resource Metrics

| Tool | Required ID | Optional parameters |
| --- | --- | --- |
| `huawei_get_ecs_metrics` | `instance_id` | None |
| `huawei_get_elb_metrics` | `elb_id` | `hours` |
| `huawei_get_eip_metrics` | `eip_id` | `hours` |
| `huawei_get_nat_gateway_metrics` | `nat_gateway_id` | `hours` |

## Cluster Monitoring Aggregation

| Parameter | Required | Description | Default |
| --- | --- | --- | --- |
| `start_time` | Yes | UTC start time, `YYYY-MM-DD HH:MM:SS`. | N/A |
| `end_time` | Yes | UTC end time, `YYYY-MM-DD HH:MM:SS`. | N/A |
| `namespace` | No | Namespace filter. | `default` |
| `top_n` | No | Number of top items. | `10` |
| `security_token` | No | Temporary token for AK/SK session credentials. | Environment fallback |
| `--cli-access-key` / `--cli-secret-key` | No | Explicit AK/SK for hcloud and `kubectl cce`. | Overrides profile/environment |
| `--cli-security-token` | No | STS token paired with explicit AK/SK. | Passed to hcloud and `kubectl cce` |
