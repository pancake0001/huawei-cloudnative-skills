#!/usr/bin/env python3
"""Tests for auto remediation decision flow."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import auto_remediation as remediation  # noqa: E402


class AutoRemediationTests(unittest.TestCase):
    @mock.patch.object(remediation, "rollback_cce_workload")
    @mock.patch.object(remediation.workload_rollout_diagnosis, "workload_rollout_diagnose")
    def test_command_not_found_generates_rollback_preview(self, diagnose_mock, rollback_mock):
        diagnose_mock.return_value = {
            "success": True,
            "summary": {"status": "rollout_blocked"},
            "top_causes": [{"type": "ContainerCommandNotFound", "title": "bad command"}],
        }
        rollback_mock.return_value = {
            "success": False,
            "requires_confirmation": True,
            "current_revision": 2,
            "target_revision": 1,
            "warning": "rollback preview",
        }

        result = remediation.auto_remediation_run(
            {
                "region": "cn-north-4",
                "cluster_id": "cluster-1",
                "namespace": "yzh",
                "workload_name": "test-yzh",
                "workload_type": "deployment",
            }
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        rollback_mock.assert_called_once()
        self.assertEqual(result["action_result"]["target_revision"], 1)
        self.assertIn("# CCE 自动恢复执行报告", result["report_markdown"])


if __name__ == "__main__":
    unittest.main()
