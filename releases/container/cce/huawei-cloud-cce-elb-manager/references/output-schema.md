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

## `huawei_list_elb_flavors`

```json
{
  "success": true,
  "region": "cn-north-4",
  "action": "huawei_list_elb_flavors",
  "risk_level": "R3",
  "count": 2,
  "l4_count": 1,
  "l7_count": 1,
  "flavors": [
    {
      "id": "...",
      "name": "...",
      "type": "L4",
      "shared": false,
      "project_id": "...",
      "flavor_sold_out": false,
      "public_border_group": "...",
      "category": 0,
      "info": {}
    }
  ],
  "l4_flavors": [],
  "l7_flavors": [],
  "page_info": {}
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
