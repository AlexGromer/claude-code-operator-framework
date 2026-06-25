# Rule: Task Execution
# Auto-loaded by Claude Code from ~/.claude/rules/

## Tiers
| Score | Tier | Action | Agents |
|-------|------|--------|--------|
| <20 | Simple | Execute directly | No agents |
| 20-65 | Standard | Goal/Result/Criteria, freeze criteria | Single Task() or parallel Task() calls |
| 65-80 | Complex | EnterPlanMode, decompose | Implicit team — coordinated named teammates |
| >80 | Critical | EnterPlanMode + user approval | Implicit team + plan approval |

Standard tasks → implicit teams допустимы, если требуется координация между агентами.

## Response (all tiers)
1. Routing (every response, 1 line): `⚙ Role | CONFIDENCE | approach` — Role = конкретный специалист, not "Direct answer"
2. Plan (Standard+, if significant)
3. Implementation
4. Summary (Standard+)

## Subagents & Teams
haiku=formatting, sonnet=development, opus=critical logic.
Nested subagents are allowed up to 5 levels (v2.1.172). Spawn subagents and teammates with mode: "acceptEdits".

Teams are implicit now — `TeamCreate`/`TeamDelete` were removed in v2.1.178. Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json `env`, then spawn teammates directly via the Agent tool, passing a `name` per teammate (no `team_name`).

**Team composition — existing agent types as teammates:**
```
Agent(subagent_type="Explore",         name="researcher")
Agent(subagent_type="deep-reviewer",   name="reviewer")
Agent(subagent_type="general-purpose", name="implementer")
Agent(subagent_type="test-writer",     name="tester")
Agent(subagent_type="soc-analyst",     name="analyst")
```
Any of 102 custom agents or built-in types (Explore, Plan, general-purpose) can be a teammate.
Spawn as many teammates as the task requires.

**Rules:**
- Spawn teammates with mode: "acceptEdits".
- The lead (main process) creates TaskCreate items, spawns named teammates, and collects results.
- Address a running teammate via SendMessage (by name); stop it via SendMessage when done.
- Background teammates: `run_in_background: true` (non-blocking).

## Agent Reporting
При запуске агентов/команд — сообщать пользователю:

Формат запуска:
"Запускаю [N] агентов: [имя1] (задача), [имя2] (задача)..."

Формат завершения:
"Агент [имя] завершил: [краткий результат]"

Для команды тиммейтов (implicit team):
"Создаю команду '[имя]': [N] тиммейтов — [тип1](задача), [тип2](задача)..."

При параллельном запуске Task():
- Перед запуском: перечислить все задачи
- При получении результатов: "[имя] готов (N из M)"
- После всех: общий summary

Если задача требует агента/навыка, которого нет в 102 доступных:
- Сообщить: "Для задачи X нет специализированного агента. Используется general-purpose."
- Записать в GAPS.md: GAP-AGENT-XXX — отсутствующий тип агента

## Post-Plan Workflow (Plan → Execution Bridge)

After PlanMode produces approved plan with atomic tasks:

### Step 1: Task Extraction
Each plan step → task record with: ID, description, files[], dependencies[], domain hint.

### Step 2: Atomic Task Scoring
Atomic tasks from plan are re-scored individually (NOT at plan-level):
- Single file, simple change → Simple (<20) → direct execution, no agent
- Multi-concern, needs testing → Standard (20-65) → single Task() agent
- Cross-cutting or architectural → Complex (65+) → rare for truly atomic; re-decompose if hit

### Step 3: Dependency DAG & Wave Grouping
Build execution waves from dependency graph:
1. **DAG**: task dependencies form directed acyclic graph
2. **Waves**: tasks with no unmet dependencies → same wave (parallel-safe)
3. **Domain clustering**: same-domain tasks in one wave → batch to single agent
4. **Resource cap**: max 5 parallel agents per wave (context/cost control)

Wave formation rules:
- Wave N contains tasks whose ALL dependencies are in Waves 0..N-1
- Within wave: group by agent type (domain affinity)
- Cross-domain wave → parallel agents, each for their domain
- Single-domain wave → one agent handles batch

### Step 3.5: Wave-Level Scoring (Batch Uplift)
After DAG grouping, re-score each wave: `wave_score = max(max(task_scores), sum(task_scores)*0.4, task_count*8)`

Uplift triggers (any one promotes tier): 3+ same-domain tasks, 4+ files, shared setup, 2+ domains → implicit team.

### Step 4: Agent Selection per Wave
Selection uses **wave_score** (not individual task scores):

| Wave score | Wave composition | Execution mode |
|-----------|-----------------|----------------|
| <20 | 1-2 Simple tasks, ≤2 files | Direct execution (no agent) |
| 20-40 | 3+ Simple same-domain OR 1-2 Standard | Single Task(subagent_type=domain_agent) |
| 40-65 | Mixed tasks OR 4+ files | Parallel Task() calls per domain |
| 65+ | Cross-domain OR needs coordination | Implicit team with domain-specific teammates |
| any | Has explicit review/test step | Implicit team: implementer + reviewer + tester |

