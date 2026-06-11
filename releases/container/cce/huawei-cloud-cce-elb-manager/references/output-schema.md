# ELB Manager Output Schema

## `huawei_list_elb`

```json
{
  "success": true,
  "region": "cn-north-4",
  "action": "huawei_list_elb",
  "risk_level": "R3",
  "count": 1,
  "loadbalancers": [
    {
      "id": "...",
      "name": "...",
      "elb_type": "dedicated",
      "provisioning_status": "ACTIVE",
      "vpc_id": "...",
      "vip_address": "10.0.0.10",
      "vip_port_id": "...",
      "l4_flavor_id": "...",
      "l7_flavor_id": "...",
      "eip_info": {}
    }
  ],
  "page_info": {}
}
```

## `huawei_resize_elb_flavor`

Preview output when `confirm` is absent or false:

```json
{
  "success": true,
  "executed": false,
  "action": "huawei_resize_elb_flavor",
  "risk_level": "R0",
  "message": "Preview only. Set confirm=true after explicit authorization to change ELB flavor.",
  "loadbalancer_id": "...",
  "current": {
    "l4_flavor_id": "...",
    "l7_flavor_id": "..."
  },
  "target": {
    "l4_flavor_id": "...",
    "l7_flavor_id": "..."
  }
}
```

Execution output:

```json
{
  "success": true,
  "executed": true,
  "action": "huawei_resize_elb_flavor",
  "risk_level": "R0",
  "loadbalancer_id": "...",
  "current": {},
  "target": {},
  "updated": {}
}
```
