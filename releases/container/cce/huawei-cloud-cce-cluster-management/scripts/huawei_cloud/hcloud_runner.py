"""hcloud KooCLI execution core for CCE cluster management skill."""

import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional



class CredentialCtx:
    """Resolved credential context for hcloud/kubectl calls."""
    def __init__(self, ak: str, sk: str, security_token: Optional[str],
                 project_id: Optional[str], injected: bool = False,
                 prefer_cli_credentials: bool = False):
        self.ak = ak
        self.sk = sk
        self.security_token = security_token
        self.project_id = project_id
        self.injected = injected
        self.prefer_cli_credentials = prefer_cli_credentials


# Credentials injected by the sandbox runtime at the process entry.
# The sandbox does not nest-inject child hcloud/kubectl-cce, so the entry
# must forward these to children itself (see kubectl_cce / _fetch_project_id).
_INJECTED_AK: Optional[str] = None
_INJECTED_SK: Optional[str] = None
_INJECTED_TOKEN: Optional[str] = None


def set_injected_credentials(ak: Optional[str], sk: Optional[str],
                              token: Optional[str] = None) -> None:
    """Record credentials injected by the sandbox at the entry point."""
    global _INJECTED_AK, _INJECTED_SK, _INJECTED_TOKEN
    _INJECTED_AK, _INJECTED_SK, _INJECTED_TOKEN = ak, sk, token


_PROJECT_ID_CACHE = {}
_STANDARD_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)

# Cached check for hcloud CLI config credentials
_HCLOUD_CONFIG_CHECKED = False
_HCLOUD_HAS_CONFIG = False


def _hcloud_config_has_credentials() -> bool:
    """Check if hcloud CLI has credentials in its config file.

    If hcloud config has AK/SK, skip passing --cli-access-key/--cli-secret-key
    as CLI arguments to avoid exposure in ps aux.
    """
    global _HCLOUD_CONFIG_CHECKED, _HCLOUD_HAS_CONFIG
    if _HCLOUD_CONFIG_CHECKED:
        return _HCLOUD_HAS_CONFIG
    _HCLOUD_CONFIG_CHECKED = True
    try:
        r = subprocess.run(
            ["hcloud", "configure", "show"],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace"
        )
        if r.returncode == 0:
            config = json.loads(r.stdout)
            ak = config.get("accessKeyId", "")
            _HCLOUD_HAS_CONFIG = bool(ak) and ak.strip() != ""
    except Exception:
        pass
    return _HCLOUD_HAS_CONFIG


def resolve_credentials(
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    region: Optional[str] = None,
    fetch_project_id: bool = True,
) -> CredentialCtx:
    """Resolve credentials from params > injected > env vars. Auto-fetch project_id if missing.

    Set fetch_project_id=False for operations that don't need project_id
    (e.g., kubectl-cce node operations) to avoid unnecessary credential exposure.
    """
    access_key = ak or _INJECTED_AK or os.environ.get("HW_ACCESS_KEY") or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK")
    secret_key = sk or _INJECTED_SK or os.environ.get("HW_SECRET_KEY") or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK")
    token = _INJECTED_TOKEN or os.environ.get("HW_SECURITY_TOKEN")
    proj_id = project_id or os.environ.get("HW_PROJECT_ID") or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
    injected = (_INJECTED_AK is not None) and not ak

    if fetch_project_id and not proj_id and region and access_key and secret_key:
        proj_id = _fetch_project_id(region, access_key, secret_key, token)

    return CredentialCtx(
        ak=access_key,
        sk=secret_key,
        security_token=token,
        project_id=proj_id,
        injected=injected,
        prefer_cli_credentials=bool(ak or sk or _INJECTED_AK or _INJECTED_SK),
    )


def _fetch_project_id(region: str, ak: str, sk: str, token: Optional[str]) -> Optional[str]:
    """Fetch project_id via hcloud IAM KeystoneListProjects, cache in process memory."""
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]

    args = [
        "hcloud", "IAM", "KeystoneListProjects",
        f"--cli-region={region}",
        "--cli-output=json",
        f"--cli-query=projects[?name=='{region}'].id",
    ]
    # Only pass AK/SK as CLI args if hcloud config doesn't have credentials
    if not _hcloud_config_has_credentials():
        args.extend([f"--cli-access-key={ak}", f"--cli-secret-key={sk}"])
        if token:
            args.append(f"--cli-security-token={token}")

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            stdout = r.stdout.strip()
            json_start = stdout.find('[')
            if json_start >= 0:
                decoder = json.JSONDecoder()
                ids, _ = decoder.raw_decode(stdout[json_start:])
            elif stdout:
                decoder = json.JSONDecoder()
                try:
                    ids, _ = decoder.raw_decode(stdout)
                except json.JSONDecodeError:
                    ids = []
            else:
                ids = []
            if ids and len(ids) > 0:
                _PROJECT_ID_CACHE[region] = ids[0]
                return ids[0]
    except Exception:
        pass
    return None


