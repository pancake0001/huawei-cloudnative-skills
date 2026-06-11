---
id: huawei-cloud-cce-elb-manager
name: huawei-cloud-cce-elb-manager
description: |
  Huawei Cloud CCE peripheral ELB management skill using Python SDK dispatcher.
  Use this skill when the user needs to list ELB load balancer instances associated with CCE workloads, inspect their current L4/L7 flavor IDs, or change a dedicated ELB instance specification by updating l4_flavor_id and/or l7_flavor_id.
  Trigger: user mentions "ELB", "load balancer", "负载均衡", "ELB实例", "ELB列表", "ELB规格", "ELB扩容", "变更ELB规格", "独享型ELB"
tags: [cce, elb, load-balancer, peripheral-resource, remediation]
---

# Huawei Cloud CCE ELB Manager

> **Execution method:** Run actions through `scripts/huawei-cloud.py` with `--action <action_name>` and `--params <json_params>`. Do not use hcloud, kubectl, or raw API calls for this skill.

## Scope

This skill manages Huawei Cloud ELB instances used as CCE peripheral resources. It currently provides three focused capabilities:

1. List ELB load balancer instances in a region.
2. List available ELB L4/L7 flavors in a region.
3. Change the flavor of a dedicated ELB instance by updating `l4_flavor_id` and/or `l7_flavor_id`.

The resize action is for dedicated ELB flavor changes. Shared ELB capacity or EIP bandwidth changes are outside this skill's current execution scope and should be handled by a separate EIP/bandwidth capability.

## Core Tools

| Action | Purpose | Risk |
|--------|---------|------|
| `huawei_list_elb` | List ELB instances and return ID, name, type, status, VIP, current L4/L7 flavor IDs, and EIP info when available. | R3 |
| `huawei_list_elb_flavors` | List available ELB L4/L7 flavors and return flavor IDs, names, type, category, shared flag, sold-out flag, and performance info. | R3 |
| `huawei_resize_elb_flavor` | Update a dedicated ELB instance's `l4_flavor_id` and/or `l7_flavor_id`. Requires `confirm=true` to execute. | R0 |

## Risk Rules

- `R3`: Read-only ELB inspection. Safe to execute without changing resources.
- `R2`: Low-risk no-cost changes. Not currently used by this skill.
- `R1`: Medium-risk changes. Not currently used by this skill.
- `R0`: High-risk ELB specification changes because they may change public entry capacity, cost, and traffic behavior. Always require explicit user authorization and `confirm=true`.

## Parameters

### `huawei_list_elb`

Required:

- `region`: Huawei Cloud region, for example `cn-north-4`.

Optional:

- `project_id`: Project ID. If omitted, the SDK can infer it from credentials when possible.
- `ak`, `sk`: Huawei Cloud credentials. Prefer environment variables.
- `limit`: Page size, default `100`.
- `marker`: Pagination marker.

Example:

```bash
python scripts/huawei-cloud.py --action huawei_list_elb --params '{"region":"cn-north-4","limit":100}'
```

### `huawei_list_elb_flavors`

Required:

- `region`: Huawei Cloud region, for example `cn-north-4`.

Optional:

- `project_id`: Project ID.
- `ak`, `sk`: Huawei Cloud credentials. Prefer environment variables.
- `limit`: Page size, default `200`.
- `marker`: Pagination marker.
- `type`: Comma-separated flavor type filter such as `L4`, `L7`, or `L4,L7`.
- `shared`: Filter shared or dedicated flavors when supported by the API.
- `list_all`: Whether to list all flavors when supported by the API.
- `category`: Comma-separated category filter.
- `flavor_sold_out`: Filter sold-out status when supported by the API.

Example:

```bash
python scripts/huawei-cloud.py --action huawei_list_elb_flavors --params '{"region":"cn-north-4","type":"L4,L7","limit":200}'
```

### `huawei_resize_elb_flavor`

Required:

- `region`: Huawei Cloud region.
- `loadbalancer_id`: ELB load balancer ID.
- At least one of:
  - `l4_flavor_id`: Target L4 flavor ID.
  - `l7_flavor_id`: Target L7 flavor ID.

Optional:

- `project_id`: Project ID.
- `ak`, `sk`: Huawei Cloud credentials. Prefer environment variables.
- `confirm`: Must be `true` to execute. When omitted or false, the action returns a preview only.

Example preview:

```bash
python scripts/huawei-cloud.py --action huawei_resize_elb_flavor --params '{"region":"cn-north-4","loadbalancer_id":"<elb-id>","l4_flavor_id":"<target-l4-flavor-id>"}'
```

Example execution after authorization:

```bash
python scripts/huawei-cloud.py --action huawei_resize_elb_flavor --params '{"region":"cn-north-4","loadbalancer_id":"<elb-id>","l4_flavor_id":"<target-l4-flavor-id>","confirm":true}'
```

## Workflow

1. Run `huawei_list_elb` to identify the target ELB and capture current `l4_flavor_id` and `l7_flavor_id`.
2. Run `huawei_list_elb_flavors` to find valid target L4/L7 flavor IDs in the same region.
3. Confirm that the target is a dedicated ELB. If no flavor IDs are present, treat it as unsupported for this skill.
4. Prepare `huawei_resize_elb_flavor` as a preview and show current and target flavor IDs.
5. Execute only after explicit authorization and `confirm=true`.
6. Re-run `huawei_list_elb` to verify the updated flavor IDs and provisioning status.

## Remediation Handoff

When RCA outputs `PeripheralResourceBottleneck` caused by high ELB connection or bandwidth usage, this skill can list candidate L4/L7 flavors first. It can provide the executable ELB flavor-change candidate only if the target ELB ID and target flavor ID are known. Otherwise, return a high-risk manual recommendation that asks the operator to choose a target ELB flavor first.
