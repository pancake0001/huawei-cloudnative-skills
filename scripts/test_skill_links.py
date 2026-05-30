#!/usr/bin/env python3
"""Tests for per-skill scripts symlinks/Junctions."""

from __future__ import annotations

import os
import stat
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PHASE_ONE_SKILLS = {
    "observability-context-builder",
    "alarm-correlation-engine",
    "pod-failure-diagnoser",
    "node-failure-diagnoser",
    "network-failure-diagnoser",
    "storage-failure-diagnoser",
    "root-cause-analyzer",
    "auto-remediation-runner",
    "daily-cluster-inspector",
    "cost-optimization-advisor",
    "capacity-trend-forecaster",
    "availability-risk-scanner",
    "container-migration-planner",
    "cce-cci-bursting-deployer",
}


def skill_dirs() -> list[Path]:
    return [
        path
        for path in sorted((REPO_ROOT / "skills").iterdir())
        if path.is_dir() and path.name != "_catalog" and (path / "SKILL.md").exists()
    ]


def is_reparse_point(path: Path) -> bool:
    try:
        attrs = os.lstat(path).st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


class SkillLinkTests(unittest.TestCase):
    def test_phase_one_skill_scripts_are_links(self):
        target = REPO_ROOT / "scripts"
        self.assertEqual(PHASE_ONE_SKILLS - {path.name for path in skill_dirs()}, set())
        for skill_dir in skill_dirs():
            link = skill_dir / "scripts"
            with self.subTest(skill=skill_dir.name):
                self.assertTrue(link.exists(), f"{link} missing")
                self.assertTrue(link.is_symlink() or is_reparse_point(link), f"{link} is not a link")
                self.assertTrue(os.path.samefile(link, target), f"{link} does not point to {target}")

    def test_scripts_were_not_copied_into_skills(self):
        for skill_dir in skill_dirs():
            scripts_dir = skill_dir / "scripts"
            copied_package = scripts_dir / "huawei_cloud"
            with self.subTest(skill=skill_dir.name):
                if copied_package.exists():
                    self.assertTrue(scripts_dir.is_symlink() or is_reparse_point(scripts_dir))


if __name__ == "__main__":
    unittest.main()
