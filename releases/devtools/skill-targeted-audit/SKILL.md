---
name: skill-targeted-audit
description: Audit a single skill or skill folder for quality, security, and compliance using skillcheck + markdownlint-cli2 + cisco-ai-skill-scanner + hwcloud-spec + gitleaks. Generate a structured report with issue details and fix strategies.
version: 1.6.0
category: devops
author: Hermes Agent
created: 2026-05-20
---

# Skill Targeted Audit

## Overview

Scan a single skill directory or a folder of skills, run three quality gates, and generate a structured report with issue details and fix strategies.

**Five checks:**

1. **skillcheck** — SKILL.md agentskills.io spec validation (pip install skillcheck)
2. **markdownlint-cli2** — Markdown style consistency (npm install -g markdownlint-cli2)
3. **cisco-ai-skill-scanner** — Security scanning: command injection, reverse shell, credential leak, dangerous functions (pip install cisco-ai-skill-scanner, CLI: `skill-scanner`)
4. **hwcloud-spec** — 华为云 SKILL.md 规范检查: frontmatter 必需字段(name/description/tags/version)、正文章节结构(概述/前置条件/核心命令/参数确认/参考文档)、文件大小(SKILL.md≤500行, 目录≤5MB)
5. **gitleaks** — 凭证泄露扫描: 检测硬编码API密钥、密码、私钥、token等800+种凭证格式 (https://github.com/gitleaks/gitleaks)

## When to Use

- Before accepting a skill contribution
- During CI/CD pipeline gate
- Periodic repository health check
- Auditing a single skill before release
- User says "audit this skill" or "check skill quality" or "scan skills for issues"

## Prerequisites

Tools are **auto-installed** on first run. If you prefer manual install:

```bash
pip install skillcheck cisco-ai-skill-scanner
npm install -g markdownlint-cli2
# gitleaks: download from https://github.com/gitleaks/gitleaks/releases
# e.g. curl -sSfL https://github.com/gitleaks/gitleaks/releases/download/v8.25.1/gitleaks_8.25.1_linux_arm64.tar.gz | tar -xz -C /usr/local/bin
```

To skip auto-install, use `--no-install` flag.

## Usage

### Scan a single skill

```
Use skill-targeted-audit to scan /path/to/my-skill
```

### Scan a folder of skills

```
Use skill-targeted-audit to scan /path/to/skills-folder
```

The agent will:

1. Detect whether input is a single skill (contains SKILL.md) or a parent folder (contains subdirs with SKILL.md)
2. Run all five checks on each skill
3. Generate a report file in the **parent directory** of the scanned path

### Report location

| Input | Report saved to |
|-------|----------------|
| `/repo/skills/python-debugpy` | `/repo/skills/skill-gate-report-<timestamp>.txt` |
| `/repo/skills` | `/repo/skill-gate-report-<timestamp>.txt` |

### Direct script invocation

```bash
python3 scripts/skill_audit.py \
  --target /path/to/skill-or-folder \
  --skillcheck /path/to/skillcheck \
  --skill-scanner /path/to/skill-scanner \
  --gitleaks /path/to/gitleaks \
  --node-bin /opt/nvm/versions/node/v18.20.8/bin
```

The audit script is at `scripts/skill_audit.py` (see linked files). The hwcloud-spec checker is at `scripts/hwcloud_spec_check.py`.

## Report structure

Five sections:

1. **Scanned Skills** — list of all skills found
2. **Issue Summary** — count by severity (CRITICAL/ERROR/WARNING) with rule breakdown (INFO excluded)
3. **Issue Details** — per-issue: skill name, rule, line number, snippet, message
4. **Fix Strategies** — actionable remediation for each unique rule/category

## Fix strategies reference

### hwcloud-spec (华为云 SKILL.md 规范)

| Rule | Fix |
|------|-----|
| frontmatter.missing.{field} | 补充必需字段: name(与目录名一致), description(含功能概要+触发词), tags(≤5个), version(语义化如1.0.0) |
| frontmatter.name-mismatch | name 字段值必须与技能目录名完全一致 |
| frontmatter.tags-too-many | 标签数超过5个，精简到5个以内 |
| frontmatter.version-format | version 需符合语义化版本号格式 (如 2.0.0) |
| frontmatter.description-too-short | description 应包含: 功能概要、技术基础、适用场景、触发词 |
| section.missing-required | 补充必需章节: 概述、前置条件、核心命令、参数确认、参考文档 |
| section.missing-recommended | 补充推荐章节: 输出格式、验证方法、最佳实践、注意事项 |
| size.skill-md-lines | SKILL.md 超500行，拆分内容到 references/ 子目录 |
| size.dir-too-large | 技能目录超5MB，拆分大文件到 references/ 或 scripts/ |

### skillcheck

| Rule | Fix |
|------|-----|
| description.quality-score low | Start description with action verb (Generates/Analyzes/Validates); add trigger context ("Use this skill whenever...") |
| disclosure.metadata-budget | Move non-essential frontmatter fields to body section |
| disclosure.body-bloat | Move large tables (>20 rows) to a referenced file under references/ |
| frontmatter.field.unknown | Add field to skillcheck.toml extension_fields, or remove from frontmatter |
| compat.unverified | Document field behavior for codex/cursor or remove unverified fields |

### markdownlint-cli2

| Rule | Fix |
|------|-----|
| MD013 line-length | Break long lines; or disable for code blocks in .markdownlint.json |
| MD036 no-emphasis-as-heading | Replace **text** pseudo-headings with ### text real headings |
| MD031 blanks-around-fences | Add blank lines before/after fenced code blocks |
| MD007 ul-indent | Fix list indentation to match configured indent (default 4) |
| MD024 no-duplicate-heading | Add distinguishing suffix or enable siblings_only |

### cisco-ai-skill-scanner

| Category | Fix |
|----------|-----|
| command_injection | Move dangerous commands to standalone scripts; reference script path in SKILL.md instead of inline code |
| reverse_shell | Remove or relocate reverse shell examples; if needed for docs, use <!-- skill-scanner:ignore --> annotation |
| credential_leak | Replace hardcoded secrets with environment variable references (${VAR} or os.environ.get()); add to .secrets.baseline if false positive. NOTE: skill-scanner YARA only catches cloud API keys (AWS/GitHub/OpenAI/Anthropic format) — for generic passwords, SMTP auth codes, Chinese credentials (授权码/密码), run gitcode-security-scanner or gitleaks separately |
| dangerous_function | Wrap eval()/exec() calls with input validation; consider safer alternatives |
| prompt_injection | Review and sanitize user-controllable input before embedding in prompts |

### gitleaks

| Rule | Fix |
|------|-----|
| generic-api-key | Replace hardcoded API key/secret with `os.environ.get("VAR")` or `${VAR}`; add to `.gitleaksignore` if false positive |
| private-key | Remove hardcoded private key; load from file or secret manager at runtime; add key file to `.gitignore` |
| (other rules) | Replace hardcoded credential with environment variable or secret manager reference; see https://gitleaks.io/docs/secrets |

## Configuration files

### skillcheck.toml

```toml
[frontmatter]
extension_fields = [
    "license",
    "platforms",
    "metadata",
    "prerequisites",
]
```

### .markdownlint.json

```json
{
  "default": true,
  "MD003": { "style": "atx" },
  "MD004": { "style": "dash" },
  "MD013": { "line_length": 200, "code_blocks": false, "tables": false },
  "MD024": { "siblings_only": true },
  "MD033": false,
  "MD034": false,
  "MD040": false,
  "MD041": false,
  "MD046": false
}
```

## CI/CD integration

```yaml
jobs:
  skill-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install skillcheck cisco-ai-skill-scanner
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm install -g markdownlint-cli2
      - name: Install gitleaks
        run: |
          curl -sSfL https://github.com/gitleaks/gitleaks/releases/download/v8.25.1/gitleaks_8.25.1_linux_amd64.tar.gz | tar -xz -C /usr/local/bin
      - name: Run audit
        run: python3 scripts/skill_audit.py --target . --output-dir .
      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: skill-gate-report
          path: skill-gate-report-*.txt
```

## Remediation Workflow (audit → fix → verify)

After running the audit and getting a FAIL, follow this sequence to fix skills:

1. **Run `markdownlint-cli2 --fix` FIRST** — it auto-fixes MD022/MD031/MD032/MD047/MD012/MD009/MD010 and many more. Do NOT write manual Python scripts to fix blank lines — `--fix` is faster and more reliable. Requires `--config` path to `.markdownlint.json`.
   ```bash
   markdownlint-cli2 "skills/my-skill/**/*.md" --config "skills/my-skill/.markdownlint.json" --fix
   ```

2. **Fix hwcloud-spec missing sections** — Add required sections (概述/前置条件/核心命令/参数确认/参考文档) by hand. These require domain knowledge and cannot be auto-fixed.

3. **Fix skillcheck `references.escape`** — skillcheck rejects `../` relative paths that escape the skill directory. Replace `[text](../other-skill/SKILL.md)` with `[text (other-skill-name)]` (plain text with skill name, no link).

4. **Fix MD036 (emphasis-as-heading)** — Replace `*text*` or `**text**` used as a pseudo-heading with either a real `### heading` or plain text. `--fix` does NOT handle MD036.

5. **Fix MD040 (fenced-code-language)** — Replace bare ` ``` ` with ` ```text ` or the appropriate language. `--fix` does NOT handle MD040.

6. **Run `markdownlint-cli2 --fix` AGAIN** — After manual edits, re-run to catch any new formatting issues introduced.

7. **Re-run the full audit** to verify PASS.

### .markdownlint.json per skill

Every skill should have a `.markdownlint.json` to configure rules (especially for non-SKILL.md files like CLAUDE.md that have inline HTML). Use this template:

```json
{
  "default": true,
  "MD003": { "style": "atx" },
  "MD004": { "style": "dash" },
  "MD013": { "line_length": 200, "code_blocks": false, "tables": false },
  "MD024": { "siblings_only": true },
  "MD033": false,
  "MD034": false,
  "MD040": false,
  "MD041": false,
  "MD046": false,
  "MD047": false,
  "MD058": false
}
```

## Bulk Fix Workflow

When markdownlint reports many issues (especially MD022/MD031/MD032), use `--fix` instead of manual editing:

```bash
# 1. Run audit to identify issues
python3 scripts/skill_audit.py --target /path/to/skills --node-bin /opt/nvm/versions/node/v18.20.8/bin

# 2. Bulk-fix markdownlint issues (handles MD022/MD031/MD032/MD047/MD012 etc. automatically)
markdownlint-cli2 "skills/**/*.md" --config "skills/.markdownlint.json" --fix

# 3. Fix remaining non-auto-fixable issues manually (MD040, MD034, MD036, MD013)

# 4. Re-run audit to verify
python3 scripts/skill_audit.py --target /path/to/skills --node-bin /opt/nvm/versions/node/v18.20.8/bin
```

**Priority**: `markdownlint --fix` > Python script fixes. The `--fix` flag handles blank-line issues (MD022/MD031/MD032/MD047/MD012) perfectly in one pass. Manual Python scripts miss edge cases and require multiple passes.

## Pitfalls

- **skill-scanner CLI name**: The pip package is `cisco-ai-skill-scanner` but the CLI binary is `skill-scanner` (not `cisco-ai-skill-scanner`)
- **skillcheck glob**: `skillcheck "**/SKILL.md"` doesn't work — use `skillcheck .` to scan a directory recursively
- **markdownlint regex parsing**: Output format is `file:line:col MDxxx/rule-name Description` — the regex must use `(.*)` not `(.+)` for the description group to avoid IndexError on truncated messages
- **skill-scanner litellm warnings**: Ignore `LiteLLM:WARNING` about bedrock/sagemaker — these are harmless unless you actually use those providers
- **Python version**: skillcheck requires Python >= 3.10; cisco-ai-skill-scanner requires 3.12+
- **Node path**: On EulerOS, npx may not be on PATH — pass `--node-bin /opt/nvm/versions/node/v18.20.8/bin`
- **skill-scanner only scans SKILL.md, NOT source code**: This is the #1 gap. skill-scanner (cisco-ai-skill-scanner) detects AI-safety risks (reverse shell, command injection, eval/exec, prompt injection) in SKILL.md only. It does NOT scan scripts/, templates/, references/ for hardcoded credentials, password leaks, or debug info leakage. For source-code-level security (credential leak, SQL injection, path traversal, debug leakage), you MUST also run gitcode-security-scanner separately. See `references/gitcode-security-scanner.md` for the full comparison table and usage.
- **skill-scanner credential blind spot**: skill-scanner (cisco-ai-skill-scanner) DOES scan all .py/.sh files in the skill dir (not just SKILL.md), but its YARA credential rules only match known cloud API key formats: AWS `AKIA...`, GitHub `ghp_...`, OpenAI `sk-...`, Anthropic `sk-ant-...`. It does NOT detect generic passwords, SMTP auth codes, Huawei cloud AK/SK, or Chinese keyword credentials (授权码/密码/密钥). The Python rule pack has no credential_checks.py — all credential detection is delegated to YARA. Additionally, `os.environ.get("VAR", "default")` patterns are excluded by YARA's `$python_imports` filter even if the default value is a real secret. **For credential/token leak detection, you MUST run gitcode-security-scanner separately** — see references/gitcode-security-scanner.md.
- **skill-scanner hangs**: Some skills cause skill-scanner to hang indefinitely. MUST use `timeout --signal=KILL` shell wrapper (NOT Python subprocess timeout alone — it fails to kill child processes). Set 15s per-skill timeout. Implementation: `shell_cmd = f"timeout --signal=KILL {timeout} " + " ".join(shlex.quote(c) for c in cmd)` then `subprocess.run(shell_cmd, shell=True, ...)`
- **markdownlint absolute glob**: When scanning a single skill, use absolute glob `str(target / "**" / "*.md")` not relative `"**/*.md"` — otherwise it scans the entire parent directory
- **skillcheck scope**: Same as markdownlint — when scanning a single skill, pass the skill directory explicitly, not the parent. Otherwise skillcheck scans all sibling directories.
- **INFO excluded from report**: INFO-level issues are NOT written to the report file. Only CRITICAL/ERROR/WARNING appear. This was an explicit user requirement.
- **Print per-skill progress**: User expects to see each skill being processed in the session output. Show tree-style output with per-check phase, with per-skill results using symbols.
- **Clean before git add**: Always remove vim swap files (`.SKILL.md.sw*`) and `__pycache__/` before staging — they slip through if you `cp -r` from a working directory. Do `git add` after cleanup, not before.
- **hwcloud-spec section aliases**: Section matching uses aliases to handle varied heading names. If a skill uses non-standard headings (e.g. "常用命令速查" instead of "核心命令"), add the heading to SECTION_ALIASES in hwcloud_spec_check.py. Common additions: Usage, Configuration, Gotchas, Command Reference, 项目参数, 适用场景.
- **hwcloud-spec false positives**: Most "missing section" errors are alias gaps, not real missing content. Always check the actual SKILL.md headings before telling user to add sections. Expand aliases first.
- **hwcloud-spec frontmatter tags**: Tags must be at the top level of frontmatter (`tags: [a, b, c]`), NOT nested under `metadata.hermes.tags`. The checker only reads top-level fields.
- **markdownlint --fix is preferred**: When many MD022/MD031/MD032 issues exist, use `markdownlint-cli2 --fix` first, then fix remaining non-auto-fixable issues (MD040/MD034/MD036/MD013) manually. Python scripts for blank-line fixing are fragile and miss edge cases.
- **.markdownlint.json for non-SKILL.md files**: CLAUDE.md and other auto-generated files may trigger MD033/MD041/MD047/MD058. Add a `.markdownlint.json` to each skill dir to disable these rules. Template:
  ```json
  {
    "default": true,
    "MD003": {"style": "atx"},
    "MD004": {"style": "dash"},
    "MD013": {"line_length": 200, "code_blocks": false, "tables": false},
    "MD024": {"siblings_only": true},
    "MD033": false, "MD034": false, "MD040": false,
    "MD041": false, "MD046": false, "MD047": false, "MD058": false
  }
  ```
- **references.escape fix**: skillcheck flags `../` relative paths as "resolves outside skill directory". Replace `[text](../other-skill/SKILL.md)` with `[text (other-skill)]` — skill name in parentheses instead of file link.
- **Do NOT manually script markdownlint fixes**: `markdownlint-cli2 --fix` handles MD022/MD031/MD032/MD047/MD012 and many more automatically. Writing Python scripts to insert blank lines is error-prone (misses edge cases, requires multiple passes). Use `--fix` first, then manually fix only what `--fix` cannot (MD036, MD040, references.escape).
- **references.escape from skillcheck**: Cross-skill relative links like `[text](../other-skill/SKILL.md)` fail skillcheck's `references.escape` rule because they resolve outside the skill directory. Replace with plain text: `[text (other-skill-name)]`.
- **MD036 not auto-fixable**: `markdownlint-cli2 --fix` does NOT fix MD036 (emphasis used as heading). Must manually replace `*pseudo-heading text*` with plain text or a real `### heading`.
- **MD040 not auto-fixable**: `markdownlint-cli2 --fix` does NOT fix MD040 (fenced code blocks missing language). Must manually add language tags: ` ``` ` → ` ```text ` or ` ```bash ` etc.
- **Iterative fix-then-audit**: After fixing, always re-run the full audit. Manual edits can introduce new markdownlint violations (e.g., adding sections without blank lines). Run `--fix` again after manual edits, then re-audit.
- **gitleaks --no-git mode**: The audit uses `gitleaks detect --no-git` which scans file contents only (not git history). This avoids false positives from already-removed secrets. To scan git history for leaked credentials, run `gitleaks detect --source /path/to/repo` (without --no-git) separately.
- **gitleaks does not detect Chinese keyword credentials**: gitleaks matches regex patterns for API keys, passwords, tokens etc. but does not detect Chinese keyword patterns like `授权码：xxx` or `密码=xxx`. For those, run gitcode-security-scanner separately.
- **gitleaks auto-install**: On first run, gitleaks binary is downloaded from GitHub releases via mirror proxies (gh-proxy.com, gh.ddlc.top). If both mirrors fail, install manually from https://github.com/gitleaks/gitleaks/releases.
- **gitleaks finding severity**: All gitleaks findings are reported as ERROR severity in the audit report, since hardcoded credentials are security issues that should be fixed before release.
- **Large repo report size**: Repos with many markdownlint errors produce huge reports (e.g. developer-skill: 21K errors → 4.3MB/86K lines). Use `head`/`tail` to read summary and verdict sections. The Issue Summary section (Section 2) gives the rule-level breakdown; Issue Details (Section 3) is the bulk. For large repos, consider scanning individual skills one at a time.
- **Repo structure variation**: Some repos have skills at the top level (e.g. developer-skill has `huawei-cloud-cli-guidance/` directly), others use a `skills/` subdirectory. The `discover_skills` function handles both: if `--target` itself contains SKILL.md → single skill; if subdirs contain SKILL.md → parent folder. Always check `ls` first to determine the correct `--target` path.
- **gitleaks git history vs current files**: The audit's `--no-git` mode only scans current file contents. Credentials already removed from current code but still in git history will NOT be caught. Run `gitleaks detect --source /path/to/repo` (without --no-git) separately to scan git history. This is especially important for repos where credentials were committed and then replaced with env vars.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| skillcheck not found | pip install skillcheck (requires Python >= 3.10) |
| skill-scanner not found | pip install cisco-ai-skill-scanner (CLI: skill-scanner) |
| markdownlint-cli2 not found | npm install -g markdownlint-cli2 |
| gitleaks not found | Download from https://github.com/gitleaks/gitleaks/releases (auto-installed on first run) |
| skill-scanner hangs on a skill | Use `timeout --signal=KILL 15` wrapper; reduce timeout if needed |
| Large repo slow | Scan individual skills instead of entire repo |

## Related Skills

- github-code-review — Code review workflows
- requesting-code-review — Pre-commit verification
- systematic-debugging — Debug failing checks

## Security Scanning

### Why skill-scanner alone is insufficient for credential detection

`skill-scanner` (cisco-ai-skill-scanner) **does scan all files** (not just SKILL.md) — strace confirms it opens `.py`, `.sh`, `.md` files. But its YARA `credential_harvesting_generic.yara` **only matches known cloud API key formats**:

| YARA pattern | What it matches | What it MISSES |
|-------------|----------------|----------------|
| `AKIA[0-9A-Z]{16}` | AWS IAM access keys | Generic `password = "xxx"` |
| `ghp_[A-Za-z0-9]{36}` | GitHub PATs | `SMTP_AUTH_CODE = "xxx"` |
| `sk-[A-Za-z0-9]{48,}` | OpenAI legacy keys | Chinese `授权码：xxx` |
| `sk-proj-...` | OpenAI project keys | Markdown `- 授权码: xxx` |
| `-----BEGIN RSA PRIVATE KEY-----` | PEM private keys | `os.environ.get("SMTP_AUTH_CODE", "realvalue")` |

The Python pack has **no `credential_checks.py`** — all credential detection is delegated to YARA. Additionally, YARA's exclusion conditions (`$template_indicators`, `$python_imports`, `$function_definitions`) are so broad that `os.environ.get()` patterns are skipped even when they contain real default values.

**Bottom line**: skill-scanner detects **AI agent malicious behavior** (reverse shell, command injection, prompt injection, cloud key theft). It does NOT detect **generic credential leaks** (passwords, SMTP auth codes, API keys in non-cloud formats, Chinese keyword credentials).

### Complementary tools

| Tool | Detects | Misses | Install |
|------|---------|--------|---------|
| skill-scanner (built-in) | Reverse shell, command injection, prompt injection, cloud API keys (AWS/GitHub/OpenAI) | Generic passwords, SMTP auth codes, Chinese credentials | Auto-installed by audit script |
| gitleaks (built-in) | 800+ credential types: API keys, passwords, private keys, tokens, generic-api-key | Chinese keyword credentials (授权码/密码), Huawei cloud AK/SK format | Auto-installed by audit script |
| gitcode-security-scanner | Generic `keyword=value` credentials, Chinese keywords (授权码/密码/密钥), Markdown list credentials, SQL injection, debug leakage | Reverse shell, command injection, prompt injection | From DTSE-SKILL repo |
| TruffleHog v3 | 800+ detector types with API verification | Returns 0 for non-cloud-format credentials in filesystem mode; verification-dependent | `curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh \| sh -s -- -b /usr/local/bin` |

**Recommended**: Run both skill-scanner (via skill-targeted-audit) AND gitcode-security-scanner for complete coverage. See `references/security-scanner-comparison.md` for detailed analysis and `references/gitcode-security-scanner.md` for standalone usage.

For complete security coverage, run **both**:
1. `skill-targeted-audit` → AI safety + quality gates + credential leak detection (skillcheck + markdownlint + skill-scanner + hwcloud-spec + gitleaks)
2. `gitcode-security-scanner` → InfoSec (Chinese keyword credentials, SQL injection, path traversal, debug leakage)

See `references/gitcode-security-scanner.md` for standalone usage (avoids the `requests` dependency issue).

## Linked Files

- `scripts/skill_audit.py` — The audit runner script (run all 5 checks, generate report)
- `scripts/hwcloud_spec_check.py` — 华为云 SKILL.md 规范检查器 (frontmatter字段/章节结构/文件大小)
