# Gap Detection & Management Protocol

## Purpose

Автоматическое обнаружение, логирование и версионирование gaps в конфигурации.
Эта секция предназначена для добавления в `09-maturity.md` (Section 3.5+).

---

## Section X: Gap Detection Protocol

### X.1 Trigger Patterns

Claude автоматически детектирует gaps по следующим триггерам:

#### Category 1: Explicit User Signals
| Pattern (EN) | Pattern (RU) | Action |
|--------------|--------------|--------|
| "This isn't covered" | "Это не описано" | Log GAP |
| "Where is X?" | "Где тут X?" | Check module, log if missing |
| "Why isn't Y mentioned?" | "Почему нет Y?" | Log GAP |
| "Add support for Z" | "Добавь поддержку Z" | Log GAP as feature request |
| User corrects response | Пользователь исправляет | Log GAP + update |

#### Category 2: Claude Self-Detection
| Condition | Trigger | Action |
|-----------|---------|--------|
| No template found | Task matches domain but no template | Log GAP |
| Tool not in tech-stack | User mentions unknown tool | Log GAP |
| Standard not covered | Compliance standard not in 01-compliance | Log GAP |
| Low routing confidence | Confidence < 40% | Log potential GAP |
| Multiple clarifications | >2 clarifying questions needed | Log GAP |
| Fallback to training | Using general knowledge, not module | Log GAP |

#### Category 3: Coverage Failures
| Condition | Detection Method | Action |
|-----------|------------------|--------|
| Test coverage < 95% | Post-analysis check | Log GAP |
| Missing auth level | Tool in use but not in settings.json | Log GAP |
| No example | Common use case without example | Log GAP |
| Outdated version | Mentioned version != current | Log GAP |

#### Category 4: Structural Issues
| Condition | Detection Method | Action |
|-----------|------------------|--------|
| Module referenced not found | Link check | Log GAP (Critical) |
| Duplicate content | Cross-module analysis | Log GAP |
| Inconsistent terminology | Same concept, different terms | Log GAP |

### X.2 Gap Lifecycle States

```
┌──────────────────────────────────────────────────────────────────────────┐
│  STATE MACHINE                                                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  🔴 DETECTED ────► 📝 LOGGED ────► 📊 TRIAGED ────► 🔧 IMPLEMENTING      │
│                                         │                   │             │
│                                         │                   ▼             │
│                                         │              ✅ RESOLVED        │
│                                         │                   │             │
│                                         │                   ▼             │
│                                         │              ✔️ VERIFIED        │
│                                         │                   │             │
│                                         └───────────────────┘             │
│                                                    │                      │
│                                                    ▼                      │
│                                              📦 ARCHIVED                  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

| State | Description | Next States |
|-------|-------------|-------------|
| 🔴 DETECTED | Gap identified during work | LOGGED |
| 📝 LOGGED | Added to GAPS.md | TRIAGED |
| 📊 TRIAGED | Priority and category assigned | IMPLEMENTING |
| 🔧 IMPLEMENTING | Work in progress | RESOLVED |
| ✅ RESOLVED | Fix applied | VERIFIED |
| ✔️ VERIFIED | Fix confirmed working | ARCHIVED |
| 📦 ARCHIVED | Moved to resolved section | — |

### X.3 Gap Logging Procedure

**При обнаружении gap, Claude выполняет:**

```
STEP 1: IDENTIFY
├─► What is missing/incorrect?
├─► Which module(s) affected?
├─► What triggered detection?
└─► What is the impact?

STEP 2: CLASSIFY
├─► Category: Tool | Coverage | Template | Compliance | Structure
├─► Priority: 
│   ├─► P1: Blocks work or critical functionality
│   ├─► P2: Significant workaround needed
│   └─► P3: Minor inconvenience
└─► Affected modules

STEP 3: LOG
├─► Assign GAP-XXX ID (next sequential)
├─► Fill template in GAPS.md
├─► Update metadata (counts)
└─► Notify user:
    
    ┌─ GAP DETECTED ───────────────────────────────────────┐
    │ ID: GAP-XXX                                          │
    │ Title: [Brief description]                           │
    │ Priority: P1/P2/P3                                   │
    │ Module: [Affected module]                            │
    │ Status: Logged to GAPS.md                            │
    │                                                      │
    │ Continue with available workaround? [Y/n]            │
    └──────────────────────────────────────────────────────┘