### Step 5: Wave Execution
```
for wave in waves:
    report: "Wave N/M: [task_count] задач, [agent_count] агентов"
    launch agents (parallel where independent)
    collect results
    verify wave completion criteria
    if failure: retry once → stop + report
    mark completed in BACKLOG.md
```

### Step 6: Backlog Synchronization
- Plan approved → ALL tasks added to BACKLOG.md with: priority, wave#, agent hint
- Wave completed → mark [x] for all wave tasks
- Session end → pending tasks persist for next session
- Format: `- [ ] [W1] Task description (P1) @agent-type — YYYY-MM-DD`

### Without Plan (Standard tasks)
- Task identified → scored → if Standard+, add to BACKLOG.md directly
- Execute via single agent or parallel Task() calls
- Mark [x] on completion

### Backlog Rotation
- Active section: max 30 items
- Completed tasks → Completed Archive (with date)
- Archive cleanup: keep last 50, older → delete
- Deferred: tasks postponed by user decision (review monthly)
- Stale detection: P3 open > 14 days, P2 > 7 days → escalate or defer

## Progressive Scope Tracking (Dynamic Re-scoring)

For Standard+ tasks: **always** call `mcp__tools-mcp__scope_track({file_path})` after
each Edit/Write, and `mcp__tools-mcp__scope_status` at start + end of task.

Track during execution: `files_modified` (Edit/Write only), `domains_touched`, `subtasks_emerged`.
Re-score: `live_score = max(initial_score, files_modified×12, domains_touched×25, subtasks_emerged×15)`

| Trigger | Action |
|---------|--------|
| `files_modified >= 4` | PAUSE, report scope, enter Plan Mode |
| `files_modified >= 6` AND `domains >= 2` | PAUSE, recommend an implicit team |
| `subtasks_emerged >= 3` | Re-score, /decompose if live_score >= 40 |
| Tier upgrade | Report: "Scope escalated: [old] → [new]. [reason]." |

Protocol: PAUSE → report to user → propose action → **user decides** (don't auto-escalate silently).

## Subagent Safety Escalation

When a subagent/teammate hits a permission boundary:
1. Don't retry the blocked action
2. Send `SendMessage` to the lead with: action description, target path, reason needed
3. The lead either executes the action in the main session, or denies with an explanation
4. Subagent continues with the result

Actions that trigger escalation:
- Edit/Write outside shared dirs and project path
- Bash commands in `ask` tier (nmap, docker run, terraform apply, kubectl apply, rm, sudo)
- Any action returning permission denied

Actions that are absolute blocks (no escalation):
- Commands in `deny` tier (rm -rf /, dd, mkfs, shutdown, reboot)
- Read of secrets (.env, credentials, ssh keys)

## PlanMode Entry Checklist
Before writing plan: 1) FILEMAP.md 2) BACKLOG.md 3) ARCHITECTURE.md (if exists) 4) related files 5) verify scope.

## Errors
Retry once with a different approach. 2nd fail → stop, suggest an alternative.
5+ reads without output → delegate. 4+ files → Plan Mode.

## Language
Russian → Russian (tech terms in English). English → English.

## Criteria Freeze
Once agreed, iterate the implementation. Keep criteria fixed — don't change them to match output.
Tool: `mcp__tools-mcp__criteria_*` (criteria_freeze, criteria_unfreeze, criteria_check, criteria_list)

## Task Tracking (BACKLOG.md via MCP)

> See also: `~/.claude/rules/mcp-preferred-operations.md` — полные правила MCP usage.

Standard+ tasks: use `mcp__backlog-mcp__*` tools, не ручной Edit.

**Format (from plan):** `- [ ] [W1] Task description (P1) @agent-type — YYYY-MM-DD`
**Format (standalone):** `- [ ] Task description (P2) — YYYY-MM-DD`
**Completed:** автоматически через `mcp__backlog-mcp__backlog_complete` (moves to `## Completed Archive`).

**Правильный workflow**:
- Session start → `mcp__backlog-mcp__backlog_stats` для count pending
- Plan approval → `mcp__backlog-mcp__backlog_add` для каждой атомарной задачи (wave, priority, agent_hint параметры)
- Task done → `mcp__backlog-mcp__backlog_complete({task_id: "substring"})` (автоматически переносит в Archive)
- Weekly rotation → `mcp__backlog-mcp__backlog_rotate` (если Active > 30, overflow → Deferred)
- Session end → pending tasks персистятся в файле для следующей сессии

**Anti-pattern**: ручная Edit BACKLOG.md для change `[ ]` → `[x]` оставляет задачу в
Active section. MCP считает such tasks как active. Используй `backlog_complete` —
это автоматически перемещает в Completed Archive.

Keep < 30 active items (enforced `backlog_rotate`). Completed Archive > 50 → prune oldest.
