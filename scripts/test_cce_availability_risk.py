#!/usr/bin/env python3
"""Tests for the CCE availability risk scanner."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import cce_availability_risk  # noqa: E402


class CceAvailabilityRiskTests(unittest.TestCase):
    def test_scan_flags_distribution_pdb_probe_gateway_and_resource_risks(self):
        inventory = {
            "nodes": [
                {"name": "node-a", "zone": "az-a", "ready": "True", "role": "worker", "allocatable_cpu_cores": 4, "allocatable_memory_bytes": 8 * 1024**3},
                {"name": "node-b", "zone": "az-b", "ready": "True", "role": "worker", "allocatable_cpu_cores": 4, "allocatable_memory_bytes": 8 * 1024**3},
            ],
            "pods": [
                {"name": "web-1", "namespace": "default", "phase": "Running", "ready": True, "node": "node-a", "zone": "az-a", "owner_key": "Deployment/default/web", "labels": {"app": "web"}},
                {"name": "web-2", "namespace": "default", "phase": "Running", "ready": True, "node": "node-a", "zone": "az-a", "owner_key": "Deployment/default/web", "labels": {"app": "web"}},
                {"name": "coredns-1", "namespace": "kube-system", "phase": "Running", "ready": True, "node": "node-a", "zone": "az-a", "owner_key": "Deployment/kube-system/coredns", "labels": {"k8s-app": "coredns"}},
                {"name": "coredns-2", "namespace": "kube-system", "phase": "Running", "ready": True, "node": "node-b", "zone": "az-b", "owner_key": "Deployment/kube-system/coredns", "labels": {"k8s-app": "coredns"}},
            ],
            "workloads": [
                {
                    "key": "Deployment/default/web",
                    "kind": "Deployment",
                    "namespace": "default",
                    "name": "web-gateway",
                    "desired_replicas": 2,
                    "labels": {"app": "web"},
                    "template_labels": {"app": "web"},
                    "node_selector": {},
                    "affinity": None,
                    "topology_spread_constraints": [],
                    "containers": [
                        {
                            "name": "web",
                            "readiness_probe": False,
                            "liveness_probe": False,
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "1000m", "memory": "1024Mi"},
                            },
                        }
                    ],
                },
                {
                    "key": "Deployment/kube-system/coredns",
                    "kind": "Deployment",
                    "namespace": "kube-system",
                    "name": "coredns",
                    "desired_replicas": 2,
                    "labels": {"k8s-app": "coredns"},
                    "template_labels": {"k8s-app": "coredns"},
                    "node_selector": {},
                    "affinity": None,
                    "topology_spread_constraints": [],
                    "containers": [{"name": "coredns", "readiness_probe": True, "liveness_probe": True, "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {}}}],
                },
            ],
            "pdbs": [],
            "services": [{"name": "web-svc", "namespace": "default", "type": "LoadBalancer", "selector": {"app": "web"}}],
            "ingresses": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir, \
            mock.patch.object(cce_availability_risk, "_collect_k8s_inventory", return_value=(inventory, [])), \
            mock.patch.object(cce_availability_risk.cce_metrics, "get_cce_node_metrics_topN", return_value={"success": True, "metrics": {}}), \
            mock.patch.object(cce_availability_risk.cce, "list_cce_clusters", return_value={"success": True, "clusters": []}), \
            mock.patch.object(cce_availability_risk.cce, "list_cce_node_pools", return_value={"success": True, "nodepools": []}):
            result = cce_availability_risk.scan_cce_availability_risk(
                region="cn-north-4",
                cluster_id="cluster-1",
                output_dir=temp_dir,
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["summary"]["risk_level"], "high")
            categories = {issue["category"] for issue in result["issues"]}
            self.assertIn("pod-distribution", categories)
            self.assertIn("az-distribution", categories)
            self.assertIn("pdb", categories)
            self.assertIn("health-check", categories)
            self.assertIn("gateway", categories)
            self.assertIn("resources", categories)
            self.assertIn("core-plugin", categories)
            self.assertTrue(Path(result["files"]["summary"]).exists())
            self.assertTrue(Path(result["files"]["report"]).exists())


if __name__ == "__main__":
    unittest.main()
