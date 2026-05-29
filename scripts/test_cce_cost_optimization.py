#!/usr/bin/env python3
"""Tests for the CCE cost optimization advisor action."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import cce_cost_optimization  # noqa: E402


def metric(node_ip: str | None = None, namespace: str | None = None, pod: str | None = None, values=None):
    payload = {"time_series": values or [[1, "10"], [2, "20"], [3, "30"]]}
    if node_ip:
        payload["node_ip"] = node_ip
        payload["node_name"] = node_ip
    if namespace:
        payload["namespace"] = namespace
    if pod:
        payload["pod"] = pod
    return payload


class CceCostOptimizationTests(unittest.TestCase):
    def test_analyze_generates_summary_report_and_hpa_preview(self):
        nodepools = {"success": True, "count": 1, "nodepools": [{"name": "pool-a", "scale_groups": []}]}
        nodes = {
            "success": True,
            "count": 2,
            "nodes": [
                {"name": "node-a", "internal_ip": "10.0.0.1", "ready": "True"},
                {"name": "node-b", "internal_ip": "10.0.0.2", "ready": "True"},
            ],
        }
        pods = {
            "success": True,
            "count": 2,
            "pods": [
                {"namespace": "default", "name": "demo-abc", "status": "Running"},
                {"namespace": "kube-system", "name": "coredns", "status": "Running"},
            ],
        }
        deployments = {"success": True, "count": 1, "deployments": [{"namespace": "default", "name": "demo"}]}
        hpas = {"success": True, "count": 0, "hpas": []}
        node_metrics = {
            "success": True,
            "metrics": {
                "cpu_top_n": [metric("10.0.0.1"), metric("10.0.0.2")],
                "memory_top_n": [metric("10.0.0.1"), metric("10.0.0.2")],
                "disk_top_n": [metric("10.0.0.1", values=[[1, "50"], [2, "55"]])],
            },
        }
        request_metrics = {
            "success": True,
            "metrics": {
                "cpu_top_n": [metric(namespace="default", pod="demo-abc", values=[[1, "10"], [2, "20"]])],
                "memory_top_n": [metric(namespace="default", pod="demo-abc", values=[[1, "20"], [2, "30"]])],
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir, \
            mock.patch.object(cce_cost_optimization.cce, "list_cce_node_pools", return_value=nodepools), \
            mock.patch.object(cce_cost_optimization.cce, "get_kubernetes_nodes", return_value=nodes), \
            mock.patch.object(cce_cost_optimization.cce, "get_kubernetes_pods", return_value=pods), \
            mock.patch.object(cce_cost_optimization.cce, "get_kubernetes_deployments", return_value=deployments), \
            mock.patch.object(cce_cost_optimization.cce_hpa, "list_cce_hpas", return_value=hpas), \
            mock.patch.object(cce_cost_optimization.cce_hpa, "generate_cce_hpa_manifest", return_value={"success": True, "manifest_yaml": "kind: HorizontalPodAutoscaler\n"}), \
            mock.patch.object(cce_cost_optimization.cce_metrics, "get_cce_node_metrics_topN", return_value=node_metrics), \
            mock.patch.object(cce_cost_optimization.cce_metrics, "get_cce_pod_metrics_topN", return_value=request_metrics):
            result = cce_cost_optimization.analyze_cce_cost_optimization(
                region="cn-north-4",
                cluster_id="cluster-1",
                output_dir=temp_dir,
            )

            self.assertTrue(result["success"])
            self.assertTrue(result["cluster_utilization"]["24h"]["overall_low_utilization"])
            self.assertEqual(result["request_analysis"]["business_pod_count"], 1)
            self.assertGreaterEqual(len(result["request_analysis"]["oversized_requests"]), 1)
            self.assertEqual(result["elasticity"]["hpa"]["status"], "not_configured")
            self.assertIn("HorizontalPodAutoscaler", result["elasticity"]["hpa"]["preview"]["manifest_yaml"])
            self.assertTrue(Path(result["files"]["summary"]).exists())
            self.assertTrue(Path(result["files"]["report"]).exists())


if __name__ == "__main__":
    unittest.main()
