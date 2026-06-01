#!/usr/bin/env python3
"""Unit tests for SWR basic edition smoke-image discovery."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import swr  # noqa: E402


class SwrSmokeImageDiscoveryTests(unittest.TestCase):
    def test_discovery_follows_namespace_repo_tag_sequence(self):
        with mock.patch.object(
            swr,
            "get_credentials_with_region",
            return_value=("ak", "sk", "project"),
        ), mock.patch.object(
            swr,
            "_signed_swr_get",
            side_effect=[
                [{"name": "pancake"}],
                [{"name": "openclaw-sandbox"}],
                [{"name": "latest"}],
            ],
        ) as signed_get:
            result = swr.discover_swr_smoke_images("cn-north-4")

        self.assertTrue(result["success"])
        self.assertEqual(
            result["candidates"][0]["image"],
            "swr.cn-north-4.myhuaweicloud.com/pancake/openclaw-sandbox:latest",
        )
        self.assertEqual(signed_get.call_args_list[0].args[1], "/v2/manage/namespaces")
        self.assertEqual(signed_get.call_args_list[1].args[1], "/v2/manage/repos")
        self.assertEqual(
            signed_get.call_args_list[2].args[1],
            "/v2/manage/namespaces/pancake/repos/openclaw-sandbox/tags",
        )

    def test_discovery_requires_project_id(self):
        with mock.patch.object(
            swr,
            "get_credentials_with_region",
            return_value=("ak", "sk", None),
        ):
            result = swr.discover_swr_smoke_images("cn-north-4")
        self.assertFalse(result["success"])
        self.assertIn("Project ID", result["error"])


if __name__ == "__main__":
    unittest.main()

