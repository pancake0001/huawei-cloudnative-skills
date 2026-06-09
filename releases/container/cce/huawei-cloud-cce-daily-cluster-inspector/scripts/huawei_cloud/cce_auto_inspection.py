#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCE 集群自动巡检模块 —— 快检 + 诊断分离架构

设计理念：
  快检（Quick Check）: 只看告警、事件、Pod/Node 监控 TopN，判断是否存在异常
  诊断（Deep Diagnosis）: 异常时才执行，归并异常信号并采集根因分析证据

使用方式：
  # 快检（用于 cron 高频调用）
  huawei_cce_quick_check region=cn-north-4 cluster_id=xxx

  # 深度诊断（快检发现异常后调用）
  huawei_cce_deep_diagnosis region=cn-north-4 cluster_id=xxx check_result=<快检结果JSON>

  # 自动巡检（快检 + 判断 + 诊断，一步到位）
  huawei_cce_auto_inspection region=cn-north-4 cluster_id=xxx

cron 配置建议：
  - 每 5 分钟执行 huawei_cce_auto_inspection，超时设 60s（无异常时 <30s 直接返回）
  - 发现异常时由 agent 自行 spawn 诊断子任务，不占巡检超时

异常判断阈值（可配置）：
  - AOM firing Critical/Major 告警
  - Kubernetes Warning/Failed/BackOff/OOM/Event 异常事件
  - Pod CPU/Memory TopN 超阈值
  - Node CPU/Memory/Disk TopN 超阈值
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .common import get_credentials_with_region
from .aom import list_aom_alarms, list_aom_instances
from .cce import (
    get_kubernetes_deployments,
    get_kubernetes_events,
    get_kubernetes_ingresses,
    get_kubernetes_nodes,
    get_kubernetes_pods,
    get_kubernetes_services,
    list_cce_clusters,
)
from .cce_metrics import get_cce_node_metrics_topN, get_cce_pod_metrics_topN
from .elb import get_elb_backend_status, get_elb_metrics
from .network import (
    get_eip_metrics,
    get_nat_gateway_metrics,
    list_eip_addresses,
    list_nat_gateways,
)
from .cce_inspection import (
    aom_alarm_inspection,
    node_status_inspection,
    pod_status_inspection,
    event_inspection,
    node_resource_monitoring_inspection,
    addon_pod_monitoring_inspection,
    biz_pod_monitoring_inspection,
)
from .cce_diagnosis import workload_diagnose, network_diagnose
from .report_generator import generate_detailed_html_report


# ========== 默认阈值配置 ==========

DEFAULT_THRESHOLDS = {
    "alarm_hours": 0.5,                # 快检告警查询时间窗口 (小时)
    "event_limit": 200,                # 快检事件采样条数
    "pod_metric_hours": 0.25,          # 快检 Pod TopN 监控窗口
    "node_metric_hours": 0.25,         # 快检 Node TopN 监控窗口
    "pod_cpu_avg_percent": 60,         # Pod CPU TopN 异常阈值
    "pod_memory_avg_percent": 80,      # Pod Memory TopN 异常阈值
    "node_cpu_percent": 80,            # Node CPU TopN 异常阈值
    "node_memory_percent": 80,         # Node Memory TopN 异常阈值
    "node_disk_percent": 85,           # Node Disk TopN 异常阈值
    "deep_event_limit": 500,           # 深诊事件采样条数
    "deep_metric_hours": 1,            # 深诊监控窗口
    "peripheral_metric_hours": 1,      # 周边资源监控窗口
}


# ========== 快检：告警 + 事件 + Pod/Node TopN，< 30s ==========

