"""Common Huawei Cloud helpers shared by service modules."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    import kubernetes
    from kubernetes import client as k8s_client

    K8S_AVAILABLE = True
    K8S_IMPORT_ERROR = None
except ImportError as exc:
    kubernetes = None
    k8s_client = None
    K8S_AVAILABLE = False
    K8S_IMPORT_ERROR = str(exc)

_PROJECT_ID_CACHE = {}
_TEMP_CERT_FILES = set()

def _register_cert_file(filepath: Optional[str]) -> None:
    if filepath:
        _TEMP_CERT_FILES.add(filepath)


def _safe_delete_file(filepath: Optional[str]) -> None:
    if not filepath:
        return
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    finally:
        _TEMP_CERT_FILES.discard(filepath)

def get_credentials(ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Get credentials from params or environment variables

    Supports multiple env var naming conventions:
    - HUAWEI_AK / HUAWEI_SK / HUAWEI_PROJECT_ID (project custom)
    - HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK / HUAWEICLOUD_SDK_PROJECT_ID (SDK official)
    - HW_ACCESS_KEY / HW_SECRET_KEY / HW_REGION_NAME (Terraform/CLI style)
    """
    access_key = ak or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY")
    secret_key = sk or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY")
    proj_id = project_id or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
    return access_key, secret_key, proj_id


def _mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def run_hcloud(
    service: str,
    operation: str,
    region: str,
    params: Optional[Dict[str, Any]] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Run a Huawei Cloud KooCLI command and parse JSON output.

    The caller may pass explicit AK/SK, but the preferred path is the local
    hcloud profile. This keeps SDK dependencies out of read-only metric calls.
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    cmd = [
        "hcloud",
        service,
        operation,
        f"--cli-region={region}",
        "--cli-output=json",
        "--cli-connect-timeout=10",
        "--cli-read-timeout=60",
    ]
    if access_key:
        cmd.append(f"--cli-access-key={access_key}")
    if secret_key:
        cmd.append(f"--cli-secret-key={secret_key}")
    if proj_id:
        cmd.append(f"--cli-project-id={proj_id}")

    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        cmd.append(f"--{key}={value}")

    safe_cmd = [
        re.sub(r"(--cli-(?:access|secret)-key=).*", r"\1***", part)
        for part in cmd
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return {"success": False, "error": "hcloud CLI not found in PATH", "command": safe_cmd}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"hcloud command timed out after {timeout}s", "command": safe_cmd}

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        message = stderr or stdout or f"hcloud exited with code {proc.returncode}"
        if access_key:
            message = message.replace(access_key, _mask_secret(access_key) or "")
        if secret_key:
            message = message.replace(secret_key, _mask_secret(secret_key) or "")
        return {"success": False, "error": message, "command": safe_cmd, "returncode": proc.returncode}

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", stdout, flags=re.S)
        if not match:
            return {"success": False, "error": "hcloud returned non-JSON output", "output": stdout[:1000], "command": safe_cmd}
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            return {"success": False, "error": f"Failed to parse hcloud JSON output: {exc}", "output": stdout[:1000], "command": safe_cmd}

    return {"success": True, "data": data, "command": safe_cmd}


def hcloud_show_metric_data(
    region: str,
    namespace: str,
    metric_name: str,
    dim_0: str,
    start_time: int,
    end_time: int,
    period: int,
    filter_name: str = "average",
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Query CES ShowMetricData via hcloud and normalize datapoints."""
    result = run_hcloud(
        "CES",
        "ShowMetricData",
        region,
        {
            "namespace": namespace,
            "metric_name": metric_name,
            "dim.0": dim_0,
            "from": start_time,
            "to": end_time,
            "period": period,
            "filter": filter_name,
            "project_id": project_id,
        },
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result
    data = result.get("data") or {}
    datapoints = data.get("datapoints") or data.get("datapoint") or data.get("metric_data") or []
    return {"success": True, "datapoints": datapoints, "raw": data}

def get_project_id_for_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None) -> Optional[str]:
    """Get project ID for a specific region via hcloud IAM if not cached.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)

    Returns:
        Project ID string or None if not found
    """
    global _PROJECT_ID_CACHE

    # Check cache first
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]

    result = run_hcloud("IAM", "KeystoneListProjects", region, {"name": region}, ak=ak, sk=sk)
    if not result.get("success"):
        result = run_hcloud("IAM", "KeystoneListProjects", region, {}, ak=ak, sk=sk)
    if result.get("success"):
        projects = (result.get("data") or {}).get("projects") or []
        for project in projects:
            name = project.get("name")
            project_id = project.get("id")
            if name and project_id:
                _PROJECT_ID_CACHE[name] = project_id
        return _PROJECT_ID_CACHE.get(region)

    return None

def get_credentials_with_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Get credentials with automatic project_id lookup for region

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional, will auto-fetch if not provided)

    Returns:
        Tuple of (access_key, secret_key, project_id)
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    # If no project_id provided, try to get it for the region
    if not proj_id and region and access_key and secret_key:
        proj_id = get_project_id_for_region(region, access_key, secret_key)

    return access_key, secret_key, proj_id
