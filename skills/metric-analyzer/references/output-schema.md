# Output Schema

# # CCE Metrics (Pod/Node)

## # TopN Result

| Field | Description |
|-------|-------------|
| `success` | Query success status |
| `region` | Huawei Cloud region |
| `cluster_id` | CCE cluster ID |
| `cluster_name` | CCE cluster name |
| `aom_instance_id` | AOM Prometheus instance used |
| `query_time` | Query execution time |
| `metrics` | Dict with cpu/memory/disk data per resource |
| `top_n` | Number of items requested |
| `hours` | Time window queried |

## # Metrics Data Structure

```json
{
  "cpu": {
    "cpu_usage_percent": 85.5,
    "status": "critical",
    "time_series": [
      {"timestamp": 1234567890, "time": "2026-05-30 17:00:00", "value": 85.5}
    ]
  },
  "memory": {
    "memory_usage_percent": 72.3,
    "status": "warning",
    "time_series": [...]
  }
}
```

## # Status Values

| Status | Condition | Threshold |
|--------|-----------|-----------|
| `critical` | Resource usage > critical threshold | CPU >80%, Memory >85% |
| `warning` | Resource usage > warning threshold | CPU >50%, Memory >50% |
| `normal` | Resource usage below warning | Below warning threshold |
| `unknown` | No data available | N/A |

---

# # Cloud Resource Metrics (ECS/ELB/EIP/NAT)

## # ECS Metrics

**API**: `huawei_get_ecs_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `cpu_util` | CPU utilization | % |
| `mem_util` | Memory utilization | % |
| `disk_util` | Disk utilization | % |
| `network_incoming_bytes_rate` | Inbound network bandwidth rate | B/s |
| `network_outgoing_bytes_rate` | Outbound network bandwidth rate | B/s |
| `disk_read_bytes_rate` | Disk read rate | B/s |
| `disk_write_bytes_rate` | Disk write rate | B/s |

## # ELB Metrics

**API**: `huawei_get_elb_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `m1_cps` | L4 new connections | count/s |
| `m14_l7_rt` | L7 response time | ms |
| `mb_l7_qps` | L7 QPS | count/s |
| `mc_l7_http_2xx` | Number of HTTP 2xx responses | count |
| `md_l7_http_3xx` | Number of HTTP 3xx responses | count |
| `me_l7_http_4xx` | Number of HTTP 4xx responses | count |
| `mf_l7_http_5xx` | Number of HTTP 5xx responses | count |

## # EIP Metrics

**API**: `huawei_get_eip_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `upstream_bandwidth` | Upstream bandwidth | bit/s |
| `downstream_bandwidth` | Downstream bandwidth | bit/s |
| `upstream_bandwidth_usage` | Upstream bandwidth utilization | % |
| `downstream_bandwidth_usage` | Downstream bandwidth utilization | % |
| `upstream_traffic` | Upstream traffic | B |
| `downstream_traffic` | Downstream traffic | B |
| `packet_loss_rate` | Packet loss rate | % |

## # NAT Gateway Metrics

**API**: `huawei_get_nat_gateway_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `snat_connection` | Number of SNAT connections | count |
| `inbound_bandwidth` | Inbound bandwidth | bit/s |
| `outbound_bandwidth` | Outbound bandwidth | bit/s |
| `snat_connection_ratio` | SNAT connection utilization | % |

---

# # Time-Series Item

| Field | Description |
|-------|-------------|
| `timestamp` | Unix timestamp (seconds) |
| `time` | Human-readable time string |
| `average` | Average value over the period |
| `min` | Minimum value over the period |
| `max` | Maximum value over the period |
