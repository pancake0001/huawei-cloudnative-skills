"""hcloud helpers used by the CCE alarm-correlation skill."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

_PROJECT_ID_CACHE: Dict[str, str] = {}
_ACTIVE_SECURITY_TOKEN: ContextVar[Optional[str]] = ContextVar("active_security_token", default=None)
_EXPLICIT_CREDENTIALS: ContextVar[bool] = ContextVar("explicit_credentials", default=False)
_STANDARD_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


def normalize_cli_credentials(params: Dict[str, str]) -> Dict[str, str]:
    """Map public --cli-* credential parameters onto the internal names."""
    normalized = dict(params)
    for cli_name, internal_name in (("cli_access_key", "ak"), ("cli_secret_key", "sk"), ("cli_security_token", "security_token")):
        value = normalized.pop(cli_name, None)
        if not value:
            continue
        if normalized.get(internal_name) and normalized[internal_name] != value:
            raise ValueError(f"{cli_name} and {internal_name} must not provide different values")
        normalized[internal_name] = value
    has_ak = bool(normalized.get("ak"))
    has_sk = bool(normalized.get("sk"))
    has_token = bool(normalized.get("security_token"))
    if has_ak != has_sk:
        raise ValueError("cli_access_key and cli_secret_key must be provided together")
    if has_token and not has_ak:
        raise ValueError("cli_security_token requires cli_access_key and cli_secret_key")
    if has_ak:
        normalized["_explicit_cli_credentials"] = "true"
    return normalized


@contextmanager
def credential_context(params: Dict[str, str]) -> Iterator[Dict[str, str]]:
    normalized = normalize_cli_credentials(params)
    token = _ACTIVE_SECURITY_TOKEN.set(normalized.get("security_token"))
    explicit = _EXPLICIT_CREDENTIALS.set(normalized.get("_explicit_cli_credentials") == "true")
    try:
        yield normalized
    finally:
        _EXPLICIT_CREDENTIALS.reset(explicit)
        _ACTIVE_SECURITY_TOKEN.reset(token)


def get_security_token(security_token: Optional[str] = None) -> Optional[str]:
    token = security_token or _ACTIVE_SECURITY_TOKEN.get()
    if token or _EXPLICIT_CREDENTIALS.get():
        return token
    return os.environ.get("HW_SECURITY_TOKEN") or os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN")


def has_explicit_credentials() -> bool:
    """Return whether the active request supplied an explicit AK/SK pair."""
    return _EXPLICIT_CREDENTIALS.get()


def _has_hcloud_profile() -> bool:
    """Return whether local hcloud profile configuration appears to exist."""
    config_dir = os.environ.get("HCLOUD_CONFIG_DIR")
    candidates = []
    if config_dir:
        candidates.append(os.path.join(config_dir, "config.json"))
    candidates.extend([
        os.path.expanduser("~/.hcloud/config.json"),
        os.path.expanduser("~/.hcloud/config.yaml"),
        os.path.expanduser("~/.hcloud/config.yml"),
    ])
    return any(os.path.isfile(path) and os.path.getsize(path) > 0 for path in candidates)


def get_credentials(ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Return optional hcloud CLI credentials.

    Priority: explicit tool parameters > local hcloud profile > environment variables.
    When a local hcloud profile exists and AK/SK are not explicitly provided, do not
    pass environment credentials so the profile remains authoritative.
    """
    if ak or sk or project_id:
        return ak, sk, project_id
    if _has_hcloud_profile():
        return None, None, None
    return (
        os.environ.get("HW_ACCESS_KEY") or os.environ.get("HUAWEICLOUD_SDK_AK"),
        os.environ.get("HW_SECRET_KEY") or os.environ.get("HUAWEICLOUD_SDK_SK"),
        os.environ.get("HW_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID"),
    )


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
    token = get_security_token() if access_key and secret_key else None
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


