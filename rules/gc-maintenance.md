# Rule: GC Maintenance
# Auto-loaded by Claude Code from ~/.claude/rules/

## GC Operations
- `gc-mcp --quick`: runs at SessionStart (hook), lightweight check
- `gc-mcp --run`: full cleanup, run manually when disk >500MB or periodically
- `gc-mcp --status`: check all 16 targets and last-run timestamps
- `gc-mcp --dry-run`: preview what would be cleaned

## 16 Targets
tasks, teams, spending_archive, spending_tracker, backlog, plans, session_env, python_caches, security_log, debug_files, empty_dirs, gz_archives, logs, temp_files, mcp_profiles, empty_jsonl

## Rules
- Never delete MEMORY.md or projects/*/memory/
- Never delete active session data (check session_id)
- Never delete Go binaries in mcp-servers/
- Completed archive in BACKLOG.md: keep last 50, older → delete
