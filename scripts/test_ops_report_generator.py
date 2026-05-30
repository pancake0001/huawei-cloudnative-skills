#!/usr/bin/env python3
"""Unit tests for ops report generator action."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import ops_report_generator  # noqa: E402


class OpsReportGeneratorTests(unittest.TestCase):
    def test_generate_ops_report_requires_scope(self):
        result = ops_report_generator.generate_ops_report(region="", cluster_id="c1")
        self.assertFalse(result["success"])
        self.assertIn("region", result["error"])

        result = ops_report_generator.generate_ops_report(region="cn-north-4", cluster_id="")
        self.assertFalse(result["success"])
        self.assertIn("cluster_id", result["error"])

    def test_generate_ops_report_rejects_invalid_type(self):
        result = ops_report_generator.generate_ops_report(
            region="cn-north-4",
            cluster_id="c1",
            report_type="invalid-type",
        )
        self.assertFalse(result["success"])
        self.assertIn("invalid report_type", result["error"])

    def test_generate_ops_report_outputs_md_html_and_embeds_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            trend_svg = tmp_path / "trend.svg"
            sim_svg = tmp_path / "sim.svg"
            trend_svg.write_text("<svg><text>trend</text></svg>", encoding="utf-8")
            sim_svg.write_text("<svg><text>sim</text></svg>", encoding="utf-8")

            daily_result = {
                "success": True,
                "has_anomaly": False,
                "anomaly_details": [],
                "normal_details": ["ok"],
                "message": "healthy",
            }
            capacity_result = {
                "success": True,
                "capacity_stats": {
                    "cpu": {"avg_percent": 31.1, "p95_percent": 52.2, "trend": "flat"},
                    "memory": {"avg_percent": 48.5, "p95_percent": 67.3, "trend": "rising"},
                },
                "simulation": {"status": "ok", "estimated_reducible_nodes": 1},
                "elasticity": {
                    "node_autoscaler": {"enabled": True},
                    "hpa": {"coverage_percent": 50.0},
                },
                "recommendations": [{"priority": "medium", "suggestion": "Tune HPA target."}],
                "files": {"trend_chart": str(trend_svg), "simulation_chart": str(sim_svg)},
                "data_gaps": [],
            }
            availability_result = {
                "success": True,
                "summary": {"risk_level": "medium", "issue_count": 3, "critical": 0, "high": 1, "medium": 2, "low": 0},
                "recommendations": ["Balance workload replicas across AZs."],
                "data_gaps": [],
                "files": {},
            }
            cost_result = {
                "success": True,
                "low_utilization": {"cluster_average_below_threshold": {"24h": False}, "nodes_clearly_below_average": [{"node": "n1"}]},
                "request_analysis": {"oversized_requests": [{"pod": "p1"}]},
                "elasticity": {"hpa": {"status": "configured"}, "node_autoscaler": {"status": "not_configured"}},
                "recommendations": ["Reduce oversized requests for low-utilization workloads."],
                "data_gaps": [],
                "files": {},
            }

            with mock.patch(
                "huawei_cloud.ops_report_generator.cce_auto_inspection.cce_auto_inspection",
                return_value=daily_result,
            ), mock.patch(
                "huawei_cloud.ops_report_generator.cce_capacity_trend.analyze_cce_capacity_trend",
                return_value=capacity_result,
            ), mock.patch(
                "huawei_cloud.ops_report_generator.cce_availability_risk.scan_cce_availability_risk",
                return_value=availability_result,
            ), mock.patch(
                "huawei_cloud.ops_report_generator.cce_cost_optimization.analyze_cce_cost_optimization",
                return_value=cost_result,
            ):
                result = ops_report_generator.generate_ops_report(
                    region="cn-north-4",
                    cluster_id="c1",
                    report_type="weekly",
                    output_dir=str(tmp_path / "report"),
                    include_raw=True,
                    oncall_summary="No unresolved sev1 incidents.",
                )

            self.assertTrue(result["success"])
            files = result["files"]
            self.assertTrue(Path(files["report"]).exists())
            self.assertTrue(Path(files["report_html"]).exists())
            self.assertTrue(Path(files["summary"]).exists())
            self.assertTrue(Path(files["raw"]).exists())

            html_text = Path(files["report_html"]).read_text(encoding="utf-8")
            self.assertIn("<svg><text>trend</text></svg>", html_text)
            self.assertIn("<svg><text>sim</text></svg>", html_text)
            self.assertIn("<table class=\"report-table\">", html_text)
            self.assertIn("Recommendations", html_text)
            self.assertIn("Data Gaps", html_text)

            md_text = Path(files["report"]).read_text(encoding="utf-8")
            self.assertIn("| # | Source | Risk Level | Recommendation |", md_text)
            self.assertIn("| # | Source | Risk Level | Gap Detail |", md_text)

            summary = json.loads(Path(files["summary"]).read_text(encoding="utf-8"))
            self.assertEqual(summary["report"]["type"], "weekly")
            self.assertEqual(summary["summary"]["oncall_copilot"]["status"], "provided")
            self.assertIn("recommendation_rows", summary)
            self.assertIn("data_gap_rows", summary)
            self.assertTrue(summary["recommendation_rows"])
            self.assertTrue(summary["data_gap_rows"])


if __name__ == "__main__":
    unittest.main()
