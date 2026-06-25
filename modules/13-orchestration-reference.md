# Module: Subagent Orchestration Reference
# On-demand reference: Load when implementing multi-agent workflows
# Version: 2.0.0 | Rewritten: 2026-02-25 (compact, project-specific only)

---

## 1. Model Selection Matrix

| Model | Cost | Speed | Use For |
|-------|------|-------|---------|
| **haiku** | 1x | fast | Formatting, data extraction, log parsing, documentation, research/exploration |
| **sonnet** | 15x | medium | Standard dev, bug analysis, test writing, code review, infrastructure |
| **opus** | 75x | slow | Security audits/pentesting, critical architecture decisions, final review |

**Hybrid strategy (recommended):** Research (haiku) → Implement (sonnet) → Validate (opus if critical)
Total: ~20x vs 75x all-opus.

**Domain defaults:**

| Domain | Model | Rationale |
|--------|-------|-----------|
| Security pentesting | opus | High-stakes, precision required |
| Security audit | sonnet | Balanced accuracy |
| DevOps production | sonnet | Infrastructure reliability |
| DevOps dev/staging | haiku | Cost-optimized |
| OSINT / research | haiku | Fast, cheap exploration |
| Documentation | haiku | No reasoning required |
| Code review | sonnet | Quality matters |
| ML/data analysis | sonnet | Moderate complexity |

Cache reads: 90% discount — use consistent prompt prefixes.
Output tokens cost 5x input — keep subagent outputs concise.

---

## 2. Our Hard Rules

- **Nesting up to 5 levels** (v2.1.172) — agents may spawn subagents, up to 5 deep. Keep it shallow; flatten when one orchestrator level suffices.
- **>10 subagents = anti-pattern** — coordination overhead exceeds parallelism gain. Sweet spot: 3-7.
- **Data via files, not prompts** — pass `/tmp/claude-<uid>/scratchpad/file.json`, not inline blobs.
- **Parallel = single message** — multiple Task calls in one response run in parallel. Sequential = separate responses.
- **Validate subagent output** — never trust blindly; check result before proceeding.

---

## 3. Our Agent Catalog (101 agents)

Invoked via skill wrappers (auto) or Task tool (manual). Full list in `CLAUDE.md`.

| Group | Count | Example agents |
|-------|-------|----------------|
| Security | 11 | web-pentester, appsec-engineer, red-teamer, llm-security-engineer |
| OSINT/Intel | 6 | osint-recon, cybint-analyst, darkint-analyst |
| DFIR/Blue | 8 | incident-commander, soc-analyst, malware-analyst, log-analyst |
| DevOps | 11 | terraform-engineer, k8s-engineer, ci-cd-engineer, sre-engineer |
| Network | 2 | network-engineer, network-scanner |
| Development | 7 | web-developer, api-developer, db-developer |
| Data/ML | 5 | ml-engineer, mlops-engineer, data-analyst |
| Testing/QA | 3 | test-writer, qa-automation-engineer, performance-engineer |
| Low-level | 8 | kernel-developer, embedded-developer, binary-analyst |
| Compliance | 3 | eu-compliance, rf-compliance |
| Business/Plan | 7 | system-architect, project-planner, risk-analyst |
| Legal/Business | 7 | legal-counsel, accountant, corporate-lawyer |
| Meta | 9 | validator, decomposer, routing-orchestrator, cost-budget |
| Internal | 6 | agent-factory, gap-manager, pipeline-state |

---

## 4. Auto-Invocation Chain (Skills → Agents)

```
User prompt
    → keyword match in skill description
    → skill wrapper (~/.claude/skills/<name>.md)
    → context: fork  (isolated execution)
    → agent: <name>  (delegates to ~/.claude/agents/<name>.md)
    → result returned
```

81 of 87 skills use `context: fork` + `agent:` for full isolated methodology.
6 utility skills (commit, pr, sync, gap, report, session-health) run in main context.

**Manual invocation via Task tool:**
```python
Task(
    subagent_type="general-purpose",
    model="sonnet",
    description="Short summary",
    prompt="""
    CONTEXT: [minimal required context]
    TASK: [specific task]
    OUTPUT FORMAT: [expected format / output file path]
    """
)
```

**Background execution:**
```python
agent_id = Task(run_in_background=True, prompt="Long task...")
# Result available via TaskOutput(task_id=agent_id)
```

---

## 5. Data Passing Patterns

**File-based handoff (always preferred for >500 chars):**
```
Agent 1 → writes /tmp/claude-<uid>/scratchpad/output.json
Agent 2 → reads /tmp/claude-<uid>/scratchpad/output.json
```

**Resume (sequential phases with shared context):**
```python
result1 = Task(prompt="Phase 1: Analysis → write analysis.json")
result2 = Task(resume=result1.agent_id, prompt="Phase 2: Implement from analysis.json")
```

**In-prompt data:** Only for <500 chars, simple values (IDs, flags, short strings).

---

## 6. Cost Budget Targets

| Operation | Target Cost | Model Stack |
|-----------|-------------|-------------|
| Quick lookup / formatting | <$0.01 | haiku |
| Standard feature implementation | <$0.50 | sonnet |
| Security audit (full) | <$2.00 | haiku+sonnet+opus |
| Multi-service refactoring | <$2.00 | haiku+sonnet+opus review |
| OSINT reconnaissance | <$0.30 | haiku |
| Code review (PR) | <$0.20 | sonnet |

**Cost monitoring:**
```bash
python ~/.claude/evaluation/costs/agent_cost_tracker.py --report session
```

**Cost anti-patterns:**
- Opus for everything → use haiku/sonnet, opus only for critical review
- 10 agents × 1 item → 1 agent × 10 items (batching)
- Large JSON in prompts → write to file, pass path
- No prompt caching → use consistent prefixes for repeated calls

---

## 7. Anti-Patterns Checklist

| Anti-Pattern | Fix |
|--------------|-----|
| >10 subagents | Batch items; 3-7 is the sweet spot |
| Excessive nesting (>5 levels) | Keep shallow; flatten when one orchestrator level suffices |
| Opus for all tasks | Match model to task criticality |
| Large data in prompts | Write to scratchpad, pass file path |
| No output validation | Always check subagent result before using |
| Spawning agents without skill | Use skill wrapper for consistent methodology |
| Agent without domain module hint | Agents reference modules/NN-name.md in Workflow |
