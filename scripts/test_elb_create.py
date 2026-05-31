#!/usr/bin/env python3
"""Unit tests for preview-first ELB creation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import elb  # noqa: E402


class ElbCreateTests(unittest.TestCase):
    def test_preview_does_not_need_credentials(self):
        result = elb.create_elb_loadbalancer(
            "cn-north-4",
            "pressure-elb",
            "network-id",
            availability_zone_list="cn-north-4a,cn-north-4b",
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(
            result["plan"]["loadbalancer"]["availability_zone_list"],
            ["cn-north-4a", "cn-north-4b"],
        )

    @patch("huawei_cloud.elb.create_elb_client")
    @patch("huawei_cloud.elb.get_credentials_with_region")
    def test_confirm_calls_elb_v3_create(self, credentials, create_client):
        credentials.return_value = ("ak", "sk", "project")
        create_client.return_value.create_load_balancer.return_value = SimpleNamespace(
            to_dict=lambda: {"loadbalancer": {"id": "lb-1", "name": "pressure-elb"}},
            request_id="request-1",
        )
        result = elb.create_elb_loadbalancer(
            "cn-north-4",
            "pressure-elb",
            "network-id",
            confirm=True,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["loadbalancer"]["id"], "lb-1")
        create_client.return_value.create_load_balancer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
