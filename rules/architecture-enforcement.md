# Rule: Architecture Enforcement
# Auto-loaded by Claude Code from ~/.claude/rules/

## When to Check ARCHITECTURE.md

Before any Complex+ task (score >= 65):
1. Read ARCHITECTURE.md if it exists in the project
2. Check if the planned changes affect architecture (new components, API changes, dependency changes)
3. If yes → update ARCHITECTURE.md as part of the task

## ADR Requirement

Create a new ADR entry when:
- Adding a new service, module, or major dependency
- Changing data storage technology or strategy
- Modifying API contracts or communication patterns
- Altering deployment architecture
- Making a significant technology choice

ADR format (append to ADR table in ARCHITECTURE.md §3):
```
| ADR-NNN | YYYY-MM-DD | Decision description | Accepted | Brief context |
```

## Change Log Auto-Update

After significant architectural changes, append to ARCHITECTURE.md §6 Change Log:
```
| YYYY-MM-DD | What changed | ADR-NNN (if applicable) | @agent-or-user |
```

## Scope

- Only applies when ARCHITECTURE.md exists in the project root
- Not required for Simple tasks (<20 score)
- Not required for chat/reference projects
- Lightweight: don't block work, just remind and update