def _parse_hcloud_stdout(stdout: str) -> Any:
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line or not line.startswith(("{", "[")):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    start = stdout.find("{")
    end = stdout.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(stdout[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _hcloud_success(returncode: int, stdout: str, parsed: Any) -> bool:
    if returncode != 0 or "[USE_ERROR]" in stdout:
        return False
    if stdout and parsed is None:
        return False
    if isinstance(parsed, dict) and parsed.get("error_code") and str(parsed.get("error_code")) != "200":
        return False
    return True


def _hcloud_error(returncode: int, stdout: str, stderr: str, parsed: Any) -> str:
    if returncode != 0:
        return stderr or stdout or f"hcloud exited with code {returncode}"
    if stdout and parsed is None:
        return "hcloud returned non-JSON output while --cli-output=json was requested"
    if isinstance(parsed, dict) and parsed.get("error_msg"):
        return str(parsed.get("error_msg"))
    return stderr or stdout or f"hcloud exited with code {returncode}"


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

    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "command": redact_command(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "data": None,
            "error": f"hcloud command timed out after {timeout} seconds",
        }
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    parsed = _parse_hcloud_stdout(stdout)
    success = _hcloud_success(completed.returncode, stdout, parsed)
    return {
        "success": success,
        "command": redact_command(command),
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "data": parsed,
        "error": None if success else _hcloud_error(completed.returncode, stdout, stderr, parsed),
    }


def resolve_cce_cluster_id(
    region: str,
    value: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a standard cluster UUID, resolving an exact cluster name when needed."""
    if _STANDARD_UUID_RE.fullmatch(value or ""):
        result = run_hcloud("CCE", "ShowCluster", region, [("cluster_id", value)], ak, sk, project_id)
        if not result.get("success"):
            return {
                "success": False,
                "error": f"Unable to verify CCE cluster_id '{value}': {result.get('error', '')}",
                "cluster_id": value,
            }
        return {"success": True, "id": value, "resolved_from_name": False}

    # CCE ListClusters returns all items and does not accept limit or offset parameters.
    result = run_hcloud("CCE", "ListClusters", region, None, ak, sk, project_id)
    if not result.get("success"):
        return {"success": False, "error": f"Unable to list CCE clusters for cluster_id resolution: {result.get('error', '')}"}
    items = ((result.get("data") or {}).get("items") or [])
    matches = [item for item in items if ((item.get("metadata") or {}).get("name") == value)]
    if len(matches) == 1:
        cluster_id = (matches[0].get("metadata") or {}).get("uid")
        if _STANDARD_UUID_RE.fullmatch(cluster_id or ""):
            return {"success": True, "id": cluster_id, "resolved_from_name": True, "name": value}
    if len(matches) > 1:
        return {"success": False, "error": f"cluster_id '{value}' matched multiple CCE clusters; provide a standard UUID"}
    return {"success": False, "error": f"cluster_id must be a standard UUID. No CCE cluster named '{value}' was found"}


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
        try:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            return {
                "success": False,
                "command": redact_command(command),
                "returncode": None,
                "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
                "data": None,
                "error": f"hcloud command timed out after {timeout} seconds",
            }
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed = _parse_hcloud_stdout(stdout)
    success = _hcloud_success(completed.returncode, stdout, parsed)
    return {
        "success": success,
        "command": redact_command(command),
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "data": parsed,
        "error": None if success else _hcloud_error(completed.returncode, stdout, stderr, parsed),
    }


def get_project_id_for_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None) -> Optional[str]:
    """Resolve a Huawei Cloud project ID for a region through hcloud."""
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]

    result = run_hcloud("IAM", "KeystoneListProjects", region, [("name", region)], ak=ak, sk=sk)
    if not result.get("success"):
        result = run_hcloud("IAM", "KeystoneListProjects", region, [], ak=ak, sk=sk)
    projects = extract_items(result.get("data"), "projects")
    for project in projects:
        name = project.get("name")
        project_id = project.get("id")
        if name == region and project_id:
            _PROJECT_ID_CACHE[region] = project_id
            return project_id
    return None


def resolve_project_id_for_region(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Optional[str]:
    """Resolve project ID using explicit input, hcloud profile, then environment."""
    if project_id:
        return project_id
    resolved = get_project_id_for_region(region, ak, sk)
    if resolved:
        return resolved
    return os.environ.get("HW_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")


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