def cce_quick_check(
    region: str,
    cluster_id: str,
    ak: str = None,
    sk: str = None,
    project_id: str = None,
    thresholds: Dict[str, Any] = None,
    elb_ids: List[str] = None,
    business_labels: List[str] = None,
) -> Dict[str, Any]:
    """CCE 集群快速巡检（<30s）

    只做轻量异常存在性判断：
    1. AOM 告警是否存在 Critical/Major firing
    2. Kubernetes Warning/Failed/BackOff/OOM 等异常事件是否存在
    3. Pod CPU/Memory TopN 是否超阈值
    4. Node CPU/Memory/Disk TopN 是否超阈值

    quick 不做应用归因、ELB/EIP/NAT 关联、Pod 状态遍历或副本数分析；
    这些在 deep diagnosis 阶段完成。

    Args:
        region: 华为云区域
        cluster_id: CCE 集群 ID
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
        thresholds: 自定义阈值（覆盖 DEFAULT_THRESHOLDS）
        elb_ids: 保留兼容参数，quick 阶段不使用
        business_labels: 业务 Pod 标签列表，如 ["app=nginx", "app=api"]

    Returns:
        {
            "success": True,
            "has_anomaly": True/False,
            "anomaly_details": [...],
            "normal_details": [...],
            "duration_seconds": 12.3,
            "metrics": {
                "alarms": {...},
                "events": {...},
                "pod_metrics_topn": {...},
                "node_metrics_topn": {...},
            }
        }
    """
    start_time = time.time()
    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    cfg = {**DEFAULT_THRESHOLDS}
    if thresholds:
        cfg.update(thresholds)

    result = {
        "success": True,
        "has_anomaly": False,
        "anomaly_details": [],
        "normal_details": [],
        "metrics": {},
        "duration_seconds": 0,
        "cluster_id": cluster_id,
        "region": region,
        "check_time": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST"),
    }

    # ---- 获取集群名称 ----
    cluster_name = cluster_id
    try:
        clusters = list_cce_clusters(region, access_key, secret_key, proj_id)
        if clusters.get("success"):
            for c in clusters.get("clusters", []):
                if c.get("id") == cluster_id:
                    cluster_name = c.get("name", cluster_id)
                    break
    except Exception:
        pass

    # ---- Step 1: AOM 告警查询 (active + history) ----
    alarm_data = {}
    try:
        alarm_result = list_aom_alarms(
            region=region,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            cluster_name=cluster_name,
            hours=cfg["alarm_hours"],
            limit=200,
        )
        alarm_data = alarm_result if alarm_result.get("success") else {"error": alarm_result.get("error", "Unknown")}
        result["metrics"]["alarms"] = alarm_data

        if alarm_result.get("success"):
            for alarm in alarm_result.get("events", []):
                alarm_text = alarm.get("event_name", "") + " " + alarm.get("message", "")
                severity = alarm.get("event_severity", "Info")
                status = str(alarm.get("status", "")).lower()

                if severity in ("Critical", "Major") and status == "firing":
                    result["has_anomaly"] = True
                    result["anomaly_details"].append({
                        "type": "aom_alarm",
                        "severity": severity,
                        "name": alarm.get("event_name"),
                        "status": alarm.get("status"),
                        "message": alarm.get("message", "")[:200],
                        "raw_text": alarm_text[:300],
                    })

            if not result["anomaly_details"]:
                result["normal_details"].append(
                    f"AOM 告警正常：{alarm_result.get('firing_count', 0)} firing, "
                    f"{alarm_result.get('resolved_count', 0)} resolved，无 Critical/Major firing"
                )
    except Exception as e:
        result["metrics"]["alarms"] = {"error": str(e)}

    # ---- Step 2: Kubernetes 异常事件采样 ----
    try:
        events_result = get_kubernetes_events(
            region=region,
            cluster_id=cluster_id,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            limit=cfg["event_limit"],
        )
        result["metrics"]["events"] = events_result if events_result.get("success") else {
            "error": events_result.get("error", "Unknown")
        }
        if events_result.get("success"):
            event_anomalies = _detect_event_anomalies(events_result.get("events", []))
            if event_anomalies:
                result["has_anomaly"] = True
                result["anomaly_details"].append({
                    "type": "k8s_event_anomaly",
                    "events": event_anomalies[:20],
                    "message": f"发现 {len(event_anomalies)} 条异常 Kubernetes Event",
                })
            else:
                result["normal_details"].append(f"Kubernetes Event 正常：最近 {events_result.get('count', 0)} 条无异常事件")
    except Exception as e:
        result["metrics"]["events"] = {"error": str(e)}

    # ---- Step 3: Pod CPU/Memory TopN ----
    try:
        pod_topn = get_cce_pod_metrics_topN(
            region=region,
            cluster_id=cluster_id,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            top_n=10,
            hours=cfg["pod_metric_hours"],
        )
        result["metrics"]["pod_metrics_topn"] = pod_topn if pod_topn.get("success") else {
            "error": pod_topn.get("error", "Unknown")
        }
        if pod_topn.get("success"):
            pod_metric_anomalies = _detect_pod_topn_anomalies(pod_topn, cfg)
            if pod_metric_anomalies:
                result["has_anomaly"] = True
                result["anomaly_details"].append({
                    "type": "pod_metric_topn_anomaly",
                    "metrics": pod_metric_anomalies[:20],
                    "message": f"发现 {len(pod_metric_anomalies)} 个 Pod TopN 监控异常",
                })
            else:
                result["normal_details"].append("Pod 监控 TopN 正常：CPU/Memory 未超过阈值")
    except Exception as e:
        result["metrics"]["pod_metrics_topn"] = {"error": str(e)}

    # ---- Step 4: Node CPU/Memory/Disk TopN ----
    try:
        node_topn = get_cce_node_metrics_topN(
            region=region,
            cluster_id=cluster_id,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            top_n=10,
            hours=cfg["node_metric_hours"],
        )
        result["metrics"]["node_metrics_topn"] = node_topn if node_topn.get("success") else {
            "error": node_topn.get("error", "Unknown")
        }
        if node_topn.get("success"):
            node_metric_anomalies = _detect_node_topn_anomalies(node_topn, cfg)
            if node_metric_anomalies:
                result["has_anomaly"] = True
                result["anomaly_details"].append({
                    "type": "node_metric_topn_anomaly",
                    "metrics": node_metric_anomalies[:20],
                    "message": f"发现 {len(node_metric_anomalies)} 个 Node TopN 监控异常",
                })
            else:
                result["normal_details"].append("Node 监控 TopN 正常：CPU/Memory/Disk 未超过阈值")
    except Exception as e:
        result["metrics"]["node_metrics_topn"] = {"error": str(e)}

    result["duration_seconds"] = round(time.time() - start_time, 2)

    return result


