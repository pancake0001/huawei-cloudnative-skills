"""Shared entry helpers (arg parsing) — importable from tests."""
from typing import Dict, Optional, Tuple

_INJECTED_FLAGS = ("--cli-access-key", "--cli-secret-key", "--cli-security-token")


def parse_args(args) -> Tuple[Dict[str, str], Tuple[Optional[str], Optional[str], Optional[str]]]:
    """Parse key=value params, extracting sandbox-injected --cli-* flags separately.

    Supports both --flag=value and --flag value forms. Returns (params, (ak, sk, token)).
    """
    params: Dict[str, str] = {}
    ak = sk = token = None
    i = 0
    while i < len(args):
        arg = args[i]
        matched = False
        for flag in _INJECTED_FLAGS:
            if arg == flag and i + 1 < len(args):
                if flag == "--cli-access-key":
                    ak = args[i + 1]
                elif flag == "--cli-secret-key":
                    sk = args[i + 1]
                else:
                    token = args[i + 1]
                i += 2
                matched = True
                break
            elif arg.startswith(flag + "="):
                val = arg.split("=", 1)[1]
                if flag == "--cli-access-key":
                    ak = val
                elif flag == "--cli-secret-key":
                    sk = val
                else:
                    token = val
                i += 1
                matched = True
                break
        if matched:
            continue
        if "=" in arg:
            k, v = arg.split("=", 1)
            params[k] = v
        i += 1
    injected = (ak, sk, token) if (ak or sk or token) else (None, None, None)
    return params, injected
