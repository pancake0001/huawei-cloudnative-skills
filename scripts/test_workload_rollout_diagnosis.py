#!/usr/bin/env python3
"""Unit tests for workload rollout diagnosis."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import workload_rollout_diagnosis as rollout  # noqa: E402


def deployment_context(**overrides):
    context = {
        "success": True,
        "region": "cn-north-4",
        "cluster_id": "cluster-1",
        "target": {"namespace": "default", "kind": "Deployment", "name": "api"},
        "workload": {
            "kind": "Deployment",
            "name": "api",
            "namespace": "default",
            "uid": "deploy-uid",
            "generation": 3,
            "observed_generation": 3,
            "desired_replicas": 2,
            "status_replicas": 2,
            "updated_replicas": 2,
            "ready_replicas": 2,
            "available_replicas": 2,
            "conditions": [],
        },
        "replicasets": [
            {
                "name": "api-old",
                "namespace": "default",
                "uid": "rs-old",
                "revision": 1,
                "desired_replicas": 0,
                "status_replicas": 0,
                "ready_replicas": 0,
                "owner_references": [{"kind": "Deployment", "name": "api", "uid": "deploy-uid"}],
                "created": "2026-05-29T01:00:00+00:00",
            },
            {
                "name": "api-new",
                "namespace": "default",
                "uid": "rs-new",
                "revision": 2,
                "desired_replicas": 2,
                "status_replicas": 2,
                "ready_replicas": 2,
                "owner_references": [{"kind": "Deployment", "name": "api", "uid": "deploy-uid"}],
                "created": "2026-05-29T02:00:00+00:00",
            },
        ],
        "pods": [
            {
                "name": "api-new-a",
                "namespace": "default",
                "uid": "pod-a",
                "phase": "Running",
                "status": "Running",
                "owner_references": [{"kind": "ReplicaSet", "name": "api-new", "uid": "rs-new"}],
                "conditions": [{"type": "Ready", "status": "True"}],
                "containers": [{"name": "app", "ready": True, "restart_count": 0, "state_detail": {"type": "running"}}],
                "init_containers": [],
            },
            {
                "name": "api-new-b",
                "namespace": "default",
                "uid": "pod-b",
                "phase": "Running",
                "status": "Running",
                "owner_references": [{"kind": "ReplicaSet", "name": "api-new", "uid": "rs-new"}],
                "conditions": [{"type": "Ready", "status": "True"}],
                "containers": [{"name": "app", "ready": True, "restart_count": 0, "state_detail": {"type": "running"}}],
                "init_containers": [],
            },
        ],
        "events": [],
        "event_filter": {"uid_count": 4, "before_count": 0, "after_count": 0},
    }
    context.update(overrides)
    return context


class WorkloadRolloutDiagnosisTests(unittest.TestCase):
    def test_filter_events_by_uid_keeps_only_related_and_sorts_descending(self):
        events = [
            {
                "event_time": "2026-05-29T01:00:00+00:00",
                "involved_object": {"uid": "pod-a", "kind": "Pod", "name": "api-a"},
            },
            {
                "event_time": "2026-05-29T03:00:00+00:00",
                "involved_object": {"uid": "other", "kind": "Pod", "name": "other"},
            },
            {
                "event_time": "2026-05-29T02:00:00+00:00",
                "involved_object": {"uid": "rs-new", "kind": "ReplicaSet", "name": "api-new"},
            },
            {
                "event_time": "2026-05-29T04:00:00+00:00",
                "involved_object": {"kind": "Pod", "name": "missing-uid"},
            },
        ]

        filtered, stats = rollout._filter_events_by_uid(events, ["pod-a", "rs-new"])

        self.assertEqual([e["involved_object"]["uid"] for e in filtered], ["rs-new", "pod-a"])
        self.assertEqual(stats["before_count"], 4)
        self.assertEqual(stats["after_count"], 2)
        self.assertEqual(stats["events_without_involved_uid"], 1)

    def test_pick_new_rs_uses_highest_deployment_revision(self):
        context = deployment_context()

        version = rollout._deployment_version(context)

        self.assertEqual(version["new_rs"]["name"], "api-new")
        self.assertEqual([pod["name"] for pod in version["new_pods"]], ["api-new-a", "api-new-b"])

    def test_generation_check_reports_control_plane_not_observed(self):
        context = deployment_context()
        context["workload"]["generation"] = 5
        context["workload"]["observed_generation"] = 4

        result = rollout.analyze_rollout_context(context, include_pod_diagnosis=False)

        self.assertEqual(result["summary"]["status"], "control_plane_not_observed")
        self.assertEqual(result["top_causes"][0]["type"], "ControlPlaneNotObserved")

    def test_failed_create_on_new_rs_reports_quota_or_admission_rejection(self):
        context = deployment_context(
            pods=[],
            replicasets=[
                {
                    "name": "api-new",
                    "namespace": "default",
                    "uid": "rs-new",
                    "revision": 3,
                    "desired_replicas": 2,
                    "status_replicas": 0,
                    "ready_replicas": 0,
                    "owner_references": [{"kind": "Deployment", "name": "api", "uid": "deploy-uid"}],
                    "created": "2026-05-29T02:00:00+00:00",
                }
            ],
            events=[
                {
                    "type": "Warning",
                    "reason": "FailedCreate",
                    "message": "pods is forbidden: exceeded quota: compute-resources",
                    "event_time": "2026-05-29T02:01:00+00:00",
                    "involved_object": {"kind": "ReplicaSet", "name": "api-new", "uid": "rs-new", "namespace": "default"},
                }
            ],
        )

        result = rollout.analyze_rollout_context(context, include_pod_diagnosis=False)

        self.assertEqual(result["summary"]["status"], "new_version_not_created")
        self.assertEqual(result["top_causes"][0]["type"], "QuotaOrAdmissionRejected")

    def test_running_not_ready_with_unhealthy_event_reports_probe_failure(self):
        context = deployment_context()
        context["workload"]["ready_replicas"] = 1
        context["workload"]["available_replicas"] = 1
        context["replicasets"][1]["ready_replicas"] = 1
        context["pods"][1]["conditions"] = [{"type": "Ready", "status": "False"}]
        context["pods"][1]["containers"][0]["ready"] = False
        context["events"] = [
            {
                "type": "Warning",
                "reason": "Unhealthy",
                "message": "Readiness probe failed: HTTP probe failed with statuscode: 500",
                "event_time": "2026-05-29T02:05:00+00:00",
                "involved_object": {"kind": "Pod", "name": "api-new-b", "uid": "pod-b", "namespace": "default"},
            }
        ]

        result = rollout.analyze_rollout_context(context, include_logs=False)

        self.assertEqual(result["summary"]["status"], "probe_failure")
        self.assertEqual(result["top_causes"][0]["type"], "ProbeFailure")
        self.assertEqual(result["pod_diagnosis"]["diagnosed_pods"], 1)

    def test_command_not_found_is_specific_top_cause_and_new_rs_desired_is_held(self):
        context = deployment_context()
        context["workload"].update({
            "status_replicas": 3,
            "updated_replicas": 1,
            "ready_replicas": 2,
            "available_replicas": 2,
        })
        context["replicasets"][1].update({
            "desired_replicas": 1,
            "status_replicas": 1,
            "ready_replicas": None,
        })
        context["pods"] = [
            {
                "name": "api-new-bad",
                "namespace": "default",
                "uid": "pod-bad",
                "phase": "Running",
                "status": "Running",
                "owner_references": [{"kind": "ReplicaSet", "name": "api-new", "uid": "rs-new"}],
                "conditions": [{"type": "Ready", "status": "False"}],
                "containers": [
                    {
                        "name": "app",
                        "image": "swr.example.com/demo/app:v2",
                        "ready": False,
                        "restart_count": 5,
                        "state_detail": {"type": "waiting", "reason": "CrashLoopBackOff", "message": "back-off"},
                        "last_state_detail": {
                            "type": "terminated",
                            "reason": "StartError",
                            "message": "exec: \"missing-binary\": executable file not found in $PATH",
                            "exit_code": 128,
                        },
                    }
                ],
                "init_containers": [],
            }
        ]
        context["events"] = [
            {
                "type": "Warning",
                "reason": "FailedStart",
                "message": "exec: \"missing-binary\": executable file not found in $PATH",
                "event_time": "2026-05-29T02:05:00+00:00",
                "involved_object": {"kind": "Pod", "name": "api-new-bad", "uid": "pod-bad", "namespace": "default"},
            }
        ]

        result = rollout.analyze_rollout_context(context, include_logs=False)
        new_rs_desired = next(layer for layer in result["funnel"] if layer["layer"] == "new_rs_desired")

        self.assertEqual(result["top_causes"][0]["type"], "ContainerCommandNotFound")
        self.assertIn("旧版本副本仍保持可用", result["summary"]["headline"])
        self.assertEqual(new_rs_desired["status"], "held")

    def test_statefulset_updated_replicas_shortfall_reports_rollout_blocked(self):
        context = {
            "workload": {
                "kind": "StatefulSet",
                "name": "db",
                "namespace": "default",
                "uid": "sts-uid",
                "generation": 4,
                "observed_generation": 4,
                "desired_replicas": 3,
                "status_replicas": 3,
                "updated_replicas": 1,
                "ready_replicas": 1,
                "available_replicas": 1,
                "current_revision": "db-1",
                "update_revision": "db-2",
                "conditions": [],
            },
            "pods": [],
            "events": [],
        }

        result = rollout.analyze_rollout_context(context, include_pod_diagnosis=False)

        self.assertEqual(result["summary"]["status"], "rollout_blocked")
        self.assertEqual(result["top_causes"][0]["type"], "RolloutBlocked")


if __name__ == "__main__":
    unittest.main()
