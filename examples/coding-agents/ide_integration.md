# Few-Shot Example: IDE Integration with Claude Code

## Task
Пользователь: "Как настроить Claude Code для работы в VS Code и терминале?"

## Solution

**Reference:** `~/.claude/modules/17-coding-agents.md` (IDE Integration)

---

## Step 1: Terminal (CLI) Setup

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version

# Configure wrapper for enhanced features
alias claude='claude-wrapper'

# Start session with project context
cd /my/project && claude
```

## Step 2: VS Code Integration

```bash
# Install VS Code extension
# Search: "Claude Code" in VS Code Extensions marketplace
# Or install via CLI:
code --install-extension anthropic.claude-code

# Configure in settings.json:
# "claude-code.apiKey": "from-env"
# "claude-code.defaultModel": "claude-sonnet-4-5-20250929"
```

## Step 3: Configuration Sync

```bash
# Ensure config exists
ls ~/.claude/CLAUDE.md     # Main config
ls ~/.claude/rules/        # Auto-loaded rules
ls ~/.claude/modules/      # On-demand modules
ls ~/.claude/skills/       # Workflow skills

# Config applies to both CLI and IDE
```

## Step 4: Verify Integration

```bash
# Test CLI
claude "What files are in this project?"

# Test VS Code
# Open command palette → Claude Code → Ask Claude
# Verify: routing feedback appears, modules load correctly
```

---

## Verification

- CLI `claude` command works from terminal
- VS Code extension installed and configured
- CLAUDE.md and rules/ are loaded in both environments
- Skills are available via `/command` syntax
