"""Credential helpers for CCE Event queries."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Iterator, Optional


_ACTIVE_SECURITY_TOKEN: ContextVar[Optional[str]] = ContextVar("active_security_token", default=None)
_EXPLICIT_CREDENTIALS: ContextVar[bool] = ContextVar("explicit_credentials", default=False)


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
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve hcloud auth in priority order: arguments, profile, environment."""
    if ak or sk or project_id:
        return ak, sk, project_id
    if has_hcloud_profile():
        return None, None, None
    return get_credentials()


def redact_command(command: list[str]) -> list[str]:
    """Redact credential values before a command is returned to callers."""
    redacted: list[str] = []
    redact_next = False
    sensitive_keys = {"--cli-access-key", "--cli-secret-key", "--cli-security-token"}
    for part in command:
        if redact_next:
            redacted.append("***")
            redact_next = False
        elif part in sensitive_keys:
            redacted.append(part)
            redact_next = True
        else:
            redacted.append(re.sub(r"(--cli-(?:access-key|secret-key|security-token)=).*", r"\1***", part))
    return redacted


def redact_command_output(text: str, command: list[str], limit: int = 2000) -> str:
    """Redact CLI credential values that may be echoed in command diagnostics."""
    redacted = text or ""
    for part in command:
        if part.startswith(("--cli-access-key=", "--cli-secret-key=", "--cli-security-token=")):
            secret = part.split("=", 1)[1]
            if secret:
                redacted = redacted.replace(secret, "***")
    return redacted[:limit]
