# Module: Implementation Workflow
# On-demand reference: Load when implementing tasks from ROADMAP
# Version: 2.0.0 | Compacted: 2026-02-25

---

## 8-Phase Workflow

```
┌──────────┐   ┌───────────┐   ┌───────────┐   ┌──────────┐
│ 1.PLAN   │──►│2.IMPLEMENT│──►│3.INTEGRATE│──►│4.DOCUMENT│
└──────────┘   └───────────┘   └───────────┘   └──────────┘
                                                      │
┌──────────┐   ┌──────────┐   ┌─────────┐   ┌────────────┐
│ 8.REPORT │◄──│  7.SYNC  │◄──│6.COMMIT │◄──│  5.VERIFY  │
└──────────┘   └──────────┘   └─────────┘   └────────────┘
              (Loop back to IMPLEMENT if VERIFY fails)
```

---

## Phase Checklists

### 1. PLAN
```
☐ Read Gap description in GAPS.md + Task in ROADMAP
☐ Define: what runs automatically (hook/anacron/trigger)
☐ Define: data flow (storage path, alert conditions, feedback)
☐ Define: which existing modules to reuse vs create new
☐ List dependencies (hooks, data files, external modules)
☐ Write Success Criteria (freeze before implementing)
```

### 2. IMPLEMENT
```
☐ Write module: ~/.claude/evaluation/[module_name].py
☐ Write tests:  ~/.claude/evaluation/tests/test_[module_name].py
☐ Run pytest -v, confirm >80% coverage
☐ Write hook integration code (if hook needed)
☐ Add CLI interface with argparse + --help
☐ Docstrings + usage examples in module header
```

**Module header format:**
```python
#!/usr/bin/env python3
"""
[Module Name] — GAP-XXX-YYY
[What it does, one line]

Usage:
    python3 module_name.py --report [daily|weekly|monthly]

Version: 1.0.0
"""
```

### 3. INTEGRATE
```
☐ Register hook in ~/.claude/settings.json (if hook needed)
☐ Add anacron job in ~/.anacron/anacrontab (if periodic)
☐ Register in metrics_tracker.py AVAILABLE_MODULES (if eval module)
☐ Test automatic execution (simulate hook / trigger manually)
☐ Verify data writes to correct path (data/*.jsonl)
☐ Verify alerts fire under expected conditions
```

**settings.json hook entry pattern:**
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "pattern",
      "hooks": [{"type": "command",
                 "command": "python3 ~/.claude/evaluation/[module].py --hook",
                 "timeout": 5000}]
    }]
  }
}
```

**Hook event types:** `PreToolUse` | `PostToolUse` | `PostToolUseFailure` | `SessionStart` | `SessionEnd` | `UserPromptSubmit` | `PreCompact` | `Stop` | `SubagentStop`

### 4. DOCUMENT
```
☐ GAPS.md: status 🟡 Open → ✅ Resolved, add date + implementation details
☐ ROADMAP.md: mark task Complete, add actual effort, update progress table
☐ CLAUDE.md: update module table + version (if architecture changed)
☐ docs/guides/*.md: update if workflow/process changed
☐ CHANGELOG.md: add version entry
```

**GAPS.md resolved entry format:**
```
#### GAP-XXX-YYY: [Title] ✅
- **Status**: ✅ Resolved (YYYY-MM-DD) | **Priority**: P[N]
- **Implementation**: [module].py ([N] lines) — [brief description]
- **Tests**: [N] pytest tests | **CLI**: `python [module].py --option`
- **Integration**: [hooks/anacron/manual] | **Version**: v1.0.0
```

### 5. VERIFY
```
☐ Module runs automatically (hook fires / anacron triggers)
☐ Data saves to correct path in right format (no data loss)
☐ Alerts appear under expected conditions
☐ settings.json is valid JSON: python -c "import json; json.load(open('$HOME/.claude/settings.json'))"
☐ pytest -v passes with >80% coverage
☐ All file paths exist and permissions are correct
```

**Quick verify commands:**
```bash
python ~/.claude/evaluation/[module].py --report weekly
echo '{"tool_name":"Read","arguments":{}}' | python ~/.claude/evaluation/hooks/[hook].py
cd ~/.claude/evaluation && pytest -v
```

### 6. COMMIT
```
☐ Secrets scan: gitleaks detect --source . --verbose — HALT if found
☐ Verify .claude/ in .gitignore
☐ All tests pass
☐ git add [specific files only — never -A]
☐ git commit with conventional message (see format below)
☐ git push / open PR if required
```

**Commit message format:**
```
feat(evaluation): implement [module name] (Task N)

- Add [module].py with [key features]
- Add N pytest tests, coverage X%
- Integrate with [hooks/anacron]
- Resolve GAP-XXX-YYY

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

### 7. SYNC
```
☐ Run: /opt/claude-code-agent-addition/scripts/sync.sh --auto -m "feat: [description]"
☐ Verify all remotes updated, no conflicts
```

### 8. REPORT
```
☐ Post summary to chat: what done, files created/changed, integration, metrics
☐ Write task report (optional): /opt/project/docs/task_reports/task_N_report.md
```

---

## Quick Reference Checklist (Copy-Paste)

```markdown
## Task N: [Title] — GAP-XXX-YYY

### 1. PLAN
- [ ] Read gap + task description
- [ ] Define automation (trigger/hook/anacron)
- [ ] Define data flow (storage, alerts, feedback)
- [ ] Freeze success criteria

### 2. IMPLEMENT
- [ ] Write module + CLI
- [ ] Write tests (>80% coverage)
- [ ] Run pytest -v

### 3. INTEGRATE
- [ ] Add to settings.json / anacrontab
- [ ] Register in metrics_tracker.py
- [ ] Test automatic execution

### 4. DOCUMENT
- [ ] GAPS.md: mark resolved
- [ ] ROADMAP.md: mark complete
- [ ] CLAUDE.md / CHANGELOG.md: update version

### 5. VERIFY
- [ ] Auto-execution works
- [ ] Data saves correctly
- [ ] settings.json valid JSON
- [ ] All tests pass

### 6. COMMIT
- [ ] gitleaks scan clean
- [ ] .claude/ in .gitignore
- [ ] Commit with conventional message

### 7. SYNC
- [ ] Run sync.sh

### 8. REPORT
- [ ] Summary to chat
```
