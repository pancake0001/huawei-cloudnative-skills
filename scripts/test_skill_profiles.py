#!/usr/bin/env python3
"""Tests for phase-one skill profiles and catalog coverage."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR / "dev"))

from generate_manifests import discover_profiles, parse_action_specs  # noqa: E402
from validate_skills import PHASE_ONE_SKILLS  # noqa: E402


HIGH_RISK_ACTIONS = {
    "huawei_delete_cce_cluster",
    "huawei_delete_cce_node",
    "huawei_resize_cce_nodepool",
    "huawei_scale_cce_workload",
    "huawei_resize_cce_workload",
    "huawei_delete_cce_workload",
    "huawei_hibernate_cce_cluster",
    "huawei_awake_cce_cluster",
    "huawei_cce_node_cordon",
    "huawei_cce_node_uncordon",
    "huawei_cce_node_drain",
    "huawei_reboot_ecs",
    "huawei_stop_ecs_instance",
    "huawei_hss_change_vul_status",
    "huawei_configure_cce_hpa",
}


class SkillProfileTests(unittest.TestCase):
    def test_phase_one_profiles_exist(self):
        profile_names = {profile.name for profile in discover_profiles()}
        self.assertEqual(PHASE_ONE_SKILLS - profile_names, set())

    def test_profile_actions_exist_in_dispatcher(self):
        action_specs = parse_action_specs()
        for profile in discover_profiles():
            with self.subTest(profile=profile.name):
                self.assertTrue(profile.tools)
                self.assertEqual([tool for tool in profile.tools if tool not in action_specs], [])

    def test_catalog_covers_phase_one_skills(self):
        catalog = (REPO_ROOT / "skills" / "_catalog" / "skill-index.md").read_text(encoding="utf-8")
        for skill in PHASE_ONE_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, catalog)

    def test_high_risk_actions_are_only_in_remediation_skill(self):
        allowed = {"auto-remediation-runner", "cost-optimization-advisor"}
        for profile in discover_profiles():
            risky = HIGH_RISK_ACTIONS.intersection(profile.tools)
            if profile.name not in allowed:
                self.assertEqual(risky, set(), profile.name)

    def test_remediation_skill_documents_preview_first(self):
        skill_dir = REPO_ROOT / "skills" / "auto-remediation-runner"
        text = "\n".join(
            [
                (skill_dir / "SKILL.md").read_text(encoding="utf-8"),
                (skill_dir / "references" / "risk-rules.md").read_text(encoding="utf-8"),
            ]
        )
        self.assertIn("confirm=true", text)
        self.assertIn("预览", text)
        self.assertIn("禁止自动", text)

    def test_cost_optimization_skill_documents_core_rules(self):
        skill_dir = REPO_ROOT / "skills" / "cost-optimization-advisor"
        text = "\n".join(
            [
                (skill_dir / "SKILL.md").read_text(encoding="utf-8"),
                (skill_dir / "references" / "workflow.md").read_text(encoding="utf-8"),
                (skill_dir / "references" / "risk-rules.md").read_text(encoding="utf-8"),
            ]
        )
        self.assertIn("24 小时", text)
        self.assertIn("7 天", text)
        self.assertIn("30%", text)
        self.assertIn("kube-system", text)
        self.assertIn("HPA", text)
        self.assertIn("autoscaler", text)
        self.assertIn("huawei_analyze_cce_cost_optimization", text)
        self.assertIn("huawei_list_cce_hpas", text)
        self.assertIn("huawei_generate_cce_hpa_manifest", text)
        self.assertIn("huawei_configure_cce_hpa", text)


if __name__ == "__main__":
    unittest.main()
