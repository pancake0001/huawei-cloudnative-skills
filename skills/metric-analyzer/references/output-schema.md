# Output Schema

## CCE Metrics (Pod/Node)

### TopN Result

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

### Metrics Data Structure

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

### Status Values

| Status | Condition | Threshold |
|--------|-----------|-----------|
| `critical` | Resource usage > critical threshold | CPU >80%, Memory >85% |
| `warning` | Resource usage > warning threshold | CPU >50%, Memory >50% |
| `normal` | Resource usage below warning | Below warning threshold |
| `unknown` | No data available | N/A |

---

## Cloud Resource Metrics (ECS/ELB/EIP/NAT)

### ECS Metrics

**API**: `huawei_get_ecs_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `cpu_util` | CPU 使用率 | % |
| `mem_util` | 内存使用率 | % |
| `disk_util` | 磁盘使用率 | % |
| `network_incoming_bytes_rate` | 网络入带宽速率 | B/s |
| `network_outgoing_bytes_rate` | 网络出带宽速率 | B/s |
| `disk_read_bytes_rate` | 磁盘读速率 | B/s |
| `disk_write_bytes_rate` | 磁盘写速率 | B/s |

### ELB Metrics

**API**: `huawei_get_elb_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `m1_cps` | L4 新建连接数 | count/s |
| `m14_l7_rt` | L7 响应时间 | ms |
| `mb_l7_qps` | L7 QPS | count/s |
| `mc_l7_http_2xx` | HTTP 2xx 响应码数量 | count |
| `md_l7_http_3xx` | HTTP 3xx 响应码数量 | count |
| `me_l7_http_4xx` | HTTP 4xx 响应码数量 | count |
| `mf_l7_http_5xx` | HTTP 5xx 响应码数量 | count |

### EIP Metrics

**API**: `huawei_get_eip_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `upstream_bandwidth` | 上行带宽 | bit/s |
| `downstream_bandwidth` | 下行带宽 | bit/s |
| `upstream_bandwidth_usage` | 上行带宽使用率 | % |
| `downstream_bandwidth_usage` | 下行带宽使用率 | % |
| `upstream_traffic` | 上行流量 | B |
| `downstream_traffic` | 下行流量 | B |
| `packet_loss_rate` | 丢包率 | % |

### NAT Gateway Metrics

**API**: `huawei_get_nat_gateway_metrics`

| Metric | Description | Unit |
|--------|-------------|------|
| `snat_connection` | SNAT 连接数 | count |
| `inbound_bandwidth` | 入带宽 | bit/s |
| `outbound_bandwidth` | 出带宽 | bit/s |
| `snat_connection_ratio` | SNAT 连接利用率 | % |

---

## Time-Series Item

| Field | Description |
|-------|-------------|
| `timestamp` | Unix timestamp (seconds) |
| `time` | Human-readable time string |
| `average` | Average value over the period |
| `min` | Minimum value over the period |
| `max` | Maximum value over the period |