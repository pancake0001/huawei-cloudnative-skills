# Output Schema

`huawei_diagnose_cce_node_configuration` always returns the same envelope. Preview, validation failure, execution failure, timeout, and successful
collection differ only in values, never in the field layout.

```json
{
  "schema_version": "1.0",
  "success": true,
  "action": "huawei_diagnose_cce_node_configuration",
  "risk_level": "R2",
  "status": "preview | succeeded | failed | timeout | collection_failed",
  "error": {"code": null, "message": null},
  "execution": {
    "requires_confirmation": false,
    "preview": null
  },
  "target": {
    "region": "cn-north-4",
    "project_id": "project-id",
    "cluster_id": "cluster-uuid",
    "node_name": "node-name",
    "node_provider_id": "provider-id"
  },
  "diagnostic_cr": {
    "name": "ncc-node-name-random",
    "manifest": {},
    "lifecycle": "CCE-managed; the controller may delete this CR after collection completes",
    "status": {"phase": "Succeeded"}
  },
  "diagnosis": {
    "health": "healthy | warning | unhealthy",
    "baseline_summary": {
      "total": 0,
      "passed": 0,
      "warning": 0,
      "critical": 0,
      "unavailable": 0,
      "informational": 0
    },
    "baseline_checks": [
      {
        "id": "network:dns",
        "category": "network",
        "source": "DNS",
        "expected": "100.125.0.0/16",
        "comparison": "all nameservers in CIDR",
        "actual": ["100.125.1.250"],
        "state": "passed | warning | critical | unavailable | informational",
        "severity": "none | warning | critical",
        "message": "All DNS nameservers match the baseline CIDR"
      }
    ],
    "findings": [],
    "data_gaps": [],
    "observations": {
      "component_status": [],
      "resource_usage": {},
      "network": {},
      "system": {},
      "collection_status": {}
    }
  },
  "debug_trace": []
}
```

`status` identifies the outcome: `preview` requires `confirm=true`; `failed` covers validation and command failures; `timeout` means no terminal
collection phase was received; and `collection_failed` is a terminal CCE collector failure. `error` is always an object. `debug_trace` is always an
array and is populated only when `debug=true`.

A completed collection with configuration findings still returns `success=true`; use `diagnosis.health` and `findings` to determine node health.
`baseline_checks` always uses the same item fields and contains every collected baseline comparison. `baseline_summary` counts these check states.
