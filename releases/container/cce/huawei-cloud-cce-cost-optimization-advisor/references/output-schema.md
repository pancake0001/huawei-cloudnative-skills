# Output Schema

`huawei_generate_cce_cost_optimization_report` accepts `output_format=html|markdown|both` and returns the requested primary artifact in `output_file`. It always returns `html_file`, `markdown_file`, and the separately generated trend-chart paths. HTML embeds the charts; Markdown retains the same findings as text and references the chart artifacts.

The cost optimization report follows this JSON structure:

```json
{
  "action": "analyze_cce_cost_optimization",
  "scope": {
    "region": "cn-north-4",
    "cluster_id": "optional",
    "excluded_namespaces": [],
    "analysis_start_date": "2026-09-01",
    "analysis_end_date_exclusive": "2026-09-08",
    "analysis_days": 7,
    "time_zone": "Asia/Shanghai",
    "start": 0,
    "end": 0,
    "data_source": "AOM Prometheus"
  },
  "capacity": {
    "minimum_total_cpu_cores": 0,
    "minimum_total_memory_gib": 0,
    "minimum_allocatable_cpu_cores": 0,
    "minimum_allocatable_memory_gib": 0,
    "average_allocatable_cpu_cores": 0,
    "average_allocatable_memory_gib": 0,
    "total_cpu_trend": {
      "sample_count": 0,
      "first_sample_at": "2026-01-01T00:00:00+08:00",
      "last_sample_at": "2026-01-01T23:55:00+08:00",
      "start": 0,
      "end": 0,
      "minimum": 0,
      "maximum": 0,
      "average": 0,
      "change": 0,
      "change_percent": 0,
      "trend": "rising | stable | falling | insufficient_data",
      "key_points": [{"at": "2026-01-01T00:00:00+08:00", "value": 0}]
    },
    "total_memory_trend": "Same structure as total_cpu_trend; values are GiB.",
    "allocatable_cpu_trend": "Same structure as total_cpu_trend; values are cores.",
    "allocatable_memory_trend": "Same structure as total_cpu_trend; values are GiB.",
    "declared_cpu_request_trend": "Same structure as allocatable_cpu_trend; values are cores.",
    "declared_memory_request_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
    "node_bound_cpu_request_trend": "Same structure as allocatable_cpu_trend; values are cores.",
    "node_bound_memory_request_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
    "pending_cpu_request_trend": "Same structure as allocatable_cpu_trend; values are cores.",
    "pending_memory_request_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
    "cpu_request_allocation_trend": "Same structure as allocatable_cpu_trend; values are percent.",
    "memory_request_allocation_trend": "Same structure as allocatable_cpu_trend; values are percent.",
    "minimum_unallocated_cpu_cores": 0,
    "minimum_unallocated_memory_gib": 0,
    "calculation": "Node-bound Requests determine allocation and unallocated redundancy; Pending Requests are reported separately. Reserve sufficiency is assessed by the capacity trend forecaster, not this skill."
  },
  "cluster_usage": {
    "cpu_usage_trend": "Same structure as allocatable_cpu_trend; values are cores.",
    "memory_usage_trend": "Same structure as allocatable_cpu_trend; values are GiB."
  },
  "resource_cost_view": {
    "meaning": "Total capacity is Kubernetes node capacity; allocatable capacity is the Pod-schedulable subset after system reservations. Allocated node-bound Requests plus unallocated redundancy equals allocatable capacity at the same timestamp. Values are resource capacity, not currency charges.",
    "total_capacity": {
      "cpu_cores_trend": "Same structure as total_cpu_trend; values are cores.",
      "memory_gib_trend": "Same structure as total_cpu_trend; values are GiB."
    },
    "total_allocatable": {
      "cpu_cores_trend": "Same structure as total_cpu_trend; values are cores.",
      "memory_gib_trend": "Same structure as total_cpu_trend; values are GiB."
    },
    "allocated": {
      "cpu_request_cores_trend": "Same structure as allocatable_cpu_trend; values are cores.",
      "memory_request_gib_trend": "Same structure as allocatable_cpu_trend; values are GiB."
    },
    "redundant_reserve": {
      "cpu_cores_trend": "Same structure as allocatable_cpu_trend; values are cores.",
      "memory_gib_trend": "Same structure as allocatable_cpu_trend; values are GiB."
    },
    "allocation_rate": {
      "cpu_percent_trend": "Same structure as allocatable_cpu_trend; values are percent.",
      "memory_percent_trend": "Same structure as allocatable_cpu_trend; values are percent."
    }
  },
  "resource_data_coverage": {
    "first_sample_at": "2026-01-01T00:00:00+08:00",
    "last_sample_at": "2026-01-01T23:55:00+08:00",
    "sample_count": 288,
    "step_seconds": 300
  },
  "gpu": {
    "detected": false,
    "resources": [{
      "resource": "nvidia.com/gpu",
      "unit": "integer",
      "allocatable_trend": "Same structure as allocatable_cpu_trend.",
      "node_bound_request_trend": "Same structure as allocatable_cpu_trend.",
      "pending_request_trend": "Same structure as allocatable_cpu_trend.",
      "allocation_trend": "Same structure as allocatable_cpu_trend; values are percent.",
      "minimum_unallocated": 0
    }],
    "actual_utilization": {
      "gpu_utilization_percent_trend": "Same structure as allocatable_cpu_trend; values are percent.",
      "gpu_memory_utilization_percent_trend": "Same structure as allocatable_cpu_trend; values are percent.",
      "xgpu_memory_utilization_percent_trend": "Same structure as allocatable_cpu_trend; values are percent.",
      "xgpu_core_utilization_percent_trend": "Same structure as allocatable_cpu_trend; values are percent."
    }
  },
  "namespace_allocation_and_usage": [
    {
      "namespace": "business",
      "declared_cpu_request_trend": "Same structure as allocatable_cpu_trend; values are cores.",
      "declared_memory_request_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
      "node_bound_cpu_request_trend": "Same structure as allocatable_cpu_trend; values are cores.",
      "node_bound_memory_request_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
      "pending_cpu_request_trend": "Same structure as allocatable_cpu_trend; values are cores.",
      "pending_memory_request_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
      "cpu_allocatable_share_trend": "Namespace node-bound CPU Requests as a percentage of total cluster allocatable CPU.",
      "memory_allocatable_share_trend": "Namespace node-bound memory Requests as a percentage of total cluster allocatable memory.",
      "cpu_allocated_cost_share_trend": "Namespace node-bound CPU Requests as a percentage of all node-bound CPU Requests.",
      "memory_allocated_cost_share_trend": "Namespace node-bound memory Requests as a percentage of all node-bound memory Requests.",
      "cpu_usage_trend": "Same structure as allocatable_cpu_trend; values are cores.",
      "memory_usage_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
      "cpu_usage_of_allocatable_trend": "Namespace actual CPU usage as a percentage of total cluster allocatable CPU.",
      "memory_usage_of_allocatable_trend": "Namespace actual memory usage as a percentage of total cluster allocatable memory.",
      "cpu_usage_to_request_trend": "Same structure as allocatable_cpu_trend; values are percent.",
      "memory_usage_to_request_trend": "Same structure as allocatable_cpu_trend; values are percent.",
      "estimated_reducible_cpu_request_cores": 0,
      "estimated_reducible_memory_request_gib": 0,
      "request_risk": "balanced | under_requested | over_requested | adjustment_not_recommended_system_namespace"
    }
  ],
  "node_pool_elasticity": [
    {
      "name": "nodepool-name",
      "autoscaling_enabled": false,
      "min_node_count": 0,
      "max_node_count": 0,
      "current_node_count": 0,
      "allocation": {
        "minimum_total_cpu_cores": 0,
        "minimum_total_memory_gib": 0,
        "minimum_allocatable_cpu_cores": 0,
        "minimum_allocatable_memory_gib": 0,
        "cpu_request_trend": "Same structure as allocatable_cpu_trend; values are cores.",
        "memory_request_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
        "minimum_unallocated_cpu_cores": 0,
        "minimum_unallocated_memory_gib": 0,
        "cpu_unallocated_trend": "Same structure as allocatable_cpu_trend; values are cores.",
        "memory_unallocated_trend": "Same structure as allocatable_cpu_trend; values are GiB.",
        "cpu_request_allocation_trend": "Same structure as allocatable_cpu_trend; values are percent.",
        "memory_request_allocation_trend": "Same structure as allocatable_cpu_trend; values are percent."
      }
    }
  ],
  "hpa": {"count": 0, "items": []},
  "estimated_rightsizing_potential": {
    "cpu_request_cores": 0,
    "memory_request_gib": 0,
    "method": "Observed peak usage plus a 30% safety margin"
  },
  "chart_file": "/local/path/cce-resource-cost-trend.html",
  "recommendations": [],
  "data_gaps": []
}
```

### Priority Classification

| Priority | Condition | Action |
|----------|-----------|--------|
| `under_requested` | Namespace CPU or memory usage exceeds its Requests at any observed sample | Investigate and increase the affected workload Requests after verification |
| `over_requested` | Namespace CPU and memory usage remain below 50% of Requests at every observed sample | Review Requests with a safety margin |
| `balanced` | Neither condition is confirmed | Continue observation |

### Request Adequacy

| Metric | Condition | Cost-analysis result |
|--------|-----------|--------|
| Namespace usage/Request | Exceeds 100% at any observed sample | `under_requested`; review an increase to workload Requests after verification |
| Namespace usage/Request | CPU and memory both remain below 50% at every observed sample | `over_requested`; review a Request reduction with a safety margin |
