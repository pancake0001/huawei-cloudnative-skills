# gitcode-security-scanner Usage

Source: `https://gitcode.com/developer-skill/DTSE-SKILL/tree/main/gitcode-security-scanner`

## Overview

A regex-based security scanner for GitCode repos. Detects hardcoded tokens, password leaks, sensitive info, SQL injection, path traversal, debug leakage in **source code files** (.py, .js, .md, .json, .yaml, etc.).

## Critical Distinction: skill-scanner vs gitcode-security-scanner

**These two tools are complementary, NOT overlapping.** Running only one gives a false sense of security.

| Aspect | skill-scanner (cisco-ai-skill-scanner) | gitcode-security-scanner |
|--------|---------------------------------------|------------------------|
| **Scan target** | All files in skill dir (SKILL.md, .py, .sh, .json, etc.) | All source code files (.py, .js, .md, .json, .yaml, .sh, etc.) |
| **Scan depth** | Full skill dir via `_discover_files()` + YARA rules | Full repo tree (scripts/, templates/, references/, etc.) |
| **Risk domain** | AI safety (reverse shell, command injection, prompt injection, eval/exec, resource abuse) | InfoSec (credential leak, SQL injection, path traversal, debug leakage) |
| **Credential detection** | ✗ YARA only matches cloud API key formats (AWS AKIA, GitHub ghp_, OpenAI sk-, Anthropic sk-ant-). Does NOT detect generic passwords, SMTP auth codes, or Chinese keyword credentials. Python pack has NO credential_checks.py. | ✓ Regex-based detection of api_key, password, secret, token, auth, credential, etc. + Chinese keywords (授权码/密码/密钥) + Markdown list format |
| **Chinese keywords** | ✗ | ✓ 授权码/密码/密钥/令牌/口令/秘钥/凭证 |
| **Markdown list format** | ✗ | ✓ `- 授权码：HPUA02...` |
| **while True / eval / nc -l** | ✓ Detects | ✗ Does NOT detect |
| **Missing license** | ✓ Detects | ✗ Does NOT detect |

**Bottom line**: skill-targeted-audit's security gate (skill-scanner) only catches AI-safety risks in SKILL.md. To catch hardcoded credentials and info leaks in source code, you MUST also run gitcode-security-scanner separately.

## Running the Scanner

The scanner scripts are at `DTSE-SKILL/gitcode-security-scanner/scripts/`. Three scanners exist:

| Scanner | Use? | Notes |
|---------|------|-------|
| `security_scanner.py` | ✓ **Use this one** | Most complete: Chinese keywords, Markdown format, config-driven rules, 3-level (high/medium/low) |
| `hybrid_security_scanner.py` | ✗ | 4-level severity but no Chinese keywords, no Markdown format, hardcoded patterns |
| `professional_scanner.py` | ✗ | Git diff + code-reviewer mode, but no Chinese keywords, no Markdown format |

### Dependency Issue

`security_scanner.py` imports `gitcode_api.py` which requires `requests`. On EulerOS system Python, `requests` is not installed and `pip install` may fail due to PEP 668.

**Workaround**: Use the hermes venv Python: `/root/.hermes/skills/.venv/bin/python3` (has `requests` installed). Or extract scanning core logic into a standalone script — the scanning logic only needs `re`, `os`, `json`.

### Standalone Scan Pattern (no GitCode API needed)

```python
import sys
sys.path.insert(0, '/tmp/DTSE-SKILL/gitcode-security-scanner/scripts')
from security_scanner import SecurityScanner

scanner = SecurityScanner('config_custom.json')  # custom config pointing to local repo
issues = scanner.scan_project('project-name', '/path/to/local/repo')
# issues = {'high': [...], 'medium': [...], 'low': [...]}
```

### Config (config.json)

Key fields:
- `repos_dir`: path to cloned repos
- `security_rules.high_risk_tokens`: keyword list for credential detection (api_key, password, secret, token, etc.)
- `security_rules.config_files`: file patterns for config detection (.env, application.yml, etc.)
- `security_rules.sensitive_patterns`: regex patterns for AK/SK, JWT, private keys (**NOTE: these are defined but NOT compiled/used by the scanner — known limitation**)

### Detection Rules (security_scanner.py)

| Rule | Severity | Pattern |
|------|----------|---------|
| hardcoded_credentials | HIGH | `keyword = "value"` where value ≥10 chars, alphanumeric |
| markdown_credentials | HIGH | `- keyword: value` in Markdown lists |
| chinese_credentials | HIGH | `授权码：value`, `密码：value` etc. |
| sql_injection | HIGH | `SELECT...FROM...${var}` string concatenation (excludes REST API paths) |
| path_traversal | HIGH | `../` + string concatenation with user input |
| debug_leakage | MEDIUM | `print/console.log` with password/token/secret args |
| config_files | MEDIUM | File name matches .env, config.json, application.yml, etc. |
| email_leak | LOW | Real email (not @example.com) — **NOTE: low level never populated in code** |
| phone_leak | LOW | Chinese mobile number pattern `1[3-9]\d{9}` — **NOTE: low level never populated in code** |

### Confidence Filtering (Two Layers)

**Layer 1 — `_is_example_or_placeholder(line)`**:
- Separates code from comments first (split on `#` and `//`)
- Code part contains `your_`, `replace_this`, `changeme`, `example.com` → skip
- Full line contains `example`, `placeholder`, `todo`, `fixme`, `xxx`, `sample`, `demo`, `test`, `mock` → skip
- Key design: if code looks real (>5 chars, no placeholder), don't skip even if comment has "example"

**Layer 2 — `_looks_like_real_token(value)`**:
- Exclude: `your_`, `placeholder`, `example`, `test`, `demo`
- Real if: length ≥15 + alphanumeric mix, OR length ≥32 + all hex (hash), OR JWT format (`eyJ...`), OR API key prefix (`sk-`, `pk-`, `ak-`, `secret_`)
- **Gap**: values of length 10-14 that don't match JWT/hash are REJECTED → short tokens like `ak1234567890` (12 chars) are missed

### False Positive Patterns

- `_meta.json` `publishedAt` timestamps (e.g. `1773500110231`) match phone number regex → LOW, ignore
- `your-email@163.com` in example configs → filtered by `example_indicators`
- `company.com` in example configs → not in exclude list, may report → acceptable LOW

## Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| `sensitive_patterns` in config.json never compiled | AK/SK/JWT/private key regexes defined but unused | Huawei cloud AK/SK only caught by keyword regex, not format-specific regex |
| `low` level issues never populated | Email/phone leaks not reported | Need separate regex pass or manual grep |
| No `node_modules`/`__pycache__` skip | Scans dependency files, slow + noisy | Pre-filter or use hybrid_security_scanner which has ignore_patterns |
| Short tokens (10-14 chars) missed by `_looks_like_real_token` | `ak1234567890` not flagged | Lower the length threshold or add format-specific rules |
| `config_files` rule flags filename only, not content | Any file named `config.json` reported as MEDIUM regardless of content | Accept as informational or refine rule |

## Fix Strategies

| Finding | Fix |
|---------|-----|
| Hardcoded token/password | Move to env var `os.environ.get("VAR", "")`, remove from SKILL.md |
| Hardcoded email | Use placeholder `${EMAIL}` or env var in docs; keep real emails only in config files not committed |
| Debug print with sensitive info | Replace with `logging.debug()` or remove |
| Chinese credential in Markdown | Replace value with `${ENV_VAR}` or `<YOUR_TOKEN>` |
| SQL injection pattern | Use parameterized queries instead of string concatenation |
| Path traversal | Validate and normalize user-supplied file paths |
