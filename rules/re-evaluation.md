# Rule: Re-evaluation
# Auto-loaded by Claude Code from ~/.claude/rules/

## When to Re-evaluate
- New data discovered that changes assumptions
- Scope escalation detected (scope_tracking_hook fires warning)
- Task failure — approach didn't work
- Domain shift — task crosses into different domain mid-execution
- User feedback contradicts current plan

## Actions
- files_modified >= 4: PAUSE, report scope, enter Plan Mode
- files_modified >= 6 AND domains >= 2: recommend an implicit team
- subtasks_emerged >= 3: re-score task, decompose if live_score >= 40
- Tier upgrade: report "Scope escalated: [old] → [new]. [reason]."

## Rules
- Don't auto-escalate silently — the user decides
- Report before changing approach
- If plan exists and becomes invalid — update plan, don't abandon it
- Re-score formula: live_score = max(initial_score, files*12, domains*25, subtasks*15)
