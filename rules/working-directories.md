# Rule: Working Directories
# Auto-loaded by Claude Code from ~/.claude/rules/

## Separation

- `~/.claude/` — Configuration (hooks, modules, rules, tools). Synced to git.
- `/opt/` — Working data (osint, pentest, devops, reverse). NOT committed.

## Working Paths (shared — globally allowed Edit/Write)

| Use Case | Path |
|----------|------|
| OSINT | `/opt/work/osint/` |
| Pentest | `/opt/work/pentest/` |
| DevOps | `/opt/work/devops/` |
| Reverse eng | `/opt/work/reverse/` |
| DFIR | `/opt/work/dfir/` |
| ML/AI | `/opt/work/ml/` |
| Compliance | `/opt/work/compliance/` |
| Business | `/opt/work/business/` |
| Go toolchain | `/opt/go/` |
| Rust/Cargo | `/opt/cargo/` |
| Scaffolding templates | `/opt/templates/` (go-repo и др.) |
| Agent work dir | `/opt/agent_work_directory/` |
| Rust toolchain | `/opt/rustup/` |
| UV cache | `/opt/uv-cache/` |
| UV tools | `/opt/uv-tools/` |
| Claude config project | `/opt/project/` |

## Project Paths (per-project — via settings.local.json)

All other `/opt/<project>/` dirs get Edit/Write through project-init generated `settings.local.json`.

## Rules

- Store working data in `/opt/`, never in `~/.claude/`
- Use timestamps in filenames for cache
- Keep raw data for re-analysis
- Hooks must use `/opt/` paths for working data
