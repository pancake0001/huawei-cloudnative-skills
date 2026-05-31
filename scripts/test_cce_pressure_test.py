#!/usr/bin/env python3
"""Unit tests for CCE pressure-test helpers."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import cce_pressure_test, dispatcher  # noqa: E402


class CcePressureTestTests(unittest.TestCase):
    def test_java_sample_preview_does_not_need_credentials(self):
        result = cce_pressure_test.deploy_cce_pressure_test_java_sample("cn-north-4", "cluster-1")
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        deployment = result["plan"]["manifest"]["deployment"]
        self.assertEqual(deployment["spec"]["replicas"], 2)
        self.assertIn("/api/work", cce_pressure_test._java_source())
        self.assertIn("readinessProbe", deployment["spec"]["template"]["spec"]["containers"][0])

    def test_route_preview_does_not_need_credentials(self):
        result = cce_pressure_test.prepare_cce_pressure_test_route(
            "cn-north-4", "cluster-1", "demo", "orders", target_port=8080
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["plan"]["network_path"], "pod -> service -> nginx-ingress -> elb")
        self.assertEqual(result["plan"]["service"]["spec"]["selector"], {"app": "orders"})

    def test_controller_endpoint_prefers_ingress_controller_service(self):
        def service(namespace, name, address, ports, labels):
            return SimpleNamespace(
                metadata=SimpleNamespace(namespace=namespace, name=name, labels=labels),
                spec=SimpleNamespace(type="LoadBalancer", ports=[SimpleNamespace(port=port) for port in ports]),
                status=SimpleNamespace(load_balancer=SimpleNamespace(ingress=[SimpleNamespace(ip=address, hostname=None)])),
            )

        core_v1 = SimpleNamespace(
            list_service_for_all_namespaces=lambda: SimpleNamespace(
                items=[
                    service("default", "nginx-70338", "192.168.0.70", [12111], {}),
                    service(
                        "kube-system",
                        "cceaddon-nginx-ingress-controller",
                        "192.168.135.155",
                        [80, 443],
                        {"component": "controller"},
                    ),
                ]
            )
        )
        result = cce_pressure_test._controller_endpoint(core_v1)
        self.assertEqual(result["selected"]["service_name"], "cceaddon-nginx-ingress-controller")
        self.assertEqual(result["selected"]["addresses"], ["192.168.135.155"])

    def test_generate_client_supports_short_connections(self):
        result = cce_pressure_test.generate_cce_pressure_test_client(
            "http://127.0.0.1/orders", namespace="demo", test_name="orders-short", model="short", vus=5
        )
        self.assertTrue(result["success"])
        self.assertIn("noConnectionReuse", result["manifest"]["configmap"]["data"]["test.js"])
        self.assertIn("Connection", result["manifest"]["configmap"]["data"]["test.js"])
        self.assertIn("kind: Job", result["manifest_yaml"])

    def test_run_preview_does_not_need_credentials(self):
        result = cce_pressure_test.run_cce_pressure_test(
            "cn-north-4", "cluster-1", "http://127.0.0.1", test_name="orders-baseline"
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["plan"]["test_name"], "orders-baseline")

    def test_extract_k6_summary(self):
        summary = cce_pressure_test._extract_k6_summary(
            'noise\nPRESSURE_TEST_RESULT {"request_count":12,"rps":3.5,"success_rate":1}\n'
        )
        self.assertEqual(summary["request_count"], 12)
        self.assertEqual(summary["rps"], 3.5)

    @patch("huawei_cloud.cce_pressure_test.cce_metrics.get_cce_pod_metrics_topN")
    @patch("huawei_cloud.cce_pressure_test.cce_k8s.get_cce_ingresses")
    @patch("huawei_cloud.cce_pressure_test.cce_k8s.get_cce_services")
    @patch("huawei_cloud.cce_pressure_test.cce_k8s.get_cce_pods")
    @patch("huawei_cloud.cce_pressure_test.cce_diagnosis.get_aom_instance")
    def test_collect_observability_auto_resolves_aom_instance(self, resolve, pods, services, ingresses, metrics):
        resolve.return_value = {"success": True, "aom_instance_id": "aom-1", "source": "cie-collector"}
        pods.return_value = {"success": True, "pods": []}
        services.return_value = {"success": True, "services": []}
        ingresses.return_value = {"success": True, "ingresses": []}
        metrics.return_value = {"success": True}
        result = cce_pressure_test.collect_cce_pressure_test_observability(
            "cn-north-4", "cluster-1", "demo", "orders"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["aom_instance_id"], "aom-1")
        self.assertEqual(result["aom_instance_resolution"]["source"], "cie-collector")

    def test_generate_report_writes_html_markdown_and_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "run.json"
            result_path.write_text(
                json.dumps(
                    {
                        "test_name": "orders-ramp",
                        "namespace": "demo",
                        "workload_name": "orders",
                        "model": "ramp",
                        "target_url": "http://127.0.0.1/orders",
                        "k6_summary": {
                            "request_count": 100,
                            "rps": 20,
                            "success_rate": 1,
                            "failure_rate": 0,
                            "latency_p95_ms": 120,
                        },
                        "metric_series": {
                            "rps": [{"timestamp": 100, "value": 5}, {"timestamp": 110, "value": 20}],
                            "latency_ms": [{"timestamp": 100, "value": 80}, {"timestamp": 110, "value": 120}],
                            "desired_replicas": [{"timestamp": 100, "value": 2}, {"timestamp": 110, "value": 4}],
                            "ready_replicas": [{"timestamp": 100, "value": 2}, {"timestamp": 110, "value": 4}],
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = cce_pressure_test.generate_cce_pressure_test_report(str(result_path))
            self.assertTrue(report["success"])
            for artifact in report["files"].values():
                self.assertTrue(Path(artifact).exists())
            html_text = Path(report["files"]["html"]).read_text(encoding="utf-8")
            markdown_text = Path(report["files"]["markdown"]).read_text(encoding="utf-8")
            self.assertIn("Curve Chart", html_text)
            self.assertIn("Relationship Assessment", html_text)
            self.assertIn("Recommendations", html_text)
            self.assertIn("Data Gaps", markdown_text)

    def test_dispatcher_registers_pressure_test_actions(self):
        expected = {
            "huawei_prepare_cce_pressure_test_route",
            "huawei_deploy_cce_pressure_test_java_sample",
            "huawei_generate_cce_pressure_test_client",
            "huawei_run_cce_pressure_test",
            "huawei_collect_cce_pressure_test_observability",
            "huawei_generate_cce_pressure_test_report",
            "huawei_create_elb",
            "huawei_resolve_cce_aom_instance",
            "huawei_get_apm_master_address",
            "huawei_inject_cce_apm_javaagent",
        }
        self.assertEqual(expected - set(dispatcher.ACTION_SPECS), set())
        self.assertEqual(
            dispatcher.ACTION_SPECS["huawei_run_cce_pressure_test"][0],
            ("region", "cluster_id", "target_url"),
        )


if __name__ == "__main__":
    unittest.main()
