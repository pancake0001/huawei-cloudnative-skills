#!/usr/bin/env python3
"""Tests for network failure diagnosis decisions and Markdown reports."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import network_failure_diagnosis as diagnosis  # noqa: E402


def base_snapshot(**overrides):
    snapshot = {
        "inputs": {
            "region": "cn-north-4",
            "cluster_id": "cluster-1",
            "namespace": "prod",
            "target_kind": "service",
            "target_name": "api",
            "service_name": "api",
            "ingress_name": None,
            "failure_symptom": "集群内服务不通",
        },
        "collected_at": "2026-05-30T10:00:00+00:00",
        "nodes": [{"name": "node-a", "ready": "True", "conditions": [{"type": "Ready", "status": "True"}]}],
        "namespaces": [{"name": "prod", "labels": {"team": "app"}}],
        "pods": [
            {
                "name": "client",
                "namespace": "prod",
                "labels": {"app": "client"},
                "node": "node-a",
                "ready": True,
                "dns_policy": "ClusterFirst",
                "dns_config": None,
                "conditions": [{"type": "Ready", "status": "True"}],
                "containers": [{"name": "app", "ready": True, "restart_count": 0}],
            },
            {
                "name": "api-1",
                "namespace": "prod",
                "labels": {"app": "api"},
                "node": "node-a",
                "ready": True,
                "dns_policy": "ClusterFirst",
                "dns_config": None,
                "conditions": [{"type": "Ready", "status": "True"}],
                "containers": [{"name": "app", "ready": True, "restart_count": 0}],
            },
        ],
        "services": [
            {
                "name": "api",
                "namespace": "prod",
                "type": "ClusterIP",
                "selector": {"app": "api"},
                "ports": [{"port": 80, "target_port": 8080, "protocol": "TCP", "node_port": None}],
                "annotations": {},
                "load_balancer_ingress": [],
            },
            {
                "name": "kube-dns",
                "namespace": "kube-system",
                "type": "ClusterIP",
                "selector": {"k8s-app": "kube-dns"},
                "ports": [{"port": 53, "target_port": 53, "protocol": "UDP"}],
                "annotations": {},
                "load_balancer_ingress": [],
            },
        ],
        "ingresses": [],
        "endpoint_slices": [
            {
                "name": "api-abc",
                "namespace": "prod",
                "service_name": "api",
                "endpoints": [{"ready": True, "target_ref": {"kind": "Pod", "name": "api-1"}}],
                "ready_endpoint_count": 1,
            },
            {
                "name": "kube-dns-abc",
                "namespace": "kube-system",
                "service_name": "kube-dns",
                "endpoints": [{"ready": True, "target_ref": {"kind": "Pod", "name": "coredns-1"}}],
                "ready_endpoint_count": 1,
            },
        ],
        "network_policies": [],
        "events": [],
        "system": {"coredns_pods": [], "ingress_controller_pods": []},
        "logs": {},
        "cloud": {"elb_ids": [], "elbs": {}},
    }
    snapshot["target"] = {
        "service": snapshot["services"][0],
        "ingress": None,
        "source_pod": snapshot["pods"][0],
        "destination_pod": snapshot["pods"][1],
        "backend_pods": [snapshot["pods"][1]],
    }
    snapshot.update(overrides)
    return snapshot


class NetworkFailureDiagnosisTests(unittest.TestCase):
    def test_node_not_ready_prunes_upper_layers(self):
        snapshot = base_snapshot()
        snapshot["nodes"][0] = {
            "name": "node-a",
            "ready": "False",
            "conditions": [{"type": "Ready", "status": "False", "reason": "KubeletNotReady"}],
        }

        assessment = diagnosis.assess_network_snapshot(snapshot)
        report = diagnosis.build_markdown_report(snapshot, assessment)

        self.assertTrue(assessment["pipeline_pruned"])
        self.assertEqual(assessment["top_causes"][0]["type"], "NodeUnhealthy")
        self.assertIn("剪枝跳过", report)

    def test_network_policy_blocks_unallowed_source(self):
        snapshot = base_snapshot()
        snapshot["network_policies"] = [
            {
                "name": "api-allow-frontend",
                "namespace": "prod",
                "pod_selector": {"match_labels": {"app": "api"}, "match_expressions": []},
                "policy_types": ["Ingress"],
                "ingress": [
                    {
                        "from": [{"pod_selector": {"match_labels": {"app": "frontend"}, "match_expressions": []}}],
                        "ports": [{"protocol": "TCP", "port": "80"}],
                    }
                ],
            }
        ]

        assessment = diagnosis.assess_network_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "NetworkPolicyBlocked")
        self.assertEqual(assessment["top_causes"][0]["confidence"], 1.0)

    def test_service_without_ready_endpoints_is_reported(self):
        snapshot = base_snapshot(endpoint_slices=[])

        assessment = diagnosis.assess_network_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "ServiceNoReadyEndpoint")
        self.assertIn("EndpointSlice", assessment["top_causes"][0]["title"])

    def test_dns_policy_none_without_dns_config_is_reported(self):
        snapshot = base_snapshot()
        snapshot["inputs"]["failure_symptom"] = "域名无法解析"
        snapshot["target"]["source_pod"]["dns_policy"] = "None"
        snapshot["target"]["source_pod"]["dns_config"] = None

        assessment = diagnosis.assess_network_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "PodDNSConfigMissing")

    def test_elb_unhealthy_backend_with_ready_pod_is_reported(self):
        snapshot = base_snapshot()
        snapshot["inputs"]["failure_symptom"] = "外部域名访问 502"
        snapshot["target"]["service"]["type"] = "LoadBalancer"
        snapshot["target"]["service"]["load_balancer_ingress"] = [{"ip": "1.2.3.4"}]
        snapshot["cloud"] = {
            "elb_ids": ["elb-1"],
            "elbs": {
                "elb-1": {
                    "backend_status": {
                        "success": True,
                        "members": [{"id": "m1", "address": "10.0.0.8", "protocol_port": 32080, "operating_status": "OFFLINE"}],
                    },
                    "metrics": {"success": True, "summary": {"abnormal_servers": 1}},
                }
            },
        }

        assessment = diagnosis.assess_network_snapshot(snapshot)
        report = diagnosis.build_markdown_report(snapshot, assessment)

        self.assertEqual(assessment["top_causes"][0]["type"], "ELBBackendUnhealthy")
        self.assertIn("## 5. 证据矩阵", report)
        self.assertIn("ELB 后端健康检查异常", report)

    def test_ingress_numeric_ids_do_not_trigger_502_504_false_positive(self):
        snapshot = base_snapshot()
        snapshot["inputs"]["failure_symptom"] = "外部域名访问偶现不通"
        snapshot["target"]["ingress"] = {
            "name": "ingress-work",
            "namespace": "prod",
            "load_balancer_ingress": [{"ip": "192.168.135.155"}],
        }
        snapshot["logs"] = {
            "kube-system/nginx-ingress-controller-1": {
                "success": True,
                "excerpt": (
                    "I0530 14:37:15 status.go:311 updating Ingress status "
                    "uid=c395c56f-0547-41ee-ab76-44a5647e54b6 resourceVersion=556895"
                ),
            }
        }

        assessment = diagnosis.assess_network_snapshot(snapshot)

        self.assertNotIn("IngressUpstreamError", {item["type"] for item in assessment["findings"]})

    def test_ingress_access_log_504_triggers_upstream_error(self):
        snapshot = base_snapshot()
        snapshot["inputs"]["failure_symptom"] = "Ingress 504"
        snapshot["target"]["ingress"] = {
            "name": "ingress-work",
            "namespace": "prod",
            "load_balancer_ingress": [{"ip": "192.168.135.155"}],
        }
        snapshot["logs"] = {
            "kube-system/nginx-ingress-controller-1": {
                "success": True,
                "excerpt": '10.0.0.1 - - "GET /api/chat HTTP/1.1" 504 162 "-" "curl"',
            }
        }

        assessment = diagnosis.assess_network_snapshot(snapshot)

        self.assertIn("IngressUpstreamError", {item["type"] for item in assessment["findings"]})

    def test_collect_cloud_context_resolves_elb_from_ingress_vip(self):
        ingress = {"load_balancer_ingress": [{"ip": "192.168.135.155"}], "annotations": {}}
        with mock.patch(
            "huawei_cloud.network_failure_diagnosis.elb.list_elb_loadbalancers",
            return_value={
                "success": True,
                "loadbalancers": [{"id": "elb-1", "vip_address": "192.168.135.155"}],
            },
        ), mock.patch(
            "huawei_cloud.network_failure_diagnosis.elb.get_elb_backend_status",
            return_value={"success": True, "members": []},
        ), mock.patch(
            "huawei_cloud.network_failure_diagnosis.elb.get_elb_metrics",
            return_value={"success": True, "metrics": {}},
        ), mock.patch(
            "huawei_cloud.network_failure_diagnosis.network.list_eip_addresses",
            return_value={"success": True, "eips": []},
        ), mock.patch(
            "huawei_cloud.network_failure_diagnosis.network.list_nat_gateways",
            return_value={"success": True, "nat_gateways": []},
        ), mock.patch(
            "huawei_cloud.network_failure_diagnosis.network.list_security_groups",
            return_value={"success": True, "security_groups": []},
        ), mock.patch(
            "huawei_cloud.network_failure_diagnosis.network.list_vpc_acls",
            return_value={"success": True, "acls": []},
        ):
            cloud = diagnosis._collect_cloud_context(
                "cn-north-4",
                service=None,
                ingress=ingress,
                elb_id=None,
                access_key="ak",
                secret_key="sk",
                project_id="project",
                hours=1,
            )

        self.assertEqual(cloud["elb_ids"], ["elb-1"])
        self.assertEqual(cloud["load_balancer_ips"], ["192.168.135.155"])


if __name__ == "__main__":
    unittest.main()