# ========== 深度诊断：异常后执行 ==========

def cce_deep_diagnosis(
    region: str,
    cluster_id: str,
    quick_check_result: Dict[str, Any] = None,
    ak: str = None,
    sk: str = None,
    project_id: str = None,
    notify_email: str = None,
    report_file: str = None,
) -> Dict[str, Any]:
    """CCE 集群深度诊断（快检发现异常后调用）

    执行多项只读 API 获取完整诊断证据：
    1. 归并 AOM 告警项
    2. 分析异常事件及关联应用对象
    3. 采集工作负载、Pod、Node、Service、Ingress 状态
    4. 分析 Pod/Node 监控异常时间段
    5. 若事件或服务涉及 ELB/EIP/NAT，关联分析周边资源状态
    6. 生成 root-cause-analyzer 交接包

    根因分析不在本函数内执行，必须交给 huawei-cloud-cce-root-cause-analyzer。
    恢复建议和恢复动作必须交给 huawei-cloud-cce-auto-remediation-runner。

    Args:
        region: 华为云区域
        cluster_id: CCE 集群 ID
        quick_check_result: 快检结果（用于提取异常上下文，可选）
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
        notify_email: 通知邮箱（可选）
        report_file: HTML 报告输出路径（默认 /tmp/cce_diag_report.html）

    Returns:
        完整诊断结果
    """
    start_time = time.time()
    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    result = {
        "success": True,
        "cluster_id": cluster_id,
        "region": region,
        "diagnosis_time": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST"),
        "quick_check_anomalies": [],
        "diagnosis": {},
        "root_cause_handoff": {},
        "remediation_handoff": {},
        "duration_seconds": 0,
    }

    # 提取快检异常上下文
    if quick_check_result and quick_check_result.get("anomaly_details"):
        result["quick_check_anomalies"] = quick_check_result["anomaly_details"]

    # ---- 获取集群名称 & AOM 实例 ----
    cluster_name = cluster_id
    aom_instance_id = None
    try:
        clusters = list_cce_clusters(region, access_key, secret_key, proj_id)
        if clusters.get("success"):
            for c in clusters.get("clusters", []):
                if c.get("id") == cluster_id:
                    cluster_name = c.get("name", cluster_id)
                    break
    except Exception:
        pass

    try:
        aom_result = list_aom_instances(region, access_key, secret_key, proj_id)
        if aom_result.get("success"):
            for inst in aom_result.get("instances", []):
                if inst.get("cluster_id") == cluster_id or inst.get("cluster_name") == cluster_name:
                    aom_instance_id = inst.get("id")
                    break
    except Exception:
        pass

    cfg = {**DEFAULT_THRESHOLDS}

    # ---- 诊断 Step 1: AOM 告警归并分析 ----
    try:
        from .aom import analyze_aom_alarms
        alarm_analysis = analyze_aom_alarms(
            region=region,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            hours=1,
        )
        result["diagnosis"]["alarm_analysis"] = alarm_analysis
    except Exception as e:
        result["diagnosis"]["alarm_analysis"] = {"error": str(e)}

    result["diagnosis"]["alarm_correlation"] = _summarize_alarm_correlation(
        result["diagnosis"].get("alarm_analysis", {}),
        result["quick_check_anomalies"],
    )

    # ---- 诊断 Step 2: Pod/Node 监控 TopN，保留完整时序用于异常时间段分析 ----
    try:
        pod_topn = get_cce_pod_metrics_topN(
            region=region,
            cluster_id=cluster_id,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            top_n=10,
            hours=cfg["deep_metric_hours"],
        )
        result["diagnosis"]["pod_metrics_topn"] = pod_topn
    except Exception as e:
        result["diagnosis"]["pod_metrics_topn"] = {"error": str(e)}

    try:
        node_topn = get_cce_node_metrics_topN(
            region=region,
            cluster_id=cluster_id,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            top_n=10,
            hours=cfg["deep_metric_hours"],
        )
        result["diagnosis"]["node_metrics_topn"] = node_topn
    except Exception as e:
        result["diagnosis"]["node_metrics_topn"] = {"error": str(e)}

    result["diagnosis"]["monitoring_windows"] = _analyze_monitoring_windows(
        result["diagnosis"].get("pod_metrics_topn", {}),
        result["diagnosis"].get("node_metrics_topn", {}),
        cfg,
    )

    # ---- 诊断 Step 3: 应用和节点对象状态 ----
    try:
        deploys_result = get_kubernetes_deployments(region, cluster_id, access_key, secret_key, proj_id)
        result["diagnosis"]["deployments"] = deploys_result
    except Exception as e:
        result["diagnosis"]["deployments"] = {"error": str(e)}

    try:
        pods_result = get_kubernetes_pods(region, cluster_id, access_key, secret_key, proj_id)
        result["diagnosis"]["pods"] = pods_result
    except Exception as e:
        result["diagnosis"]["pods"] = {"error": str(e)}

    try:
        nodes_result = get_kubernetes_nodes(region, cluster_id, access_key, secret_key, proj_id)
        result["diagnosis"]["nodes"] = nodes_result
    except Exception as e:
        result["diagnosis"]["nodes"] = {"error": str(e)}

    try:
        services_result = get_kubernetes_services(region, cluster_id, access_key, secret_key, proj_id)
        result["diagnosis"]["services"] = services_result
    except Exception as e:
        result["diagnosis"]["services"] = {"error": str(e)}

    try:
        ingresses_result = get_kubernetes_ingresses(region, cluster_id, access_key, secret_key, proj_id)
        result["diagnosis"]["ingresses"] = ingresses_result
    except Exception as e:
        result["diagnosis"]["ingresses"] = {"error": str(e)}

    # ---- 诊断 Step 4: 集群事件详细分析 ----
    try:
        events_result = get_kubernetes_events(
            region,
            cluster_id,
            access_key,
            secret_key,
            proj_id,
            limit=cfg["deep_event_limit"],
        )
        result["diagnosis"]["events"] = events_result
    except Exception as e:
        result["diagnosis"]["events"] = {"error": str(e)}

    result["diagnosis"]["event_analysis"] = _analyze_abnormal_events(
        result["diagnosis"].get("events", {}),
        result["diagnosis"].get("pods", {}),
        result["diagnosis"].get("deployments", {}),
    )
    result["diagnosis"]["application_evidence"] = _analyze_application_evidence(
        result["quick_check_anomalies"],
        result["diagnosis"].get("event_analysis", {}),
        result["diagnosis"].get("pods", {}),
        result["diagnosis"].get("deployments", {}),
        result["diagnosis"].get("services", {}),
        result["diagnosis"].get("ingresses", {}),
    )

    # ---- 诊断 Step 5: 周边资源状态分析（仅在涉及入口/网络资源时触发）----
    result["diagnosis"]["peripheral_resources"] = _analyze_peripheral_resources(
        region=region,
        cluster_id=cluster_id,
        ak=access_key,
        sk=secret_key,
        project_id=proj_id,
        services=result["diagnosis"].get("services", {}),
        ingresses=result["diagnosis"].get("ingresses", {}),
        events=result["diagnosis"].get("event_analysis", {}),
        quick_anomalies=result["quick_check_anomalies"],
        hours=cfg["peripheral_metric_hours"],
    )

    # ---- 诊断 Step 6: 根因分析交接 ----
    result["root_cause_handoff"] = {
        "skill": "huawei-cloud-cce-root-cause-analyzer",
        "required": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "time_window": _derive_handoff_time_window(result["diagnosis"].get("monitoring_windows", {})),
        "symptoms": result["quick_check_anomalies"],
        "evidence": result["diagnosis"],
        "analysis_focus": [
            "correlate merged AOM alarms with Kubernetes abnormal events",
            "verify affected application/workload evidence before selecting root cause",
            "inspect Pod/Node metric abnormal windows and event timestamps for temporal order",
            "include ELB/EIP/NAT status when ingress, service, or network symptoms are present",
        ],
        "data_gaps": _collect_diagnosis_data_gaps(result["diagnosis"]),
    }
    result["remediation_handoff"] = {
        "skill": "huawei-cloud-cce-auto-remediation-runner",
        "requires_root_cause": True,
        "mode": "advice | preview | authorized_execution",
        "message": "Run root-cause analysis first, then use root-cause-backed remediation hints for recovery advice or authorized action.",
    }

    result["duration_seconds"] = round(time.time() - start_time, 2)

    return result


