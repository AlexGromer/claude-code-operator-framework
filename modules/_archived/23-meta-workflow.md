# Module: Meta-Workflow & Session Lifecycle
# Version: 1.0.0 | Updated: 2026-02-25 | Auto-loaded: No

## 1. Session Lifecycle

```
SessionStart → health check → drift check → classify prompt → execute/plan → verify → SessionEnd
```

**Start**: hooks inject reinforcement rules + frozen criteria + domain context.
**Classify**: complexity score → tier (Simple/Standard/Complex/Critical).
**Execute**: direct (Simple) or plan mode (Complex/Critical).
**End**: continuity record saved → session summary generated.

**Multi-session continuity**:
```
Session N end → save {task, files, progress, next_steps} → session_continuity.jsonl
Session N+1 start → load last record → inject "Previous session worked on: {task}"
```

**Context limit (PreCompact)**: save task state to MEMORY.md "In-Progress" → inject recovery prompt.

---

## 2. Workflow Hierarchy (3 levels)

```
Meta-workflow (this module): PLAN → IMPLEMENT → INTEGRATE → DOCUMENT → VERIFY → COMMIT → SYNC → REPORT
  └── Domain workflows (modules 18-dfir, 22-security): tool→MCP mappings per domain
      └── Agent workflows (agents/*.md): specialized steps per agent role
```

**Meta-workflow (8 phases)**:
1. **PLAN**: Classify task, freeze criteria (Standard+), decompose (Complex+)
2. **IMPLEMENT**: Execute steps with tools, agent delegation
3. **INTEGRATE**: Merge results, resolve conflicts
4. **DOCUMENT**: Update affected docs (CHANGELOG, MEMORY, comments)
5. **VERIFY**: Run tests, code review hook, manual check
6. **COMMIT**: Secrets scan, .gitignore check, commit
7. **SYNC**: Push (if requested), sync config
8. **REPORT**: Summary of changes, next steps

**Activation**: prompt → UserPromptSubmit → skill match → agent → workflow section → module hint.

---

## 3. Verification Gates

| Gate | Trigger | Tool |
|------|---------|------|
| Code review | After Write/Edit | `code_review_hook.py` (automatic) |
| Secrets scan | Before commit | `gitleaks detect` (mandatory-checks.md) |
| Tests | Before commit | `pytest` / `npm test` (if test suite exists) |
| .gitignore | Before commit | Check `.claude/` present |

---

## 4. Session Hygiene

**Signs of degraded session**:
- History >50K tokens → response quality drops
- Budget >80% spent → model downgrades
- >5 tool errors → possible hook/config issue
- Context >80% → auto-compact imminent

**Action**: Check `/session-health` → if REOPEN RECOMMENDED → save state, exit, start new session.

**Mandatory workflow elements per agent**:
1. Authorization check (READ/NETWORK_ACTIVE/etc.)
2. Input validation (target, scope, parameters)
3. Execution steps (tools + methodology)
4. Output format (report, artifacts, files)
5. Verification (tests, manual review)
6. Cleanup (temp files, connections)

---

## 5. Multi-Project & Multi-Session

**Multi-project isolation**:
- Memory: `~/.claude/projects/<hash>/memory/` (per-project)
- Working data: `/opt/<project>/` (isolated)
- MCP: global `~/.claude.json` + per-project `.mcp.json` override
- Settings: global `~/.claude/settings.json` + project `.claude/settings.json`

**Multi-session in one project**:
- File locking: `fcntl.flock` on shared files (budget, continuity, ~/.claude.json)
- Session ID: unique UUID, no collisions
- Git conflicts: resolve as normal git conflicts
- Recommendation: **1 session per project** for simplicity

**Database access**:
- Migrations: ONLY from one session (use migration lock)
- Read-only queries: safe from multiple sessions
- Write: through transaction isolation (DB-level)
- Test DBs: each session creates temp DB (pytest-postgresql pattern)

---

## 6. Save/Restore Protocol

**When to save** (triggers):
1. PreCompact hook: context >80% → automatic
2. SessionEnd: always → automatic
3. Session health: REOPEN RECOMMENDED → user-triggered
4. MCP rotation: before restart → mandatory

**What to save** (7 fields):
```json
{
  "task_description": "what we were doing",
  "files_modified": ["list", "of", "files"],
  "progress": "what was completed",
  "next_steps": "what to do next",
  "decisions_made": "key decisions to not re-debate",
  "git_state": {"branch": "main", "last_commit": "abc123"},
  "plan_file": "/path/to/plan.md (if EnterPlanMode was used)"
}
```

**Where**: `session_continuity.jsonl` (primary) + `memory/MEMORY.md` "In-Progress" (backup).
**How to restore**: SessionStart hook reads last record → injects as additionalContext.
