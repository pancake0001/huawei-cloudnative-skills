# Output Schema

```json
{
  "summary": {
    "checks": 9,
    "findings": 0,
    "failed_checks": 0,
    "status_counts": {"healthy": 5, "degraded": 0, "unavailable": 0},
    "overall_status": "healthy | degraded | unavailable"
  },
  "cluster": {
    "region": "cn-north-4",
    "cluster_id": "optional"
  },
  "checks": [],
  "findings": [],
  "data_gaps": [],
  "report_file": "optional"
}
```

## ELB Check

The `elb_monitoring_inspection` entry in `checks` uses this compact shape:

```json
{
  "action": "elb_monitoring_inspection",
  "scope": {"region": "<region>", "cluster_id": "<cluster-uuid>"},
  "association_summary": {
    "method": "listener_description.cluster_id",
    "matched_listeners": 1,
    "matched_loadbalancers": 1,
    "listener_pages": 1,
    "listener_listing_truncated": false
  },
  "metric_window_hours": 1,
  "loadbalancers": [
    {
      "id": "<elb-id>",
      "name": "<elb-name>",
      "provisioning_status": "ACTIVE",
      "operating_status": "ONLINE",
      "admin_state_up": true,
      "matched_listeners": [],
      "metrics": {
        "m9_abnormal_servers": {"latest": 0, "peak": 0},
        "l7_con_usage": {"latest": 12.5, "peak": 35.0}
      }
    }
  ],
  "findings": [],
  "data_gaps": []
}
```

`matched_loadbalancers: 0` with no findings is a successful empty association result. It does not establish the health of unrelated ELBs in the same project.

