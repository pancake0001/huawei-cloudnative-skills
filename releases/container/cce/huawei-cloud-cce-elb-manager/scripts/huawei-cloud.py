#!/usr/bin/env python3
"""Minimal Huawei Cloud ELB manager dispatcher."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
    from huaweicloudsdkelb.v3 import ElbClient
    from huaweicloudsdkelb.v3.model import (
        ListFlavorsRequest,
        ListLoadBalancersRequest,
        ShowLoadBalancerRequest,
        UpdateLoadBalancerOption,
        UpdateLoadBalancerRequest,
        UpdateLoadBalancerRequestBody,
    )
    from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest

    SDK_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as exc:
    SDK_AVAILABLE = False
    IMPORT_ERROR = str(exc)


ELB_ENDPOINTS = {
    "cn-north-4": "elb.cn-north-4.myhuaweicloud.com",
    "cn-north-1": "elb.cn-north-1.myhuaweicloud.com",
    "cn-north-9": "elb.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "elb.cn-east-3.myhuaweicloud.com",
    "cn-east-2": "elb.cn-east-2.myhuaweicloud.com",
    "cn-south-1": "elb.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "elb.cn-southwest-2.myhuaweicloud.com",
    "cn-west-3": "elb.cn-west-3.myhuaweicloud.com",
    "ap-southeast-1": "elb.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "elb.ap-southeast-2.myhuaweicloud.com",
    "ap-southeast-3": "elb.ap-southeast-3.myhuaweicloud.com",
    "ap-southeast-4": "elb.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "elb.af-south-1.myhuaweicloud.com",
    "la-south-2": "elb.la-south-2.myhuaweicloud.com",
    "la-north-2": "elb.la-north-2.myhuaweicloud.com",
    "eu-west-0": "elb.eu-west-0.myhuaweicloud.com",
    "ap-northeast-1": "elb.ap-northeast-1.myhuaweicloud.com",
}
IAM_ENDPOINT = "https://iam.myhuaweicloud.com"
_PROJECT_ID_CACHE: dict[str, str] = {}


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


def _int(value: Any, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _csv_list(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    items = [item.strip() for item in str(value).split(",")]
    return [item for item in items if item]


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            str(key): _json_safe(item)
            for key, item in value.__dict__.items()
            if not key.startswith("_")
        }
    return str(value)


def _credentials(params: Dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    ak = params.get("ak") or os.getenv("HUAWEI_AK") or os.getenv("HUAWEI_CLOUD_AK")
    sk = params.get("sk") or os.getenv("HUAWEI_SK") or os.getenv("HUAWEI_CLOUD_SK")
    project_id = params.get("project_id") or os.getenv("HUAWEI_PROJECT_ID") or os.getenv("HUAWEI_CLOUD_PROJECT_ID")
    return ak, sk, project_id


def _create_iam_client(ak: str, sk: str) -> IamClient:
    credentials = GlobalCredentials(ak=ak, sk=sk)
    return IamClient.new_builder().with_credentials(credentials).with_endpoint(IAM_ENDPOINT).build()


def _get_project_id_for_region(region: str, ak: str, sk: str) -> Optional[str]:
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]
    try:
        client = _create_iam_client(ak, sk)
        request = KeystoneListProjectsRequest()
        request.name = region
        response = client.keystone_list_projects(request)
        for project in getattr(response, "projects", None) or []:
            if getattr(project, "name", None) == region and getattr(project, "id", None):
                _PROJECT_ID_CACHE[region] = project.id
                return project.id

        fallback = KeystoneListProjectsRequest()
        response = client.keystone_list_projects(fallback)
        for project in getattr(response, "projects", None) or []:
            name = getattr(project, "name", None)
            project_id = getattr(project, "id", None)
            if name and project_id:
                _PROJECT_ID_CACHE[name] = project_id
        return _PROJECT_ID_CACHE.get(region)
    except Exception:
        return None


def _create_elb_client(region: str, ak: str, sk: str, project_id: Optional[str]) -> ElbClient:
    if not project_id:
        project_id = _get_project_id_for_region(region, ak, sk)
    credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id) if project_id else BasicCredentials(ak=ak, sk=sk)
    endpoint = ELB_ENDPOINTS.get(region, f"elb.{region}.myhuaweicloud.com")
    return ElbClient.new_builder().with_credentials(credentials).with_endpoint(endpoint).build()


def _ensure_sdk_and_auth(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}
    ak, sk, _ = _credentials(params)
    if not ak or not sk:
        return {"success": False, "error": "Credentials not provided. Set HUAWEI_AK/HUAWEI_SK or HUAWEI_CLOUD_AK/HUAWEI_CLOUD_SK, or pass ak/sk parameters."}
    return None


def _lb_to_dict(lb: Any) -> Dict[str, Any]:
    guaranteed = getattr(lb, "guaranteed", None)
    provider = getattr(lb, "provider", None)
    lb_type = getattr(lb, "type", None)
    l4_flavor_id = getattr(lb, "l4_flavor_id", None)
    l7_flavor_id = getattr(lb, "l7_flavor_id", None)
    is_dedicated = bool(
        guaranteed is True
        or (provider and "vlb" in str(provider).lower())
        or (lb_type and str(lb_type).lower() == "dedicated")
        or l4_flavor_id
        or l7_flavor_id
    )
    result = {
        "id": getattr(lb, "id", None),
        "name": getattr(lb, "name", None),
        "type": lb_type,
        "elb_type": "dedicated" if is_dedicated else "shared",
        "guaranteed": guaranteed,
        "provider": provider,
        "l4_flavor_id": l4_flavor_id,
        "l7_flavor_id": l7_flavor_id,
        "provisioning_status": getattr(lb, "provisioning_status", None),
        "vpc_id": getattr(lb, "vpc_id", None),
        "vip_address": getattr(lb, "vip_address", None),
        "vip_port_id": getattr(lb, "vip_port_id", None),
        "created_at": str(getattr(lb, "created_at", "")) or None,
        "updated_at": str(getattr(lb, "updated_at", "")) or None,
    }
    eip_info = getattr(lb, "eip_info", None)
    if eip_info:
        result["eip_info"] = {
            "eip": getattr(eip_info, "eip", None),
            "eip_id": getattr(eip_info, "eip_id", None),
        }
    return result


def _flavor_to_dict(flavor: Any) -> Dict[str, Any]:
    return {
        "id": getattr(flavor, "id", None),
        "name": getattr(flavor, "name", None),
        "type": getattr(flavor, "type", None),
        "shared": getattr(flavor, "shared", None),
        "project_id": getattr(flavor, "project_id", None),
        "flavor_sold_out": getattr(flavor, "flavor_sold_out", None),
        "public_border_group": getattr(flavor, "public_border_group", None),
        "category": getattr(flavor, "category", None),
        "info": _json_safe(getattr(flavor, "info", None)),
    }


def huawei_list_elb_flavors(params: Dict[str, Any]) -> Dict[str, Any]:
    missing = [key for key in ("region",) if not params.get(key)]
    if missing:
        return {"success": False, "error": f"Missing required parameters: {', '.join(missing)}"}
    guard = _ensure_sdk_and_auth(params)
    if guard:
        return guard

    ak, sk, project_id = _credentials(params)
    try:
        client = _create_elb_client(params["region"], ak, sk, project_id)
        request = ListFlavorsRequest()
        request.limit = _int(params.get("limit"), 200)
        if params.get("marker"):
            request.marker = params["marker"]
        if "list_all" in params:
            request.list_all = _bool(params.get("list_all"), False)
        if "shared" in params:
            request.shared = _bool(params.get("shared"), False)
        if "flavor_sold_out" in params:
            request.flavor_sold_out = _bool(params.get("flavor_sold_out"), False)
        if params.get("type"):
            request.type = _csv_list(params.get("type"))
        if params.get("name"):
            request.name = _csv_list(params.get("name"))
        if params.get("id"):
            request.id = _csv_list(params.get("id"))
        if params.get("public_border_group"):
            request.public_border_group = _csv_list(params.get("public_border_group"))
        if params.get("category"):
            request.category = [_int(item, 0) for item in _csv_list(params.get("category")) or []]

        response = client.list_flavors(request)
        flavors = [_flavor_to_dict(flavor) for flavor in (getattr(response, "flavors", None) or [])]
        l4_flavors = [flavor for flavor in flavors if str(flavor.get("type") or "").lower() in {"l4", "layer4", "4"}]
        l7_flavors = [flavor for flavor in flavors if str(flavor.get("type") or "").lower() in {"l7", "layer7", "7"}]
        result = {
            "success": True,
            "region": params["region"],
            "action": "huawei_list_elb_flavors",
            "risk_level": "R3",
            "count": len(flavors),
            "l4_count": len(l4_flavors),
            "l7_count": len(l7_flavors),
            "flavors": flavors,
            "l4_flavors": l4_flavors,
            "l7_flavors": l7_flavors,
        }
        page_info = getattr(response, "page_info", None)
        if page_info:
            result["page_info"] = _json_safe(page_info)
        return result
    except ClientRequestException as exc:
        return {"success": False, "error": f"{exc.error_code} - {exc.error_msg}", "request_id": getattr(exc, "request_id", None)}
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}


def huawei_list_elb(params: Dict[str, Any]) -> Dict[str, Any]:
    missing = [key for key in ("region",) if not params.get(key)]
    if missing:
        return {"success": False, "error": f"Missing required parameters: {', '.join(missing)}"}
    guard = _ensure_sdk_and_auth(params)
    if guard:
        return guard

    ak, sk, project_id = _credentials(params)
    try:
        client = _create_elb_client(params["region"], ak, sk, project_id)
        request = ListLoadBalancersRequest()
        request.page_size = str(_int(params.get("limit"), 100))
        if params.get("marker"):
            request.marker = params["marker"]
        response = client.list_load_balancers(request)
        loadbalancers = [_lb_to_dict(lb) for lb in (getattr(response, "loadbalancers", None) or [])]
        result = {
            "success": True,
            "region": params["region"],
            "action": "huawei_list_elb",
            "risk_level": "R3",
            "count": len(loadbalancers),
            "loadbalancers": loadbalancers,
        }
        page_info = getattr(response, "page_info", None)
        if page_info:
            result["page_info"] = {
                "next_marker": getattr(page_info, "next_marker", None),
                "current_count": getattr(page_info, "current_count", None),
            }
        return result
    except ClientRequestException as exc:
        return {"success": False, "error": f"{exc.error_code} - {exc.error_msg}", "request_id": getattr(exc, "request_id", None)}
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}


def _show_loadbalancer(client: ElbClient, loadbalancer_id: str) -> Any:
    request = ShowLoadBalancerRequest()
    request.loadbalancer_id = loadbalancer_id
    return client.show_load_balancer(request).loadbalancer


def huawei_resize_elb_flavor(params: Dict[str, Any]) -> Dict[str, Any]:
    missing = [key for key in ("region", "loadbalancer_id") if not params.get(key)]
    if missing:
        return {"success": False, "error": f"Missing required parameters: {', '.join(missing)}"}
    if not params.get("l4_flavor_id") and not params.get("l7_flavor_id"):
        return {"success": False, "error": "At least one of l4_flavor_id or l7_flavor_id is required."}
    guard = _ensure_sdk_and_auth(params)
    if guard:
        return guard

    ak, sk, project_id = _credentials(params)
    try:
        client = _create_elb_client(params["region"], ak, sk, project_id)
        current_lb = _show_loadbalancer(client, params["loadbalancer_id"])
        current = {
            "l4_flavor_id": getattr(current_lb, "l4_flavor_id", None),
            "l7_flavor_id": getattr(current_lb, "l7_flavor_id", None),
            "provisioning_status": getattr(current_lb, "provisioning_status", None),
        }
        if not current["l4_flavor_id"] and not current["l7_flavor_id"]:
            return {
                "success": False,
                "action": "huawei_resize_elb_flavor",
                "risk_level": "R0",
                "error": "Target ELB does not expose l4_flavor_id or l7_flavor_id. Shared ELB flavor change is not supported by this skill.",
                "loadbalancer_id": params["loadbalancer_id"],
                "current": current,
            }

        target = {
            "l4_flavor_id": params.get("l4_flavor_id") or current["l4_flavor_id"],
            "l7_flavor_id": params.get("l7_flavor_id") or current["l7_flavor_id"],
        }
        base = {
            "success": True,
            "action": "huawei_resize_elb_flavor",
            "risk_level": "R0",
            "loadbalancer_id": params["loadbalancer_id"],
            "current": current,
            "target": target,
        }
        if not _bool(params.get("confirm"), False):
            base.update({
                "executed": False,
                "message": "Preview only. Set confirm=true after explicit authorization to change ELB flavor.",
            })
            return base

        option = UpdateLoadBalancerOption()
        if params.get("l4_flavor_id"):
            option.l4_flavor_id = params["l4_flavor_id"]
        if params.get("l7_flavor_id"):
            option.l7_flavor_id = params["l7_flavor_id"]
        request = UpdateLoadBalancerRequest()
        request.loadbalancer_id = params["loadbalancer_id"]
        request.body = UpdateLoadBalancerRequestBody(loadbalancer=option)
        response = client.update_load_balancer(request)
        updated = _lb_to_dict(response.loadbalancer)
        base.update({"executed": True, "updated": updated})
        return base
    except ClientRequestException as exc:
        return {"success": False, "action": "huawei_resize_elb_flavor", "risk_level": "R0", "error": f"{exc.error_code} - {exc.error_msg}", "request_id": getattr(exc, "request_id", None)}
    except Exception as exc:
        return {"success": False, "action": "huawei_resize_elb_flavor", "risk_level": "R0", "error": str(exc), "error_type": type(exc).__name__}


ACTIONS = {
    "huawei_list_elb_flavors": huawei_list_elb_flavors,
    "huawei_list_elb": huawei_list_elb,
    "huawei_resize_elb_flavor": huawei_resize_elb_flavor,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Huawei Cloud ELB manager")
    parser.add_argument("--action", required=True, choices=sorted(ACTIONS.keys()))
    parser.add_argument("--params", default="{}", help="JSON parameters")
    args = parser.parse_args()
    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as exc:
        print(json.dumps({"success": False, "error": f"Invalid JSON params: {exc}"}, ensure_ascii=False))
        sys.exit(1)
    result = ACTIONS[args.action](params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
