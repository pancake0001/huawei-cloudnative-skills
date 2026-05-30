#!/usr/bin/env python3
"""Tests for CCE change impact analysis classification and reports."""

from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import change_impact_analysis as analysis  # noqa: E402


def audit_event(**overrides):
    event = {
        "time": "2026-05-30 10:01:00",
        "verb": "patch",
        "resource": "configmaps",
        "namespace": "kube-system",
        "name": "coredns",
        "user": "ops@example.com",
        "user_agent": "kubectl/v1.28",
        "status_code": 200,
        "request_uri": "/api/v1/namespaces/kube-system/configmaps/coredns",
        "content": '{"requestObject":{"data":{"Corefile":".:53 { forward . 10.0.0.2 }"}}}',
        "raw": {"requestObject": {"data": {"Corefile": ".:53 { forward . 10.0.0.2 }"}}},
    }
    event.update(overrides)
    return event


class ChangeImpactAnalysisTests(unittest.TestCase):
    def test_coredns_configmap_change_is_critical_global_change(self):
        change = analysis.classify_audit_event(audit_event())
        self.assertIsNotNone(change)
        assert change is not None

        analysis.score_changes([change])

        self.assertEqual(change["category"], "global_config_change")
        self.assertEqual(change["risk_level"], "Critical")
        self.assertGreaterEqual(change["risk_score"], 90)
        self.assertIn("全集群", change["blast_radius"])

    def test_hpa_only_workload_scale_is_filtered_as_noise(self):
        change = analysis.classify_audit_event(
            audit_event(
                resource="deployments",
                namespace="prod",
                name="api",
                user="system:serviceaccount:kube-system:horizontal-pod-autoscaler",
                user_agent="horizontal-pod-autoscaler",
                raw={"requestObject": {"spec": {"replicas": 4}}},
                content='{"requestObject":{"spec":{"replicas":4}}}',
            )
        )

        self.assertIsNone(change)

    def test_manual_replica_change_is_kept(self):
        change = analysis.classify_audit_event(
            audit_event(
                resource="deployments",
                namespace="prod",
                name="api",
                user="ops@example.com",
                user_agent="kubectl/v1.28",
                raw={"requestObject": {"spec": {"replicas": 1}}},
                content='{"requestObject":{"spec":{"replicas":1}}}',
            )
        )

        self.assertIsNotNone(change)

    def test_cce_managed_packageversion_rbac_update_is_filtered(self):
        change = analysis.classify_audit_event(
            audit_event(
                verb="update",
                resource="clusterroles",
                api_group="rbac.authorization.k8s.io",
                namespace=None,
                name="system:cce:packageversion",
                user="system:masters",
                user_agent="Go-http-client/2.0",
                request_uri="/apis/rbac.authorization.k8s.io/v1/clusterroles/system:cce:packageversion",
                raw={"requestObject": {"rules": [{"resources": ["packageversions"], "verbs": ["get"]}]}},
                content='{"requestObject":{"rules":[{"resources":["packageversions"],"verbs":["get"]}]}}',
            )
        )

        self.assertIsNone(change)

    def test_user_clusterrole_update_is_kept(self):
        change = analysis.classify_audit_event(
            audit_event(
                verb="update",
                resource="clusterroles",
                api_group="rbac.authorization.k8s.io",
                namespace=None,
                name="custom-admin",
                user="ops@example.com",
                user_agent="kubectl/v1.28",
                request_uri="/apis/rbac.authorization.k8s.io/v1/clusterroles/custom-admin",
                raw={"requestObject": {"rules": [{"resources": ["secrets"], "verbs": ["*"]}]}},
                content='{"requestObject":{"rules":[{"resources":["secrets"],"verbs":["*"]}]}}',
            )
        )

        self.assertIsNotNone(change)

    def test_serviceaccount_token_and_node_status_are_filtered(self):
        token_change = analysis.classify_audit_event(
            audit_event(
                verb="create",
                resource="serviceaccounts",
                subresource="token",
                namespace="kube-system",
                name="cceaddon-nginx-ingress",
                user="system:node:192.168.32.218",
                user_agent="kubelet/v1.34.3",
                request_uri="/api/v1/namespaces/kube-system/serviceaccounts/cceaddon-nginx-ingress/token",
            )
        )
        node_status_change = analysis.classify_audit_event(
            audit_event(
                verb="patch",
                resource="nodes",
                subresource="status",
                namespace=None,
                name="192.168.32.117",
                user="system:node:192.168.32.117",
                user_agent="kubelet/v1.34.3",
                request_uri="/api/v1/nodes/192.168.32.117/status",
            )
        )

        self.assertIsNone(token_change)
        self.assertIsNone(node_status_change)

    def test_scheduler_binding_and_controller_rollout_updates_are_filtered(self):
        binding_change = analysis.classify_audit_event(
            audit_event(
                verb="create",
                resource="pods",
                subresource="binding",
                namespace="default",
                name="abclient-587ccfdd4b-jksjs",
                user="system:kube-scheduler",
                user_agent="kube-scheduler/v1.34.2",
                request_uri="/api/v1/namespaces/default/pods/abclient-587ccfdd4b-jksjs/binding",
            )
        )
        controller_update = analysis.classify_audit_event(
            audit_event(
                verb="update",
                resource="deployments",
                subresource="status",
                namespace="default",
                name="abclient",
                user="system:serviceaccount:kube-system:deployment-controller",
                user_agent="kube-controller-manager/v1.34.2",
                request_uri="/apis/apps/v1/namespaces/default/deployments/abclient",
                raw={"requestObject": {"spec": {"replicas": 10}, "status": {"readyReplicas": 9}}},
                content='{"requestObject":{"spec":{"replicas":10},"status":{"readyReplicas":9}}}',
            )
        )

        self.assertIsNone(binding_change)
        self.assertIsNone(controller_update)

    def test_status_subresources_are_filtered_even_with_full_spec_echo(self):
        change = analysis.classify_audit_event(
            audit_event(
                verb="update",
                resource="replicasets",
                subresource="status",
                namespace="default",
                name="abclient-587ccfdd4b",
                user="system:serviceaccount:kube-system:replicaset-controller",
                user_agent="kube-controller-manager/v1.34.2",
                request_uri="/apis/apps/v1/namespaces/default/replicasets/abclient-587ccfdd4b/status",
                raw={"requestObject": {"spec": {"template": {"spec": {"containers": [{"image": "demo:v2"}]}}}}},
                content='{"requestObject":{"spec":{"template":{"spec":{"containers":[{"image":"demo:v2"}]}}}}}',
            )
        )

        self.assertIsNone(change)

    def test_ingress_change_maps_to_backend_service(self):
        change = analysis.classify_audit_event(
            audit_event(
                resource="ingresses",
                namespace="prod",
                name="api-ingress",
                raw={"requestObject": {"spec": {"rules": [{"host": "api.example.com"}]}}},
                content='{"requestObject":{"spec":{"rules":[{"host":"api.example.com"}]}}}',
            ),
            namespace="prod",
            target_name="api",
        )
        assert change is not None
        snapshots = {
            "pods": [{"namespace": "prod", "name": "api-123", "labels": {"app": "api"}}],
            "services": [{"namespace": "prod", "name": "api", "selector": {"app": "api"}}],
            "ingresses": [
                {
                    "namespace": "prod",
                    "name": "api-ingress",
                    "rules": [{"paths": [{"backend": {"service_name": "api", "service_port": 80}}]}],
                }
            ],
            "nodes": [],
        }

        analysis.assemble_blast_radius([change], snapshots)
        analysis.score_changes([change])

        self.assertIn("prod/api", change["impacted_entities"]["services"])
        self.assertGreaterEqual(change["risk_score"], 60)

    def test_action_returns_complete_markdown_report_with_mocked_capture(self):
        captures = {
            "audit": {"success": True, "summary": {"matched_events": 1}, "events": [audit_event()]},
            "k8s_events_lts": {
                "success": True,
                "event_count": 1,
                "events": [
                    {
                        "last_timestamp": "2026-05-30 10:05:00",
                        "reason": "DNSConfigChanged",
                        "message": "CoreDNS reload after coredns ConfigMap update",
                        "namespace": "kube-system",
                        "name": "coredns",
                    }
                ],
            },
            "aom": {"success": True, "alarms": []},
            "snapshots": {
                "raw": {"pods": {"success": True}, "services": {"success": True}},
                "pods": [],
                "services": [],
                "ingresses": [],
                "nodes": [{"name": "node-a"}],
            },
        }

        with mock.patch(
            "huawei_cloud.change_impact_analysis.collect_shadow_captures",
            return_value=captures,
        ):
            result = analysis.analyze_change_impact(
                {
                    "region": "cn-north-4",
                    "cluster_id": "cluster-1",
                    "start_time": "2026-05-30 10:00:00",
                    "end_time": "2026-05-30 11:00:00",
                    "fault_time": "2026-05-30 10:10:00",
                    "include_snapshots": "true",
                }
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["core_change_count"], 1)
        self.assertIn("# CCE 变更影响分析报告", result["report_markdown"])
        self.assertIn("Analysis-Trace-ID", result["report_markdown"])
        self.assertIn("核心变更时间线", result["report_markdown"])
        self.assertIn("证据矩阵", result["report_markdown"])
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
