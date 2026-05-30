#!/usr/bin/env python3
"""Validate the simplified multi-skill structure."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path

from generate_manifests import (
    REPO_ROOT,
    SKILLS_DIR,
    build_manifest,
    discover_profiles,
    parse_action_specs,
)


FRONTMATTER_PATTERN = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PHASE_ONE_SKILLS = {
    "observability-context-builder",
    "alarm-correlation-engine",
    "pod-failure-diagnoser",
    "workload-failure-diagnoser",
    "node-failure-diagnoser",
    "network-failure-diagnoser",
    "root-cause-analyzer",
    "auto-remediation-runner",
    "daily-cluster-inspector",
    "cost-optimization-advisor",
    "capacity-trend-forecaster",
    "availability-risk-scanner",
    "container-migration-planner",
}


def _is_reparse_point(path: Path) -> bool:
    try:
        attrs = os.lstat(path).st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _same_target(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except OSError:
        return left.resolve() == right.resolve()


def _scripts_link_ok(skill_dir: Path) -> bool:
    link = skill_dir / "scripts"
    root_scripts = REPO_ROOT / "scripts"
    if not link.exists():
        return False
    if not (link.is_symlink() or _is_reparse_point(link)):
        return False
    return _same_target(link, root_scripts)


def _parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.search(text)
    if not match:
        raise ValueError("missing YAML frontmatter")
    data: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate() -> list[str]:
    errors: list[str] = []
    action_specs = parse_action_specs()
    profiles = discover_profiles()
    profile_by_name = {profile.name: profile for profile in profiles}

    catalog_path = SKILLS_DIR / "_catalog" / "skill-index.md"
    if not catalog_path.exists():
        errors.append("missing skills/_catalog/skill-index.md")
    elif (SKILLS_DIR / "_catalog" / "SKILL.md").exists():
        errors.append("skills/_catalog must not contain SKILL.md")

    missing_phase_one = sorted(PHASE_ONE_SKILLS - set(profile_by_name))
    if missing_phase_one:
        errors.append(f"missing phase-one skill profiles: {', '.join(missing_phase_one)}")

    for profile in profiles:
        skill_dir = profile.path.parent
        rel_skill = skill_dir.relative_to(REPO_ROOT)
        if skill_dir.name != profile.name:
            errors.append(f"{rel_skill}: profile name does not match directory")
        if not NAME_PATTERN.fullmatch(skill_dir.name):
            errors.append(f"{rel_skill}: skill name is not lowercase hyphen-case")
        if not profile.tools:
            errors.append(f"{rel_skill}: profile tools must not be empty")
        for tool in profile.tools:
            if tool not in action_specs:
                errors.append(f"{rel_skill}: unknown action {tool}")
        for reference in profile.references:
            if not (skill_dir / reference).exists():
                errors.append(f"{rel_skill}: missing reference {reference}")
        if not _scripts_link_ok(skill_dir):
            errors.append(f"{rel_skill}: scripts link is missing or does not point to repo scripts")
        copied_scripts = skill_dir / "scripts" / "huawei_cloud"
        if copied_scripts.exists() and not _scripts_link_ok(skill_dir):
            errors.append(f"{rel_skill}: scripts appears to be copied instead of linked")

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{rel_skill}: missing SKILL.md")
        else:
            try:
                frontmatter = _parse_frontmatter(skill_md)
            except ValueError as exc:
                errors.append(f"{rel_skill}/SKILL.md: {exc}")
            else:
                keys = set(frontmatter)
                if keys != {"name", "description"}:
                    errors.append(f"{rel_skill}/SKILL.md: frontmatter must contain only name and description")
                if frontmatter.get("name") != profile.name:
                    errors.append(f"{rel_skill}/SKILL.md: frontmatter name does not match profile")
                if not frontmatter.get("description"):
                    errors.append(f"{rel_skill}/SKILL.md: description is empty")

        manifest_path = skill_dir / "manifest.json"
        if not manifest_path.exists():
            errors.append(f"{rel_skill}: missing manifest.json")
        else:
            try:
                manifest = _json(manifest_path)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel_skill}/manifest.json: invalid JSON: {exc}")
            else:
                expected = build_manifest(profile, action_specs)
                manifest_tools = [tool.get("name") for tool in manifest.get("tools", [])]  # type: ignore[union-attr]
                expected_tools = [tool["name"] for tool in expected["tools"]]  # type: ignore[index]
                if manifest.get("name") != profile.name:
                    errors.append(f"{rel_skill}/manifest.json: name does not match profile")
                if manifest_tools != expected_tools:
                    errors.append(f"{rel_skill}/manifest.json: tools do not match skill-profile.yaml")
                for tool in manifest.get("tools", []):  # type: ignore[union-attr]
                    if tool.get("script") != "scripts/huawei-cloud.py":
                        errors.append(f"{rel_skill}/manifest.json: tool {tool.get('name')} uses wrong script path")

    for manifest_path in sorted(SKILLS_DIR.glob("*/manifest.json")):
        try:
            _json(manifest_path)
        except json.JSONDecodeError as exc:
            errors.append(f"{manifest_path.relative_to(REPO_ROOT)}: invalid JSON: {exc}")

    if catalog_path.exists():
        catalog = catalog_path.read_text(encoding="utf-8")
        for skill in sorted(PHASE_ONE_SKILLS):
            if skill not in catalog:
                errors.append(f"skills/_catalog/skill-index.md: missing {skill}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
