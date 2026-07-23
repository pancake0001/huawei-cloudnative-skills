"""LTS log queries through hcloud for historical Kubernetes Event queries."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .common import get_credentials


def _timestamp(value: Optional[str], default: datetime) -> int:
    if not value:
        return int(default.timestamp() * 1000)
    if "-" in value:
        return int(datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    return int(value)


def _has_hcloud_profile() -> bool:
    config_dir = os.environ.get("HCLOUD_CONFIG_DIR")
    candidates = [os.path.join(config_dir, "config.json")] if config_dir else []
    candidates.extend(
        [
            os.path.expanduser("~/.hcloud/config.json"),
            os.path.expanduser("~/.hcloud/config.yaml"),
            os.path.expanduser("~/.hcloud/config.yml"),
        ]
    )
    return any(os.path.isfile(path) and os.path.getsize(path) > 0 for path in candidates)


def _hcloud_credentials(
    ak: Optional[str], sk: Optional[str], project_id: Optional[str]
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve credentials in tool-parameter, profile, then environment order."""
    if ak or sk or project_id:
        return ak, sk, project_id
    if _has_hcloud_profile():
        return None, None, None
    return get_credentials()


def _parse_hcloud_json(output: str) -> Dict[str, Any]:
    text = (output or "").strip()
    start = text.find("{")
    if start < 0:
        raise ValueError("hcloud returned non-JSON output")
    return json.loads(text[start:])


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
    """Query one LTS stream through ``hcloud LTS ListLogs``."""
    now = datetime.now()
    access_key, secret_key, resolved_project_id = _hcloud_credentials(ak, sk, project_id)
    cmd = [
        "hcloud",
        "LTS",
        "ListLogs",
        f"--cli-region={region}",
        f"--log_group_id={log_group_id}",
        f"--log_stream_id={log_stream_id}",
        f"--start_time={_timestamp(start_time, now - timedelta(hours=1))}",
        f"--end_time={_timestamp(end_time, now)}",
        f"--limit={max(1, min(limit, 1000))}",
        "--is_desc=true",
        "--cli-output=json",
        "--cli-connect-timeout=10",
        "--cli-read-timeout=60",
    ]
    if resolved_project_id:
        cmd.append(f"--project_id={resolved_project_id}")
    if access_key:
        cmd.append(f"--cli-access-key={access_key}")
    if secret_key:
        cmd.append(f"--cli-secret-key={secret_key}")
    if keywords:
        cmd.append(f"--keywords={keywords}")
    if scroll_id:
        cmd.append(f"--scroll_id={scroll_id}")

    try:
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=75, check=False)
    except FileNotFoundError:
        return {"success": False, "error": "hcloud not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "hcloud LTS ListLogs timed out after 75 seconds"}

    if completed.returncode:
        return {
            "success": False,
            "error": (completed.stderr or completed.stdout or f"hcloud exited with code {completed.returncode}")[:2000],
        }

    try:
        response = _parse_hcloud_json(completed.stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"success": False, "error": f"hcloud LTS ListLogs response parsing failed: {exc}"}

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
        "total": len(logs),
        "scroll_id": next_scroll_id,
        "has_more": bool(next_scroll_id),
        "logs": logs,
    }
