#!/usr/bin/env python3
"""Unit tests for Pod failure diagnosis."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import pod_diagnosis  # noqa: E402


def pod_fixture(**overrides):
    pod = {
        "name": "demo-7c9d",
        "namespace": "default",
        "status": "Running",
        "phase": "Running",
        "reason": None,
        "message": None,
        "node": "192.168.0.10",
        "ip": "10.0.0.12",
        "host_ip": "192.168.0.10",
        "qos_class": "Burstable",
        "owner_references": [{"kind": "ReplicaSet", "name": "demo-7c9d"}],
        "conditions": [{"type": "Ready", "status": "False"}],
        "containers": [
            {
                "name": "app",
                "image": "swr.example.com/demo/app:v1",
                "ready": False,
                "restart_count": 6,
                "state_detail": {"type": "waiting", "reason": "CrashLoopBackOff", "message": "back-off"},
                "last_state_detail": {"type": "terminated", "reason": "Error", "exit_code": 1},
                "resources": {"requests": {"memory": "256Mi"}, "limits": {"memory": "512Mi"}},
            }
        ],
        "init_containers": [],
        "image_pull_secrets": ["default-secret"],
    }
    pod.update(overrides)
    return pod


class PodFailureDiagnosisTests(unittest.TestCase):
    def test_crashloop_diagnosis_collects_previous_logs_and_masks_secrets(self):
        events = [
            {
                "type": "Warning",
                "reason": "BackOff",
                "message": "Back-off restarting failed container app",
                "last_timestamp": "2026-05-29T01:00:00Z",
                "count": 4,
                "involved_object": {"kind": "Pod", "name": "demo-7c9d", "namespace": "default"},
            }
        ]

        def fake_logs(*args, **kwargs):
            if kwargs.get("previous"):
                return {"success": True, "logs": "boot\npassword=super-secret\nexit 1"}
            return {"success": True, "logs": "starting"}

        with mock.patch("huawei_cloud.pod_diagnosis.cce.get_kubernetes_pods", return_value={"success": True, "pods": [pod_fixture()]}), \
            mock.patch("huawei_cloud.pod_diagnosis.cce.get_kubernetes_events", return_value={"success": True, "events": events}), \
            mock.patch("huawei_cloud.pod_diagnosis.cce.get_pod_logs", side_effect=fake_logs) as mocked_logs:
            result = pod_diagnosis.pod_failure_diagnose("cn-north-4", "cluster-1", namespace="default", pod_name="demo-7c9d")

        self.assertTrue(result["success"])
        self.assertEqual(result["top_causes"][0]["type"], "CrashLoopBackOff")
        self.assertEqual(mocked_logs.call_count, 2)
        previous_excerpt = result["pods"][0]["logs"]["previous"]["excerpt"]
        self.assertIn("password=***", previous_excerpt)
        self.assertNotIn("super-secret", previous_excerpt)

    def test_image_pull_backoff_uses_events_without_log_call(self):
        pod = pod_fixture(
            status="Pending",
            phase="Pending",
            conditions=[{"type": "PodScheduled", "status": "True"}],
            containers=[
                {
                    "name": "app",
                    "image": "swr.example.com/demo/missing:notfound",
                    "ready": False,
                    "restart_count": 0,
                    "state_detail": {"type": "waiting", "reason": "ImagePullBackOff", "message": "back-off pulling image"},
                    "last_state_detail": {},
                }
            ],
        )
        events = [
            {
                "type": "Warning",
                "reason": "Failed",
                "message": "Failed to pull image: manifest unknown",
                "involved_object": {"kind": "Pod", "name": "demo-7c9d", "namespace": "default"},
            }
        ]

        with mock.patch("huawei_cloud.pod_diagnosis.cce.get_kubernetes_pods", return_value={"success": True, "pods": [pod]}), \
            mock.patch("huawei_cloud.pod_diagnosis.cce.get_kubernetes_events", return_value={"success": True, "events": events}), \
            mock.patch("huawei_cloud.pod_diagnosis.cce.get_pod_logs") as mocked_logs:
            result = pod_diagnosis.pod_failure_diagnose("cn-north-4", "cluster-1", namespace="default", pod_name="demo-7c9d")

        self.assertTrue(result["success"])
        self.assertEqual(result["top_causes"][0]["type"], "ImagePullBackOff")
        mocked_logs.assert_not_called()

    def test_pending_storage_is_detected_from_failed_mount_event(self):
        pod = pod_fixture(
            status="Pending",
            phase="Pending",
            conditions=[{"type": "PodScheduled", "status": "False", "reason": "Unschedulable"}],
            containers=[],
        )
        events = [
            {
                "type": "Warning",
                "reason": "FailedMount",
                "message": "MountVolume.SetUp failed for volume pvc-demo: timeout",
                "involved_object": {"kind": "Pod", "name": "demo-7c9d", "namespace": "default"},
            }
        ]

        diag = pod_diagnosis._diagnose_pod(pod, events)
        issue_types = {issue["type"] for issue in diag["issues"]}

        self.assertIn("PendingStorage", issue_types)

    def test_running_crashloop_with_successful_mount_is_not_storage_or_image_pull(self):
        events = [
            {
                "type": "Normal",
                "reason": "SuccessfulMountVolume",
                "message": "Successfully mounted volumes for pod demo",
                "involved_object": {"kind": "Pod", "name": "demo-7c9d", "namespace": "default"},
            },
            {
                "type": "Warning",
                "reason": "FailedStart",
                "message": "exec: \"aaa\": executable file not found in $PATH",
                "involved_object": {"kind": "Pod", "name": "demo-7c9d", "namespace": "default"},
            },
        ]

        diag = pod_diagnosis._diagnose_pod(pod_fixture(), events)
        issue_types = {issue["type"] for issue in diag["issues"]}

        self.assertIn("CrashLoopBackOff", issue_types)
        self.assertNotIn("PendingStorage", issue_types)
        self.assertNotIn("ImagePullBackOff", issue_types)


if __name__ == "__main__":
    unittest.main()
