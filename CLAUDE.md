# Claude Code Configuration v9.0

## Environment

- MCP servers: LOCAL scope. Essential: 13 servers (github, fetch, filesystem, memory, git, sequential-thinking, sqlite, backlog-mcp, profile-mcp, doctor-mcp, gc-mcp, score-mcp, tools-mcp).
- Output Style: `operator.md` (PRIMARY). 7 styles available: operator, learning, research, pair-programming, incident, architecture, documentation. Switch via `/config`.
- Behavioral precedence (highest→lowest): Output Style + `--append-system-prompt-file CORE_INSTRUCTIONS.md` (both **system-prompt level**) > Managed `/etc/claude-code/CLAUDE.md` > this file > `rules/*.md` > hooks additionalContext. NB: everything from "Managed" downward is injected as **user-message/context** (after the system prompt), not at system-prompt level — only the Output Style and the appended core-instructions file modify the system prompt itself.

## Architecture

- `output-styles/` — 7 Output Style files (system prompt level, PRIMARY behavioral control)
- `rules/` — Auto-loaded every request (15 behavior rules, detailed)
- `modules/` — On-demand domain knowledge (13 active, 13 archived)
- `hooks/` — 21 hook entries across 13 events in settings.json (25 scripts in hooks/)
- `agents/` — 102 custom subagents
- `skills/` — 102 skill wrappers (96 fork incl. project-init + 6 utility)
- `tools/` — 2 CLI utilities + 15 Go MCP tools via tools-mcp
- `mcp-servers/` — 6 Go servers (backlog, doctor, gc, profile, score, tools)
- `templates/project-init/` — 32 template files (ARCHITECTURE, permissions, FILEMAP, etc.)

## Auto-Invocation

```
User prompt → keyword match → Skill → context: fork → agent: <name> → isolated execution → result
```

## Memory Rules

- MEMORY.md: quick references only, < 200 lines
- Detailed summaries → `projects/<path>/memory/session_summary.md`
- Project-specific data → project `MEMORY.md`

## MCP Tool Quick Reference

| Task | Tool |
|------|------|
| Criteria freeze/check | `mcp__tools-mcp__criteria_*` |
| Backlog management | `mcp__backlog-mcp__backlog_*` |
| Profile management | `mcp__profile-mcp__profile_*` |
| System health | `mcp__doctor-mcp__doctor_*` |
| Garbage collection | `mcp__gc-mcp__gc_*` |
| Task scoring | `mcp__score-mcp__score_*` |
| Scope tracking | `mcp__tools-mcp__scope_*` |
| Session/usage | `mcp__tools-mcp__session_*`, `usage_*` |

## Changelog

Current version: 9.0.0 (2026-03-22)
- v9.0.0: Architecture Redesign (Path C). Output Style PRIMARY (7 styles: operator, learning, research, pair-programming, incident, architecture, documentation). Wrapper v3 (banner, bootstrap, MCP essential, --append-system-prompt-file). CORE_INSTRUCTIONS shrunk to 27 lines (backup). Managed /etc/claude-code/CLAUDE.md created. CLAUDE.md cleaned (<80 lines, no behavioral rules).
- v8.0.0: Phase 1-3 verification + cleanup. 1.1GB→561MB. Error handling, latency, concurrent safety fixes. Domain prompts, 1M context, Go acceleration roadmap. Windows porting, install.sh, VS Codium compat.

Full changelog: `/opt/project/CHANGELOG.md`
