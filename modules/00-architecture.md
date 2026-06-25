# Module: Agent Architecture Framework
# Version: 2.0.0 | Updated: 2026-02-25 | Auto-loaded: No

## 1. 8-Layer Model

```
Layer 8: USER INTERFACE      — CLI, output formatting, user feedback
Layer 7: SESSION MANAGEMENT  — Context history, health checks, token tracking
Layer 6: ORCHESTRATION       — Task decomposition, subagent spawning, model routing
Layer 5: REASONING           — CoT/ReAct/ToT, planning, anti-hallucination
Layer 4: TOOLS & ACTIONS     — Bash/Read/Write/Edit/Grep, MCP servers, skills
Layer 3: KNOWLEDGE           — Modules (on-demand), rules (auto), examples (on-demand)
Layer 2: SAFETY & SECURITY   — Authorization levels, mandatory checks, hooks
Layer 1: FOUNDATION          — Output Styles (7, PRIMARY), CLAUDE.md, CORE_INSTRUCTIONS.md, managed policy, settings.json
```

**Priority hierarchy (L1):**
```
Output Style (PRIMARY, system-prompt level) > CORE_INSTRUCTIONS.md (--append-system-prompt) > managed /etc/claude-code/CLAUDE.md > CLAUDE.md > rules/ (auto) > modules/ (on-demand) > hooks additionalContext > built-in
```

**Auto-loaded:** CLAUDE.md, rules/, hooks/, MCP, agents, skills
**On-demand (manual):** modules/, examples/

---

## 2. Extension Points

| Layer | What to Add | Where |
|-------|-------------|-------|
| L7 | Session hooks | `hooks/Session*.py` → `settings.json` |
| L6 | Model routing rules | `evaluation/costs/model_router.py` |
| L4 | MCP servers | `~/.claude.json` → `projects."*".mcpServers` (LOCAL scope) |
| L4 | Skills (workflow wrappers) | `~/.claude/skills/*.md` (`context: fork` + `agent:`) |
| L4 | CLI tools | `~/.claude/tools/*.py` (2 active) |
| L3 | Domain modules | `~/.claude/modules/NN-name.md` |
| L3 | Few-shot examples | `~/.claude/examples/*/` |
| L2 | PreToolUse/PostToolUse hooks | `~/.claude/hooks/*.py` → `settings.json` || L1 | Critical override rules | `~/.claude/CORE_INSTRUCTIONS.md` (≤80 lines) |
| L1 | New agents | `~/.claude/agents/<name>.md` (auto-loaded) |

**Adding a new agent (quick steps):**
1. Create `~/.claude/agents/<name>.md` with 10-field template
2. Create matching skill `~/.claude/skills/<name>.md` with `context: fork` + `agent: <name>`
3. Update CLAUDE.md agent catalog + MEMORY.md component status

---

## 3. Diagnostic Quick Reference

| Symptom | Layer | Check |
|---------|-------|-------|
| Output not rendering | L8 | Terminal markdown support |
| Session slow / context lost | L7 | History size (`session_health_check.py`), reopen |
| High API costs | L6 | Model selection (use haiku for simple tasks) |
| Subagent fails silently | L6 | Prompt clarity, tool availability |
| Poor reasoning / hallucinations | L5 | Prompting technique, add CoVe / WebSearch |
| Tool not found / MCP error | L4 | `claude mcp list` — verify LOCAL scope |
| Skill not auto-invoked | L4 | Check `context: fork` + `agent:` in skill file |
| Wrong domain knowledge | L3 | Load module explicitly: `Read ~/.claude/modules/NN.md` |
| Operation blocked by hook | L2 | Authorization level, check hook output |
| Rules ignored | L1 | Verify CORE_INSTRUCTIONS.md, check settings.json hooks |
| Agent not found | L1 | File exists in `~/.claude/agents/`? Name matches skill? |

**Diagnostic commands:**
```bash
claude mcp list                                          # Verify MCP (LOCAL scope)
cat ~/.claude/evaluation/data/current_session_id        # Session ID
echo '{"tool_name":"Bash"}' | python ~/.claude/hooks/hook_name.py  # Test hook
mcp__profile-mcp__profile_load(profile_name="<profile>")           # Load domain MCP
```

---

## 4. Data Flow

```
User prompt
    │
    ▼
UserPromptSubmit hook → MCP profile rotation, session health, criteria check
    │
    ▼
Layer 1 (Foundation): CLAUDE.md + rules/ + CORE_INSTRUCTIONS → identity & policies
    │
    ▼
Layer 5 (Reasoning): keyword match → skill description → context:fork → agent dispatch
    │
    ├── Layer 3 (Knowledge): module hint in agent → Read modules/NN-name.md
    ├── Layer 2 (Safety): PreToolUse hooks → scope/dry-run/budget check
    │
    ▼
Layer 4 (Tools): Bash / MCP / WebSearch / WebFetch execute
    │
    ▼
PostToolUse hooks → evidence log (DFIR), cache (OSINT), code review (Write/Edit)
    │
    ▼
Layer 6 (Orchestration): subagent result → aggregate → response
    │
    ▼
Layer 7 (Session): token tracking, health update
    │
    ▼
Layer 8 (UI): formatted output to user
```

### Auto-Invocation Chain

