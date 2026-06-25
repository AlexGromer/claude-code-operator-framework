# Relevance Maintenance Protocol
# Version: 1.0.0 | Created: 2026-02-05

## Overview

Протокол поддержания актуальности контента конфигурации Claude Code.

**Principle:** Устаревший контент = неверные рекомендации = потеря доверия.

---

## 1. Review Schedule

### 1.1 Review Frequency Matrix

| Content Type | Frequency | Trigger | Responsible |
|--------------|-----------|---------|-------------|
| Security advisories | **Weekly** | CVE alerts, vendor bulletins | Auto + Manual |
| Tool versions | **Weekly** | Package updates | Auto (staleness_checker.py) |
| API changes | **Monthly** | Breaking changes | Manual review |
| Framework updates | **Monthly** | Major releases | Manual review |
| Module content | **Quarterly** | Staleness score | staleness_checker.py |
| Architecture | **Annually** | Major refactoring | Manual audit |

### 1.2 Automated Schedule (anacron)

```bash
# ~/.anacron/anacrontab entries
7   10  staleness_weekly    python3 ~/.claude/tools/staleness_checker.py --mode weekly
30  15  staleness_monthly   python3 ~/.claude/tools/staleness_checker.py --mode monthly --report
90  20  staleness_quarterly python3 ~/.claude/tools/staleness_checker.py --mode quarterly --full-audit
```

---

## 2. Staleness Indicators

### 2.1 Time-Based Indicators

| Age | Status | Action |
|-----|--------|--------|
| 0-3 months | 🟢 Fresh | No action |
| 3-6 months | 🟡 Aging | Review recommended |
| 6-12 months | 🟠 Stale | Update required |
| >12 months | 🔴 Critical | Immediate attention |

### 2.2 Version-Based Indicators

```
STALENESS_VERSION = current_major - referenced_major

| Difference | Status |
|------------|--------|
| 0 | 🟢 Current |
| 1 | 🟡 One major behind |
| 2+ | 🔴 Critically outdated |
```

### 2.3 Usage-Based Indicators

| Usage Rate | Status | Action |
|------------|--------|--------|
| >20% | 🟢 High demand | Priority maintenance |
| 10-20% | 🟡 Moderate | Standard maintenance |
| 5-10% | 🟠 Low | Review for consolidation |
| <5% | 🔴 Very low | Consider deprecation |

### 2.4 External Indicators

| Signal | Detection | Action |
|--------|-----------|--------|
| Upstream deprecated | GitHub API check | Begin deprecation |
| Project archived | GitHub API check | Immediate deprecation |
| Security vulnerability | CVE database | Urgent update |
| License change | License file check | Legal review |

---

## 3. Staleness Scoring Formula

```python
def calculate_staleness_score(content):
    """
    Calculate staleness score (0-100, higher = more stale)
    """
    score = 0

    # Time factor (0-40 points)
    months_since_update = (now - last_update).days / 30
    if months_since_update > 12:
        score += 40
    elif months_since_update > 6:
        score += 30
    elif months_since_update > 3:
        score += 15

    # Version factor (0-30 points)
    version_diff = current_version - referenced_version
    score += min(version_diff * 10, 30)

    # Usage factor (0-20 points)
    if usage_rate < 5:
        score += 20
    elif usage_rate < 10:
        score += 10

    # External factor (0-10 points)
    if has_security_issues:
        score += 10
    if upstream_deprecated:
        score += 10

    return min(score, 100)
```

### Staleness Thresholds

| Score | Status | Action Required |
|-------|--------|-----------------|
| 0-20 | 🟢 Healthy | None |
| 21-40 | 🟡 Attention | Schedule review |
| 41-60 | 🟠 Stale | Update within 2 weeks |
| 61-80 | 🔴 Critical | Update within 1 week |
| 81-100 | ⛔ Dangerous | Immediate action |

---

## 4. Actions on Staleness

### 4.1 Level 1: Minor Updates (Score 21-40)

**Scope:** Version numbers, links, minor corrections

**Process:**
```
1. Identify outdated references
2. Update in-place
3. Bump patch version
4. No review required
```

**Examples:**
- Update tool version: `nmap 7.93` → `nmap 7.95`
- Fix broken link
- Correct typo

### 4.2 Level 2: Moderate Updates (Score 41-60)

**Scope:** Section rewrites, new examples, API changes

**Process:**
```
1. Review affected sections
2. Rewrite/update content
3. Update examples
4. Bump minor version
5. Self-review
```

**Examples:**
- Rewrite deprecated API usage
- Add new feature documentation
- Update workflow for new version

### 4.3 Level 3: Major Updates (Score 61-80)

**Scope:** Full module rewrites, architecture changes

**Process:**
```
1. Create update plan
2. Rewrite module
3. Update all dependencies
4. Bump major version
5. Review required
6. Update GAPS.md
```

**Examples:**
- Framework migration (e.g., LangChain v1 → v2)
- Major tool replacement
- Architecture restructure

### 4.4 Level 4: Critical/Deprecation (Score 81-100)

**Scope:** Deprecation, removal, security patches

**Process:**
```
1. IMMEDIATE: Add deprecation notice
2. Create migration guide
3. Update all references
4. Follow deprecation protocol
5. Remove after grace period
```

