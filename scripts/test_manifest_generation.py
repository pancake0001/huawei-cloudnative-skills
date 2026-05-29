#!/usr/bin/env python3
"""Tests for manifest generation."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR / "dev"))

from generate_manifests import build_manifest, discover_profiles, parse_action_specs  # noqa: E402


class ManifestGenerationTests(unittest.TestCase):
    def test_all_manifests_are_valid_json(self):
        manifests = sorted((REPO_ROOT / "skills").glob("*/manifest.json"))
        self.assertTrue(manifests)
        for manifest_path in manifests:
            with self.subTest(manifest=manifest_path):
                with manifest_path.open(encoding="utf-8") as handle:
                    json.load(handle)

    def test_generated_manifest_tools_match_profiles(self):
        action_specs = parse_action_specs()
        for profile in discover_profiles():
            manifest = json.loads((profile.path.parent / "manifest.json").read_text(encoding="utf-8"))
            expected = build_manifest(profile, action_specs)
            self.assertEqual(
                [tool["name"] for tool in manifest["tools"]],
                [tool["name"] for tool in expected["tools"]],
            )

    def test_check_mode_passes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "dev" / "generate_manifests.py"), "--check"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

