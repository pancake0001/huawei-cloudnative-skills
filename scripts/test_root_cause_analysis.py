#!/usr/bin/env python3
"""Tests for root cause synthesis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import root_cause_analysis as analysis  # noqa: E402


class RootCauseAnalysisTests(unittest.TestCase):
    @mock.patch.object(analysis.aom, "analyze_aom_alarms")
    @mock.patch.object(analysis.change_impact_analysis, "analyze_change_impact")
    @mock.patch.object(analysis.dependency_impact_analysis, "analyze_dependency_impact")
    @mock.patch.object(analysis.workload_rollout_diagnosis, "workload_rollout_diagnose")
    def test_rollout_command_not_found_becomes_top_root_cause(
        self,
        rollout_mock,
        dependency_mock,
        change_mock,
        alarms_mock,
    ):
        rollout_mock.return_value = {
            "success": True,
            "target": {"namespace": "yzh", "name": "test-yzh"},
            "summary": {"status": "rollout_blocked", "headline": "启动命令不存在"},
            "events": {"timeline": []},
            "top_causes": [
                {
                    "type": "ContainerCommandNotFound",
                    "title": "新版本容器启动命令或入口文件不存在",
                    "confidence": 0.94,
                    "evidence": [{"source": "pod", "message": "exec: not found"}],
                    "recommendation": ["回滚到上一稳定版本。"],
                }
            ],
        }
        dependency_mock.return_value = {
            "success": True,
            "summary": {
                "risk_level": "High",
                "risk_reason": "目标 Pod 全部不可用且存在 Service 暴露路径。",
                "pod_health": {"total": 1, "ready": 0, "unready": 1},
            },
            "propagation_paths": [{"path": ["Service:yzh/test-yzh", "Pods:yzh/test-yzh-a"]}],
        }
        change_mock.return_value = {"success": True, "top_changes": []}
        alarms_mock.return_value = {"success": True, "sudden_alarms": []}

        result = analysis.analyze_root_cause(
            {"region": "cn-north-4", "cluster_id": "cluster-1", "namespace": "yzh", "workload_name": "test-yzh"}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["top_causes"][0]["type"], "ContainerCommandNotFound")
        self.assertGreaterEqual(result["top_causes"][0]["confidence"], 0.94)
        self.assertEqual(result["top_causes"][0]["remediation_hint"]["action"], "huawei_auto_remediation_run")
        self.assertIn("# CCE 综合根因分析报告", result["report_markdown"])


if __name__ == "__main__":
    unittest.main()
