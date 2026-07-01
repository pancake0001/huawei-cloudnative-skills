"""hcloud helpers used by the CCE alarm-correlation skill."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Tuple


def get_credentials(ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Return optional credentials from params or environment variables.

    hcloud can also use its configured profile, so missing AK/SK is not an error here.
    """
    access_key = ak or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY")
    secret_key = sk or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY")
    proj_id = project_id or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
    return access_key, secret_key, proj_id


def get_credentials_with_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Compatibility wrapper for existing dispatcher signatures."""
    del region
    return get_credentials(ak, sk, project_id)


def redact_command(command: Iterable[str]) -> List[str]:
    """Return a command with secret-bearing hcloud options redacted."""
    redacted: List[str] = []
    sensitive_prefixes = ("--cli-access-key=", "--cli-secret-key=", "--cli-security-token=")
    sensitive_keys = {"--cli-access-key", "--cli-secret-key", "--cli-security-token"}
    skip_value = False
    for item in command:
        if skip_value:
            redacted.append("***")
            skip_value = False
            continue
        if item in sensitive_keys:
            redacted.append(item)
            skip_value = True
            continue
        if item.startswith(sensitive_prefixes):
            key = item.split("=", 1)[0]
            redacted.append(f"{key}=***")
            continue
        redacted.append(item)
    return redacted


def _base_hcloud_command(
    service: str,
    operation: str,
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> List[str]:
    if not shutil.which("hcloud"):
        raise RuntimeError("hcloud CLI is not installed or not found in PATH")

    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    command = ["hcloud", service, operation, f"--cli-region={region}", "--cli-output=json"]
    if access_key and secret_key:
        command.extend([f"--cli-access-key={access_key}", f"--cli-secret-key={secret_key}"])
    token = os.environ.get("HUAWEI_SECURITY_TOKEN") or os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN")
    if token:
        command.append(f"--cli-security-token={token}")
    if proj_id:
        command.append(f"--project_id={proj_id}")
    return command


def _append_param(command: List[str], key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        value = "true" if value else "false"
    command.append(f"--{key}={value}")


def run_hcloud(
    service: str,
    operation: str,
    region: str,
    params: Optional[Iterable[Tuple[str, Any]]] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    timeout: int = 60,
    dryrun: bool = False,
) -> Dict[str, Any]:
    """Run hcloud and parse JSON output when possible."""
    command = _base_hcloud_command(service, operation, region, ak, sk, project_id)
    for key, value in params or []:
        _append_param(command, key, value)
    if dryrun:
        command.append("--dryrun")

    completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    parsed: Any = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None

    success = completed.returncode == 0 and not stdout.startswith("[USE_ERROR]")
    return {
        "success": success,
        "command": redact_command(command),
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "data": parsed,
        "error": None if success else (stderr or stdout or f"hcloud exited with code {completed.returncode}"),
    }


def run_hcloud_json_input(
    service: str,
    operation: str,
    region: str,
    payload: Dict[str, Any],
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    timeout: int = 60,
    dryrun: bool = False,
) -> Dict[str, Any]:
    """Run hcloud with a temporary --cli-jsonInput file."""
    fd, path = tempfile.mkstemp(prefix="hcloud-aom-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        command = _base_hcloud_command(service, operation, region, ak, sk, project_id)
        command.append(f"--cli-jsonInput={path}")
        if dryrun:
            command.append("--dryrun")
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed: Any = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None

    success = completed.returncode == 0 and not stdout.startswith("[USE_ERROR]")
    return {
        "success": success,
        "command": redact_command(command),
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "data": parsed,
        "error": None if success else (stderr or stdout or f"hcloud exited with code {completed.returncode}"),
    }


def extract_items(data: Any, *keys: str) -> List[Dict[str, Any]]:
    """Extract a list of dictionaries from a hcloud JSON response."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    for value in data.values():
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return value
    return []
