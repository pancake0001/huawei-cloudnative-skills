"""Minimal runtime helpers for the autoscaling diagnoser.

Cloud inventory uses hcloud. The only direct service request retained by this skill
is the authenticated AOM Prometheus query in ``aom.get_aom_prom_metrics_http``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional


_PROJECT_ID_CACHE: Dict[str, str] = {}


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
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=75, check=False)
    except FileNotFoundError:
        return {"success": False, "error": "hcloud is required but was not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "hcloud request timed out"}
    output = (completed.stdout or "").strip()
    if completed.returncode:
        return {"success": False, "error": (completed.stderr or output or "hcloud request failed").strip().replace("\n", " ")[:500]}
    try:
        return {"success": True, "data": json.loads(output)}
    except json.JSONDecodeError:
        return {"success": False, "error": "hcloud returned an invalid JSON response"}


def get_project_id_for_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None) -> Optional[str]:
    if os.environ.get("HW_PROJECT_ID"):
        return os.environ["HW_PROJECT_ID"]
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]
    command = ["hcloud", "IAM", "KeystoneListProjects", "--cli-output=json", "--cli-connect-timeout=10", "--cli-read-timeout=60", *_credential_args(ak, sk, None)]
    result = _run_hcloud_json(command)
    for project in ((result.get("data") or {}).get("projects") or []):
        if project.get("name") == region and project.get("id"):
            _PROJECT_ID_CACHE[region] = project["id"]
            return project["id"]
    return None


def get_credentials_with_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple[Optional[str], Optional[str], Optional[str]]:
    access_key, secret_key, resolved_project_id = get_credentials(ak, sk, project_id)
    if not resolved_project_id:
        resolved_project_id = get_project_id_for_region(region, access_key, secret_key)
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