```
User prompt → UserPromptSubmit hook → workflow_autoloader:
  1. Keyword match → domain detection → module context injection
  2. Complexity score → tier classification (Simple/Standard/Complex/Critical)
  3. Skill auto-match (by description keywords) → context: fork → agent execution
  4. Agent loads module hint → full methodology → result to main context
```
Skill matching: by description keywords, not by name.
Agent conflicts: routing-orchestrator agent resolves ambiguous routing.

**Hook event map (v6.0):**
```
SessionStart(4+4) → SessionEnd(1) → UserPromptSubmit(1)
PreToolUse(3) → PostToolUse(3) → PostToolUseFailure(1)
PreCompact(1)
```
Total: 14 settings.json registrations + 4 ~/.claude.json hooks

---

## 5. Complexity Scoring (workflow_autoloader.py)

| Factor | Max pts | Logic |
|--------|---------|-------|
| Word count | 25 | >80w=25, >30=15, >10=5 |
| Domain detection | 30 | 3+ domains=25, 2=15, 1=8; bonus +5 if top≥8 |
| Tool mentions | 20 | count×5, cap 20 (24 tool keywords) |
| Action complexity | 15 | count×5, cap 15 (32 keywords incl. Russian) |
| Multi-step modifiers | 10 | count×5, cap 10 (10 conjunctions) |
| File count | 10 | count×3, cap 10 (file paths in prompt) |

**Tiers:**
| Score | Tier | Action |
|-------|------|--------|
| <20 | Simple | Execute directly, no ceremony |
| 20-65 | Standard | State Goal/Result/Criteria, freeze criteria |
| 65-80 | Complex | EnterPlanMode recommended, decompose |
| >80 | Critical | EnterPlanMode required, user approval |

---

## 6. Concurrency Model

| Resource | Access | Protection |
|----------|--------|------------|
| `~/.claude.json` | R/W | profile-mcp (Go MCP server) |
| `budget_spending.jsonl` | Append | `fcntl.flock` (unified_cost_hook) |
| `session_continuity.jsonl` | Append | `fcntl.flock` (session_end_hook) |
| Git working tree | R/W | Git index.lock |
| `/opt/<project>/` | R/W | Convention: 1 session per project |

**Hook error handling:** timeout 5s → log error → continue (never block tool execution)

**Hook Overhead** (measured 2026-02-25, v6.0 after cleanup):

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| PreToolUse hooks/call | 9 | 3 | -67% |
| PostToolUse hooks/call | 13 | 3 | -77% |
| Total registrations | 33 | 14 | -58% |
| Latency per Bash call | ~1872ms | ~430ms | -77% |

Benchmark tool: `python ~/.claude/tools/hook_benchmark.py`
Thresholds: <500ms OK | 500-2000ms optimize | >2000ms consolidate

---

## 7. Workflow Architecture (3 levels)

```
Meta-workflow (module 14): PLAN → IMPLEMENT → INTEGRATE → DOCUMENT → VERIFY → COMMIT → SYNC → REPORT
  └── Domain workflows (modules 18, 22): tool→MCP mappings per domain
      └── Agent workflows (agents/*.md): specialized steps per agent role
```

**Meta-workflow** (module 14-implementation): 8-phase universal workflow for all tasks.
**Domain workflows** (modules 18-dfir, 22-security): aggregate tool pipelines per domain.
**Agent workflows** (102 agents): concrete step-by-step instructions per specialization.

**Verification gates:**
- After Write/Edit → `code_review_hook` (automatic)
- Before commit → `gitleaks detect` (mandatory-checks.md)
- Before push → tests pass

**Mandatory workflow elements (agent-level):**
1. Authorization check (READ/NETWORK_ACTIVE/etc.)
2. Input validation
3. Execution steps with tools
4. Output format
5. Verification
6. Cleanup

---

## 8. Agent Teams (Experimental)

Enable: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json `env`.

**Architecture**: Lead session + N teammates. Each teammate = independent Claude Code
instance (own context, loads CLAUDE.md/MCP/skills — does not inherit lead's history).

**Mechanism (v2.1.178+)**: `TeamCreate`/`TeamDelete` were removed. Teams are now implicit —
spawn teammates directly via the Agent tool, passing a `name` per teammate (`team_name` is
accepted but ignored). Coordination tools remain:
- `TaskCreate` / `TaskUpdate` / `TaskList` — shared task list with file-locking
- `SendMessage` — address a running teammate by name (or broadcast)

**Display**: `teammateMode: auto|in-process|tmux` in settings.json.

**Hook events**: `TeammateIdle` (exit 2 keeps working), `TaskCompleted` (exit 2 blocks).

**Nesting**: nested subagents are allowed up to 5 levels (v2.1.172) — agents may spawn agents.

**vs Subagents**: Subagents report to caller only. Teammates communicate directly + self-coordinate via shared task list.

**`isolation: worktree`** — Subagent frontmatter field (not Agent Teams). Gives each subagent a temporary git worktree; auto-cleaned if no changes.

---

## 9. Experimental Env Vars

| Variable | Effect |
|----------|--------|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Enables Agent Teams |
| `ENABLE_TOOL_SEARCH=auto\|true\|false` | MCP tool search (auto at 10% context) |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` | Strips anthropic-beta headers |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` | Disables background subagent execution |
| `CLAUDE_CODE_DISABLE_1M_CONTEXT` | Disables 1M context window |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=N` | Auto-compact trigger at N% (default 95%) |
