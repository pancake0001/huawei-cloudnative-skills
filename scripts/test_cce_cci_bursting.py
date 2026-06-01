#!/usr/bin/env python3
"""Unit tests for CCE to CCI 2.0 bursting helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
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
        self.assertEqual(result["addon_plan"]["project_id"], "project")
        self.assertEqual(result["addon_plan"]["values"]["basic.project_id"], "project")
        configure.assert_not_called()

    def test_smoke_workload_preview_does_not_need_credentials(self):
        result = cce_cci_bursting.deploy_cce_cci_smoke_workload("cn-north-4", "cluster-1")
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertIsNone(result["image"])
        self.assertEqual(
            result["image_selection"]["fallback_image"],
            cce_cci_bursting.DEFAULT_SMOKE_IMAGE,
        )

    def test_smoke_workload_preview_outside_cn_north_4_defers_image_discovery(self):
        result = cce_cci_bursting.deploy_cce_cci_smoke_workload("cn-south-1", "cluster-1")
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertIsNone(result["image_selection"]["fallback_image"])

    def test_cpu_and_memory_quantity_parsers(self):
        self.assertEqual(cce_cci_bursting._cpu_millicores("250m"), 250)
        self.assertEqual(cce_cci_bursting._cpu_millicores("2"), 2000)
        self.assertEqual(cce_cci_bursting._memory_bytes("4Gi"), 4 * 1024**3)

    def test_node_capacity_warns_for_single_small_physical_node(self):
        node = SimpleNamespace(
            metadata=SimpleNamespace(name="node-1", labels={}),
            spec=SimpleNamespace(unschedulable=False),
            status=SimpleNamespace(allocatable={"cpu": "2", "memory": "4Gi"}),
        )
        pod = SimpleNamespace(
            spec=SimpleNamespace(
                node_name="node-1",
                containers=[
                    SimpleNamespace(
                        resources=SimpleNamespace(requests={"cpu": "500m", "memory": "512Mi"})
                    )
                ],
            )
        )
        core = SimpleNamespace(
            list_node=lambda: SimpleNamespace(items=[node]),
            list_pod_for_all_namespaces=lambda: SimpleNamespace(items=[pod]),
        )
        with mock.patch.object(
            cce_cci_bursting, "_credentials", return_value=("ak", "sk", "project", None)
        ), mock.patch.object(
            cce_cci_bursting.cce_k8s, "_setup_k8s_client", return_value=(None, None, None)
        ), mock.patch.object(
            cce_cci_bursting.k8s_client, "CoreV1Api", return_value=core
        ):
            result = cce_cci_bursting.check_cce_cci_node_capacity("cn-north-4", "cluster-1")
        self.assertTrue(result["success"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["schedulable_physical_node_count"], 1)
        self.assertTrue(result["warnings"])

    def test_cvs_gateway_endpoint_receives_route_tables(self):
        client = mock.Mock()
        client.create_endpoint.return_value.to_dict.return_value = {"id": "vpcep-1"}
        with mock.patch.object(
            cce_cci_bursting,
            "_describe_public_service",
            return_value={"id": "service-1", "service_type": "cvs_gateway"},
        ), mock.patch.object(
            cce_cci_bursting,
            "CreateEndpointRequestBody",
            side_effect=lambda **kwargs: SimpleNamespace(**kwargs),
        ), mock.patch.object(
            cce_cci_bursting,
            "CreateEndpointRequest",
            side_effect=lambda body: SimpleNamespace(body=body),
        ):
            result = cce_cci_bursting._create_endpoint(
                client,
                "cn-north-4.com.myhuaweicloud.v4.obsv2.lz11",
                "vpc-1",
                "subnet-1",
                ["rt-1"],
            )
        self.assertEqual(result["service_type"], "cvs_gateway")
        body = client.create_endpoint.call_args.args[0].body
        self.assertEqual(body.routetables, ["rt-1"])

    def test_addon_diagnostics_redacts_log_and_reports_internal_status(self):
        addon_pod = SimpleNamespace(
            metadata=SimpleNamespace(name="bursting-cceaddon-vk-1"),
            status=SimpleNamespace(phase="Running"),
            spec=SimpleNamespace(node_name="node-1"),
        )
        core = SimpleNamespace(
            list_namespaced_pod=lambda namespace: SimpleNamespace(items=[addon_pod]),
            read_namespaced_pod_log=lambda *args, **kwargs: "region mismatch southchina token=secret-value",
            read_namespaced_config_map=lambda *args, **kwargs: SimpleNamespace(
                data={"enableBurstingNode": "false"}
            ),
        )
        apps = SimpleNamespace(
            list_namespaced_replica_set=lambda namespace: SimpleNamespace(items=[])
        )
        with mock.patch.object(
            cce_cci_bursting, "_credentials", return_value=("ak", "sk", "project", None)
        ), mock.patch.object(
            cce_cci_bursting.cce_k8s, "_setup_k8s_client", return_value=(None, None, None)
        ), mock.patch.object(
            cce_cci_bursting.k8s_client, "CoreV1Api", return_value=core
        ), mock.patch.object(
            cce_cci_bursting.k8s_client, "AppsV1Api", return_value=apps
        ):
            result = cce_cci_bursting.diagnose_cce_cci_bursting_addon("cn-north-4", "cluster-1")
        self.assertTrue(result["success"])
        self.assertIn("token=<redacted>", result["log_samples"][0]["tail"])
        self.assertIn("region-mismatch", {item["code"] for item in result["findings"]})
        self.assertIn("bursting-node-disabled", {item["code"] for item in result["findings"]})

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
