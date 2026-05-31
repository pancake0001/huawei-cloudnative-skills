#!/usr/bin/env python3
"""Unit tests for preview-first CCE APM Java agent injection."""

from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import cce_apm  # noqa: E402


class MissingSecret(Exception):
    status = 404


class CceApmTests(unittest.TestCase):
    def test_preview_redacts_secret_and_does_not_need_credentials(self):
        result = cce_apm.inject_cce_apm_javaagent(
            "cn-north-4",
            "cluster-1",
            "demo",
            "orders",
            "orders-apm",
            "retail",
            "pressure",
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["plan"]["secret"]["values"], "<redacted>")
        patch_body = result["plan"]["workload_patch"]
        init = patch_body["spec"]["template"]["spec"]["initContainers"][0]
        self.assertIn('\"$APM_SECRET_KEY\"', init["args"][0])
        self.assertNotIn("secret-key-value", str(patch_body))

    @patch("huawei_cloud.cce_apm.k8s_client")
    @patch("huawei_cloud.cce_apm.cce_k8s._setup_k8s_client")
    @patch("huawei_cloud.cce_apm.apm.get_apm_master_address")
    @patch("huawei_cloud.cce_apm.get_credentials_with_region")
    def test_confirm_upserts_secret_and_patches_workload(self, credentials, master, setup, client):
        credentials.return_value = ("cloud-ak", "cloud-sk", "project")
        master.return_value = {"success": True, "master_address": "10.0.0.8:41333"}
        setup.return_value = (None, None, None)
        apps = SimpleNamespace(
            read_namespaced_deployment=lambda name, namespace: SimpleNamespace(
                spec=SimpleNamespace(
                    template=SimpleNamespace(
                        spec=SimpleNamespace(containers=[SimpleNamespace(name="orders")])
                    )
                )
            ),
            patch_namespaced_deployment=lambda name, namespace, body: SimpleNamespace(
                metadata=SimpleNamespace(generation=2)
            ),
        )
        created = {}

        def create_secret(namespace, body):
            created.update(body)

        core = SimpleNamespace(
            read_namespaced_secret=lambda name, namespace: (_ for _ in ()).throw(MissingSecret()),
            create_namespaced_secret=create_secret,
        )
        client.AppsV1Api.return_value = apps
        client.CoreV1Api.return_value = core

        result = cce_apm.inject_cce_apm_javaagent(
            "cn-north-4",
            "cluster-1",
            "demo",
            "orders",
            "orders-apm",
            "retail",
            "pressure",
            confirm=True,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["target_containers"], ["orders"])
        self.assertEqual(result["secret"]["values"], "<redacted>")
        self.assertEqual(base64.b64decode(created["data"]["access-key"]).decode(), "cloud-ak")
        self.assertEqual(base64.b64decode(created["data"]["secret-key"]).decode(), "cloud-sk")


if __name__ == "__main__":
    unittest.main()
