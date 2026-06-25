# Rule: MCP Operations
# Auto-loaded by Claude Code from ~/.claude/rules/

## Scope Hierarchy

1. Managed (Anthropic) > 2. CLI (`claude mcp add`) > 3. **Local** (`~/.claude.json` projects."*") > 4. Project (`.mcp.json`) > 5. User
- We use LOCAL scope (#3). USER scope NOT loaded in sessions.
- Essential servers (13: github, fetch, filesystem, memory, git, sequential-thinking, sqlite, backlog-mcp, profile-mcp, doctor-mcp, gc-mcp, score-mcp, tools-mcp) never unloaded.
  - Source of truth: profile-mcp Go binary (profiles.go). Keep in sync manually. Run: `profile-mcp --list` to verify.

## Profile Rotation

- Automatic via UserPromptSubmit hook (keyword detection in prompt)
- Rotation modifies `~/.claude.json` → requires session restart
- Banner: "MCP PROFILE ROTATED — SESSION REOPEN REQUIRED"
- Tool: profile-mcp (`mcp__profile-mcp__profile_load`)

## Restart Protocol

- MCP changes require restart (new servers unavailable in current session)
- Before restart: save task state to MEMORY.md "In-Progress" section
- After restart: read MEMORY.md for continuity

## Offline Fallback

- If MCP server is down → use CLI tools directly (e.g., pd-tools down → `subfinder` CLI)
- Do NOT block work on unavailable MCP servers
