# Rule: Agent Routing
# Auto-loaded by Claude Code from ~/.claude/rules/

## Model Selection
- haiku: formatting, reporting, scanning, cost tracking (lightweight)
- sonnet: development, security, analysis, most tasks (balanced)
- opus: critical logic, exploit research, kernel development (complex reasoning)
- inherit: iterator agent (inherits parent model)

## Delegation Rules
- Spawn all subagents and teammates with mode: "acceptEdits"
- 5+ file reads without output: delegate to a subagent
- Read-Once Rule: pass file content to the subagent instead of re-reading
- Config files (<50 lines): pass full content
- Code files: pass relevant functions with line ranges
- Large files (>200 lines): pass summary + key sections

## Team Composition
- Use the Agent tool with subagent_type for single tasks
- For coordinated multi-agent work (Complex+): spawn named teammates via the Agent tool (implicit team; `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)
- Available: 102 custom agents + built-in (Explore, Plan, general-purpose)
- Background agents: run_in_background: true for non-blocking