# ========== 自动巡检：快检 + 判断 + 诊断 ==========

def cce_auto_inspection(
    region: str,
    cluster_id: str,
    ak: str = None,
    sk: str = None,
    project_id: str = None,
    thresholds: Dict[str, Any] = None,
    elb_ids: List[str] = None,
    notify_email: str = None,
) -> Dict[str, Any]:
    """CCE 集群自动巡检（快检 + 诊断一步到位）

    流程：
    1. 执行快速巡检
    2. 有异常 → 自动执行深度诊断 → 返回诊断结果
    3. 无异常 → 返回 HEARTBEAT_OK

    适合 cron 调用：
    - 无异常时 <30s 返回，不浪费资源
    - 有异常时自动深诊，但建议 cron 超时设 300s
    - 更好的做法：cron 只调快检，异常时由 agent spawn 诊断子任务

    Args:
        region: 华为云区域
        cluster_id: CCE 集群 ID
        ak: Access Key ID
        sk: Secret Access Key
        project_id: Project ID
        thresholds: 自定义阈值
        elb_ids: ELB ID 列表
        notify_email: 通知邮箱

    Returns:
        快检结果（无异常） 或 深诊结果（有异常）
    """
    # Step 1: 快检
    check_result = cce_quick_check(
        region=region,
        cluster_id=cluster_id,
        ak=ak,
        sk=sk,
        project_id=project_id,
        thresholds=thresholds,
        elb_ids=elb_ids,
    )

    if not check_result.get("has_anomaly"):
        # 无异常，直接返回
        check_result["auto_inspection"] = "HEARTBEAT_OK"
        check_result["message"] = (
            f"✅ 巡检正常 ({check_result['duration_seconds']}s) | "
            + " | ".join(check_result.get("normal_details", []))
        )
        return check_result

    # Step 2: 有异常，执行深度诊断
    diag_result = cce_deep_diagnosis(
        region=region,
        cluster_id=cluster_id,
        quick_check_result=check_result,
        ak=ak,
        sk=sk,
        project_id=project_id,
        notify_email=notify_email,
    )

    diag_result["auto_inspection"] = "ANOMALY_DETECTED"
    diag_result["quick_check"] = check_result
    diag_result["message"] = _format_diagnosis_summary(diag_result)

    return diag_result


