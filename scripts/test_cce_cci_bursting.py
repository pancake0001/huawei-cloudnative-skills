#!/usr/bin/env python3
"""Unit tests for CCE to CCI 2.0 bursting helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import cce_cci_bursting  # noqa: E402


class CceCciBurstingTests(unittest.TestCase):
    def test_obs_policy_detection_accepts_obs_actions(self):
        self.assertTrue(
            cce_cci_bursting._contains_obs_policy(
                {"policy_statement": [{"action": ["obs:*:*"], "resource": ["obs:*:*:*:*"]}]}
            )
        )

    def test_obs_policy_detection_rejects_unrelated_gateway(self):
        self.assertFalse(
            cce_cci_bursting._contains_obs_policy(
                {"policy_statement": [{"action": ["sfs:*:*"], "resource": ["sfs:*:*:*:*"]}]}
            )
        )

    def test_find_obs_endpoint_requires_obs_evidence(self):
        endpoint = {
            "id": "vpcep-1",
            "service_name": "cn-north-4.com.myhuaweicloud.v4.storage.lz13",
            "service_type": "cvs_gateway",
            "status": "accepted",
        }
        with mock.patch.object(
            cce_cci_bursting,
            "_endpoint_detail",
            return_value={"policy_statement": [{"action": ["obs:*:*"]}]},
        ):
            result = cce_cci_bursting._find_obs_endpoint(mock.Mock(), [endpoint])
        self.assertEqual(result["id"], "vpcep-1")
        self.assertTrue(result["obs_policy_verified"])

    def test_setup_preview_never_configures_addon(self):
        precheck = {
            "success": True,
            "network": {"cci_neutron_subnet_id": "neutron-1"},
            "subnet_roles": {"vpcep_vpc_subnet_id": "vpc-subnet-1"},
        }
        with mock.patch.object(
            cce_cci_bursting, "_credentials", return_value=("ak", "sk", "project", None)
        ), mock.patch.object(
            cce_cci_bursting, "precheck_cce_cci_bursting", return_value=precheck
        ), mock.patch.object(
            cce_cci_bursting,
            "ensure_cce_cci_vpcep",
            return_value={"success": False, "requires_confirmation": True},
        ), mock.patch.object(
            cce_cci_bursting.cce_addon, "configure_cce_bursting_addon"
        ) as configure:
            result = cce_cci_bursting.setup_cce_cci_bursting("cn-north-4", "cluster-1")
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        configure.assert_not_called()

    def test_smoke_workload_preview_does_not_need_credentials(self):
        result = cce_cci_bursting.deploy_cce_cci_smoke_workload("cn-north-4", "cluster-1")
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["image"], cce_cci_bursting.DEFAULT_SMOKE_IMAGE)

    def test_smoke_workload_requires_regional_image_outside_cn_north_4(self):
        result = cce_cci_bursting.deploy_cce_cci_smoke_workload("cn-south-1", "cluster-1")
        self.assertFalse(result["success"])
        self.assertIn("regional SWR image", result["error"])

    def test_verify_reports_running_workload_on_bursting_node(self):
        addons = {
            "success": True,
            "addons": [{"name": "virtual-kubelet", "uid": "addon-1", "status": "running"}],
        }
        nodes = {"success": True, "nodes": [{"name": "bursting-node", "ready": "True", "labels": {}}]}
        pods = {
            "success": True,
            "pods": [
                {
                    "name": "demo-1",
                    "status": "Running",
                    "node": "bursting-node",
                    "labels": {"app": "demo"},
                }
            ],
        }
        deployments = {"success": True, "deployments": [{"name": "demo"}]}
        events = {"success": True, "events": []}
        with mock.patch.object(
            cce_cci_bursting, "_credentials", return_value=("ak", "sk", "project", None)
        ), mock.patch.object(
            cce_cci_bursting.cce_addon, "list_cce_addons", return_value=addons
        ), mock.patch.object(
            cce_cci_bursting.cce, "get_kubernetes_nodes", return_value=nodes
        ), mock.patch.object(
            cce_cci_bursting.cce_k8s, "get_cce_pods", return_value=pods
        ), mock.patch.object(
            cce_cci_bursting.cce_k8s, "get_cce_deployments", return_value=deployments
        ), mock.patch.object(
            cce_cci_bursting.cce_k8s, "get_cce_events", return_value=events
        ):
            result = cce_cci_bursting.verify_cce_cci_bursting(
                "cn-north-4", "cluster-1", namespace="lab", workload_name="demo"
            )
        self.assertTrue(result["success"])
        self.assertEqual(result["workload"]["phase_distribution"], {"Running": 1})
        self.assertEqual(result["workload"]["node_distribution"], {"bursting-node": 1})


if __name__ == "__main__":
    unittest.main()
