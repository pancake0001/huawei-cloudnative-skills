#!/usr/bin/env python3
"""Tests for node failure diagnosis evidence scoring and reports."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import node_failure_diagnosis as diagnosis  # noqa: E402


def node_with_conditions(*conditions):
    return {
        "name": "node-a",
        "internal_ip": "10.0.0.8",
        "ready": next((item["status"] for item in conditions if item["type"] == "Ready"), "Unknown"),
        "conditions": list(conditions),
    }


class NodeFailureDiagnosisTests(unittest.TestCase):
    def test_memory_pressure_with_stale_lease_is_high_confidence(self):
        node = node_with_conditions(
            {"type": "Ready", "status": "Unknown", "reason": "NodeStatusUnknown"},
            {"type": "MemoryPressure", "status": "True", "reason": "KubeletHasInsufficientMemory"},
        )
        lease = {
            "stale": True,
            "renew_delay_seconds": 72,
            "threshold_seconds": 40,
            "renew_time": "2026-05-30T10:00:00Z",
        }
        events = [
            {
                "reason": "SystemOOM",
                "message": "System OOM encountered, critical process might be killed.",
                "source": "kubelet",
                "type": "Warning",
                "last_timestamp": "2026-05-30T10:12:05Z",
                "involved_object": {"kind": "Node", "name": "node-a"},
            }
        ]
        pods = [
            {
                "namespace": "prod",
                "name": "java-api-1",
                "phase": "Running",
                "containers": [
                    {
                        "name": "app",
                        "restart_count": 2,
                        "last_state_detail": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137},
                    }
                ],
            }
        ]

        assessment = diagnosis.assess_node_failure_context(node, lease, events, pods, [])
        report = diagnosis.build_markdown_report(node, lease, events, [], assessment)

        self.assertEqual(assessment["liveness"]["case"], "A")
        self.assertEqual(assessment["root_category"], "MemoryPressure")
        self.assertEqual(assessment["confidence"], "高 (High)")
        self.assertIn("内存压力", assessment["conclusion"])
        self.assertIn("## 3. 关键排查", report)
        self.assertIn("SystemOOM", report)

    def test_disk_pressure_from_eviction_event_and_evicted_pod(self):
        node = node_with_conditions(
            {"type": "Ready", "status": "False", "reason": "KubeletNotReady"},
            {"type": "DiskPressure", "status": "True", "reason": "KubeletHasDiskPressure"},
        )
        lease = {"stale": False, "renew_delay_seconds": 4, "threshold_seconds": 40}
        events = [
            {
                "reason": "EvictionThresholdMet",
                "message": "Attempting to reclaim ephemeral-storage from imagefs and nodefs.",
                "source": "kubelet",
                "type": "Warning",
            }
        ]
        pods = [
            {
                "namespace": "default",
                "name": "worker-1",
                "phase": "Failed",
                "reason": "Evicted",
                "message": "The node was low on resource: DiskPressure.",
                "containers": [],
            }
        ]

        assessment = diagnosis.assess_node_failure_context(node, lease, events, pods, [])

        self.assertEqual(assessment["liveness"]["case"], "B")
        self.assertEqual(assessment["root_category"], "DiskPressure")
        self.assertGreaterEqual(assessment["scores"]["DiskPressure"], 10)

    def test_cni_sandbox_event_identifies_network_failure(self):
        node = node_with_conditions({"type": "Ready", "status": "True"})
        lease = {"stale": False, "renew_delay_seconds": 2, "threshold_seconds": 40}
        pods = [
            {
                "namespace": "prod",
                "name": "new-api-1",
                "phase": "Pending",
                "containers": [
                    {
                        "name": "app",
                        "restart_count": 0,
                        "state_detail": {
                            "type": "waiting",
                            "reason": "ContainerCreating",
                            "message": "creating container",
                        },
                    }
                ],
            }
        ]
        pod_events = [
            {
                "reason": "FailedCreatePodSandBox",
                "message": "network plugin returns error: timeout waiting for DHCP",
                "source": "kubelet",
                "type": "Warning",
                "involved_object": {"kind": "Pod", "namespace": "prod", "name": "new-api-1"},
            }
        ]

        assessment = diagnosis.assess_node_failure_context(node, lease, [], pods, pod_events)

        self.assertEqual(assessment["liveness"]["case"], "C")
        self.assertEqual(assessment["root_category"], "Network")
        self.assertIn("CNI", assessment["evidence"][0]["signal"])

    def test_ready_unknown_stale_lease_keeps_disconnected_conclusion_without_overclaiming(self):
        node = node_with_conditions(
            {"type": "Ready", "status": "Unknown", "reason": "NodeStatusUnknown"},
            {"type": "MemoryPressure", "status": "Unknown", "reason": "NodeStatusUnknown"},
            {"type": "DiskPressure", "status": "Unknown", "reason": "NodeStatusUnknown"},
            {"type": "NetworkUnavailable", "status": "False", "reason": "RouteCreated"},
        )
        node["taints"] = [
            {"key": "node.kubernetes.io/unreachable", "effect": "NoSchedule"},
            {"key": "node.kubernetes.io/unreachable", "effect": "NoExecute"},
        ]
        lease = {"stale": True, "renew_delay_seconds": 280, "threshold_seconds": 40}
        events = [
            {
                "reason": "NodeNotReady",
                "message": "Node is not ready",
                "source": "node-controller",
                "type": "Warning",
                "last_timestamp": "2026-05-30T03:21:02Z",
            },
            {
                "reason": "NodeNotReady",
                "message": "Node is not ready",
                "source": "node-controller",
                "type": "Warning",
                "last_timestamp": "2026-05-30T03:21:02Z",
            },
        ]
        pods = [
            {
                "namespace": "kube-system",
                "name": "node-local-dns-abc",
                "phase": "Running",
                "containers": [{"restart_count": 0}],
            }
        ]

        assessment = diagnosis.assess_node_failure_context(node, lease, events, pods, [])
        report = diagnosis.build_markdown_report(node, lease, events, [], assessment)

        self.assertEqual(assessment["root_category"], "ControlPlaneDisconnected")
        self.assertEqual(assessment["confidence"], "高 (High)")
        self.assertIn("控制面与节点失联", assessment["conclusion"])
        health_by_item = {item["item"]: item for item in assessment["health_items"]}
        self.assertEqual(health_by_item["内存压力"]["status"], "不可判定")
        self.assertEqual(health_by_item["磁盘压力"]["status"], "不可判定")
        self.assertEqual(health_by_item["网络状态"]["status"], "候选")
        self.assertIn("节点污点", report)
        self.assertIn("指标快照", report)
        self.assertEqual(
            len([item for item in assessment["evidence"] if item["signal"] == "NodeNotReady"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
