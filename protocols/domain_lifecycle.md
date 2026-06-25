# Domain Lifecycle Protocol
# Version: 1.0.0 | Created: 2026-02-05

## Overview

Формализованный протокол управления жизненным циклом доменов в конфигурации Claude Code.

**Lifecycle Phases:**
```
PROPOSAL → REVIEW → IMPLEMENTATION → ACTIVE → DEPRECATION → REMOVAL
```

---

## Phase 1: PROPOSAL

### 1.1 Trigger Criteria

Новый домен предлагается когда:
- Появляется новая область задач (>10 запросов/месяц)
- Существующие модули не покрывают тематику
- Есть чёткая CLI-релевантность (≥60/100)

### 1.2 Required Artifacts

| Artifact | Description | Template |
|----------|-------------|----------|
| Domain Proposal | Обоснование, scope, CLI relevance | `templates/domain_proposal.md` |
| Dependency Map | Связи с существующими доменами | Inline in proposal |
| Resource Estimate | Effort в часах, complexity | Inline in proposal |

### 1.3 CLI Relevance Scoring

**Scoring Formula:**
```
CLI_SCORE = (
    direct_cli_usage * 40 +      # 0-40: Direct use in CLI tasks
    automation_potential * 25 +   # 0-25: Can be automated via hooks/skills
    cross_domain_value * 20 +     # 0-20: Benefits other domains
    user_demand * 15              # 0-15: Frequency of user requests
) / 100
```

**Thresholds:**
| Score | Decision |
|-------|----------|
| ≥80 | ✅ Auto-approve, HIGH priority |
| 60-79 | ✅ Approve with review |
| 40-59 | 🟡 Conditional (needs strong justification) |
| <40 | ❌ Reject (low CLI relevance) |

### 1.4 Proposal Checklist

```
☐ Domain name follows naming convention (lowercase, hyphenated)
☐ CLI relevance score calculated (≥60 required)
☐ No overlap with existing domains (checked via grep)
☐ At least 3 example use cases provided
☐ Resource estimate provided (hours)
☐ Dependencies identified
☐ Gap ID assigned (GAP-DOM-XXX)
```

---

## Phase 2: REVIEW

### 2.1 Review Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| CLI Relevance | 40% | Score ≥60/100 |
| Uniqueness | 25% | No significant overlap |
| Completeness | 20% | All artifacts provided |
| Feasibility | 15% | Reasonable effort estimate |

### 2.2 Conflict Detection

**Check for overlaps:**
```bash
# Search existing modules for keyword overlap
grep -r "KEYWORD" ~/.claude/modules/
grep -r "KEYWORD" ~/.claude/rules/

# Check GAPS.md for related gaps
grep "KEYWORD" ~/.claude/GAPS.md
```

### 2.3 Review Checklist

```
☐ CLI relevance score verified
☐ No duplicate domain exists
☐ Dependencies are resolvable
☐ Effort estimate is realistic
☐ Examples are meaningful
☐ Approved by: [reviewer]
☐ Date: [YYYY-MM-DD]
```

---

## Phase 3: IMPLEMENTATION

### 3.1 Module Creation

**File Structure:**
```
~/.claude/modules/XX-domainname.md   # Main module
~/.claude/examples/domainname/       # Examples directory
  ├── example_01.md
  ├── example_02.md
  └── example_03.md
```

**Module Template:**
```markdown
# Module: [Domain Name]
# Version: 1.0.0 | Auto-loaded: No

## Overview
[Brief description]

## Section 1: [Topic]
[Content]

## Few-Shot Examples
See: `examples/domainname/`

## Integration
- Related modules: [list]
- Skills: [list]
- MCP servers: [list]
```

### 3.2 Implementation Checklist

```
☐ Module file created (modules/XX-domainname.md)
☐ Examples directory created (≥3 examples)
☐ Module follows template structure
☐ Cross-references added to related modules
☐ CLAUDE.md updated (module list)
☐ GAPS.md updated (gap marked implementing)
☐ Integration tests passed
```

### 3.3 Integration Points

| Integration | Action Required |
|-------------|-----------------|
| CLAUDE.md | Add to module list table |
| Role Routing | Add keywords to routing table |
| Examples | Create domain examples directory |
| Skills | Create domain skill if applicable |

---

## Phase 4: ACTIVE (Maintenance)

### 4.1 Health Indicators

