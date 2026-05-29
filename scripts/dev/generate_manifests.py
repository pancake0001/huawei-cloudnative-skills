#!/usr/bin/env python3
"""Generate skill manifest.json files from skill-profile.yaml.

The generator is intentionally static: it reads dispatcher.py text instead of
importing Huawei SDK modules. This keeps the metadata workflow usable before
cloud SDK dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
DISPATCHER_PATH = REPO_ROOT / "scripts" / "huawei_cloud" / "dispatcher.py"
SCRIPT_PATH = "scripts/huawei-cloud.py"


@dataclass(frozen=True)
class ActionSpec:
    name: str
    required: tuple[str, ...]


@dataclass(frozen=True)
class SkillProfile:
    name: str
    level: str
    domain: str
    description: str
    tools: tuple[str, ...]
    references: tuple[str, ...]
    guardrails: dict[str, str]
    path: Path


def repo_root() -> Path:
    return REPO_ROOT


def parse_action_specs(dispatcher_path: Path = DISPATCHER_PATH) -> dict[str, ActionSpec]:
    text = dispatcher_path.read_text(encoding="utf-8")
    marker = "ACTION_SPECS"
    try:
        start = text.index(marker)
        body_start = text.index("{", start) + 1
        body_end = text.index("\n}\n\n\ndef is_registered_action", body_start)
    except ValueError as exc:
        raise RuntimeError("Cannot locate ACTION_SPECS in dispatcher.py") from exc

    body = text[body_start:body_end]
    pattern = re.compile(r'^\s*"(?P<name>huawei_[^"]+)":\s*\(\((?P<required>[^)]*)\),', re.MULTILINE)
    specs: dict[str, ActionSpec] = {}
    for match in pattern.finditer(body):
        required = tuple(re.findall(r'"([^"]+)"', match.group("required")))
        name = match.group("name")
        specs[name] = ActionSpec(name=name, required=required)
    if not specs:
        raise RuntimeError("No dispatcher actions found")
    return specs


def _parse_list(lines: list[str], start: int) -> tuple[list[str], int]:
    items: list[str] = []
    index = start
    while index < len(lines):
        raw = lines[index]
        if not raw.startswith("  ") and raw.strip():
            break
        stripped = raw.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip().strip('"').strip("'"))
        index += 1
    return items, index


def _parse_mapping(lines: list[str], start: int) -> tuple[dict[str, str], int]:
    data: dict[str, str] = {}
    index = start
    while index < len(lines):
        raw = lines[index]
        if not raw.startswith("  ") and raw.strip():
            break
        stripped = raw.strip()
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
        index += 1
    return data, index


def read_profile(path: Path) -> SkillProfile:
    lines = path.read_text(encoding="utf-8").splitlines()
    data: dict[str, object] = {}
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        index += 1
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = value.strip('"').strip("'")
            continue
        if key in {"tools", "references"}:
            data[key], index = _parse_list(lines, index)
        elif key == "guardrails":
            data[key], index = _parse_mapping(lines, index)
        else:
            data[key] = ""

    missing = [key for key in ("name", "level", "domain", "description", "tools") if not data.get(key)]
    if missing:
        raise ValueError(f"{path}: missing required profile fields: {', '.join(missing)}")

    return SkillProfile(
        name=str(data["name"]),
        level=str(data["level"]),
        domain=str(data["domain"]),
        description=str(data["description"]),
        tools=tuple(data.get("tools", [])),  # type: ignore[arg-type]
        references=tuple(data.get("references", [])),  # type: ignore[arg-type]
        guardrails=dict(data.get("guardrails", {})),  # type: ignore[arg-type]
        path=path,
    )


def discover_profiles(skills_dir: Path = SKILLS_DIR) -> list[SkillProfile]:
    profiles: list[SkillProfile] = []
    for profile_path in sorted(skills_dir.glob("*/skill-profile.yaml")):
        profiles.append(read_profile(profile_path))
    return profiles


def _param_description(name: str) -> str:
    descriptions = {
        "region": "Huawei Cloud region, for example cn-north-4.",
        "ak": "Access Key ID. Prefer HUAWEI_AK environment variable.",
        "sk": "Secret Access Key. Prefer HUAWEI_SK environment variable.",
        "project_id": "Huawei Cloud project ID. Prefer HUAWEI_PROJECT_ID environment variable.",
        "confirm": "Must be true only after explicit user confirmation.",
    }
    return descriptions.get(name, f"{name} parameter.")


def _param_schema(required: Iterable[str]) -> dict[str, object]:
    required_list = list(required)
    properties: dict[str, dict[str, str]] = {}
    for name in [*required_list, "ak", "sk", "project_id"]:
        if name not in properties:
            properties[name] = {"type": "string", "description": _param_description(name)}
    return {
        "type": "object",
        "properties": properties,
        "required": required_list,
    }


def build_manifest(profile: SkillProfile, action_specs: dict[str, ActionSpec]) -> dict[str, object]:
    missing = [tool for tool in profile.tools if tool not in action_specs]
    if missing:
        raise ValueError(f"{profile.path}: unknown dispatcher actions: {', '.join(missing)}")

    return {
        "version": "1.0.0",
        "name": profile.name,
        "description": profile.description,
        "level": profile.level,
        "domain": profile.domain,
        "tools": [
            {
                "name": tool,
                "description": f"Run {tool} through the shared Huawei Cloud dispatcher.",
                "parameters": _param_schema(action_specs[tool].required),
                "script": SCRIPT_PATH,
            }
            for tool in profile.tools
        ],
    }


def build_legacy_manifest(action_specs: dict[str, ActionSpec]) -> dict[str, object]:
    return {
        "version": "1.0.0",
        "name": "huawei-cloud",
        "description": "Aggregate Huawei Cloud operations skill backed by the shared dispatcher.",
        "tools": [
            {
                "name": spec.name,
                "description": f"Run {spec.name} through the shared Huawei Cloud dispatcher.",
                "parameters": _param_schema(spec.required),
                "script": SCRIPT_PATH,
            }
            for spec in action_specs.values()
        ],
    }


def _json_text(manifest: dict[str, object]) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def generated_targets(profiles: list[SkillProfile], action_specs: dict[str, ActionSpec]) -> dict[Path, str]:
    targets: dict[Path, str] = {}
    legacy_skill = SKILLS_DIR / "huawei-cloud"
    if legacy_skill.exists():
        targets[legacy_skill / "manifest.json"] = _json_text(build_legacy_manifest(action_specs))

    for profile in profiles:
        manifest_path = profile.path.parent / "manifest.json"
        targets[manifest_path] = _json_text(build_manifest(profile, action_specs))
    return targets


def run(check: bool = False) -> int:
    action_specs = parse_action_specs()
    profiles = discover_profiles()
    targets = generated_targets(profiles, action_specs)
    failures: list[str] = []

    for path, content in targets.items():
        if check:
            if not path.exists():
                failures.append(f"missing generated manifest: {path.relative_to(REPO_ROOT)}")
                continue
            current = path.read_text(encoding="utf-8")
            if current != content:
                failures.append(f"manifest out of date: {path.relative_to(REPO_ROOT)}")
            continue
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    if check:
        print("manifest check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated manifests without writing files.")
    args = parser.parse_args()
    return run(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())

