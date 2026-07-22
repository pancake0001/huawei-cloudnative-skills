"""Minimal LTS log query helper used by historical Kubernetes Event queries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
from huaweicloudsdkcore.region.region import Region
from huaweicloudsdklts.v2 import LtsClient

from .common import get_credentials, get_project_id_for_region


def _create_lts_client(region: str, ak: str, sk: str, project_id: Optional[str]) -> LtsClient:
    resolved_project_id = project_id or get_project_id_for_region(region, ak, sk)
    if not resolved_project_id:
        raise RuntimeError(f"unable to resolve project_id for {region}")
    endpoint = f"lts.{region}.myhuaweicloud.com"
    credentials = BasicCredentials(ak=ak, sk=sk, project_id=resolved_project_id)
    return LtsClient.new_builder().with_credentials(credentials).with_region(Region(id=region, endpoint=endpoint)).build()


def _timestamp(value: Optional[str], default: datetime) -> int:
    if not value:
        return int(default.timestamp() * 1000)
    if "-" in value:
        return int(datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    return int(value)


def query_logs(
    region: str,
    log_group_id: str,
    log_stream_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    keywords: Optional[str] = None,
    limit: int = 1000,
    scroll_id: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    **_: Any,
) -> Dict[str, Any]:
    """Query one LTS stream and return normalized log records."""
    access_key, secret_key, resolved_project_id = get_credentials(ak, sk, project_id)
    if not access_key or not secret_key:
        return {"success": False, "error": "credentials are required"}
    try:
        from huaweicloudsdklts.v2 import ListLogsRequest, QueryLtsLogParams

        now = datetime.now()
        body = QueryLtsLogParams(
            start_time=_timestamp(start_time, now - timedelta(hours=1)),
            end_time=_timestamp(end_time, now),
            limit=limit,
            is_desc=True,
        )
        if keywords:
            body.keywords = keywords
        if scroll_id:
            body.scroll_id = scroll_id
        response = _create_lts_client(region, access_key, secret_key, resolved_project_id).list_logs(
            ListLogsRequest(log_group_id=log_group_id, log_stream_id=log_stream_id, body=body)
        )
        logs = [
            {
                "content": getattr(log, "content", str(log)),
                "timestamp": getattr(log, "timestamp", None),
                "log_group_id": log_group_id,
                "log_stream_id": log_stream_id,
            }
            for log in (response.logs or [])
        ]
        next_scroll_id = getattr(response, "scroll_id", None)
        return {
            "success": True,
            "log_group_id": log_group_id,
            "log_stream_id": log_stream_id,
            "total": len(logs),
            "scroll_id": next_scroll_id,
            "has_more": bool(next_scroll_id),
            "logs": logs,
        }
    except ClientRequestException as exc:
        return {"success": False, "error": exc.error_msg, "error_code": exc.error_code, "status_code": exc.status_code}
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
