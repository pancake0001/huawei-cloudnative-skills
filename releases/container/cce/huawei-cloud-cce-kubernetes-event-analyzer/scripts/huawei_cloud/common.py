"""Minimal SDK helpers for historical CCE Event queries."""

from __future__ import annotations

import os
from typing import Optional

from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest

try:
    from kubernetes import client as k8s_client
except ImportError:
    k8s_client = None


_PROJECT_ID_CACHE: dict[str, str] = {}
_TEMP_CERT_FILES: set[str] = set()


def _register_cert_file(filepath: Optional[str]) -> None:
    if filepath:
        _TEMP_CERT_FILES.add(filepath)


def _safe_delete_file(filepath: Optional[str]) -> None:
    if not filepath:
        return
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    finally:
        _TEMP_CERT_FILES.discard(filepath)


def get_credentials(
    ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve explicit credentials before environment-variable fallback."""
    return (
        ak or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY"),
        sk or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY"),
        project_id or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID") or os.environ.get("HW_PROJECT_ID"),
    )


def _create_iam_client(ak: str, sk: str) -> IamClient:
    return IamClient.new_builder().with_credentials(GlobalCredentials(ak=ak, sk=sk)).with_endpoint("iam.myhuaweicloud.com").build()


def get_project_id_for_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None) -> Optional[str]:
    """Resolve and cache the IAM project that has the requested region name."""
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]
    access_key, secret_key, _ = get_credentials(ak, sk)
    if not access_key or not secret_key:
        return None
    try:
        request = KeystoneListProjectsRequest()
        request.name = region
        projects = _create_iam_client(access_key, secret_key).keystone_list_projects(request).projects or []
        for project in projects:
            if project.name == region:
                _PROJECT_ID_CACHE[region] = project.id
                return project.id
    except Exception:
        return None
    return None


def get_credentials_with_region(
    region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    access_key, secret_key, resolved_project_id = get_credentials(ak, sk, project_id)
    if not resolved_project_id and access_key and secret_key:
        resolved_project_id = get_project_id_for_region(region, access_key, secret_key)
    return access_key, secret_key, resolved_project_id


def create_cce_client(region: str, ak: str, sk: str, project_id: Optional[str] = None) -> CceClient:
    credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id) if project_id else BasicCredentials(ak=ak, sk=sk)
    return CceClient.new_builder().with_credentials(credentials).with_endpoint(f"cce.{region}.myhuaweicloud.com").build()