def _build_auth_args(ctx: CredentialCtx) -> list:
    """Build hcloud CLI auth arguments.

    Explicit or sandbox-injected credentials override a local hcloud profile.
    """
    args = []
    if ctx.prefer_cli_credentials or not _hcloud_config_has_credentials():
        args.extend([f"--cli-access-key={ctx.ak}", f"--cli-secret-key={ctx.sk}"])
        if ctx.security_token:
            args.append(f"--cli-security-token={ctx.security_token}")
    if ctx.project_id:
        args.append(f"--cli-project-id={ctx.project_id}")
    return args


def _redact_hcloud_output(text: str, ctx: CredentialCtx, limit: int = 2000) -> str:
    """Redact credentials if hcloud echoes them in a diagnostic response."""
    redacted = text or ""
    for secret in (ctx.ak, ctx.sk, ctx.security_token):
        if secret:
            redacted = redacted.replace(secret, "***")
    return redacted[:limit]


def _redact_hcloud_command(args: List[str]) -> List[str]:
    return [re.sub(r"(--cli-(?:access-key|secret-key|security-token)=).*", r"\1***", arg) for arg in args]


def _parse_hcloud_output(stdout: str) -> tuple[Optional[Any], Optional[str]]:
    """Parse the JSON response without treating pure text as a successful response."""
    text = (stdout or "").strip()
    if not text:
        return None, "empty output"
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            return value, None
        except json.JSONDecodeError:
            continue
    return None, "no valid JSON object or array found"


def _normalize_hcloud_result(
    args: List[str], result: subprocess.CompletedProcess[str], ctx: CredentialCtx, service: str, operation: str
) -> Dict[str, Any]:
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    safe_stdout = _redact_hcloud_output(stdout, ctx)
    safe_stderr = _redact_hcloud_output(stderr, ctx)
    command = _redact_hcloud_command(args)
    if result.returncode:
        diagnostic = safe_stderr or safe_stdout
        return {
            "success": False,
            "error": f"hcloud exited with code {result.returncode}: {diagnostic}" if diagnostic else f"hcloud exited with code {result.returncode}",
            "raw_error": diagnostic or None,
            "stdout": safe_stdout,
            "stderr": safe_stderr,
            "returncode": result.returncode,
            "command": command,
        }
    if "[USE_ERROR]" in stdout:
        return {
            "success": False,
            "error": f"hcloud usage error: {safe_stdout}",
            "raw_error": safe_stdout or None,
            "stdout": safe_stdout,
            "stderr": safe_stderr,
            "returncode": result.returncode,
            "command": command,
        }
    data, parse_error = _parse_hcloud_output(stdout)
    if parse_error:
        diagnostic = safe_stderr or safe_stdout
        return {
            "success": False,
            "error": f"hcloud returned non-JSON output: {diagnostic}" if diagnostic else f"hcloud returned non-JSON output: {parse_error}",
            "raw_error": diagnostic or None,
            "stdout": safe_stdout,
            "stderr": safe_stderr,
            "returncode": result.returncode,
            "command": command,
        }
    if isinstance(data, dict):
        status = data.get("status", "")
        code = data.get("code")
        error_code = data.get("error_code") or data.get("errorCode")
        if status == "Failure" or (isinstance(code, int) and code >= 400) or error_code or (isinstance(code, str) and code and data.get("message")):
            error = data.get("error_msg") or data.get("errorMessage") or data.get("message", "")
            return {
                "success": False,
                "error": f"{error_code or code}: {error}",
                "data": data,
                "raw_error": safe_stderr or safe_stdout or None,
                "stdout": safe_stdout,
                "stderr": safe_stderr,
                "returncode": result.returncode,
                "command": command,
            }
    return {"success": True, "data": data, "message": f"{service} {operation} completed", "returncode": result.returncode, "command": command}


