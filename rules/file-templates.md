# Rule: File Templates
# Auto-loaded by Claude Code from ~/.claude/rules/

## Template Files and Their Rules

| File | Create | Update | Constraints |
|------|--------|--------|-------------|
| FILEMAP.md | At project-init | On Write (hook auto-updates) | Check before Glob/Grep |
| ARCHITECTURE.md | At project-init (base + type extension) | On Complex+ tasks, add ADR | Update ARCHITECTURE.md §6 Change Log |
| BACKLOG.md | At project-init | Standard+ tasks: add/complete | <30 active, stale P3>14d P2>7d, mark [x] on wave completion |
| MEMORY.md | At project-init | On new findings, In-Progress on compaction/exit | <200 lines index, topic files for details |
| .claude-ver | At project-init | On upgrade | Contains: config-version, stack, domains |
| .gitignore | At project-init (copy template) | Append on upgrade | NEVER delete patterns |
| settings.local.json | At project-init (merge base+type) | NEVER widen global permissions | Project can only narrow |
| ONBOARDING.md | Template reference at init | Not copied to project | Used as questionnaire checklist |

## Templates Location
All templates: `~/.claude/templates/project-init/`
