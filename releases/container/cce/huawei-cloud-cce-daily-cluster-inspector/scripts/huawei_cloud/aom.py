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


def _query_aom_prometheus(region: str, aom_instance_id: str, endpoint: str, query: str, query_params: list[tuple[str, str]], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str], **details: Any) -> Dict[str, Any]:
    """Run one AK/SK-signed AOM Prometheus request."""
    access_key, secret_key, resolved_project_id = get_credentials_with_region(region, ak, sk, project_id, security_token)
    if not access_key or not secret_key:
        return {"success": False, "error": "AK and SK are required for the direct AOM Prometheus query"}
    if not resolved_project_id:
        return {"success": False, "error": "project_id is required for the direct AOM Prometheus query"}

    now = int(time.time())
    path = f"/v1/{resolved_project_id}/{aom_instance_id}/aom/api/v1/{endpoint}" if aom_instance_id and aom_instance_id not in {"default", "0", "Prometheus_AOM_Default"} else f"/v1/{resolved_project_id}/aom/api/v1/{endpoint}"
    encode = lambda value: quote(str(value), safe="~")
    canonical_uri = "/".join(encode(part) for part in unquote(path).split("/"))
    if not canonical_uri.endswith("/"):
        canonical_uri += "/"
    canonical_query = "&".join(f"{encode(key)}={encode(value)}" for key, value in sorted(query_params))
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now))
    host = f"aom.{region}.myhuaweicloud.com"
    signed_headers = "host;x-project-id;x-sdk-date"
    canonical_headers = f"host:{host}\nx-project-id:{resolved_project_id}\nx-sdk-date:{timestamp}\n"
    if security_token:
        signed_headers = "host;x-project-id;x-sdk-date;x-security-token"
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
    return {"success": True, "region": region, "aom_instance_id": aom_instance_id, "query": query, "result": payload, **details}


def get_aom_prom_metrics_http(region: str, aom_instance_id: str, query: str, start: Optional[int] = None, end: Optional[int] = None, step: int = 60, hours: int = 1, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """Query an AOM Prometheus range using an AK/SK-signed HTTP request."""
    now = int(time.time())
    end_time = end or now
    start_time = start or end_time - hours * 3600
    return _query_aom_prometheus(
        region,
        aom_instance_id,
        "query_range",
        query,
        [("end", str(end_time)), ("query", query), ("start", str(start_time)), ("step", str(step))],
        ak,
        sk,
        project_id,
        security_token,
        time_range={"start": start_time, "end": end_time, "step": step},
    )


def get_aom_prom_instant_query_http(region: str, aom_instance_id: str, query: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Query the current value of an AOM Prometheus expression."""
    query_time = int(time.time())
    query_params = [("query", query), ("time", str(query_time))]
    if limit is not None:
        query_params.append(("limit", str(max(1, int(limit)))))
    return _query_aom_prometheus(
        region,
        aom_instance_id,
        "query",
        query,
        query_params,
        ak,
        sk,
        project_id,
        security_token,
        query_time=query_time,
    )
