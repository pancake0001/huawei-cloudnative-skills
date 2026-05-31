#!/bin/bash
SKILLS_SRC="$(dirname "$0")"
SKILL_DIR="$SKILLS_SRC/skills"

mkdir -p "$SKILL_DIR"

for category in devtools; do
  for skill_dir in "$SKILLS_SRC/$category"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    cp -r "$skill_dir" "$SKILL_DIR/"
    echo "  [OK] $skill_name"
  done
done

for category in cce cci swr ucs; do
  for skill_dir in "$SKILLS_SRC/container/$category"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    cp -r "$skill_dir" "$SKILL_DIR/"
    echo "  [OK] $skill_name"
  done
done

echo ""
echo "=== Copied skills ==="
find "$SKILL_DIR" -maxdepth 1 -type d | sort

echo ""
echo "=== Ready to build ==="
echo "docker build -t aicli:with-skills $SKILLS_SRC"