# ========== 辅助函数 ==========

EVENT_ANOMALY_KEYWORDS = (
    "Warning",
    "Failed",
    "BackOff",
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "Unhealthy",
    "FailedScheduling",
    "FailedMount",
    "OOMKilled",
    "Killing",
    "NotReady",
)


def _detect_event_anomalies(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect abnormal Kubernetes events without doing root-cause analysis."""
    anomalies = []
    for event in events or []:
        event_type = event.get("type")
        reason = event.get("reason") or ""
        message = event.get("message") or ""
        text = f"{event_type} {reason} {message}"
        if event_type == "Warning" or any(keyword in text for keyword in EVENT_ANOMALY_KEYWORDS):
            involved = _get_event_involved_object(event)
            anomalies.append({
                "namespace": event.get("namespace") or involved.get("namespace"),
                "reason": reason,
                "type": event_type,
                "message": message[:240],
                "count": event.get("count", 1),
                "last_timestamp": event.get("last_timestamp"),
                "object": involved,
            })
    return anomalies


def _get_event_involved_object(event: Dict[str, Any]) -> Dict[str, Any]:
    obj = event.get("involved_object") or event.get("involvedObject") or {}
    return {
        "kind": obj.get("kind") or event.get("object_kind"),
        "name": obj.get("name") or event.get("object_name") or event.get("name"),
        "namespace": obj.get("namespace") or event.get("namespace"),
    }


def _detect_pod_topn_anomalies(topn: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    metrics = topn.get("metrics", {}) if isinstance(topn, dict) else {}
    anomalies = []
    for item in metrics.get("cpu_top_n", []) or []:
        value = item.get("cpu_usage_percent")
        if _to_float(value) is not None and float(value) > cfg["pod_cpu_avg_percent"]:
            anomalies.append({
                "scope": "pod",
                "metric": "cpu_usage_percent",
                "namespace": item.get("namespace"),
                "name": item.get("pod"),
                "value": value,
                "threshold": cfg["pod_cpu_avg_percent"],
            })
    for item in metrics.get("memory_top_n", []) or []:
        value = item.get("memory_usage_percent")
        if _to_float(value) is not None and float(value) > cfg["pod_memory_avg_percent"]:
            anomalies.append({
                "scope": "pod",
                "metric": "memory_usage_percent",
                "namespace": item.get("namespace"),
                "name": item.get("pod"),
                "value": value,
                "threshold": cfg["pod_memory_avg_percent"],
            })
    return anomalies


def _detect_node_topn_anomalies(topn: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    metrics = topn.get("metrics", {}) if isinstance(topn, dict) else {}
    checks = [
        ("cpu_top_n", "cpu_usage_percent", cfg["node_cpu_percent"]),
        ("memory_top_n", "memory_usage_percent", cfg["node_memory_percent"]),
        ("disk_top_n", "disk_usage_percent", cfg["node_disk_percent"]),
    ]
    anomalies = []
    for list_key, metric_name, threshold in checks:
        for item in metrics.get(list_key, []) or []:
            value = item.get(metric_name)
            if _to_float(value) is not None and float(value) > threshold:
                anomalies.append({
                    "scope": "node",
                    "metric": metric_name,
                    "name": item.get("node_name") or item.get("node_ip") or item.get("instance"),
                    "node_ip": item.get("node_ip"),
                    "value": value,
                    "threshold": threshold,
                })
    return anomalies


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _summarize_alarm_correlation(alarm_analysis: Dict[str, Any], quick_anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge alarm output into compact evidence groups for RCA."""
    quick_alarm_names = {
        item.get("name")
        for item in quick_anomalies or []
        if item.get("type") == "aom_alarm" and item.get("name")
    }
    groups = {}
    for key in ("alarms", "events", "alarm_events", "items"):
        for alarm in alarm_analysis.get(key, []) if isinstance(alarm_analysis, dict) else []:
            name = alarm.get("event_name") or alarm.get("name") or alarm.get("alarm_name") or "unknown"
            severity = alarm.get("event_severity") or alarm.get("severity") or "Info"
            group_key = f"{severity}:{name}"
            groups.setdefault(group_key, {
                "name": name,
                "severity": severity,
                "count": 0,
                "statuses": set(),
                "messages": [],
                "matched_quick_check": name in quick_alarm_names,
            })
            groups[group_key]["count"] += 1
            if alarm.get("status"):
                groups[group_key]["statuses"].add(str(alarm.get("status")))
            msg = alarm.get("message") or alarm.get("description")
            if msg and len(groups[group_key]["messages"]) < 3:
                groups[group_key]["messages"].append(str(msg)[:240])

    merged = []
    for group in groups.values():
        group["statuses"] = sorted(group["statuses"])
        merged.append(group)
    return {
        "merged_alarm_groups": sorted(merged, key=lambda x: (x["severity"], x["name"])),
        "quick_alarm_names": sorted(quick_alarm_names),
        "raw_summary": alarm_analysis.get("summary") if isinstance(alarm_analysis, dict) else None,
    }


def _analyze_monitoring_windows(
    pod_topn: Dict[str, Any],
    node_topn: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    windows = []
    pod_metrics = pod_topn.get("metrics", {}) if isinstance(pod_topn, dict) else {}
    node_metrics = node_topn.get("metrics", {}) if isinstance(node_topn, dict) else {}
    metric_specs = [
        ("pod", pod_metrics.get("cpu_top_n", []), "cpu_usage_percent", cfg["pod_cpu_avg_percent"], "pod"),
        ("pod", pod_metrics.get("memory_top_n", []), "memory_usage_percent", cfg["pod_memory_avg_percent"], "pod"),
        ("node", node_metrics.get("cpu_top_n", []), "cpu_usage_percent", cfg["node_cpu_percent"], "node_name"),
        ("node", node_metrics.get("memory_top_n", []), "memory_usage_percent", cfg["node_memory_percent"], "node_name"),
        ("node", node_metrics.get("disk_top_n", []), "disk_usage_percent", cfg["node_disk_percent"], "node_name"),
    ]
    for scope, items, metric_name, threshold, name_key in metric_specs:
        for item in items or []:
            abnormal_window = _find_abnormal_window(item.get("time_series", []), threshold)
            if abnormal_window:
                windows.append({
                    "scope": scope,
                    "metric": metric_name,
                    "name": item.get(name_key) or item.get("node_ip") or item.get("instance"),
                    "namespace": item.get("namespace"),
                    "threshold": threshold,
                    **abnormal_window,
                })
    return {
        "abnormal_windows": windows,
        "count": len(windows),
        "analysis_note": "Windows are derived from AOM TopN time_series and should be correlated with event/alarm timestamps by root-cause-analyzer.",
    }


def _find_abnormal_window(time_series: List[Any], threshold: float) -> Optional[Dict[str, Any]]:
    points = []
    for point in time_series or []:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            value = _to_float(point[1])
            if value is not None and value > threshold:
                points.append((point[0], value))
    if not points:
        return None
    return {
        "start": _format_ts(points[0][0]),
        "end": _format_ts(points[-1][0]),
        "peak": round(max(value for _, value in points), 2),
        "abnormal_points": len(points),
    }


def _format_ts(ts: Any) -> Any:
    try:
        ts_value = float(ts)
        if ts_value > 10_000_000_000:
            ts_value = ts_value / 1000
        return datetime.fromtimestamp(ts_value, timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")
    except (TypeError, ValueError, OSError):
        return ts


def _analyze_abnormal_events(
    events_result: Dict[str, Any],
    pods_result: Dict[str, Any],
    deployments_result: Dict[str, Any],
) -> Dict[str, Any]:
    abnormal_events = _detect_event_anomalies(events_result.get("events", []) if isinstance(events_result, dict) else [])
    grouped = {}
    for event in abnormal_events:
        obj = event.get("object", {})
        key = f"{obj.get('namespace') or event.get('namespace')}/{obj.get('kind') or 'Unknown'}/{obj.get('name') or 'unknown'}"
        grouped.setdefault(key, {
            "object": obj,
            "namespace": obj.get("namespace") or event.get("namespace"),
            "event_count": 0,
            "reasons": {},
            "latest_event_time": None,
            "messages": [],
        })
        group = grouped[key]
        group["event_count"] += event.get("count") or 1
        reason = event.get("reason") or "Unknown"
        group["reasons"][reason] = group["reasons"].get(reason, 0) + 1
        group["latest_event_time"] = event.get("last_timestamp") or group["latest_event_time"]
        if event.get("message") and len(group["messages"]) < 5:
            group["messages"].append(event["message"])

    pods_by_name = _index_by_namespace_name(pods_result.get("pods", []) if isinstance(pods_result, dict) else [])
    deployments_by_name = _index_by_namespace_name(
        deployments_result.get("deployments", []) if isinstance(deployments_result, dict) else []
    )
    for group in grouped.values():
        obj = group["object"]
        ns = obj.get("namespace")
        name = obj.get("name")
        if obj.get("kind") == "Pod":
            group["pod"] = pods_by_name.get(f"{ns}/{name}")
        if obj.get("kind") in ("Deployment", "ReplicaSet"):
            group["deployment"] = deployments_by_name.get(f"{ns}/{name}")

    return {
        "abnormal_events": abnormal_events[:100],
        "groups": list(grouped.values()),
        "count": len(abnormal_events),
    }


def _index_by_namespace_name(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        f"{item.get('namespace')}/{item.get('name')}": item
        for item in items or []
        if item.get("name")
    }


def _analyze_application_evidence(
    quick_anomalies: List[Dict[str, Any]],
    event_analysis: Dict[str, Any],
    pods_result: Dict[str, Any],
    deployments_result: Dict[str, Any],
    services_result: Dict[str, Any],
    ingresses_result: Dict[str, Any],
) -> Dict[str, Any]:
    affected = {}
    for group in event_analysis.get("groups", []) if isinstance(event_analysis, dict) else []:
        obj = group.get("object", {})
        key = f"{obj.get('namespace')}/{obj.get('kind')}/{obj.get('name')}"
        affected[key] = {
            "object": obj,
            "event_reasons": group.get("reasons", {}),
            "event_count": group.get("event_count"),
            "latest_event_time": group.get("latest_event_time"),
            "pod_status": (group.get("pod") or {}).get("status"),
            "pod_state_reason": (group.get("pod") or {}).get("state_reason"),
            "deployment_replicas": _deployment_replica_summary(group.get("deployment")),
        }

    return {
        "affected_objects": list(affected.values()),
        "pod_state_summary": _summarize_pod_states(pods_result.get("pods", []) if isinstance(pods_result, dict) else []),
        "deployment_replica_mismatches": _find_deployment_mismatches(
            deployments_result.get("deployments", []) if isinstance(deployments_result, dict) else []
        ),
        "service_count": len(services_result.get("services", []) if isinstance(services_result, dict) else []),
        "ingress_count": len(ingresses_result.get("ingresses", []) if isinstance(ingresses_result, dict) else []),
        "quick_symptom_types": sorted({item.get("type") for item in quick_anomalies or [] if item.get("type")}),
        "note": "This is application fault evidence for root-cause-analyzer, not the final root cause.",
    }


def _deployment_replica_summary(deployment: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not deployment:
        return None
    return {
        "name": deployment.get("name"),
        "namespace": deployment.get("namespace"),
        "ready": deployment.get("ready_replicas", 0),
        "desired": deployment.get("replicas", 0),
        "available": deployment.get("available_replicas", 0),
    }


def _summarize_pod_states(pods: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {}
    for pod in pods or []:
        status = pod.get("state_reason") or pod.get("status") or "Unknown"
        summary[status] = summary.get(status, 0) + 1
    return summary


def _find_deployment_mismatches(deployments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mismatches = []
    for deployment in deployments or []:
        desired = deployment.get("replicas", 0)
        ready = deployment.get("ready_replicas", 0)
        if desired and ready != desired:
            mismatches.append({
                "namespace": deployment.get("namespace"),
                "name": deployment.get("name"),
                "ready": ready,
                "desired": desired,
                "available": deployment.get("available_replicas", 0),
            })
    return mismatches


def _analyze_peripheral_resources(
    region: str,
    cluster_id: str,
    ak: str,
    sk: str,
    project_id: str,
    services: Dict[str, Any],
    ingresses: Dict[str, Any],
    events: Dict[str, Any],
    quick_anomalies: List[Dict[str, Any]],
    hours: int = 1,
) -> Dict[str, Any]:
    elb_ids = _discover_elb_ids(services, ingresses)
    should_check_network = bool(elb_ids) or _has_network_signal(events, quick_anomalies)
    if not should_check_network:
        return {
            "checked": False,
            "reason": "No LoadBalancer/Ingress ELB id or network-related event/alarm signal found.",
            "associated_elb_ids": [],
        }

    resource_status = {
        "checked": True,
        "associated_elb_ids": sorted(elb_ids),
        "elb": {},
        "eip": {},
        "nat": {},
        "data_gaps": [],
    }
    for elb_id in sorted(elb_ids):
        try:
            resource_status["elb"][elb_id] = {
                "backend_status": get_elb_backend_status(region, elb_id, ak, sk, project_id),
                "metrics": get_elb_metrics(
                    region,
                    elb_id,
                    hours=hours,
                    period=300,
                    ak=ak,
                    sk=sk,
                    project_id=project_id,
                ),
            }
        except Exception as exc:
            resource_status["data_gaps"].append({"source": f"elb:{elb_id}", "reason": str(exc)})

    try:
        eips = list_eip_addresses(region, ak, sk, project_id)
        resource_status["eip"]["list"] = eips
        for eip_id in _select_eip_ids(eips, services):
            try:
                resource_status["eip"].setdefault("metrics", {})[eip_id] = get_eip_metrics(
                    region, eip_id, hours=hours, period=300, ak=ak, sk=sk, project_id=project_id
                )
            except Exception as exc:
                resource_status["data_gaps"].append({"source": f"eip:{eip_id}", "reason": str(exc)})
    except Exception as exc:
        resource_status["data_gaps"].append({"source": "eip:list", "reason": str(exc)})

    try:
        nat_gateways = list_nat_gateways(region, ak, sk, project_id)
        resource_status["nat"]["list"] = nat_gateways
        for nat_id in _select_nat_gateway_ids(nat_gateways):
            try:
                resource_status["nat"].setdefault("metrics", {})[nat_id] = get_nat_gateway_metrics(
                    region, nat_id, hours=hours, period=300, ak=ak, sk=sk, project_id=project_id
                )
            except Exception as exc:
                resource_status["data_gaps"].append({"source": f"nat:{nat_id}", "reason": str(exc)})
    except Exception as exc:
        resource_status["data_gaps"].append({"source": "nat:list", "reason": str(exc)})
    return resource_status


def _discover_elb_ids(services: Dict[str, Any], ingresses: Dict[str, Any]) -> set:
    ids = set()
    service_items = services.get("services", []) if isinstance(services, dict) else []
    ingress_items = ingresses.get("ingresses", []) if isinstance(ingresses, dict) else []
    for svc in service_items:
        annotations = svc.get("annotations", {}) or {}
        if svc.get("type") == "LoadBalancer":
            for key in ("kubernetes.io/elb.id", "elb.id", "loadbalancer.openstack.org/id"):
                if annotations.get(key):
                    ids.add(annotations[key])
    for ingress in ingress_items:
        annotations = ingress.get("annotations", {}) or {}
        for key in ("kubernetes.io/elb.id", "elb.id", "loadbalancer.openstack.org/id"):
            if annotations.get(key):
                ids.add(annotations[key])
    return ids


def _has_network_signal(events: Dict[str, Any], quick_anomalies: List[Dict[str, Any]]) -> bool:
    keywords = ("ELB", "EIP", "NAT", "LoadBalancer", "Ingress", "Service", "network", "Network", "连接", "访问")
    text = json.dumps({"events": events, "quick": quick_anomalies}, ensure_ascii=False)
    return any(keyword in text for keyword in keywords)


def _select_eip_ids(eips: Dict[str, Any], services: Dict[str, Any]) -> List[str]:
    service_ips = set()
    service_items = services.get("services", []) if isinstance(services, dict) else []
    for svc in service_items:
        for value in (svc.get("load_balancer_ip"), svc.get("external_ip"), svc.get("external_ips")):
            if isinstance(value, list):
                service_ips.update(str(item) for item in value if item)
            elif value:
                service_ips.add(str(value))

    ids = []
    eip_items = (eips.get("eips", []) or eips.get("publicips", []) or []) if isinstance(eips, dict) else []
    for eip in eip_items:
        eip_addr = eip.get("public_ip_address") or eip.get("publicip_address") or eip.get("ip_address")
        eip_id = eip.get("id") or eip.get("publicip_id")
        if eip_id and (not service_ips or str(eip_addr) in service_ips):
            ids.append(eip_id)
    return ids[:10]


def _select_nat_gateway_ids(nat_gateways: Dict[str, Any]) -> List[str]:
    gateways = nat_gateways.get("nat_gateways", []) if isinstance(nat_gateways, dict) else []
    return [item.get("id") for item in gateways if item.get("id")][:10]


def _derive_handoff_time_window(monitoring_windows: Dict[str, Any]) -> str:
    windows = monitoring_windows.get("abnormal_windows", []) if isinstance(monitoring_windows, dict) else []
    starts = [item.get("start") for item in windows if item.get("start")]
    ends = [item.get("end") for item in windows if item.get("end")]
    if starts and ends:
        return f"{min(starts)} ~ {max(ends)}"
    return "Use quick check, event, alarm, and diagnosis timestamps"

def _get_recent_values(time_series: list, recent_minutes: int) -> List[float]:
    """从 time_series 中提取最近 N 分钟的值"""
    if not time_series:
        return []

    now = time.time()
    cutoff = now - recent_minutes * 60
    values = []

    for point in time_series:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            ts = point[0]
            val = point[1]
            if isinstance(ts, (int, float)) and ts >= cutoff:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
    return values


def _collect_diagnosis_data_gaps(diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect failed or missing diagnosis evidence for root-cause handoff."""
    gaps = []
    for key, value in diagnosis.items():
        if isinstance(value, dict) and value.get("error"):
            gaps.append({"source": key, "reason": value.get("error")})
        elif not value:
            gaps.append({"source": key, "reason": "missing_or_empty"})
    return gaps


def _format_diagnosis_summary(diag: Dict) -> str:
    """格式化诊断结果为人类可读摘要"""
    qc = diag.get("quick_check", {})
    anomalies = qc.get("anomaly_details", [])
    root_cause_handoff = diag.get("root_cause_handoff", {})
    remediation_handoff = diag.get("remediation_handoff", {})

    lines = ["🚨 CCE集群异常 - 深度诊断证据采集完成", ""]

    # 异常摘要
    lines.append("📊 异常摘要")
    for a in anomalies[:6]:
        msg = a.get("message", a.get("type", ""))
        lines.append(f"  - {msg}")

    lines.append("")
    lines.append("🔍 根因诊断：待交给 huawei-cloud-cce-root-cause-analyzer")
    if root_cause_handoff.get("data_gaps"):
        lines.append(f"  数据缺口: {len(root_cause_handoff['data_gaps'])} 项")

    lines.append("")
    lines.append("📋 恢复建议：待 root-cause-analyzer 输出根因后交给 huawei-cloud-cce-auto-remediation-runner")
    if remediation_handoff.get("mode"):
        lines.append(f"  模式: {remediation_handoff['mode']}")

    # 耗时
    lines.append(f"\n⏱️ 快检 {qc.get('duration_seconds', 0)}s + 诊断 {diag.get('duration_seconds', 0)}s")

    return "\n".join(lines)
