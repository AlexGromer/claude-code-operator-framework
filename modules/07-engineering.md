# Module 07: Software Engineering (compact)

Project-specific standards and targets. Generic knowledge (SOLID, DRY, design patterns,
test pyramids, log levels, MoSCoW, etc.) not repeated — Claude knows them.

---

## Test Coverage Targets

| Code Type | Minimum | Target |
|-----------|---------|--------|
| New features | 80% | 90% |
| Bug fixes | Lines touched + edge cases | 100% of fix |
| Refactoring | Maintain existing | No decrease |
| Utilities | 90% | 95% |
| Critical path | 95% | 100% |

Project test suite: `~/.claude/` — **1,640+ tests in 77 files** (`pytest`).
Run: `pytest -v --cov=. --cov-report=term-missing` from `~/.claude/`.

---

## Code Review Checklist (project standard)

- [ ] Logic correct, edge cases handled, no obvious bugs
- [ ] Follows project patterns (see existing agents/skills/hooks for style)
- [ ] No hardcoded secrets, no `.claude/` paths in committed code
- [ ] Input validation present, no injection vectors
- [ ] No N+1 queries, appropriate caching
- [ ] Tests cover the change; test names are clear
- [ ] `gitleaks detect --source . --verbose` passes (mandatory before commit)
- [ ] `.claude/` present in `.gitignore`

Hook `code_review_hook.py` runs automatically on Write/Edit — fix CRITICAL/HIGH before continuing.

---

## Performance Budgets (Claude Code agent operations)

```yaml
simple_query:
  max_latency_ms: 2000
  max_tokens: 50000
  max_cost_usd: 0.10

code_generation:
  max_latency_ms: 10000
  max_tokens: 150000
  max_cost_usd: 0.50

multi_file_refactor:
  max_latency_ms: 30000
  max_tokens: 500000
  max_cost_usd: 2.00
```

---

## Anthropic API — Project-Specific Patterns

### Adaptive Thinking (Opus 4.6+; on Opus 4.7/4.8 it is the ONLY mode — manual budget_tokens → 400)

Old `{"thinking": {"type": "enabled", "budget_tokens": 10000}}` is DEPRECATED.

```json
{
  "thinking": {"type": "adaptive"},
  "output_config": {"effort": "high"}
}
```

Effort levels: `max` (Opus only, no depth limit) | `xhigh` | `high` (default on Opus 4.8) | `medium` | `low`

| Task | Model | Effort |
|------|-------|--------|
| Data extraction | haiku | low |
| Code review | sonnet | medium |
| Security analysis | opus | high |
| Architecture design | opus | max |

### Batch API (50% cost savings for non-urgent work)

Use for: bulk analysis, multi-PR review, test generation, doc generation.
Processing time: 12–24 hours. Not for interactive sessions.

```python
batch = client.messages.batches.create(requests=[
    {"custom_id": "task-1", "params": {"model": "claude-sonnet-4-6", "max_tokens": 1024,
     "messages": [{"role": "user", "content": "..."}]}}
])
# Check: client.messages.batches.retrieve(batch.id)
# Results: client.messages.batches.results(batch.id)  (when processing_status == "ended")
```

Cost example: Sonnet $15/M tokens sync → $7.50/M batch (50% off).

### Context Window (Opus 4.8 / current — 1M ctx, 128k out; pricing below applies to current Opus)

| Range | Input | Output |
|-------|-------|--------|
| ≤200K tokens | $5/M | $25/M |
| >200K tokens | $10/M (2x) | $37.50/M (1.5x) |

128K output token limit. Use for: large codebase navigation, extended agent sessions.

---

## ADR Template

```markdown
# ADR-XXX: [Title]
**Date:** YYYY-MM-DD  **Status:** Proposed / Accepted / Deprecated

## Decision
[What was decided]

## Rationale + Alternatives Considered
1. Chosen approach — why
2. Alternative — pros/cons

## Consequences
- Positive: ...  Negative: ...  Risks: ...
```

---

## Few-Shot Examples (reference paths)

| Task | Path |
|------|------|
| Code review | `~/.claude/examples/common/code_review.md` |
| Refactoring smells | `~/.claude/examples/engineering/refactoring_smells.md` |
| TDD workflow | `~/.claude/examples/engineering/tdd_workflow.md` |
| Unit tests | `~/.claude/examples/engineering/unit_test_example.md` |
| Integration tests | `~/.claude/examples/engineering/integration_testing.md` |
| Performance opt | `~/.claude/examples/engineering/performance_optimization.md` |
| API design | `~/.claude/examples/engineering/api_design.md` |
| Debugging | `~/.claude/examples/engineering/debugging_methodology.md` |
