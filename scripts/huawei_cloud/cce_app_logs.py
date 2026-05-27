"""Application log discovery and query helpers."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from typing import Any, Dict, Optional

from . import lts
from .common import _register_cert_file, _safe_delete_file, create_cce_client, get_credentials_with_region, k8s_client


def get_cce_logconfigs_action(params: Dict[str, str]) -> Dict[str, Any]:
    region = params["region"]
    cluster_id = params["cluster_id"]
    namespace = params.get("namespace")
    ak, sk, project_id = get_credentials_with_region(region, params.get("ak"), params.get("sk"), params.get("project_id"))

    temp_files = []
    try:
        from huaweicloudsdkcce.v3.model.cluster_cert_duration import ClusterCertDuration
        from huaweicloudsdkcce.v3.model.create_kubernetes_cluster_cert_request import CreateKubernetesClusterCertRequest

        cce_client = create_cce_client(region, ak, sk, project_id)
        cert_request = CreateKubernetesClusterCertRequest()
        cert_request.cluster_id = cluster_id
        body = ClusterCertDuration()
        body.duration = 1
        cert_request.body = body
        cert_response = cce_client.create_kubernetes_cluster_cert(cert_request)
        kubeconfig_data = cert_response.to_dict()

        external_cluster = None
        for cluster in kubeconfig_data.get("clusters", []):
            if "external" in cluster.get("name", "") and "TLS" not in cluster.get("name", ""):
                external_cluster = cluster
                break
        if not external_cluster:
            external_cluster = kubeconfig_data.get("clusters", [{}])[0]
        if not external_cluster:
            return {"success": False, "error": "Could not find cluster endpoint"}

        configuration = k8s_client.Configuration()
        configuration.host = external_cluster.get("cluster", {}).get("server")
        configuration.verify_ssl = False

        user_data = None
        for user in kubeconfig_data.get("users", []):
            if user.get("name") == "user":
                user_data = user.get("user", {})
                break

        if user_data and user_data.get("client_certificate_data"):
            cert_file = tempfile.mktemp(suffix=".crt")
            with open(cert_file, "wb") as handle:
                handle.write(base64.b64decode(user_data["client_certificate_data"]))
            configuration.cert_file = cert_file
            temp_files.append(cert_file)
            _register_cert_file(cert_file)

        if user_data and user_data.get("client_key_data"):
            key_file = tempfile.mktemp(suffix=".key")
            with open(key_file, "wb") as handle:
                handle.write(base64.b64decode(user_data["client_key_data"]))
            configuration.key_file = key_file
            temp_files.append(key_file)
            _register_cert_file(key_file)

        k8s_client.Configuration.set_default(configuration)
        custom_api = k8s_client.CustomObjectsApi()

        logconfigs = []
        tried = []
        cr_combinations = [
            ("logging.openvessel.io", "v1", "logconfigs"),
            ("lts.opentelekomcloud.com", "v1", "logconfigs"),
            ("lts.huaweicloud.com", "v1", "logconfigs"),
            ("lts.io", "v1", "logconfigs"),
            ("logging.huaweicloud.com", "v1", "logconfigs"),
            ("lts.opentelekomcloud.com", "v1alpha1", "logconfigs"),
            ("lts.opentelekomcloud.com", "v1beta1", "logconfigs"),
        ]
        for group, version, plural in cr_combinations:
            tried.append(f"{group}/{version}/{plural}")
            try:
                if namespace:
                    api_result = custom_api.list_namespaced_custom_object(group=group, version=version, namespace=namespace, plural=plural)
                else:
                    api_result = custom_api.list_cluster_custom_object(group=group, version=version, plural=plural)
                for item in api_result.get("items", []):
                    logconfigs.append(
                        {
                            "name": item.get("metadata", {}).get("name"),
                            "namespace": item.get("metadata", {}).get("namespace"),
                            "creation_time": str(item.get("metadata", {}).get("creationTimestamp")),
                            "spec": item.get("spec", {}),
                            "status": item.get("status", {}),
                            "api_version": f"{group}/{version}",
                        }
                    )
                if logconfigs:
                    break
            except Exception:
                continue

        return {
            "success": True,
            "cluster_id": cluster_id,
            "namespace": namespace or "all",
            "count": len(logconfigs),
            "tried_api_combinations": tried,
            "logconfigs": logconfigs,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}
    finally:
        for file_path in temp_files:
            _safe_delete_file(file_path)


def get_application_log_stream_action(params: Dict[str, str]) -> Dict[str, Any]:
    cluster_id = params["cluster_id"]
    app_name = params["app_name"]
    namespace = params.get("namespace")  # 不设置默认值，用于匹配逻辑

    # 去掉 namespace 参数，让 get_cce_logconfigs_action 搜索所有命名空间
    search_params = {k: v for k, v in params.items() if k != "namespace"}
    logconfig_result = get_cce_logconfigs_action(search_params)
    if not logconfig_result.get("success"):
        return logconfig_result

    logconfigs = logconfig_result.get("logconfigs", [])
    if not logconfigs:
        return {"success": False, "error": "集群中未找到任何LogConfig采集规则", "note": "请先配置日志采集规则或确认日志采集组件已安装"}

    match_type = None
    matched_config: Optional[Dict[str, Any]] = None

    for logconfig in logconfigs:
        try:
            if logconfig.get("spec", {}).get("inputDetail", {}).get("type") != "container_stdout":
                continue
            workloads = logconfig.get("spec", {}).get("inputDetail", {}).get("containerStdout", {}).get("workloads", [])
            for workload in workloads:
                if workload.get("namespace") == namespace and workload.get("name") == app_name:
                    matched_config = logconfig
                    match_type = "精确匹配应用LogConfig"
                    break
            if matched_config:
                break
        except Exception:
            continue

    if not matched_config:
        for logconfig in logconfigs:
            try:
                if logconfig.get("spec", {}).get("inputDetail", {}).get("type") != "container_stdout":
                    continue
                container_stdout = logconfig.get("spec", {}).get("inputDetail", {}).get("containerStdout", {})
                if container_stdout.get("allContainers") is not True:
                    continue
                allowed_namespaces = container_stdout.get("namespaces", [])
                if not allowed_namespaces or namespace in allowed_namespaces:
                    matched_config = logconfig
                    match_type = "命名空间全局LogConfig匹配"
                    break
            except Exception:
                continue

    if not matched_config:
        for logconfig in logconfigs:
            try:
                if logconfig.get("name") == "default-stdout" and logconfig.get("spec", {}).get("inputDetail", {}).get("type") == "container_stdout":
                    matched_config = logconfig
                    match_type = "默认default-stdout LogConfig匹配"
                    break
            except Exception:
                continue

    if not matched_config:
        return {"success": False, "error": "未匹配到任何日志采集规则", "note": "请检查应用是否配置了LogConfig采集规则，或集群是否存在default-stdout默认采集规则"}

    try:
        lts_config = matched_config.get("spec", {}).get("outputDetail", {}).get("LTS", {})
        log_group_id = lts_config.get("ltsGroupID")
        log_stream_id = lts_config.get("ltsStreamID", lts_config.get("streamID"))
        if not log_stream_id:
            log_stream_id = matched_config.get("spec", {}).get("logConfigStatus", {}).get("LTS", {}).get("streamID")
        if not log_group_id or not log_stream_id:
            return {
                "success": False,
                "error": "匹配到的LogConfig中未找到有效的日志组/流ID",
                "match_type": match_type,
                "logconfig_name": matched_config.get("name"),
            }
        return {
            "success": True,
            "match_type": match_type,
            "logconfig_name": matched_config.get("name"),
            "app_name": app_name,
            "namespace": namespace,
            "log_group_id": log_group_id,
            "log_stream_id": log_stream_id,
            "cluster_id": cluster_id,
        }
    except Exception as exc:
        return {"success": False, "error": f"解析LogConfig配置失败: {exc}", "match_type": match_type, "logconfig_name": matched_config.get("name")}


def query_application_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    namespace = params.get("namespace", "default")
    app_name = params["app_name"]
    custom_labels = _parse_labels(params.get("labels"))
    stream_result = get_application_log_stream_action(params)
    if not stream_result.get("success"):
        return stream_result

    system_labels = {"appName": app_name, "nameSpace": namespace}
    final_labels = system_labels.copy()
    if custom_labels:
        final_labels.update(custom_labels)

    result = lts.query_logs(
        region=params["region"],
        log_group_id=stream_result["log_group_id"],
        log_stream_id=stream_result["log_stream_id"],
        start_time=params.get("start_time"),
        end_time=params.get("end_time"),
        keywords=params.get("keywords"),
        limit=int(params.get("limit", 1000)),
        labels=final_labels,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )
    result.update(
        {
            "cluster_id": params["cluster_id"],
            "namespace": namespace,
            "app_name": app_name,
            "match_type": stream_result.get("match_type"),
            "logconfig_name": stream_result.get("logconfig_name"),
            "auto_label_filter": system_labels,
            "custom_labels": custom_labels,
            "final_labels": final_labels,
        }
    )
    return result


def query_application_recent_logs_action(params: Dict[str, str]) -> Dict[str, Any]:
    namespace = params.get("namespace", "default")
    app_name = params["app_name"]
    custom_labels = _parse_labels(params.get("labels"))
    stream_result = get_application_log_stream_action(params)
    if not stream_result.get("success"):
        return stream_result

    system_labels = {"appName": app_name, "nameSpace": namespace}
    final_labels = system_labels.copy()
    if custom_labels:
        final_labels.update(custom_labels)

    result = lts.get_recent_logs(
        region=params["region"],
        log_group_id=stream_result["log_group_id"],
        log_stream_id=stream_result["log_stream_id"],
        hours=int(params.get("hours", 1)),
        limit=int(params.get("limit", 1000)),
        keywords=params.get("keywords"),
        labels=final_labels,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
    )
    result.update(
        {
            "cluster_id": params["cluster_id"],
            "namespace": namespace,
            "app_name": app_name,
            "match_type": stream_result.get("match_type"),
            "logconfig_name": stream_result.get("logconfig_name"),
            "auto_label_filter": system_labels,
            "custom_labels": custom_labels,
            "final_labels": final_labels,
        }
    )
    return result


def _parse_labels(labels: Optional[str]) -> Optional[Dict[str, str]]:
    if not labels:
        return None
    if isinstance(labels, dict):
        return labels
    return json.loads(labels)