STEP 4: CONTINUE
├─► If workaround exists: proceed with task
├─► If no workaround: explain limitation
└─► At end of response: summarize gaps detected
```

### X.4 Gap Resolution Procedure

**При закрытии gap:**

```
STEP 1: IMPLEMENT FIX
├─► Make changes to affected module(s)
├─► Update tech-stack if needed
├─► Update settings.json if needed
└─► Update routing keywords if needed

STEP 2: VERIFY
├─► Test the fix manually
├─► Check no regressions
└─► Confirm user acceptance

STEP 3: UPDATE GAPS.md
├─► Change status to ✅ RESOLVED
├─► Fill resolution details:
│   ├─► Resolved in: v[X.Y.Z]
│   ├─► Commit: [description]
│   └─► Verified: [date]
├─► Move to Archive section
└─► Update statistics

STEP 4: VERSION BUMP
├─► Determine bump type:
│   ├─► PATCH: Single gap, minor fix
│   ├─► MINOR: New tool/section, multiple gaps
│   └─► MAJOR: New module, structural change
├─► Update GAPS.md version
├─► Update Changelog
└─► Update affected module versions
```

### X.5 Versioning Protocol

**GAPS.md Version Format:** `MAJOR.MINOR.PATCH`

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Initial creation | 1.0.0 | First version |
| New gap logged | — | No version change (tracking) |
| Single gap resolved | PATCH | 1.0.0 → 1.0.1 |
| Multiple related gaps resolved | MINOR | 1.0.1 → 1.1.0 |
| Backlog restructure | MAJOR | 1.1.0 → 2.0.0 |

**Commit Message Format:**
```
Type: fix | feat | chore | refactor
Scope: gaps | <module-name>

Examples:
- chore(gaps): log GAP-009 missing TypeScript examples
- fix(gaps): resolve GAP-001 Helm coverage
- feat(devops): add Helm section, resolves GAP-001
```

### X.6 Integration with Reasoning Pipeline

Добавить в CLAUDE.md между шагами EXECUTE и SUMMARIZE:

```
REASONING PIPELINE v3.3
├── ...
├── 9. EXECUTE    → Implement with explanations
│       ↓
├── 10. GAP CHECK
│       ├─► Scan for trigger patterns during execution
│       ├─► If gap detected:
│       │   ├─► Log to GAPS.md
│       │   ├─► Notify user with GAP DETECTED box
│       │   └─► Continue if workaround available
│       └─► At response end: list any gaps found
│       ↓
├── 11. AUTO-COMMIT (NEW)
│       ├─► If gap resolved OR config improved:
│       │   ├─► Create backup snapshot
│       │   ├─► Prepare diff for modified files
│       │   ├─► Show User Confirmation UI
│       │   └─► If approved:
│       │       ├─► Determine version bump (PATCH/MINOR/MAJOR)
│       │       ├─► Update CHANGELOG.md
│       │       ├─► Git commit with conventional message
│       │       ├─► Git push to remote
│       │       └─► Update GAPS.md resolution details
│       └─► (See: 09-maturity.md Section 9)
│       ↓
└── 12. SUMMARIZE → What was done, decisions, commits made, next steps
```

### X.7 Integration with Automated Improvement Protocol

При переходе gap в статус ✅ RESOLVED, автоматически запускается workflow:

```
GAP RESOLVED
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AUTO-COMMIT TRIGGER                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Backup создаётся автоматически                                           │
│  2. Claude готовит diff всех изменённых файлов                              │
│  3. User Confirmation UI показывается пользователю:                          │
│     ┌─ PENDING CHANGES ──────────────────────────────────────────┐          │
│     │ Modified files:                                            │          │
│     │ [x] 09-maturity.md (+45 lines)                            │          │
│     │ [x] GAPS.md (GAP-001 resolved)                             │          │
│     │                                                            │          │
│     │ Version: 3.2.0 → 3.2.1 (PATCH)                            │          │
│     │ Commit: fix(gaps): resolve GAP-001 Helm coverage          │          │
│     │                                                            │          │
│     │ [Confirm All] [Select Files] [Cancel]                      │          │
│     └────────────────────────────────────────────────────────────┘          │
│  4. При подтверждении: version bump → changelog → commit → push             │
│  5. GAPS.md обновляется с commit reference                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Mapping Gap Priority → Version Bump:**

