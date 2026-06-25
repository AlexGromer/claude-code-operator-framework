# Rule: Auto-Action
# Auto-loaded by Claude Code from ~/.claude/rules/

## AUTO_ACTION Directives
SessionStart hook emits AUTO_ACTION when project needs initialization:
- `AUTO_ACTION: /project-init` — new project, no .claude-ver
- `AUTO_ACTION: /project-init --upgrade` — .claude-ver version < current
- `AUTO_ACTION: /project-init --check` — .claude-ver exists but essential files missing

## Execution
1. Execute Skill(skill: "project-init") BEFORE responding to user
2. Do NOT ask permission. Do NOT explain. Execute FIRST.
3. Report result briefly after execution.

## Mechanical Fallback
Wrapper creates .claude-ver + BACKLOG.md + .gitignore + essential MCP config mechanically.
Full init (ARCHITECTURE, permissions, ONBOARDING) = LLM skill.

## Modes
- New project (no .claude-ver): full questionnaire (12 project types)
- Check mode (--check): automatic, no questionnaire, create missing files from templates
- Upgrade mode (--upgrade): automatic, no questionnaire, merge new templates

## Cooldown
1 hour (.claude-init-attempted marker file). Skip /tmp and ~/.claude/ paths.
