from .common import *


MAX_ECS_RESOLUTION_PAGES = 100


def resolve_ecs_instance_id(region: str, value: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Validate an ECS UUID or resolve one exact server-name match."""
    if is_standard_uuid(value):
        return {"success": True, "id": value, "resolved_from_name": False}

    matches = []
    marker = None
    seen_markers = set()
    for _ in range(MAX_ECS_RESOLUTION_PAGES):
        params = {"project_id": project_id, "limit": 100}
        if marker:
            params["marker"] = marker
        result = run_hcloud("ECS", "ListCloudServers", region, params, ak=ak, sk=sk, project_id=project_id)
        if not result.get("success"):
            return {"success": False, "error": f"Unable to list ECS instances for instance_id resolution: {result.get('error', '')}"}
        servers = (result.get("data") or {}).get("servers") or []
        matches.extend(item for item in servers if item.get("name") == value)
        if len(servers) < 100:
            break
        marker = servers[-1].get("id")
        if not marker or marker in seen_markers:
            return {"success": False, "error": "ECS instance listing returned an invalid pagination marker; provide instance_id as a standard UUID"}
        seen_markers.add(marker)
    else:
        return {"success": False, "error": f"ECS instance listing exceeded {MAX_ECS_RESOLUTION_PAGES} pages; provide instance_id as a standard UUID"}

    if len(matches) == 1 and is_standard_uuid(matches[0].get("id")):
        return {"success": True, "id": matches[0]["id"], "resolved_from_name": True}
    if len(matches) > 1:
        return {"success": False, "error": f"instance_id '{value}' matched multiple ECS instances; provide a standard UUID"}
    return {"success": False, "error": f"instance_id must be a standard UUID. No ECS instance named '{value}' was found"}


def get_ecs_metrics(region: str, instance_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Get monitoring metrics for a specific ECS instance."""
    _, _, proj_id = get_credentials(ak, sk, project_id)

    if not instance_id:
        return {
            "success": False,
            "error": "instance_id is required"
        }

    try:
        end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)

        metrics_to_query = [
            "cpu_util",
            "mem_util",
            "disk_util",
            "network_incoming_bytes_rate",
            "network_outgoing_bytes_rate",
            "disk_read_bytes_rate",
            "disk_write_bytes_rate",
        ]

        all_metrics = {}
        metric_errors = {}

        for metric_name in metrics_to_query:
            try:
                metric_result = hcloud_show_metric_data(
                    region,
                    "SYS.ECS",
                    metric_name,
                    f"instance_id,{instance_id}",
                    start_time,
                    end_time,
                    300,
                    "average",
                    ak,
                    sk,
                    proj_id,
                )
                if metric_result.get("success") and metric_result.get("datapoints"):
                    datapoints = []
                    for dp in metric_result["datapoints"]:
                        datapoints.append({
                            "timestamp": dp.get("timestamp"),
                            "average": dp.get("average"),
                            "min": dp.get("min"),
                            "max": dp.get("max"),
                            "unit": dp.get("unit", "")
                        })
                    latest = datapoints[-1] if datapoints else None
                    all_metrics[metric_name] = {
                        "datapoints": datapoints,
                        "latest_value": latest.get("average") if latest else None,
                        "unit": latest.get("unit", "") if latest else ""
                    }
                else:
                    if not metric_result.get("success"):
                        metric_errors[metric_name] = metric_result.get("error", "hcloud metric query failed")
                    all_metrics[metric_name] = {
                        "datapoints": [],
                        "note": "No data available",
                        **({"error": metric_result.get("error")} if not metric_result.get("success") else {}),
                    }

            except Exception as e:
                metric_errors[metric_name] = str(e)
                all_metrics[metric_name] = {"error": str(e)}

        has_datapoints = any(item.get("datapoints") for item in all_metrics.values() if isinstance(item, dict))
        response = {
            "success": not metric_errors or has_datapoints,
            "region": region,
            "instance_id": instance_id,
            "source": "hcloud",
            "time_range": {
                "start": datetime.fromtimestamp(start_time / 1000, tz=timezone.utc).isoformat(),
                "end": datetime.fromtimestamp(end_time / 1000, tz=timezone.utc).isoformat(),
                "period": "5min"
            },
            "metrics": all_metrics
        }
        if metric_errors:
            response["metric_errors"] = metric_errors
            if not has_datapoints:
                response["error"] = "All ECS metric queries failed"
        return response

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
