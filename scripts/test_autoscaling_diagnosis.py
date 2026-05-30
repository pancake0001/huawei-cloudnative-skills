#!/usr/bin/env python3
"""Tests for CCE autoscaling diagnosis routing and root causes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import autoscaling_diagnosis as diagnosis  # noqa: E402


def base_raw(**overrides):
    raw = {
        "hpas": {"success": True, "count": 0, "hpas": []},
        "addons": {"success": True, "count": 0, "addons": []},
        "nodepools": {"success": True, "count": 0, "nodepools": []},
        "pods": {"success": True, "count": 0, "pods": []},
        "events": {"success": True, "count": 0, "events": []},
        "deployments": {"success": True, "count": 0, "deployments": []},
        "statefulsets": {"success": True, "count": 0, "statefulsets": []},
    }
    raw.update(overrides)
    return raw


def hpa(name="api-hpa", desired=2, current=2, max_replicas=5, current_cpu=90, target_cpu=60):
    return {
        "name": name,
        "namespace": "default",
        "scale_target_ref": {"kind": "Deployment", "name": "api", "api_version": "apps/v1"},
        "min_replicas": 1,
        "max_replicas": max_replicas,
        "current_replicas": current,
        "desired_replicas": desired,
        "metrics": [
            {
                "type": "Resource",
                "resource": {
                    "name": "cpu",
                    "target": {"type": "Utilization", "average_utilization": target_cpu},
                },
            }
        ],
        "current_metrics": [
            {
                "type": "Resource",
                "resource": {
                    "name": "cpu",
                    "current": {"average_utilization": current_cpu},
                },
            }
        ],
        "conditions": [{"type": "ScalingActive", "status": "True", "reason": "ValidMetricFound"}],
    }


def pod(name, phase="Running", requests=None):
    return {
        "name": name,
        "namespace": "default",
        "phase": phase,
        "status": phase,
        "owner_references": [{"kind": "ReplicaSet", "name": "api-6fbb7f"}],
        "annotation_keys": [],
        "containers": [
            {
                "name": "app",
                "resources": {"requests": requests or {}, "limits": {}},
            }
        ],
    }


class AutoscalingDiagnosisTests(unittest.TestCase):
    def test_hpa_missing_request_blocks_workload_scaling(self):
        raw = base_raw(
            hpas={"success": True, "count": 1, "hpas": [hpa()]},
            addons={"success": True, "count": 1, "addons": [{"name": "metrics-server", "version": "1.0.0"}]},
            pods={"success": True, "count": 1, "pods": [pod("api-6fbb7f-aaa", requests={})]},
            deployments={
                "success": True,
                "count": 1,
                "deployments": [{"name": "api", "namespace": "default", "desired_replicas": 2, "ready_replicas": 2}],
            },
        )

        result = diagnosis.assess_autoscaling_context(
            raw,
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么我的pod不能自动扩容",
            namespace="default",
            workload_name="api",
            workload_type="Deployment",
        )

        self.assertEqual(result["route"], "A")
        self.assertIn("HPA_CONTAINER_REQUEST_MISSING", {issue["code"] for issue in result["issues"]})
        self.assertIn("# CCE 弹性伸缩自动化诊断报告", result["report_markdown"])

    def test_unknown_intent_cascades_from_hpa_to_ca_when_pending_appears(self):
        raw = base_raw(
            hpas={"success": True, "count": 1, "hpas": [hpa(desired=5, current=3)]},
            addons={
                "success": True,
                "count": 2,
                "addons": [
                    {"name": "cce-cluster-autoscaler", "template_name": "autoscaler", "version": "1.13.8"},
                    {"name": "metrics-server", "version": "1.0.0"},
                ],
            },
            nodepools={
                "success": True,
                "count": 1,
                "nodepools": [
                    {
                        "name": "pool-a",
                        "scale_groups": [
                            {
                                "name": "default",
                                "initial_node_count": 2,
                                "autoscaling": {"enable": True, "min_node_count": 1, "max_node_count": 5},
                            }
                        ],
                    }
                ],
            },
            pods={"success": True, "count": 2, "pods": [pod("api-6fbb7f-aaa", "Running", {"cpu": "100m"}), pod("api-6fbb7f-bbb", "Pending", {"cpu": "100m"})]},
            events={
                "success": True,
                "count": 1,
                "events": [
                    {
                        "namespace": "default",
                        "reason": "FailedScheduling",
                        "message": "0/2 nodes are available: 2 Insufficient cpu.",
                        "involved_object": {"kind": "Pod", "namespace": "default", "name": "api-6fbb7f-bbb"},
                    }
                ],
            },
            deployments={
                "success": True,
                "count": 1,
                "deployments": [{"name": "api", "namespace": "default", "desired_replicas": 5, "ready_replicas": 3}],
            },
        )

        result = diagnosis.assess_autoscaling_context(
            raw,
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么不自动扩容了",
            namespace="default",
            workload_name="api",
            workload_type="Deployment",
        )

        self.assertEqual(result["route"], "C")
        self.assertIn("PENDING_INSUFFICIENT_RESOURCES", {issue["code"] for issue in result["issues"]})
        self.assertTrue(any("继续进入路径 B" in step for step in result["process"]))

    def test_node_autoscaling_disabled_is_critical(self):
        raw = base_raw(
            addons={"success": True, "count": 1, "addons": [{"name": "cluster-autoscaler", "version": "1.13.8"}]},
            nodepools={"success": True, "count": 1, "nodepools": [{"name": "pool-a", "scale_groups": [{"name": "default"}]}]},
            pods={"success": True, "count": 1, "pods": [pod("api-6fbb7f-bbb", "Pending", {"cpu": "100m"})]},
            events={
                "success": True,
                "count": 1,
                "events": [
                    {
                        "namespace": "default",
                        "reason": "FailedScheduling",
                        "message": "0/1 nodes are available: 1 Insufficient memory.",
                        "involved_object": {"kind": "Pod", "namespace": "default", "name": "api-6fbb7f-bbb"},
                    }
                ],
            },
        )

        result = diagnosis.assess_autoscaling_context(
            raw,
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么我的node不能自动扩容了",
        )

        self.assertEqual(result["route"], "B")
        self.assertIn("NODEPOOL_AUTOSCALING_DISABLED", {issue["code"] for issue in result["issues"]})

    def test_no_hpa_or_ca_blocks_at_gateway(self):
        result = diagnosis.assess_autoscaling_context(
            base_raw(),
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么不自动扩容了",
        )

        self.assertEqual(result["route"], "BLOCKED")
        self.assertIn("AUTOSCALING_CAPABILITY_ABSENT", {issue["code"] for issue in result["issues"]})

    def test_ca_log_analysis_detects_quota_and_subnet_errors(self):
        """CA Pod 日志中应识别出配额超限和子网 IP 耗竭信号。"""
        raw = base_raw(
            addons={
                "success": True,
                "count": 1,
                "addons": [{"name": "cluster-autoscaler", "template_name": "autoscaler", "version": "1.13.8"}],
            },
            nodepools={
                "success": True,
                "count": 1,
                "nodepools": [{
                    "name": "pool-a",
                    "scale_groups": [{
                        "name": "default",
                        "initial_node_count": 1,
                        "autoscaling": {"enable": True, "min_node_count": 1, "max_node_count": 10},
                    }],
                }],
            },
            pods={"success": True, "count": 1, "pods": [pod("api-6fbb7f-bbb", "Pending", {"cpu": "100m"})]},
            events={
                "success": True,
                "count": 1,
                "events": [{
                    "namespace": "default",
                    "reason": "FailedScheduling",
                    "message": "0/1 nodes are available: 1 Insufficient cpu.",
                    "involved_object": {"kind": "Pod", "namespace": "default", "name": "api-6fbb7f-bbb"},
                }],
            },
            ca_pod_logs={
                "success": True,
                "ca_pod_found": True,
                "ca_pod_name": "cce-cluster-autoscaler-abc123",
                "ca_pod_namespace": "kube-system",
                "ca_container": "autoscaler",
                "tail_lines": 200,
                "log_lines": (
                    "I0530 10:00:00.000000       1 static_autoscaler.go:210] pod default/api-6fbb7f-bbb is unschedulable\n"
                    "I0530 10:00:01.000000       1 scale_up.go:354] No expansion options\n"
                    "W0530 10:00:02.000000       1 static_autoscaler.go:480] Failed to create node: Quota exceeded for ECS instances\n"
                    "E0530 10:00:03.000000       1 scale_up.go:420] subnet ip exhausted: no available ip in subnet-xxx\n"
                    "I0530 10:00:04.000000       1 static_autoscaler.go:300] skipping node group pool-a: max node group size reached\n"
                ),
            },
        )

        result = diagnosis.assess_autoscaling_context(
            raw,
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么不自动扩容node了",
        )

        self.assertEqual(result["route"], "B")
        issue_codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("CA_LOG_QUOTA_EXCEEDED", issue_codes)
        self.assertIn("CA_LOG_SUBNET_IP_EXHAUSTED", issue_codes)
        self.assertIn("CA_LOG_NO_EXPANSION_OPTIONS", issue_codes)
        self.assertIn("CA_LOG_MAX_NODE_GROUP_SIZE", issue_codes)

    def test_ca_log_analysis_scale_down_pdb_protection(self):
        """CA Pod 日志中应识别出缩容时的 safe-to-evict/PDB 保护信号。"""
        raw = base_raw(
            addons={
                "success": True,
                "count": 1,
                "addons": [{"name": "cluster-autoscaler", "template_name": "autoscaler", "version": "1.13.8"}],
            },
            nodepools={
                "success": True,
                "count": 1,
                "nodepools": [{
                    "name": "pool-a",
                    "scale_groups": [{
                        "name": "default",
                        "initial_node_count": 3,
                        "autoscaling": {"enable": True, "min_node_count": 1, "max_node_count": 10},
                    }],
                }],
            },
            pods={"success": True, "count": 1, "pods": [pod("api-6fbb7f-aaa", "Running", {"cpu": "100m"})]},
            events={"success": True, "count": 0, "events": []},
            ca_pod_logs={
                "success": True,
                "ca_pod_found": True,
                "ca_pod_name": "cce-cluster-autoscaler-abc123",
                "ca_pod_namespace": "kube-system",
                "ca_container": "autoscaler",
                "tail_lines": 200,
                "log_lines": (
                    "I0530 10:00:00.000000       1 scale_down.go:500] node node-1 is not suitable for removal: "
                    "pod default/api-6fbb7f-aaa is not safe to evict: annotation cluster-autoscaler.kubernetes.io/safe-to-evict=false\n"
                    "I0530 10:00:01.000000       1 scale_down.go:600] Scale down: no candidates for deletion\n"
                ),
            },
        )

        result = diagnosis.assess_autoscaling_context(
            raw,
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么node不能缩容",
            scale_direction="scale_down",
        )

        issue_codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("CA_LOG_SAFE_TO_EVICT_BLOCK", issue_codes)
        self.assertIn("CA_LOG_NO_SCALE_DOWN_CANDIDATES", issue_codes)

    def test_ca_addon_abnormal_status_is_critical(self):
        """CA 插件状态为 abnormal/failed 时应标记为 critical。"""
        raw = base_raw(
            hpas={"success": True, "count": 0, "hpas": []},
            addons={
                "success": True,
                "count": 1,
                "addons": [{"name": "autoscaler", "template_name": "cluster-autoscaler", "version": "1.34.35", "status": "abnormal"}],
            },
            nodepools={
                "success": True,
                "count": 1,
                "nodepools": [{
                    "name": "pool-a",
                    "scale_groups": [{
                        "name": "default",
                        "initial_node_count": 1,
                        "autoscaling": {"enable": True, "min_node_count": 1, "max_node_count": 10},
                    }],
                }],
            },
            pods={"success": True, "count": 1, "pods": [pod("api-6fbb7f-bbb", "Pending", {"cpu": "100m"})]},
            events={
                "success": True,
                "count": 1,
                "events": [{
                    "namespace": "default",
                    "reason": "FailedScheduling",
                    "message": "0/1 nodes are available: 1 Insufficient cpu.",
                    "involved_object": {"kind": "Pod", "namespace": "default", "name": "api-6fbb7f-bbb"},
                }],
            },
        )

        result = diagnosis.assess_autoscaling_context(
            raw,
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么node扩不出来",
        )

        self.assertEqual(result["route"], "B")
        issue_codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("CA_ADDON_STATUS_ABNORMAL", issue_codes)

    def test_ca_pod_crash_loop_backoff_is_critical(self):
        """CA Pod CrashLoopBackOff 时应标记为 critical 并包含 previous 日志。"""
        raw = base_raw(
            addons={
                "success": True,
                "count": 1,
                "addons": [{"name": "autoscaler", "template_name": "cluster-autoscaler", "version": "1.34.35", "status": "running"}],
            },
            nodepools={
                "success": True,
                "count": 1,
                "nodepools": [{
                    "name": "pool-a",
                    "scale_groups": [{
                        "name": "default",
                        "initial_node_count": 1,
                        "autoscaling": {"enable": True, "min_node_count": 1, "max_node_count": 10},
                    }],
                }],
            },
            pods={"success": True, "count": 1, "pods": [pod("api-6fbb7f-bbb", "Pending", {"cpu": "100m"})]},
            events={
                "success": True,
                "count": 1,
                "events": [{
                    "namespace": "default",
                    "reason": "FailedScheduling",
                    "message": "0/1 nodes are available: 1 Insufficient cpu.",
                    "involved_object": {"kind": "Pod", "namespace": "default", "name": "api-6fbb7f-bbb"},
                }],
            },
            ca_pod_logs={
                "success": True,
                "ca_pod_found": True,
                "ca_pod_name": "cluster-autoscaler-abc123",
                "ca_pod_namespace": "kube-system",
                "ca_container": "cluster-autoscaler",
                "ca_pod_phase": "Running",
                "ca_pod_unhealthy": [
                    {"container": "cluster-autoscaler", "reason": "CrashLoopBackOff",
                     "message": "back-off 2m40s restarting failed container"},
                ],
                "log_lines": "I0530 10:00:00.000000 some log output from previous",
                "log_source": "previous",
                "tail_lines": 200,
            },
        )

        result = diagnosis.assess_autoscaling_context(
            raw,
            region="cn-north-4",
            cluster_id="cluster-1",
            question="为什么node弹不出来",
        )

        issue_codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("CA_POD_UNHEALTHY", issue_codes)


if __name__ == "__main__":
    unittest.main()