| Gap Priority | Fix Type | Version Bump |
|--------------|----------|--------------|
| P1 (Critical) | Usually feat | MINOR |
| P2 (Significant) | Usually fix | PATCH |
| P3 (Minor) | Usually chore | PATCH |
| Multiple gaps | Depends on scope | MINOR or MAJOR |

**GAPS.md Auto-Update при commit:**

```markdown
### GAP-XXX: [Title]
- **Status**: 🟢 Resolved
- **Priority**: P2
...
**Resolution:**
- Resolved in: **v3.2.1**
- Commit: **fix(gaps): resolve GAP-XXX [description]**
- Verified: **2025-01-20**
- Push: **gitlab.com/user/claude-config@abc1234**
```

### X.7 Gap Report Template (for GAPS.md)

```markdown
### GAP-XXX: [Short descriptive title]
- **Status**: 🔴 Open | 🟡 In Progress | 🟢 Resolved
- **Priority**: P1 | P2 | P3
- **Category**: Tool | Coverage | Template | Compliance | Structure
- **Detected**: YYYY-MM-DD
- **Module**: [Affected module(s)]
- **Trigger**: [Category: specific trigger]

**Description:**
[Detailed description of what's missing or incorrect]

**Impact:**
- [ ] Blocks task completion
- [ ] Requires workaround
- [ ] Inconvenience only

**Proposed Fix:**
[Specific changes needed with file references]

**Resolution:**
- Resolved in: v[X.Y.Z] | —
- Commit: [description] | —
- Verified: YYYY-MM-DD | —
```

### X.8 Notification Formats

**Gap Detected (inline):**
```
⚠️ Gap detected: [brief description] → Logged as GAP-XXX
```

**Gap Detected (box, for significant gaps):**
```
┌─ GAP DETECTED ───────────────────────────────────────┐
│ ID: GAP-XXX                                          │
│ Title: [Brief description]                           │
│ Priority: P1/P2/P3                                   │
│ Module: [Affected module]                            │
│ Status: Logged to GAPS.md                            │
└──────────────────────────────────────────────────────┘
```

**End of Response Summary:**
```
### Gaps Identified This Session
| ID | Title | Priority | Status |
|----|-------|----------|--------|
| GAP-XXX | [Title] | P1 | Logged |
```

### X.9 Automated Gap Discovery Commands

User может запросить проверку gaps и управление коммитами:

| Command | Action |
|---------|--------|
| "Check for gaps" | Analyze current context for missing coverage |
| "Review GAPS.md" | Show current backlog status |
| "Prioritize gaps" | Re-assess priorities based on usage |
| "Resolve GAP-XXX" | Start resolution workflow |
| "Archive resolved gaps" | Move verified gaps to archive |
| **"commit changes"** | Start auto-commit workflow for pending changes |
| **"show pending changes"** | Display uncommitted modifications |
| **"rollback to [timestamp]"** | Restore from backup snapshot |
| **"setup git"** | Run Initial Setup Wizard for git integration |

### X.10 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Gap detection rate | >90% | Gaps found vs gaps existing |
| Resolution time (P1) | <1 session | Time from detected to resolved |
| Resolution time (P2) | <3 sessions | Time from detected to resolved |
| Resolution time (P3) | <10 sessions | Time from detected to resolved |
| Verification rate | 100% | Resolved gaps verified |

---

## End of Gap Detection Protocol

**Note:** This section should be added to `09-maturity.md` as Section 3.5 or renumbered appropriately.

**Integration:** Auto-commit workflow defined in `09-maturity.md` Section 9 (Automated Improvement Protocol).
