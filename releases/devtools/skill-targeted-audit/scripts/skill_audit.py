#!/usr/bin/env python3
"""Skill Targeted Audit — skillcheck + markdownlint-cli2 + cisco-ai-skill-scanner + gitleaks"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# 导入华为云规范检查
sys.path.insert(0, str(Path(__file__).parent))
from hwcloud_spec_check import run_hwcloud_spec_check

# ── CLI ──

def parse_args():
    p = argparse.ArgumentParser(description="Skill gate audit")
    p.add_argument("--target", required=True, help="Single skill dir or parent folder of skills")
    p.add_argument("--output-dir", default=None, help="Report output dir (default: parent of target)")
    p.add_argument("--skillcheck", default="skillcheck", help="skillcheck binary path")
    p.add_argument("--markdownlint", default="markdownlint-cli2", help="markdownlint-cli2 binary path")
    p.add_argument("--skill-scanner", default="skill-scanner", help="skill-scanner binary path")
    p.add_argument("--gitleaks", default="gitleaks", help="gitleaks binary path")
    p.add_argument("--node-bin", default="", help="Node bin dir for npx (e.g. /opt/nvm/versions/node/v18.20.8/bin)")
    p.add_argument("--no-install", action="store_true", help="Skip auto-install of tools")
    return p.parse_args()

# ── Auto-install ──

def ensure_tools(no_install=False):
    """Auto-install missing tools. Skip if --no-install."""
    if no_install:
        return
    # skillcheck + skill-scanner (pip)
    for pkg, cli in [("skillcheck", "skillcheck"), ("cisco-ai-skill-scanner", "skill-scanner")]:
        if not shutil.which(cli):
            print(f"  Auto-installing {pkg} ...", flush=True)
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=False)
    # markdownlint-cli2 (npm)
    if not shutil.which("markdownlint-cli2"):
        print("  Auto-installing markdownlint-cli2 ...", flush=True)
        subprocess.run(["npm", "install", "-g", "markdownlint-cli2"], check=False)
    # gitleaks (download binary)
    if not shutil.which("gitleaks"):
        print("  Auto-installing gitleaks ...", flush=True)
        _install_gitleaks()

# ── Discover skills ──

def discover_skills(target: Path):
    """Return list of skill dirs. If target itself has SKILL.md → [target], else find subdirs with SKILL.md."""
    if (target / "SKILL.md").exists():
        return [target]
    skills = sorted([d for d in target.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
    return skills

# ── Run checks ──

def run_cmd(cmd, timeout=120):
    """Run command with timeout. On Linux uses timeout --signal=KILL, on Windows uses subprocess timeout."""
    import platform
    if platform.system() == "Windows":
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
            return r.stdout + r.stderr, r.returncode
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out", 137
    else:
        try:
            shell_cmd = f"timeout --signal=KILL {timeout} " + " ".join(shlex.quote(c) for c in cmd)
            r = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True)
            return r.stdout + r.stderr, r.returncode
        except FileNotFoundError:
            return f"ERROR: command not found: {cmd[0]}", 127

def run_skillcheck(target: Path, skillcheck_bin: str):
    """Run skillcheck on target, return parsed results."""
    config = target / "skillcheck.toml"
    cmd = [skillcheck_bin, str(target)]
    if config.exists():
        cmd += ["--config", str(config)]
    cmd += ["--format", "json"]
    out, rc = run_cmd(cmd)
    try:
        data = json.loads(out)
        return data
    except Exception:
        # fallback: run text format
        cmd2 = [skillcheck_bin, str(target)]
        if config.exists():
            cmd2 += ["--config", str(config)]
        out2, rc2 = run_cmd(cmd2)
        return {"raw_text": out2, "parse_error": True}

def run_markdownlint(target: Path, markdownlint_bin: str, node_bin: str):
    """Run markdownlint-cli2 on target, return raw output."""
    config = target / ".markdownlint.json"
    ml = os.path.join(node_bin, markdownlint_bin) if node_bin else markdownlint_bin
    # Use absolute glob to avoid scanning parent dir
    glob_pattern = str(target / "**" / "*.md")
    cmd = [ml, glob_pattern, "--config", str(config)] if config.exists() else [ml, glob_pattern]
    out, rc = run_cmd(cmd, timeout=60)
    return out, rc

def run_skill_scanner(skill_dir: Path, scanner_bin: str):
    """Run skill-scanner scan on a single skill dir, return parsed JSON."""
    cmd = [scanner_bin, "scan", str(skill_dir), "--format", "json"]
    out, rc = run_cmd(cmd, timeout=15)
    if "Killed" in out or rc == 137:
        return {"raw_text": "TIMEOUT (killed by timeout wrapper)", "parse_error": True}
    try:
        data = json.loads(out)
        return data
    except Exception:
        return {"raw_text": out, "parse_error": True}

def _install_gitleaks():
    """Download and install gitleaks binary."""
    import platform, tempfile, tarfile
    arch = "arm64" if platform.machine() in ("aarch64", "arm64") else "amd64"
    version = "8.25.1"
    filename = f"gitleaks_{version}_linux_{arch}.tar.gz"
    mirrors = [
        f"https://gh-proxy.com/https://github.com/gitleaks/gitleaks/releases/download/v{version}/{filename}",
        f"https://gh.ddlc.top/https://github.com/gitleaks/gitleaks/releases/download/v{version}/{filename}",
    ]
    for url in mirrors:
        try:
            tmp = tempfile.mktemp(suffix=".tar.gz")
            r = subprocess.run(["curl", "-fsSL", "-o", tmp, url, "--connect-timeout", "10", "-m", "120"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                continue
            with tarfile.open(tmp, "r:gz") as tf:
                tf.extractall(path="/usr/local/bin")
            os.unlink(tmp)
            if shutil.which("gitleaks"):
                print("  gitleaks installed successfully", flush=True)
                return
        except Exception:
            continue
    print("  WARNING: gitleaks auto-install failed; install manually from https://github.com/gitleaks/gitleaks/releases", flush=True)

def run_gitleaks(skill_dir: Path, gitleaks_bin: str):
    """Run gitleaks detect on a single skill dir (--no-git mode), return parsed JSON."""
    # Use a temp file for JSON report to avoid stdout noise
    import tempfile
    report_file = tempfile.mktemp(suffix=".json")
    cmd = [gitleaks_bin, "detect", "--source", str(skill_dir),
           "--no-banner", "--no-git",
           "--report-format", "json", "--report-path", report_file]
    out, rc = run_cmd(cmd, timeout=30)
    try:
        with open(report_file, "r", encoding="utf-8") as f:
            findings = json.load(f)
        os.unlink(report_file)
        return {"findings": findings, "leaks_found": len(findings) > 0}
    except Exception:
        # Clean up temp file if it exists
        if os.path.exists(report_file):
            os.unlink(report_file)
        return {"findings": [], "leaks_found": False, "raw_text": out, "parse_error": True}

# ── Parse markdownlint output ──

def parse_markdownlint(raw: str):
    """Parse markdownlint-cli2 text output into structured list."""
    issues = []
    # pattern: filepath:line:col MDxxx/rule-name Description
    # Use (.*) not (.+) for description — some messages are empty or truncated
    pat = re.compile(r'^(.+?):(\d+):?(\d+)?\s+(?:error\s+|warning\s+)?(MD\d+/\S+)\s+(.*)$', re.MULTILINE)
    for m in pat.finditer(raw):
        issues.append({
            "file": m.group(1),
            "line": int(m.group(2)),
            "col": int(m.group(3)) if m.group(3) else 0,
            "rule": m.group(4),
            "message": m.group(5).strip(),
        })
    return issues

# ── Fix strategies ──

FIX_STRATEGIES = {
    # skillcheck
    "description.quality-score": "Start description with action verb (Generates/Analyzes/Validates); add trigger context like 'Use this skill whenever...'",
    "disclosure.metadata-budget": "Move non-essential frontmatter fields to the body section to reduce token count below 100",
    "disclosure.body-bloat": "Move large tables (>20 rows) to a referenced file under references/ directory",
    "frontmatter.field.unknown": "Add field to skillcheck.toml extension_fields, or remove from frontmatter",
    "compat.unverified": "Document field behavior for codex/cursor or remove unverified fields from frontmatter",
    # markdownlint
    "MD013": "Break long lines; or disable for code blocks/tables in .markdownlint.json: MD013: {code_blocks: false, tables: false}",
    "MD036": "Replace **text** pseudo-headings with ### text real headings",
    "MD031": "Add blank lines before and after fenced code blocks",
    "MD007": "Fix list indentation to match configured indent (default 4 spaces)",
    "MD024": "Add distinguishing suffix to duplicate headings, or enable siblings_only in config",
    # skill-scanner
    "command_injection": "Move dangerous commands (nc, curl|sh, etc.) to standalone scripts under scripts/; reference script path in SKILL.md instead of inline code",
    "reverse_shell": "Remove or relocate reverse shell examples; if needed for documentation, add <!-- skill-scanner:ignore --> annotation",
    "credential_leak": "Replace hardcoded secrets with environment variable references (${VAR}); add to .secrets.baseline if false positive",
    "dangerous_function": "Wrap eval()/exec() calls with input validation; consider safer alternatives like ast.literal_eval()",
    "prompt_injection": "Review and sanitize user-controllable input before embedding in prompts; use structured input templates",
    # gitleaks
    "generic-api-key": "Replace hardcoded API key/secret with environment variable reference (${VAR} or os.environ.get()); add to .gitleaksignore if false positive",
    "private-key": "Remove hardcoded private key; load from file or secret manager at runtime; add key file to .gitignore",
    "gitleaks": "Replace hardcoded credential with environment variable or secret manager reference; see https://gitleaks.io/docs/secrets for rule-specific remediation",
    # 华为云规范
    "frontmatter": "检查 SKILL.md YAML frontmatter 格式：必需字段(name/description/tags/version)、类型正确、name与目录名一致",
    "section": "按华为云规范补充正文章节：概述、前置条件、核心命令、参数确认、参考文档为必需章节",
    "size": "SKILL.md 建议在500行内，技能目录总大小建议在5MB内，超限时拆分内容到 references/ 子目录",
}

def get_fix_strategy(rule_or_category: str) -> str:
    if rule_or_category in FIX_STRATEGIES:
        return FIX_STRATEGIES[rule_or_category]
    prefix = rule_or_category.split("/")[0].split("_")[0]
    for key in FIX_STRATEGIES:
        if key.lower() == prefix.lower():
            return FIX_STRATEGIES[key]
    return "Review the issue and apply best practices for this category"

# ── Build report ──

def build_report(target: Path, skills: list, sc_data, md_raw, md_rc, md_issues, scanner_results, hwcloud_results=None, gitleaks_results=None):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    L = []
    def a(s=""): L.append(s)

    a("=" * 72)
    a("  Skill Gate Audit Report")
    a(f"  Scan target: {target}")
    a(f"  Skills scanned: {len(skills)}")
    a(f"  Generated: {now}")
    a("=" * 72)
    a()

    # ── Section 1: Scanned Skills ──
    a("── 1. Scanned Skills ──")
    a()
    for s in skills:
        a(f"  ✔ {s.name}")
    a()

    # ── Collect all issues by severity ──
    critical_issues = []
    error_issues = []
    warning_issues = []
    # NOTE: info_issues collected but NOT written to report per user requirement

    # skillcheck issues
    sc_pass = True
    if sc_data and not sc_data.get("parse_error"):
        for r in sc_data.get("results", []):
            skill_name = Path(r["path"]).parent.name if "/" in r["path"] else r["path"]
            for d in r.get("diagnostics", []):
                sev = d.get("severity", "info")
                issue = {"skill": skill_name, "source": "skillcheck", "rule": d["rule"], "severity": sev, "message": d["message"]}
                if sev == "warning":
                    warning_issues.append(issue)
                elif sev == "info":
                    pass  # skip INFO
                else:
                    error_issues.append(issue)
        if sc_data.get("files_failed", 0) > 0:
            sc_pass = False

    # markdownlint issues
    md_pass = md_rc == 0
    for iss in md_issues:
        rule_prefix = iss["rule"].split("/")[0]
        issue = {"skill": iss["file"], "source": "markdownlint", "rule": iss["rule"], "severity": "error",
                 "message": iss["message"], "line": iss["line"], "rule_prefix": rule_prefix}
        error_issues.append(issue)

    # skill-scanner issues
    scanner_pass = True
    for sr in scanner_results:
        skill_name = sr.get("skill_name", "")
        if not sr.get("is_safe", True):
            scanner_pass = False
        for f in sr.get("findings", []):
            sev_raw = f.get("severity", "CRITICAL").lower()
            issue = {"skill": skill_name, "source": "skill-scanner", "rule": f.get("rule_id", ""),
                     "severity": sev_raw, "category": f.get("category", ""),
                     "message": f.get("description", ""), "line": f.get("line_number", 0),
                     "snippet": f.get("snippet", ""), "remediation": f.get("remediation", "")}
            if sev_raw == "critical":
                critical_issues.append(issue)
            elif sev_raw == "high":
                error_issues.append(issue)
            elif sev_raw == "medium":
                warning_issues.append(issue)
            # skip low/info

    # 华为云规范检查 issues
    hwcloud_pass = True
    if hwcloud_results:
        for hr in hwcloud_results:
            for iss in hr.get("issues", []):
                sev = iss.get("severity", "warning")
                issue = {**iss, "source": "hwcloud-spec", "rule_prefix": iss.get("rule", "").split(".")[0]}
                if sev == "error":
                    error_issues.append(issue)
                    hwcloud_pass = False
                elif sev == "warning":
                    warning_issues.append(issue)
                # skip info

    # gitleaks issues
    gitleaks_pass = True
    if gitleaks_results:
        for gr in gitleaks_results:
            skill_name = gr.get("skill_name", "")
            for f in gr.get("findings", []):
                # gitleaks finding fields: RuleID, File, StartLine, Secret, Match, Entropy, Description
                rule_id = f.get("RuleID", "unknown")
                fpath = f.get("File", "")
                line = f.get("StartLine", 0)
                secret = f.get("Secret", "")
                match = f.get("Match", "")
                desc = f.get("Description", rule_id)
                # Truncate secret for display (never show full secret in report)
                snippet = match[:80] + "..." if len(match) > 80 else match
                issue = {
                    "skill": skill_name, "source": "gitleaks", "rule": rule_id,
                    "severity": "error", "category": rule_id,
                    "message": desc, "line": line,
                    "snippet": snippet, "rule_prefix": rule_id,
                    "file": fpath,
                }
                error_issues.append(issue)
                gitleaks_pass = False

    # ── Section 2: Issue Summary ──
    a("── 2. Issue Summary ──")
    a()
    if critical_issues:
        cats = {}
        for i in critical_issues:
            c = i.get("category", i["rule"])
            cats[c] = cats.get(c, 0) + 1
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(cats.items()))
        a(f"  CRITICAL  {len(critical_issues):>3}  {detail} (skill-scanner)")
    if error_issues:
        rules = {}
        for i in error_issues:
            r = i.get("rule_prefix", i["rule"])
            rules[r] = rules.get(r, 0) + 1
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(rules.items()))
        src = set(i["source"] for i in error_issues)
        a(f"  ERROR    {len(error_issues):>3}  {detail} ({', '.join(src)})")
    if warning_issues:
        rules = {}
        for i in warning_issues:
            r = i["rule"]
            rules[r] = rules.get(r, 0) + 1
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(rules.items()))
        a(f"  WARNING  {len(warning_issues):>3}  {detail} (skillcheck)")
    if not critical_issues and not error_issues and not warning_issues:
        a("  (no issues found)")
    a()

    # ── Section 3: Issue Details ──
    a("── 3. Issue Details ──")
    a()

    def detail_block(issues, label):
        if not issues:
            return
        for i in issues:
            a(f"  [{label}] {i['skill']} — {i.get('category', i['rule'])}")
            if i.get("line"):
                a(f"    L{i['line']}  {i['rule']}")
            else:
                a(f"    {i['rule']}")
            if i.get("snippet"):
                a(f"    Snippet: {i['snippet'][:120]}")
            if i.get("message"):
                a(f"    {i['message'][:150]}")
            a()

    detail_block(critical_issues, "CRITICAL")
    detail_block(error_issues, "ERROR")
    detail_block(warning_issues, "WARNING")

    # ── Section 4: Fix Strategies ──
    a("── 4. Fix Strategies ──")
    a()

    seen_rules = set()
    all_issues = critical_issues + error_issues + warning_issues
    for i in all_issues:
        rule_key = i.get("category") or i.get("rule_prefix") or i["rule"]
        if rule_key in seen_rules:
            continue
        seen_rules.add(rule_key)
        sev = i["severity"].upper() if i["severity"] != "error" else "ERROR"
        strategy = get_fix_strategy(rule_key)
        a(f"  [{sev}] {rule_key}")
        a(f"    Strategy: {strategy}")
        a()

    if not seen_rules:
        a("  (no issues to fix)")
        a()

    # ── Verdict ──
    a("=" * 72)
    checks = [
        ("skillcheck", sc_pass),
        ("markdownlint", md_pass),
        ("skill-scanner", scanner_pass),
        ("hwcloud-spec", hwcloud_pass if hwcloud_results is not None else True),
        ("gitleaks", gitleaks_pass if gitleaks_results is not None else True),
    ]
    pass_count = sum(1 for _, v in checks if v)
    total = len(checks)
    if pass_count == total:
        a(f"  Gate Verdict: PASS  |  {'  '.join(f'{n} OK' for n, _ in checks)}")
    else:
        parts = [f"{n} OK" if v else f"{n} FAIL" for n, v in checks]
        a(f"  Gate Verdict: FAIL  |  {'  '.join(parts)}")
    a("=" * 72)

    return "\n".join(L)

# ── Main ──

def main():
    args = parse_args()
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"ERROR: target not found: {target}", file=sys.stderr)
        sys.exit(1)

    # Auto-install tools
    ensure_tools(no_install=args.no_install)

    skills = discover_skills(target)
    if not skills:
        print(f"ERROR: no skills found under: {target}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else target.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {len(skills)} skill(s) under {target} ...")

    # 1. skillcheck
    print("  [1/5] skillcheck ...", end=" ", flush=True)
    sc_data = run_skillcheck(target, args.skillcheck)
    print("done")

    # 2. markdownlint-cli2
    print("  [2/5] markdownlint-cli2 ...", end=" ", flush=True)
    md_raw, md_rc = run_markdownlint(target, args.markdownlint, args.node_bin)
    md_issues = parse_markdownlint(md_raw)
    print(f"done ({len(md_issues)} issues)")

    # 3. skill-scanner (per skill)
    print("  [3/5] skill-scanner ...", flush=True)
    scanner_results = []
    for s in skills:
        print(f"    scanning {s.name} ...", end=" ", flush=True)
        sr = run_skill_scanner(s, args.skill_scanner)
        sr["skill_name"] = s.name
        safe = sr.get("is_safe", True)
        print("safe" if safe else "ISSUES FOUND")
        scanner_results.append(sr)

    # 4. 华为云 SKILL.md 规范检查 (per skill)
    print("  [4/5] 华为云规范检查 ...", flush=True)
    hwcloud_results = []
    for s in skills:
        print(f"    checking {s.name} ...", end=" ", flush=True)
        hr = run_hwcloud_spec_check(s)
        issue_count = len(hr.get("issues", []))
        print(f"{'OK' if issue_count == 0 else f'{issue_count} issues'}")
        hwcloud_results.append(hr)

    # 5. gitleaks 凭证扫描 (per skill)
    print("  [5/5] gitleaks ...", flush=True)
    gitleaks_results = []
    gitleaks_bin = shutil.which(args.gitleaks) or args.gitleaks
    if not shutil.which(args.gitleaks):
        print("    SKIP (gitleaks not found, install: https://github.com/gitleaks/gitleaks/releases)")
    else:
        for s in skills:
            print(f"    scanning {s.name} ...", end=" ", flush=True)
            gr = run_gitleaks(s, gitleaks_bin)
            gr["skill_name"] = s.name
            leaks = gr.get("leaks_found", False)
            finding_count = len(gr.get("findings", []))
            print(f"{'CLEAN' if not leaks else f'{finding_count} LEAKS'}")
            gitleaks_results.append(gr)

    # Build report
    report = build_report(target, skills, sc_data, md_raw, md_rc, md_issues, scanner_results, hwcloud_results, gitleaks_results)

    # Write report
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    report_path = output_dir / f"skill-gate-report-{ts}.txt"
    report_path.write_text(report, encoding="utf-8")

    print(f"\nReport saved: {report_path}")
    return report_path

if __name__ == "__main__":
    main()
