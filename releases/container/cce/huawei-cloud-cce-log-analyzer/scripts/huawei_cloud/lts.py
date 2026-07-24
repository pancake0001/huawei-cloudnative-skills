"""LTS group, stream, and log query helpers through hcloud."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from . import common


def _timestamp(value: Optional[str], default: datetime) -> int:
    if not value:
        return int(default.timestamp() * 1000)
    if "-" in value:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    return int(value)


def _groups(region: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    return common.run_hcloud(common.hcloud_command("LTS", "ListLogGroups", region, ak, sk, project_id))


def list_log_groups(
    region: str,
    limit: int = 0,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    result = _groups(region, ak, sk, project_id)
    if not result.get("success"):
        return result
    groups = [group for group in (result["data"].get("log_groups") or []) if isinstance(group, dict)]
    if limit > 0:
        groups = groups[:limit]
    return {
        "success": True,
        "total": len(groups),
        "log_groups": [
            {
                "log_group_id": group.get("log_group_id"),
                "log_group_name": group.get("log_group_name"),
                "creation_time": group.get("creation_time"),
                "ttl_in_days": group.get("ttl_in_days"),
            }
            for group in groups
        ],
    }


def list_log_streams(
    region: str,
    log_group_id: Optional[str] = None,
    limit: int = 0,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    group_name = None
    if log_group_id:
        groups_result = _groups(region, ak, sk, project_id)
        if not groups_result.get("success"):
            return groups_result
        group = next(
            (item for item in (groups_result["data"].get("log_groups") or []) if item.get("log_group_id") == log_group_id),
            None,
        )
        if not group:
            return {"success": False, "error": f"LTS log group {log_group_id} was not found"}
        group_name = group.get("log_group_name")

    command = common.hcloud_command("LTS", "ListLogStreams", region, ak, sk, project_id)
    if group_name:
        command.append(f"--log_group_name={group_name}")
    result = common.run_hcloud(command)
    if not result.get("success"):
        return result
    streams = [stream for stream in (result["data"].get("log_streams") or []) if isinstance(stream, dict)]
    if limit > 0:
        streams = streams[:limit]
    return {
        "success": True,
        "total": len(streams),
        "log_streams": [
            {
                "log_stream_id": stream.get("log_stream_id"),
                "log_stream_name": stream.get("log_stream_name"),
                "log_group_id": stream.get("log_group_id") or log_group_id,
                "creation_time": stream.get("creation_time"),
            }
            for stream in streams
        ],
    }


def query_logs(
    region: str,
    log_group_id: str,
    log_stream_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    keywords: Optional[str] = None,
    limit: int = 1000,
    scroll_id: Optional[str] = None,
    is_desc: bool = True,
    is_iterative: bool = False,
    labels: Optional[Dict[str, str]] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    command = common.hcloud_command("LTS", "ListLogs", region, ak, sk, project_id)
    command.extend(
        [
            f"--log_group_id={log_group_id}",
            f"--log_stream_id={log_stream_id}",
            f"--start_time={_timestamp(start_time, now - timedelta(hours=1))}",
            f"--end_time={_timestamp(end_time, now)}",
            f"--limit={max(1, min(limit, 1000))}",
            f"--is_desc={str(is_desc).lower()}",
            "--highlight=false",
        ]
    )
    if keywords:
        command.append(f"--keywords={keywords}")
    if scroll_id:
        command.append(f"--scroll_id={scroll_id}")
    if is_iterative:
        command.append("--is_iterative=true")
    for key, value in (labels or {}).items():
        command.append(f"--labels.{key}={value}")

    result = common.run_hcloud(command)
    if not result.get("success"):
        return result
    response = result["data"]
    logs = [
        {
            "content": item.get("content", ""),
            "timestamp": item.get("timestamp"),
            "log_group_id": log_group_id,
            "log_stream_id": log_stream_id,
        }
        for item in (response.get("logs") or [])
        if isinstance(item, dict)
    ]
    next_scroll_id = response.get("scroll_id")
    return {
        "success": True,
        "log_group_id": log_group_id,
        "log_stream_id": log_stream_id,
        "start_time": _timestamp(start_time, now - timedelta(hours=1)),
        "end_time": _timestamp(end_time, now),
        "total": len(logs),
        "scroll_id": next_scroll_id,
        "has_more": bool(next_scroll_id),
        "logs": logs,
    }
