#!/usr/bin/env python3
"""Unit tests for Huawei Cloud APM helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import apm  # noqa: E402


class ApmTests(unittest.TestCase):
    @patch("huawei_cloud.apm.requests.get")
    def test_get_master_address_with_token(self, get):
        get.return_value = SimpleNamespace(
            status_code=200,
            text='{"data":{"master_address":"10.0.0.8:41333"}}',
            json=lambda: {"data": {"master_address": "10.0.0.8:41333"}},
        )
        result = apm.get_apm_master_address("cn-north-4", auth_token="token")
        self.assertTrue(result["success"])
        self.assertEqual(result["master_address"], "10.0.0.8:41333")
        self.assertEqual(get.call_args.kwargs["headers"]["X-Auth-Token"], "token")


if __name__ == "__main__":
    unittest.main()
