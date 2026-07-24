"""Credential and hcloud helpers for CCE log analysis."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Optional


def get_credentials(
    ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve explicit credentials before environment-variable fallback."""
    return (
        ak or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY"),
        sk or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY"),
        project_id or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID") or os.environ.get("HW_PROJECT_ID"),
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
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve hcloud authentication: arguments, profile, then environment."""
    if ak or sk or project_id:
        return ak, sk, project_id
    if has_hcloud_profile():
        return None, None, None
    return get_credentials()


def redact_command(command: list[str]) -> list[str]:
    """Redact credential values before returning a command to callers."""
    return [
        re.sub(r"(--cli-(?:access-key|secret-key|security-token)=).*", r"\1***", part)
        for part in command
    ]


def run_hcloud(command: list[str]) -> dict[str, Any]:
    """Run hcloud and require a complete JSON response."""
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
    try:
        return {"success": True, "data": json.loads((process.stdout or "").strip() or "{}")}
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "error": f"hcloud returned non-JSON output: {exc}",
            "command": safe_command,
        }


def hcloud_command(
    service: str,
    operation: str,
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> list[str]:
    """Build an hcloud command with the shared authentication priority."""
    access_key, secret_key, resolved_project_id = resolve_hcloud_credentials(ak, sk, project_id)
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
    return command