**Examples:**
- Security vulnerability in documented tool
- Upstream project abandoned
- Functionality moved to different module

---

## 5. Automation

### 5.1 staleness_checker.py

**Location:** `~/.claude/tools/staleness_checker.py`

**Features:**
- Scans all modules, rules, examples
- Calculates staleness scores
- Checks tool versions against latest
- Generates reports (JSON, Markdown)
- Creates GAPS.md entries for stale content

**Usage:**
```bash
# Weekly quick check
python staleness_checker.py --mode weekly

# Monthly with report
python staleness_checker.py --mode monthly --report

# Full quarterly audit
python staleness_checker.py --mode quarterly --full-audit

# Check specific file
python staleness_checker.py --file modules/03-devops.md
```

### 5.2 Report Format

```markdown
# Staleness Report - YYYY-MM-DD

## Summary
- Total files scanned: XX
- Healthy (0-20): XX
- Attention (21-40): XX
- Stale (41-60): XX
- Critical (61-80): XX
- Dangerous (81-100): XX

## Critical Items (Immediate Action)

| File | Score | Last Update | Issue |
|------|-------|-------------|-------|
| [file] | [score] | [date] | [issue] |

## Stale Items (Update Within 2 Weeks)

| File | Score | Last Update | Issue |
|------|-------|-------------|-------|
| [file] | [score] | [date] | [issue] |

## Recommendations

1. [recommendation 1]
2. [recommendation 2]
```

### 5.3 Integration Points

| System | Integration |
|--------|-------------|
| anacron | Weekly/monthly/quarterly jobs |
| metrics_tracker.py | `--report staleness` |
| GAPS.md | Auto-create GAP-STALE-XXX entries |
| Session summary | Show critical staleness alerts |

---

## 6. Version Tracking

### 6.1 Tools to Track

```yaml
# ~/.claude/tools/tracked_versions.yaml
tools:
  - name: nmap
    current: "7.95"
    check_command: "nmap --version | head -1"

  - name: terraform
    current: "1.7.0"
    check_command: "terraform version | head -1"

  - name: kubectl
    current: "1.29.0"
    check_command: "kubectl version --client -o json | jq -r '.clientVersion.gitVersion'"

frameworks:
  - name: langchain
    current: "0.1.0"
    check_command: "pip show langchain | grep Version"

  - name: react
    current: "18.2.0"
    check_command: "npm show react version"
```

### 6.2 Version Check Automation

```bash
# Weekly version check via anacron
7 10 version_check python3 ~/.claude/tools/version_checker.py --update-tracking
```

---

## 7. Security Update Protocol

### 7.1 CVE Monitoring

**Sources:**
- NVD (National Vulnerability Database)
- GitHub Security Advisories
- Vendor security bulletins
- CISA alerts

**Process:**
```
1. DETECT: CVE affects documented tool/library
2. ASSESS: Severity (CVSS score)
3. ACT:
   - CRITICAL (9.0-10.0): Immediate update, same day
   - HIGH (7.0-8.9): Update within 48 hours
   - MEDIUM (4.0-6.9): Update within 1 week
   - LOW (0.1-3.9): Update in next maintenance cycle
4. DOCUMENT: Update GAPS.md with GAP-SEC-XXX
5. VERIFY: Confirm fix applied
```

### 7.2 Security Alert Template

```markdown
> 🔴 **SECURITY ALERT** (CVE-YYYY-XXXXX)
> Tool: [tool name]
> Severity: [CRITICAL/HIGH/MEDIUM/LOW]
> Affected versions: [versions]
> Fixed in: [version]
> Action: Update immediately to [version]
```

---

## 8. Reporting

### 8.1 Weekly Report (Automated)

**Contents:**
- New CVEs affecting documented tools
- Tools with available updates
- Files approaching staleness threshold

**Delivery:** Session summary, logs

### 8.2 Monthly Report (Automated)

**Contents:**
- Full staleness scan results
- Version drift analysis
- Usage statistics
- Recommendations

**Delivery:** `~/.claude/logs/staleness_monthly_YYYYMM.md`

### 8.3 Quarterly Audit (Manual Review)

**Contents:**
- Complete content review
- Architecture assessment
- Gap analysis
- Roadmap update

**Delivery:** Update to UNIFIED_IMPLEMENTATION_ROADMAP.md

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RELEVANCE MAINTENANCE QUICK REFERENCE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STALENESS SCORE ACTIONS:                                                   │
│  ├── 0-20:  ✅ No action needed                                             │
│  ├── 21-40: 🟡 Schedule review                                              │
│  ├── 41-60: 🟠 Update within 2 weeks                                        │
│  ├── 61-80: 🔴 Update within 1 week                                         │
│  └── 81-100: ⛔ Immediate action required                                   │
│                                                                              │
│  CHECK STALENESS:                                                           │
│  python ~/.claude/tools/staleness_checker.py --mode weekly                  │
│                                                                              │
│  CHECK VERSIONS:                                                            │
│  python ~/.claude/tools/version_checker.py --update-tracking                │
│                                                                              │
│  FULL AUDIT:                                                                │
│  python ~/.claude/tools/staleness_checker.py --mode quarterly --full-audit  │
│                                                                              │
│  SECURITY CHECK:                                                            │
│  Check CVE databases for documented tools                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**Version History:**
- v1.0.0 (2026-02-05): Initial release
