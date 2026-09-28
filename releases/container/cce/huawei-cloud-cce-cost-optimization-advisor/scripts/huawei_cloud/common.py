"""Minimal runtime helpers for the autoscaling diagnoser.

Cloud inventory uses hcloud. The only direct service request retained by this skill
is the authenticated AOM Prometheus query in ``aom.get_aom_prom_metrics_http``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from contextvars import ContextVar
from typing import Any, Dict, List, Optional


_PROJECT_ID_CACHE: Dict[str, str] = {}
_DEBUG_TRACE: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar("debug_trace", default=None)
_DEBUG_RESPONSE_LIMIT: ContextVar[int] = ContextVar("debug_response_limit", default=4_000)
_SENSITIVE_ARGUMENTS = {"--cli-access-key", "--cli-secret-key", "--cli-security-token"}


def enable_debug_trace(trace: List[Dict[str, Any]], response_limit: Any = 4_000) -> tuple[Any, Any]:
    return _DEBUG_TRACE.set(trace), _DEBUG_RESPONSE_LIMIT.set(debug_response_limit(response_limit))


def disable_debug_trace(token: tuple[Any, Any]) -> None:
    trace_token, limit_token = token
    _DEBUG_TRACE.reset(trace_token)
    _DEBUG_RESPONSE_LIMIT.reset(limit_token)


def current_debug_trace() -> Optional[List[Dict[str, Any]]]:
    return _DEBUG_TRACE.get()


def _redact_command(command: List[str]) -> List[str]:
    redacted: List[str] = []
    redact_next = False
    for part in command:
        if redact_next:
            redacted.append("***")
            redact_next = False
            continue
        name, separator, _ = part.partition("=")
        if name in _SENSITIVE_ARGUMENTS:
            redacted.append(f"{name}=***" if separator else name)
            redact_next = not bool(separator)
        else:
            redacted.append(part)
    return redacted


def debug_response_limit(value: Any) -> int:
    try:
        return max(200, min(int(value), 20_000))
    except (TypeError, ValueError):
        return 4_000


def current_debug_response_limit() -> int:
    return _DEBUG_RESPONSE_LIMIT.get()


def record_debug_event(event: Dict[str, Any], trace: Optional[List[Dict[str, Any]]] = None) -> None:
    target = trace if trace is not None else current_debug_trace()
    if target is not None:
        target.append(event)


def get_credentials(ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple[Optional[str], Optional[str], Optional[str]]:
    return ak or os.environ.get("HW_ACCESS_KEY"), sk or os.environ.get("HW_SECRET_KEY"), project_id or os.environ.get("HW_PROJECT_ID")


def _credential_args(ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str] = None) -> List[str]:
    args: List[str] = []
    if project_id:
        args.append(f"--cli-project-id={project_id}")
    if ak:
        args.append(f"--cli-access-key={ak}")
    if sk:
        args.append(f"--cli-secret-key={sk}")
    if security_token:
        args.append(f"--cli-security-token={security_token}")
    return args


def _hcloud_command(region: str, operation: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str], *arguments: str) -> List[str]:
    return ["hcloud", "CCE", operation, f"--cli-region={region}", "--cli-output=json", "--cli-connect-timeout=10", "--cli-read-timeout=60", *_credential_args(ak, sk, project_id, security_token), *arguments]


def _run_hcloud_json(command: List[str]) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=75, check=False)
    except FileNotFoundError:
        record_debug_event({"type": "hcloud", "command": _redact_command(command), "error": "hcloud was not found in PATH"})
        return {"success": False, "error": "hcloud is required but was not found in PATH"}
    except subprocess.TimeoutExpired:
        record_debug_event({"type": "hcloud", "command": _redact_command(command), "duration_ms": round((time.monotonic() - started) * 1000), "error": "request timed out"})
        return {"success": False, "error": "hcloud request timed out"}
    record_debug_event({
        "type": "hcloud",
        "command": _redact_command(command),
        "exit_code": completed.returncode,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "stdout_preview": (completed.stdout or "")[:current_debug_response_limit()],
        "stderr_preview": (completed.stderr or "")[:current_debug_response_limit()],
        "response_truncated": len(completed.stdout or "") > current_debug_response_limit() or len(completed.stderr or "") > current_debug_response_limit(),
    })
    output = (completed.stdout or "").strip()
    if completed.returncode:
        return {"success": False, "error": (completed.stderr or output or "hcloud request failed").strip().replace("\n", " ")[:500]}
    try:
        data, _ = json.JSONDecoder().raw_decode(output)
    except json.JSONDecodeError:
        return {"success": False, "error": "hcloud returned an invalid JSON response"}
    if isinstance(data, dict) and str(data.get("status", "")).lower() == "failure":
        return {"success": False, "error": data.get("errorMessage") or data.get("error_msg") or data.get("message") or "hcloud request failed"}
    return {"success": True, "data": data}


def get_project_id_for_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None, security_token: Optional[str] = None) -> Optional[str]:
    if os.environ.get("HW_PROJECT_ID"):
        return os.environ["HW_PROJECT_ID"]
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]
    command = ["hcloud", "IAM", "KeystoneListProjects", "--cli-output=json", "--cli-connect-timeout=10", "--cli-read-timeout=60", *_credential_args(ak, sk, None, security_token)]
    result = _run_hcloud_json(command)
    for project in ((result.get("data") or {}).get("projects") or []):
        if project.get("name") == region and project.get("id"):
            _PROJECT_ID_CACHE[region] = project["id"]
            return project["id"]
    return None


def get_credentials_with_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> tuple[Optional[str], Optional[str], Optional[str]]:
    access_key, secret_key, resolved_project_id = get_credentials(ak, sk, project_id)
    if not resolved_project_id:
        resolved_project_id = get_project_id_for_region(region, access_key, secret_key, security_token)
    return access_key, secret_key, resolved_project_id


def resolve_cce_cluster_id(region: str, value: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    uuid_pattern = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    if uuid_pattern.fullmatch(value or ""):
        result = _run_hcloud_json(_hcloud_command(region, "ShowCluster", ak, sk, project_id, security_token, f"--cluster_id={value}"))
        return {"success": True, "id": value, "resolved_from_name": False} if result.get("success") else {"success": False, "error": f"Unable to verify CCE cluster_id '{value}': {result.get('error')}"}
    listed = _run_hcloud_json(_hcloud_command(region, "ListClusters", ak, sk, project_id, security_token))
    if not listed.get("success"):
        return {"success": False, "error": f"Unable to resolve CCE cluster name '{value}': {listed.get('error')}"}
    matches = [item for item in (listed.get("data") or {}).get("items", []) if (item.get("metadata") or {}).get("name") == value]
    if len(matches) != 1:
        return {"success": False, "error": f"cluster_id '{value}' {'matched multiple clusters' if matches else 'was not found'}; provide a valid cluster UUID or exact unique cluster name"}
    cluster_id = (matches[0].get("metadata") or {}).get("uid")
    verified = _run_hcloud_json(_hcloud_command(region, "ShowCluster", ak, sk, project_id, security_token, f"--cluster_id={cluster_id}"))
    return {"success": True, "id": cluster_id, "resolved_from_name": True} if verified.get("success") else {"success": False, "error": f"Unable to verify CCE cluster resolved from '{value}': {verified.get('error')}"}
