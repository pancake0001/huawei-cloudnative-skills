"""Direct authenticated AOM Prometheus reads used by availability checks."""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any, Dict, Optional
from urllib.parse import quote, unquote

import requests

from .common import get_credentials_with_region


def get_aom_prom_metrics_http(region: str, aom_instance_id: str, query: str, start: Optional[int] = None, end: Optional[int] = None, step: int = 60, hours: int = 1, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """Query AOM Prometheus using an AK/SK-signed HTTP request."""
    access_key, secret_key, resolved_project_id = get_credentials_with_region(region, ak, sk, project_id)
    if not access_key or not secret_key:
        return {"success": False, "error": "AK and SK are required for the direct AOM Prometheus query"}
    if not resolved_project_id:
        return {"success": False, "error": "project_id is required for the direct AOM Prometheus query"}

    now = int(time.time())
    end_time = end or now
    start_time = start or end_time - hours * 3600
    path = f"/v1/{resolved_project_id}/{aom_instance_id}/aom/api/v1/query_range" if aom_instance_id and aom_instance_id not in {"default", "0", "Prometheus_AOM_Default"} else f"/v1/{resolved_project_id}/aom/api/v1/query_range"
    query_params = [("end", str(end_time)), ("query", query), ("start", str(start_time)), ("step", str(step))]
    encode = lambda value: quote(str(value), safe="~")
    canonical_uri = "/".join(encode(part) for part in unquote(path).split("/"))
    if not canonical_uri.endswith("/"):
        canonical_uri += "/"
    canonical_query = "&".join(f"{encode(key)}={encode(value)}" for key, value in sorted(query_params))
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now))
    host = f"aom.{region}.myhuaweicloud.com"
    signed_header_names = ["host", "x-project-id", "x-sdk-date"]
    if security_token:
        signed_header_names.append("x-security-token")
    signed_headers = ";".join(signed_header_names)
    canonical_headers = f"host:{host}\nx-project-id:{resolved_project_id}\nx-sdk-date:{timestamp}\n"
    if security_token:
        canonical_headers += f"x-security-token:{security_token}\n"
    canonical_request = f"GET\n{canonical_uri}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{hashlib.sha256(b'').hexdigest()}"
    string_to_sign = f"SDK-HMAC-SHA256\n{timestamp}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    signature = hmac.new(secret_key.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    headers = {"Host": host, "X-Project-Id": resolved_project_id, "X-Sdk-Date": timestamp, "Authorization": f"SDK-HMAC-SHA256 Access={access_key}, SignedHeaders={signed_headers}, Signature={signature}"}
    if security_token:
        headers["X-Security-Token"] = security_token
    url = f"https://{host}{path}?" + "&".join(f"{key}={urllib.parse.quote(str(value))}" for key, value in query_params)
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=True)
    except requests.RequestException as exc:
        return {"success": False, "error": str(exc)}
    if response.status_code != 200:
        return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:500]}"}
    try:
        payload = response.json()
    except ValueError:
        return {"success": False, "error": "AOM returned an invalid JSON response"}
    return {"success": True, "region": region, "aom_instance_id": aom_instance_id, "query": query, "time_range": {"start": start_time, "end": end_time, "step": step}, "result": payload}
