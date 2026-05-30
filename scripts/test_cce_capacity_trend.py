#!/usr/bin/env python3
"""Tests for the CCE capacity trend forecaster."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import cce_capacity_trend  # noqa: E402


def metric(node_ip: str, values):
    return {
        "node_ip": node_ip,
        "node_name": node_ip,
        "time_series": values,
    }


class CceCapacityTrendTests(unittest.TestCase):
    def test_analyze_generates_report_charts_history_and_hpa_preview(self):
        nodes = {
            "success": True,
            "count": 3,
            "nodes": [
                {"name": "node-a", "internal_ip": "10.0.0.1", "ready": "True"},
                {"name": "node-b", "internal_ip": "10.0.0.2", "ready": "True"},
                {"name": "node-c", "internal_ip": "10.0.0.3", "ready": "True"},
            ],
        }
        nodepools = {
            "success": True,
            "nodepools": [
                {
                    "name": "pool-a",
                    "scale_groups": [
                        {
                            "name": "default",
                            "autoscaling": {
                                "enable": True,
                                "min_node_count": 1,
                                "max_node_count": 6,
                                "scale_down_cooldown_time": 10,
                            },
                        }
                    ],
                }
            ],
        }
        deployments = {
            "success": True,
            "deployments": [
                {"namespace": "default", "name": "demo", "desired_replicas": 2, "replicas": 2},
                {"namespace": "kube-system", "name": "coredns", "desired_replicas": 2},
            ],
        }
        hpas = {"success": True, "count": 0, "hpas": []}
        node_metrics = {
            "success": True,
            "metrics": {
                "cpu_top_n": [
                    metric("10.0.0.1", [[1, "12"], [2, "14"], [3, "16"], [4, "18"]]),
                    metric("10.0.0.2", [[1, "10"], [2, "11"], [3, "12"], [4, "13"]]),
                ],
                "memory_top_n": [
                    metric("10.0.0.1", [[1, "30"], [2, "32"], [3, "34"], [4, "36"]]),
                    metric("10.0.0.2", [[1, "25"], [2, "26"], [3, "27"], [4, "28"]]),
                ],
                "disk_top_n": [
                    metric("10.0.0.1", [[1, "40"], [2, "40"], [3, "41"], [4, "41"]]),
                ],
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir, \
            mock.patch.object(cce_capacity_trend.cce, "list_cce_clusters", return_value={"success": True, "clusters": [{"id": "cluster-1", "name": "demo-cluster"}]}), \
            mock.patch.object(cce_capacity_trend.cce, "get_kubernetes_nodes", return_value=nodes), \
            mock.patch.object(cce_capacity_trend.cce, "list_cce_node_pools", return_value=nodepools), \
            mock.patch.object(cce_capacity_trend.cce, "get_kubernetes_deployments", return_value=deployments), \
            mock.patch.object(cce_capacity_trend.cce_hpa, "list_cce_hpas", return_value=hpas), \
            mock.patch.object(cce_capacity_trend.cce_hpa, "generate_cce_hpa_manifest", return_value={"success": True, "hpa_name": "demo-hpa", "namespace": "default", "workload_name": "demo", "manifest_yaml": "kind: HorizontalPodAutoscaler\n"}), \
            mock.patch.object(cce_capacity_trend.cce_metrics, "get_cce_node_metrics_topN", return_value=node_metrics), \
            mock.patch.object(cce_capacity_trend.cce_diagnosis, "get_aom_instance", return_value={"success": True, "aom_instance_id": "aom-1"}):
            result = cce_capacity_trend.analyze_cce_capacity_trend(
                region="cn-north-4",
                cluster_id="cluster-1",
                hours=24,
                output_dir=temp_dir,
                include_raw=True,
                action_note="baseline before tuning",
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["cluster_name"], "demo-cluster")
            self.assertEqual(result["elasticity"]["hpa"]["status"], "not_configured")
            self.assertEqual(result["elasticity"]["hpa"]["coverage_percent"], 0)
            self.assertGreater(len(result["capacity_series"]), 0)
            self.assertEqual(result["simulation"]["status"], "ok")
            self.assertGreaterEqual(result["simulation"]["estimated_reducible_nodes"], 1)
            recommendation_ids = {item["id"] for item in result["recommendations"]}
            self.assertIn("increase-hpa-coverage", recommendation_ids)
            self.assertTrue(Path(result["files"]["summary"]).exists())
            self.assertTrue(Path(result["files"]["report"]).exists())
            self.assertTrue(Path(result["files"]["report_html"]).exists())
            self.assertTrue(Path(result["files"]["trend_chart"]).exists())
            self.assertTrue(Path(result["files"]["simulation_chart"]).exists())
            self.assertTrue(Path(result["files"]["history_record"]).exists())
            self.assertTrue(Path(result["files"]["raw_node_metrics"]).exists())
            html_text = Path(result["files"]["report_html"]).read_text(encoding="utf-8")
            self.assertIn("CCE Capacity Trend Forecast Report", html_text)
            self.assertIn("<svg", html_text)

    def test_rejects_missing_cluster_id(self):
        result = cce_capacity_trend.analyze_cce_capacity_trend(region="cn-north-4", cluster_id="")
        self.assertFalse(result["success"])
        self.assertIn("cluster_id", result["error"])


if __name__ == "__main__":
    unittest.main()