| Indicator | Healthy | Warning | Critical |
|-----------|---------|---------|----------|
| Last update | <3 months | 3-6 months | >6 months |
| Usage rate | >10% | 5-10% | <5% |
| Error rate | <1% | 1-5% | >5% |
| User satisfaction | >80% | 60-80% | <60% |

### 4.2 Regular Maintenance

**Monthly:**
- Check for outdated tool versions
- Review user feedback
- Update examples if needed

**Quarterly:**
- Full content review
- CLI relevance re-assessment
- Integration check

### 4.3 Versioning

**Semantic Versioning:**
- MAJOR: Breaking changes, restructure
- MINOR: New sections, features
- PATCH: Bug fixes, typos, updates

---

## Phase 5: DEPRECATION

### 5.1 Deprecation Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Staleness | >6 months no updates | Review for deprecation |
| Low usage | <5% for 3+ months | Consider consolidation |
| Superseded | New domain covers functionality | Migrate and deprecate |
| External | Upstream tool/framework deprecated | Deprecate with notice |

### 5.2 Deprecation Process

```
1. ANNOUNCE
   ├── Add deprecation notice to module header
   ├── Log GAP-DEP-XXX in GAPS.md
   └── Notify in session summary (1 month)

2. MIGRATE
   ├── Document migration path
   ├── Update cross-references
   └── Move useful content to successor

3. ARCHIVE
   ├── Move to archived/ directory
   ├── Remove from CLAUDE.md
   └── Keep for reference (6 months)
```

### 5.3 Deprecation Notice Template

```markdown
> ⚠️ **DEPRECATED** (since YYYY-MM-DD)
> This module is deprecated and will be removed on YYYY-MM-DD.
> Migration: Use [successor module] instead.
> Reason: [explanation]
```

---

## Phase 6: REMOVAL

### 6.1 Removal Criteria

Domain can be removed when:
- Deprecation period complete (≥3 months)
- All references updated
- No active users (verified via metrics)
- Migration path documented

### 6.2 Removal Checklist

```
☐ Deprecation period complete (≥3 months)
☐ Migration path documented and verified
☐ All cross-references removed
☐ Examples archived or migrated
☐ CLAUDE.md updated
☐ GAPS.md updated (gap closed)
☐ Role routing keywords removed
☐ Skills deprecated/removed
☐ Final backup created
```

### 6.3 Archive Structure

```
~/.claude/archived/
├── modules/
│   └── XX-domainname.md.archived.YYYYMMDD
└── examples/
    └── domainname.tar.gz
```

---

## Quick Reference: Domain Addition

**4-Phase Fast Track (for CLI-critical domains):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DOMAIN ADDITION QUICK REFERENCE                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: JUSTIFY (30 min)                                                  │
│  ☐ Calculate CLI relevance score (must be ≥60)                              │
│  ☐ List 3+ use cases                                                        │
│  ☐ Check for overlaps: grep -r "keyword" ~/.claude/modules/                 │
│  ☐ Estimate effort                                                          │
│                                                                              │
│  PHASE 2: CREATE (1-2h)                                                     │
│  ☐ Create module: ~/.claude/modules/XX-name.md                              │
│  ☐ Create examples: ~/.claude/examples/name/ (≥3 files)                     │
│  ☐ Follow module template                                                   │
│                                                                              │
│  PHASE 3: INTEGRATE (30 min)                                                │
│  ☐ Add to CLAUDE.md module list                                             │
│  ☐ Add keywords to role-routing.md                                          │
│  ☐ Cross-reference related modules                                          │
│  ☐ Create skill if applicable                                               │
│                                                                              │
│  PHASE 4: VERIFY (30 min)                                                   │
│  ☐ Test module loading                                                      │
│  ☐ Test role routing                                                        │
│  ☐ Update GAPS.md                                                           │
│  ☐ Run sync.sh                                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Domain Naming Convention

**Format:** `XX-domainname.md`

| Range | Category |
|-------|----------|
| 00-09 | Core (architecture, maturity) |
| 01-09 | Compliance, Security |
| 10-19 | Technical domains (DevOps, Engineering) |
| 20-29 | Specialized (Education, Writing) |
| 30-39 | Advanced (Low-level, Research) |
| 40-49 | Integration (MCP, Skills, Orchestration) |

---

**Version History:**
- v1.0.0 (2026-02-05): Initial release
