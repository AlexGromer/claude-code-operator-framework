# Claude Code Operator Framework

A modular configuration framework for [Claude Code](https://docs.claude.com/en/docs/claude-code):
output styles, auto-loaded behavior rules, a library of specialized subagents,
event hooks, custom MCP servers, and project templates — designed for
structured, auditable, multi-domain work.

> This is a **public, sanitized** template. The persona ("User" identity) in the
> output styles is left blank for you to fill in. No personal data, secrets, or
> owner-specific automation is included.

## What's inside

| Directory | Purpose |
|-----------|---------|
| `output-styles/` | Behavioral styles (system-prompt level). `operator.md` is the primary one: routing, task-tier scoring, AUTO_ACTION, domain awareness. Plus learning / research / architecture / incident / pair-programming / documentation. |
| `rules/` | Auto-loaded behavior rules (anti-hallucination, authorization levels, mandatory pre-commit checks, code-before-write, task execution, agent routing, …). |
| `agents/` | A library of specialized subagent definitions (security, DevOps, data, docs, review, …). |
| `hooks/` | Event hooks (SessionStart/End, PreToolUse/PostToolUse, UserPromptSubmit) for routing, scope tracking, secret scanning, metrics. |
| `mcp-servers/` | Custom Go MCP servers (backlog, doctor, gc, profile, score, tools). |
| `modules/` | On-demand domain knowledge referenced by agents. |
| `templates/` | Project-init templates (ARCHITECTURE, permissions, FILEMAP, etc.). |
| `CLAUDE.md`, `CORE_INSTRUCTIONS.md` | Top-level config + reinforcement instructions. |

## Install

These files map onto your `~/.claude/` configuration directory.

```bash
git clone <this-repo> claude-code-operator-framework
cd claude-code-operator-framework
# Review settings.json, then copy the pieces you want into ~/.claude/
# (output-styles/, rules/, agents/, hooks/, modules/, templates/, CLAUDE.md, ...)
```

Build the Go MCP servers if you want them:

```bash
cd mcp-servers/<server> && go build -o <server> .
```

## Customize

1. **Set your persona.** Open `output-styles/operator.md` (and any other styles
   you use) and fill in the `## User` block with your role, stack, and how you
   want the assistant to treat you. It ships blank by design.
2. **Pick an active style** via Claude Code's output-style setting.
3. **Trim to taste.** Remove agents/rules/modules you don't need; adjust
   `settings.json` permissions to your environment.

## Security

- `settings.json` defines permission allow/ask/deny tiers — review them before use.
- Hooks include a pre-commit secrets scan; never commit real keys.
- Keep credentials out of the repo (`.gitignore` covers common secret patterns).

## Status

Reference framework — adapt freely. Counts and module sets evolve; treat the
directory listing above as the source of truth rather than any hardcoded number.
