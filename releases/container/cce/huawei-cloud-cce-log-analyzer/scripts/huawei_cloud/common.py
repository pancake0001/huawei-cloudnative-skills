"""Credential and hcloud helpers for CCE log analysis."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Optional


_STANDARD_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


def get_credentials(
    ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve explicit credentials before environment-variable fallback."""
    return (
        ak or os.environ.get("HW_ACCESS_KEY") or os.environ.get("HUAWEICLOUD_SDK_AK"),
        sk or os.environ.get("HW_SECRET_KEY") or os.environ.get("HUAWEICLOUD_SDK_SK"),
        project_id or os.environ.get("HW_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID"),
    )


def has_hcloud_profile() -> bool:
    """Return whether a usable local hcloud profile is present."""
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


def resolve_hcloud_credentials(
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Resolve hcloud authentication: arguments, profile, then environment."""
    if ak or sk or project_id or security_token:
        return ak, sk, project_id, security_token
    if has_hcloud_profile():
        return None, None, None, None
    access_key, secret_key, resolved_project_id = get_credentials()
    return access_key, secret_key, resolved_project_id, os.environ.get("HW_SECURITY_TOKEN")


def redact_command(command: list[str]) -> list[str]:
    """Redact credential values before returning a command to callers."""
    return [
        re.sub(r"(--cli-(?:access-key|secret-key|security-token)=).*", r"\1***", part)
        for part in command
    ]


def _parse_hcloud_output(output: str) -> Any:
    """Parse hcloud JSON while tolerating diagnostics appended after the payload."""
    candidate = output.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # LTS log content can contain literal backslashes (for example, regexes)
        # that hcloud emits without JSON escaping.
        candidate = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Some hcloud releases append terminal diagnostics after a valid JSON
            # response. Keep only the first JSON value in that case.
            value, _ = json.JSONDecoder().raw_decode(candidate)
            return value


def run_hcloud(command: list[str]) -> dict[str, Any]:
    """Run hcloud and parse its JSON response."""
    safe_command = redact_command(command)
    try:
        process = subprocess.run(command, text=True, capture_output=True, timeout=75, check=False)
    except FileNotFoundError:
        return {"success": False, "error": "hcloud not found in PATH", "command": safe_command}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "hcloud command timed out after 75 seconds", "command": safe_command}
    if process.returncode:
        return {
            "success": False,
            "error": (process.stderr or process.stdout or f"hcloud exited with code {process.returncode}")[:2000],
            "command": safe_command,
        }
    output = (process.stdout or "").strip() or "{}"
    try:
        data = _parse_hcloud_output(output)
    except json.JSONDecodeError as error:
        return {
            "success": False,
            "error": f"hcloud returned non-JSON output: {error}",
            "command": safe_command,
        }
    if isinstance(data, dict) and data.get("error_code"):
        return {
            "success": False,
            "error": f"{data['error_code']}: {data.get('error_msg', 'hcloud request failed')}",
            "command": safe_command,
        }
    return {"success": True, "data": data}


def hcloud_command(
    service: str,
    operation: str,
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> list[str]:
    """Build an hcloud command with the shared authentication priority."""
    access_key, secret_key, resolved_project_id, resolved_security_token = resolve_hcloud_credentials(
        ak, sk, project_id, security_token
    )
    command = [
        "hcloud", service, operation, f"--cli-region={region}", "--cli-output=json",
        "--cli-connect-timeout=10", "--cli-read-timeout=60",
    ]
    if resolved_project_id:
        command.append(f"--cli-project-id={resolved_project_id}")
    if access_key:
        command.append(f"--cli-access-key={access_key}")
    if secret_key:
        command.append(f"--cli-secret-key={secret_key}")
    if resolved_security_token:
        command.append(f"--cli-security-token={resolved_security_token}")
    return command


def resolve_cce_cluster_id(
    region: str,
    value: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> dict[str, Any]:
    """Validate a cluster UUID or resolve one exact CCE cluster-name match."""
    if _STANDARD_UUID_RE.fullmatch(value or ""):
        result = run_hcloud(
            hcloud_command("CCE", "ShowCluster", region, ak, sk, project_id, security_token)
            + [f"--cluster_id={value}"]
        )
        if not result.get("success"):
            return {
                "success": False,
                "error": f"Unable to verify CCE cluster_id '{value}': {result.get('error', '')}",
                "cluster_id": value,
            }
        return {"success": True, "id": value, "resolved_from_name": False}
    # CCE ListClusters returns all items and does not accept limit or offset parameters.
    result = run_hcloud(hcloud_command("CCE", "ListClusters", region, ak, sk, project_id, security_token))
    if not result.get("success"):
        return {"success": False, "error": f"Unable to list CCE clusters for cluster_id resolution: {result.get('error', '')}"}
    items = ((result.get("data") or {}).get("items") or [])
    matches = [item for item in items if ((item.get("metadata") or {}).get("name") == value)]
    if len(matches) == 1:
        cluster_id = (matches[0].get("metadata") or {}).get("uid")
        if _STANDARD_UUID_RE.fullmatch(cluster_id or ""):
            verification = run_hcloud(
                hcloud_command("CCE", "ShowCluster", region, ak, sk, project_id, security_token)
                + [f"--cluster_id={cluster_id}"]
            )
            if not verification.get("success"):
                return {
                    "success": False,
                    "error": f"Unable to verify CCE cluster resolved from name '{value}': {verification.get('error', '')}",
                    "cluster_id": cluster_id,
                }
            return {"success": True, "id": cluster_id, "resolved_from_name": True}
    if len(matches) > 1:
        return {"success": False, "error": f"cluster_id '{value}' matched multiple CCE clusters; provide a standard UUID"}
    return {"success": False, "error": f"cluster_id must be a standard UUID. No CCE cluster named '{value}' was found"}