def run(
    ctx: CredentialCtx,
    region: str,
    service: str,
    operation: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute hcloud command and return normalized result."""
    args = ["hcloud", service, operation, f"--cli-region={region}", "--cli-output=json"]
    args.extend(_build_auth_args(ctx))

    # Always include project_id as a hcloud param (needed for path-based APIs)
    effective_params = dict(params)
    if ctx.project_id and "project_id" not in effective_params:
        effective_params["project_id"] = ctx.project_id

    for key, value in effective_params.items():
        args.append(f"--{key}={value}")

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        return _normalize_hcloud_result(args, r, ctx, service, operation)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"hcloud {service} {operation} timed out"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Failed to parse hcloud output: {e}", "raw": r.stdout[:500]}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def resolve_cce_cluster_id(ctx: CredentialCtx, region: str, value: str) -> Dict[str, Any]:
    """Validate a cluster UUID or resolve one exact CCE cluster-name match."""
    if _STANDARD_UUID_RE.fullmatch(value or ""):
        result = run(ctx, region, "CCE", "ShowCluster", {"cluster_id": value})
        if not result.get("success"):
            return {
                "success": False,
                "error": f"Unable to verify CCE cluster_id '{value}': {result.get('error', '')}",
                "cluster_id": value,
            }
        return {"success": True, "id": value, "resolved_from_name": False}
    # CCE ListClusters returns all items and does not accept limit or offset parameters.
    result = run(ctx, region, "CCE", "ListClusters", {})
    if not result.get("success"):
        return {"success": False, "error": f"Unable to list CCE clusters for cluster_id resolution: {result.get('error', '')}"}
    items = ((result.get("data") or {}).get("items") or [])
    matches = [item for item in items if ((item.get("metadata") or {}).get("name") == value)]
    if len(matches) == 1:
        cluster_id = (matches[0].get("metadata") or {}).get("uid")
        if _STANDARD_UUID_RE.fullmatch(cluster_id or ""):
            verification = run(ctx, region, "CCE", "ShowCluster", {"cluster_id": cluster_id})
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


def run_with_body(
    ctx: CredentialCtx,
    region: str,
    service: str,
    operation: str,
    body: Dict[str, Any],
    path_params: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute hcloud with complex nested body via --cli-jsonInput."""
    json_input = {}
    if path_params:
        json_input["path"] = path_params
    if query_params:
        json_input["query"] = query_params
    json_input["body"] = body

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(json_input, f)
        tmp_path = f.name

    try:
        args = ["hcloud", service, operation, f"--cli-region={region}", "--cli-output=json"]
        args.extend(_build_auth_args(ctx))
        args.append(f"--cli-jsonInput={tmp_path}")

        r = subprocess.run(args, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        return _normalize_hcloud_result(args, r, ctx, service, operation)
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ============================================================
# kubectl-cce: Kubernetes operations via kubectl cce plugin (no EIP needed)
# ============================================================

def kubectl_cce(ctx: CredentialCtx, region: str, cluster_id: str,
                args: List[str], timeout: int = 120) -> Dict[str, Any]:
    """Execute a kubectl cce command against a CCE cluster.

    Uses the kubectl-cce plugin which connects through the CCE API Gateway.
    No cluster EIP or manual kubeconfig required.

    Credentials are passed via environment variables (HW_ACCESS_KEY, HW_SECRET_KEY,
    HW_SECURITY_TOKEN, HW_PROJECT_ID) which the plugin reads automatically.
    """
    cmd = [
        "kubectl", "cce", "--cce-insecure-upstream-tls=true",
        f"--cluster-id={cluster_id}",
        f"--region={region}",
    ]
    if ctx.project_id:
        cmd.append(f"--project-id={ctx.project_id}")
    if ctx.injected:
        cmd.append(f"--cli-access-key={ctx.ak}")
        cmd.append(f"--cli-secret-key={ctx.sk}")
        if ctx.security_token:
            cmd.append(f"--cli-security-token={ctx.security_token}")
    cmd.extend(args)

    env = dict(os.environ)
    if not ctx.injected:
        # env-var mode: pass credentials via environment (no flags in child argv)
        if not env.get("HW_ACCESS_KEY") and ctx.ak:
            env["HW_ACCESS_KEY"] = ctx.ak
        if not env.get("HW_SECRET_KEY") and ctx.sk:
            env["HW_SECRET_KEY"] = ctx.sk
        if ctx.security_token and not env.get("HW_SECURITY_TOKEN"):
            env["HW_SECURITY_TOKEN"] = ctx.security_token
        if ctx.project_id and not env.get("HW_PROJECT_ID"):
            env["HW_PROJECT_ID"] = ctx.project_id
    # when injected, credentials are forwarded as --cli-* flags above only

    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env,
        )
        if r.returncode == 0:
            stdout = r.stdout.strip()
            # Try to parse JSON output (for -o json commands)
            if stdout.startswith("{") or stdout.startswith("["):
                try:
                    data = json.loads(stdout)
                    return {"success": True, "data": data, "stdout": stdout}
                except json.JSONDecodeError:
                    pass
            return {"success": True, "stdout": stdout}
        else:
            err = r.stderr.strip() or r.stdout.strip()
            return {"success": False, "error": err, "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"kubectl cce command timed out ({timeout}s)"}
    except FileNotFoundError:
        return {"success": False, "error": "kubectl or kubectl-cce plugin not found. Install via huawei-cloud-kubectl-cce-installer skill."}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
