#!/usr/bin/env python3
"""Unit tests for preview-first CCE node-pool creation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import cce_nodepool  # noqa: E402


class CceNodePoolTests(unittest.TestCase):
    def test_create_preview_does_not_need_credentials(self):
        result = cce_nodepool.create_node_pool(
            "cn-north-4",
            "cluster-1",
            "burst-worker",
            "c7.large.2",
            "cn-north-4a",
            40,
            "GPSSD",
            2,
            ssh_key="KeyPair-dev",
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["operation"], "create_nodepool")
        self.assertEqual(result["plan"]["initial_node_count"], 2)


if __name__ == "__main__":
    unittest.main()

