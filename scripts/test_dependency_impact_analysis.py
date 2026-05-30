#!/usr/bin/env python3
"""Tests for dependency impact analysis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import dependency_impact_analysis as analysis  # noqa: E402


class DependencyImpactAnalysisTests(unittest.TestCase):
    @mock.patch.object(analysis.cce, "get_kubernetes_nodes")
    @mock.patch.object(analysis.cce, "get_kubernetes_ingresses")
    @mock.patch.object(analysis.cce, "get_kubernetes_services")
    @mock.patch.object(analysis.cce, "get_kubernetes_pods")
    def test_unready_target_with_service_and_ingress_is_high_impact(
        self,
        pods_mock,
        services_mock,
        ingresses_mock,
        nodes_mock,
    ):
        pods_mock.return_value = {
            "success": True,
            "count": 1,
            "pods": [
                {
                    "namespace": "prod",
                    "name": "api-abc",
                    "status": "Running",
                    "node": "node-a",
                    "ip": "10.0.0.8",
                    "labels": {"app": "api"},
                    "conditions": [{"type": "Ready", "status": "False"}],
                    "containers": [{"name": "app", "ready": False}],
                }
            ],
        }
        services_mock.return_value = {
            "success": True,
            "count": 1,
            "services": [
                {
                    "namespace": "prod",
                    "name": "api",
                    "type": "ClusterIP",
                    "cluster_ip": "10.247.0.1",
                    "selector": {"app": "api"},
                    "ports": [{"port": 80}],
                }
            ],
        }
        ingresses_mock.return_value = {
            "success": True,
            "count": 1,
            "ingresses": [
                {
                    "namespace": "prod",
                    "name": "api-ing",
                    "rules": [{"host": "api.example.com", "paths": [{"backend": {"service_name": "api", "service_port": 80}}]}],
                    "load_balancer_ingress": [{"ip": "1.2.3.4"}],
                }
            ],
        }
        nodes_mock.return_value = {"success": True, "count": 1, "nodes": [{"name": "node-a"}]}

        result = analysis.analyze_dependency_impact(
            {"region": "cn-north-4", "cluster_id": "cluster-1", "namespace": "prod", "target_name": "api"}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["risk_level"], "High")
        self.assertEqual(result["target"]["services"], ["prod/api"])
        self.assertEqual(result["target"]["ingresses"], ["prod/api-ing"])
        self.assertIn("Ingress:prod/api-ing", result["propagation_paths"][0]["path"][0])
        self.assertIn("# CCE 依赖影响面分析报告", result["report_markdown"])


if __name__ == "__main__":
    unittest.main()
