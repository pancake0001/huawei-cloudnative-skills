#!/usr/bin/env python3
"""Tests for storage failure diagnosis decisions and Markdown reports."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import storage_failure_diagnosis as diagnosis  # noqa: E402


def base_snapshot(**overrides):
    snapshot = {
        "inputs": {
            "region": "cn-north-4",
            "cluster_id": "cluster-1",
            "namespace": "prod",
            "pvc_name": "data",
            "pod_name": "app-0",
            "failure_symptom": "应用写入正常",
        },
        "collected_at": "2026-05-30T10:00:00+00:00",
        "pvcs": [
            {
                "name": "data",
                "namespace": "prod",
                "status": "Bound",
                "volume": "pv-data",
                "storage_class": "csi-disk",
                "capacity": {"storage": "10Gi"},
                "requested": {"storage": "10Gi"},
                "finalizers": [],
            }
        ],
        "pvs": [
            {
                "name": "pv-data",
                "status": "Bound",
                "storage_class": "csi-disk",
                "capacity": {"storage": "10Gi"},
                "claim_ref": {"namespace": "prod", "name": "data"},
                "source": {"type": "csi", "driver": "disk.csi.everest.io", "volume_handle": "vol-1"},
                "node_affinity": {
                    "required": [
                        {
                            "match_expressions": [
                                {"key": "topology.kubernetes.io/zone", "operator": "In", "values": ["cn-north-4a"]}
                            ],
                            "match_fields": [],
                        }
                    ]
                },
            }
        ],
        "storage_classes": [
            {
                "name": "csi-disk",
                "provisioner": "everest-csi-provisioner",
                "parameters": {"everest.io/disk-volume-type": "SAS"},
                "volume_binding_mode": "Immediate",
            }
        ],
        "pods": [
            {
                "name": "app-0",
                "namespace": "prod",
                "phase": "Running",
                "node": "node-a",
                "volumes": [{"name": "data", "pvc": "data"}],
                "volume_mounts": [{"name": "data", "mount_path": "/data", "source": {"pvc": "data"}}],
                "containers": [{"name": "app", "ready": True, "restart_count": 0}],
                "tolerations": [],
            }
        ],
        "nodes": [
            {
                "name": "node-a",
                "ready": "True",
                "labels": {"topology.kubernetes.io/zone": "cn-north-4a", "kubernetes.io/hostname": "node-a"},
                "conditions": [{"type": "Ready", "status": "True"}],
                "taints": [],
            }
        ],
        "events": [],
        "volume_attachments": [],
        "network_policies": [],
        "node_stats": {},
        "pvc_volume_stats": [],
        "csi_logs": {},
        "cloud_storage": {},
    }
    snapshot.update(overrides)
    return snapshot


class StorageFailureDiagnosisTests(unittest.TestCase):
    def test_wait_for_first_consumer_without_pod_is_normal_behavior(self):
        snapshot = base_snapshot(
            pvcs=[{"name": "data", "namespace": "prod", "status": "Pending", "volume": None, "storage_class": "csi-disk"}],
            pvs=[],
            pods=[],
            storage_classes=[{"name": "csi-disk", "provisioner": "everest", "volume_binding_mode": "WaitForFirstConsumer", "parameters": {}}],
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "NormalWaitForFirstConsumer")
        self.assertEqual(assessment["confidence"], "高 (High)")

    def test_evs_quota_exceeded_is_reported_from_failed_provisioning(self):
        snapshot = base_snapshot(
            pvcs=[{"name": "data", "namespace": "prod", "status": "Pending", "volume": None, "storage_class": "csi-disk"}],
            pvs=[],
            pods=[],
            events=[
                {
                    "reason": "FailedProvisioning",
                    "message": "Create EVS volume failed: QuotaExceeded",
                    "involved_object": {"kind": "PersistentVolumeClaim", "name": "data", "namespace": "prod"},
                }
            ],
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "EVSQuotaExceeded")

    def test_local_pv_node_offline_is_highest_confidence(self):
        snapshot = base_snapshot(
            pvs=[
                {
                    "name": "pv-data",
                    "status": "Bound",
                    "storage_class": "local",
                    "source": {"type": "local", "path": "/mnt/data"},
                    "node_affinity": {"required": [{"match_fields": [{"key": "metadata.name", "operator": "In", "values": ["node-a"]}], "match_expressions": []}]},
                }
            ],
            storage_classes=[{"name": "local", "provisioner": "kubernetes.io/no-provisioner", "parameters": {}, "volume_binding_mode": "WaitForFirstConsumer"}],
            pods=[
                {
                    "name": "app-0",
                    "namespace": "prod",
                    "phase": "Pending",
                    "node": None,
                    "volumes": [{"name": "data", "pvc": "data"}],
                    "volume_mounts": [],
                    "containers": [],
                    "tolerations": [],
                }
            ],
            nodes=[{"name": "node-a", "ready": "False", "labels": {"kubernetes.io/hostname": "node-a"}, "conditions": [{"type": "Ready", "status": "False"}], "taints": []}],
            events=[
                {
                    "reason": "FailedScheduling",
                    "message": "0/1 nodes are available: node(s) had volume node affinity conflict.",
                    "involved_object": {"kind": "Pod", "name": "app-0", "namespace": "prod"},
                }
            ],
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "LocalPVNodeOffline")
        self.assertEqual(assessment["top_causes"][0]["confidence"], 1.0)

    def test_evs_attach_limit_is_reported_from_volume_attachment(self):
        snapshot = base_snapshot(
            pods=[
                {
                    "name": "app-0",
                    "namespace": "prod",
                    "phase": "Pending",
                    "node": "node-a",
                    "volumes": [{"name": "data", "pvc": "data"}],
                    "volume_mounts": [{"name": "data", "mount_path": "/data", "source": {"pvc": "data"}}],
                    "containers": [{"name": "app", "waiting_reason": "ContainerCreating"}],
                    "tolerations": [],
                }
            ],
            volume_attachments=[
                {
                    "name": "va-1",
                    "volume_name": "pv-data",
                    "node_name": "node-a",
                    "attached": False,
                    "attach_error": {"message": "exceeded max volume attach limit"},
                }
            ],
            events=[
                {
                    "reason": "FailedAttachVolume",
                    "message": "AttachVolume.Attach failed for volume pv-data",
                    "involved_object": {"kind": "Pod", "name": "app-0", "namespace": "prod"},
                }
            ],
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "EVSNodeAttachLimitExceeded")

    def test_sfs_mount_timeout_reports_network_block(self):
        snapshot = base_snapshot(
            pvs=[
                {
                    "name": "pv-data",
                    "status": "Bound",
                    "storage_class": "csi-nas",
                    "source": {"type": "nfs", "server": "10.0.0.10", "path": "/"},
                    "node_affinity": {},
                }
            ],
            storage_classes=[{"name": "csi-nas", "provisioner": "everest-csi-provisioner", "parameters": {"type": "sfs"}, "volume_binding_mode": "Immediate"}],
            pods=[
                {
                    "name": "app-0",
                    "namespace": "prod",
                    "phase": "Pending",
                    "node": "node-a",
                    "volumes": [{"name": "data", "pvc": "data"}],
                    "volume_mounts": [],
                    "containers": [{"name": "app", "waiting_reason": "ContainerCreating"}],
                    "tolerations": [],
                }
            ],
            events=[
                {
                    "reason": "FailedMount",
                    "message": "MountVolume.SetUp failed: mount.nfs: connection timed out",
                    "involved_object": {"kind": "Pod", "name": "app-0", "namespace": "prod"},
                }
            ],
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "SFSNfsNetworkBlocked")

    def test_obs_403_in_csi_logs_reports_credential_failure(self):
        snapshot = base_snapshot(
            pvs=[
                {
                    "name": "pv-data",
                    "status": "Bound",
                    "storage_class": "csi-obs",
                    "source": {"type": "csi", "driver": "obs.csi.everest.io", "volume_handle": "bucket-a"},
                    "node_affinity": {},
                }
            ],
            storage_classes=[{"name": "csi-obs", "provisioner": "everest-csi-provisioner", "parameters": {"type": "obs"}, "volume_binding_mode": "Immediate"}],
            pods=[
                {
                    "name": "app-0",
                    "namespace": "prod",
                    "phase": "Pending",
                    "node": "node-a",
                    "volumes": [{"name": "data", "pvc": "data"}],
                    "volume_mounts": [],
                    "containers": [{"name": "app", "waiting_reason": "ContainerCreating"}],
                    "tolerations": [],
                }
            ],
            events=[
                {
                    "reason": "FailedMount",
                    "message": "MountVolume.SetUp failed for OBS volume",
                    "involved_object": {"kind": "Pod", "name": "app-0", "namespace": "prod"},
                }
            ],
            csi_logs={"kube-system/everest-csi-driver:driver": {"success": True, "excerpt": "obs mount failed: 403 SignatureDoesNotMatch"}},
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "OBSCredentialInvalid")

    def test_obs_invalid_ak_event_reports_credential_failure(self):
        snapshot = base_snapshot(
            pvs=[
                {
                    "name": "pv-data",
                    "status": "Bound",
                    "storage_class": "csi-obs",
                    "source": {"type": "csi", "driver": "obs.csi.everest.io", "volume_handle": "bucket-a"},
                    "node_affinity": {},
                }
            ],
            storage_classes=[{"name": "csi-obs", "provisioner": "everest-csi-provisioner", "parameters": {"type": "obs"}, "volume_binding_mode": "Immediate"}],
            pods=[
                {
                    "name": "app-0",
                    "namespace": "prod",
                    "phase": "Pending",
                    "node": "node-a",
                    "volumes": [{"name": "data", "pvc": "data"}],
                    "volume_mounts": [],
                    "containers": [{"name": "app", "waiting_reason": "ContainerCreating"}],
                    "tolerations": [],
                }
            ],
            events=[
                {
                    "reason": "FailedMount",
                    "message": "MountVolume.SetUp failed: failed to save temporary ak sk file: obsfs: ak size is invalid. obsfs: fuse_opt_parse fail",
                    "involved_object": {"kind": "Pod", "name": "app-0", "namespace": "prod"},
                }
            ],
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "OBSCredentialInvalid")
        evidence = assessment["top_causes"][0]["evidence"][0]
        self.assertIn("ak size is invalid", evidence["matched_errors"])

    def test_capacity_exhaustion_uses_kubelet_volume_stats(self):
        snapshot = base_snapshot(
            pvc_volume_stats=[
                {
                    "node": "node-a",
                    "pvc": {"namespace": "prod", "name": "data"},
                    "used_bytes": 980,
                    "capacity_bytes": 1000,
                    "usage_ratio": 0.98,
                }
            ]
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "PVCCapacityExhausted")

    def test_pvc_protection_reports_residual_pod(self):
        snapshot = base_snapshot(
            pvcs=[
                {
                    "name": "data",
                    "namespace": "prod",
                    "status": "Bound",
                    "volume": "pv-data",
                    "storage_class": "csi-disk",
                    "deletion_timestamp": "2026-05-30T10:00:00Z",
                    "finalizers": ["kubernetes.io/pvc-protection"],
                }
            ]
        )

        assessment = diagnosis.assess_storage_snapshot(snapshot)

        self.assertEqual(assessment["top_causes"][0]["type"], "PVCProtectionBlocked")

    def test_markdown_report_contains_required_sections(self):
        snapshot = base_snapshot()
        assessment = diagnosis.assess_storage_snapshot(snapshot)
        report = diagnosis.build_markdown_report(snapshot, assessment)

        for title in [
            "# CCE 存储故障自动化诊断报告",
            "## 1. 诊断总览",
            "## 2. 排查过程",
            "## 3. 关键对象关系",
            "## 4. 证据矩阵",
            "## 5. 诊断结论",
            "## 6. 建议动作与验证标准",
            "## 7. 数据缺口与人工确认",
        ]:
            self.assertIn(title, report)


if __name__ == "__main__":
    unittest.main()
