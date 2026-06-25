# Unified Budget Hook

**File:** `~/.claude/evaluation/hooks/unified_budget_hook.py`
**Type:** PreToolUse (blocking)
**Created:** 2026-02-06
**Purpose:** Merge budget_check_hook.py and usage_limit_hook.py into a single unified hook

---

## Features

### 1. Usage Limit Tracking
- Atomically increments tool usage counts with file locking (`fcntl.flock`)
- Blocks expensive tools (WebSearch, Task) when limits exceeded
- Warns at 80% threshold for all tools
- Stores counts in: `~/.claude/evaluation/data/tool_usage_counts.json`

**Tool Limits:**
```python
{
    "WebSearch": 50,
    "WebFetch": 100,
    "Task": 150,
    "Bash": 500,
    "Edit": 200,
    "Write": 100,
    "default": 1000,
}
```

### 2. Budget Checking
- Estimates cost per tool call
- Checks against session/daily/weekly/monthly budgets via `budget_manager`
- Blocks operations if hard limits exceeded
- Warns at soft limits (80% threshold)
- Skips budget check for read-only tools (Read, Grep, Glob, TaskList, TaskGet)

**Tool Cost Estimates (USD):**
```python
{
    "Task": 0.05,
    "WebSearch": 0.02,
    "WebFetch": 0.01,
    "Bash": 0.005,
    "Edit": 0.003,
    "Write": 0.003,
    "Read": 0.002,
    "Grep": 0.001,
    "Glob": 0.001,
    "mcp__github__create_pull_request": 0.01,
    "default": 0.002,
}
```

---

## Execution Flow

```
TOOL INVOCATION
      │
      ▼
┌─────────────────────────────────────────────────┐
│ 1. READ INPUT JSON                              │
│    - tool_name                                  │
│    - CLAUDE_SESSION_ID from environment         │
└────────────┬────────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────────┐
│ 2. USAGE LIMIT CHECK                            │
│    a. Atomic load+increment+save (fcntl lock)   │
│    b. Check if count >= limit                   │
│    c. Block if WebSearch/Task over limit        │
│    d. Warn if >= 80% threshold                  │
└────────────┬────────────────────────────────────┘
             │
             ├─► BLOCK? → return {"decision": "block", "reason": "..."}
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 3. BUDGET CHECK                                 │
│    a. Estimate tool cost                        │
│    b. Call budget_manager.can_spend()           │
│    c. Block if hard budget exceeded             │
│    d. Warn if soft budget threshold reached     │
└────────────┬────────────────────────────────────┘
             │
             ├─► BLOCK? → return {"decision": "block", "reason": "..."}
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 4. OUTPUT DECISION                              │
│    - Block: {"decision": "block", "reason": ...}│
│    - Allow: {}                                  │
│    - Warnings: written to stderr                │
└─────────────────────────────────────────────────┘
```

---

## Decision Logic

**Most Restrictive Result Wins:**

| Usage Check | Budget Check | Result |
|-------------|--------------|--------|
| BLOCK | * | BLOCK (usage reason) |
| ALLOW | BLOCK | BLOCK (budget reason) |
| WARN | ALLOW | ALLOW + warn (usage) |
| ALLOW | WARN | ALLOW + warn (budget) |
| WARN | WARN | ALLOW + warn (both) |
| ALLOW | ALLOW | ALLOW |

---

## Integration

### settings.json Configuration

Replace both `budget_check_hook.py` and `usage_limit_hook.py` with:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/evaluation/hooks/unified_budget_hook.py",
            "timeout": 2000,
            "blocking": true
          }
        ]
      }
    ]
  }
}
```

---

## Files & Dependencies

**Created Files:**
- `~/.claude/evaluation/hooks/unified_budget_hook.py` — The unified hook

**Dependencies:**
- `~/.claude/evaluation/costs/budget_manager.py` — Budget management (imported)
- `~/.claude/evaluation/data/tool_usage_counts.json` — Usage counts (read/write with lock)
- `~/.claude/evaluation/data/tool_usage_counts.lock` — File lock
- `~/.claude/evaluation/data/budget_spending.jsonl` — Budget spending log (via budget_manager)
- `~/.claude/evaluation/data/budget_config.json` — Budget configuration (via budget_manager)

**Environment Variables:**
- `CLAUDE_SESSION_ID` — Session identifier (required for session budget tracking)

---

## Testing

```bash
# Test with read-only tool (should bypass budget check)
echo '{"tool_name": "Read"}' | CLAUDE_SESSION_ID=test python3 unified_budget_hook.py

# Test with Bash (should check both usage + budget)
echo '{"tool_name": "Bash"}' | CLAUDE_SESSION_ID=test python3 unified_budget_hook.py

# Test syntax
python3 -c "import ast; ast.parse(open('unified_budget_hook.py').read())"

# Verify constants
python3 -c "import unified_budget_hook as h; print(h.TOOL_LIMITS, h.TOOL_COST_ESTIMATES)"
```

---

## Error Handling

**Graceful Degradation:**
- If `budget_manager` import fails → skip budget check, continue with usage check
- If file locking fails → log error, allow operation (never crash)
- If JSON parsing fails → log error, allow operation
- If `CLAUDE_SESSION_ID` not set → warn, skip session budget check

**All exceptions are caught** and logged to stderr. Hook NEVER crashes the tool execution.

---

## Advantages Over Separate Hooks

1. **Single stdin read** — No duplicate JSON parsing
2. **Atomic execution** — Both checks run together, consistent view
3. **Most restrictive result** — Proper precedence (block > warn > allow)
4. **Reduced overhead** — One hook invocation instead of two
5. **Unified logging** — All warnings in one place
6. **Simpler configuration** — One PreToolUse entry instead of two

---

## Migration from Separate Hooks

**Before:**
```json
"PreToolUse": [
  {"matcher": "*", "hooks": [{"command": "python budget_check_hook.py"}]},
  {"matcher": "*", "hooks": [{"command": "python usage_limit_hook.py"}]}
]
```

**After:**
```json
"PreToolUse": [
  {"matcher": "*", "hooks": [{"command": "python unified_budget_hook.py"}]}
]
```

**Behavior Change:**
- None — identical functionality, same decision logic

**Optional Cleanup:**
```bash
# After verifying unified hook works, remove old hooks
rm ~/.claude/evaluation/hooks/budget_check_hook.py
rm ~/.claude/evaluation/hooks/usage_limit_hook.py
```

---

## Version History

- **v1.0.0** (2026-02-06): Initial unified implementation
  - Merged budget_check_hook.py (v1.0) + usage_limit_hook.py (v1.0)
  - Atomic file locking for usage counts
  - Most restrictive result logic
  - Graceful error handling
