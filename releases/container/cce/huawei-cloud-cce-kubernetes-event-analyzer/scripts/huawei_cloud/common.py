"""Credential helpers for CCE Event queries."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Iterator, Optional


_ACTIVE_SECURITY_TOKEN: ContextVar[Optional[str]] = ContextVar("active_security_token", default=None)


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
    return normalized


@contextmanager
def credential_context(params: Dict[str, str]) -> Iterator[Dict[str, str]]:
    normalized = normalize_cli_credentials(params)
    token = _ACTIVE_SECURITY_TOKEN.set(normalized.get("security_token"))
    try:
        yield normalized
    finally:
        _ACTIVE_SECURITY_TOKEN.reset(token)


def get_security_token(security_token: Optional[str] = None) -> Optional[str]:
    return security_token or _ACTIVE_SECURITY_TOKEN.get() or os.environ.get("HUAWEI_SECURITY_TOKEN") or os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN") or os.environ.get("HW_SECURITY_TOKEN")


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
