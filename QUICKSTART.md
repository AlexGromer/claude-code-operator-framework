# Quickstart

A fast path to trying the Claude Code Operator Framework.

## 1. Get the files

```bash
git clone <this-repo> claude-code-operator-framework
cd claude-code-operator-framework
```

## 2. Install into your Claude Code config

Copy the parts you want into `~/.claude/` (back up your existing config first):

```bash
cp -r output-styles rules agents hooks modules templates ~/.claude/
cp CLAUDE.md CORE_INSTRUCTIONS.md ~/.claude/
# review settings.json and merge what you need — do NOT blindly overwrite it
```

## 3. Fill in your persona

Open `~/.claude/output-styles/operator.md` and complete the `## User` block:

```
## User
Senior engineer, backend + infra. Treat me as a peer; be concise and direct.
```

Do the same for any other style you plan to use. They ship with a blank
placeholder on purpose.

## 4. Select a style

Set your active output style to `Operator` (or another) via Claude Code's
configuration / `/config`.

## 5. (Optional) Build the MCP servers

```bash
for s in backlog doctor gc profile score tools; do
  (cd mcp-servers/$s-mcp 2>/dev/null && go build -o $s-mcp .) ;
done
```

Then register the ones you want in your MCP config.

## Notes

- Review `settings.json` permission tiers before enabling — they gate what runs
  automatically vs. asks for confirmation.
- Never commit real API keys/tokens; the hooks include a pre-commit secrets scan.
- Remove agents/rules/modules you don't need — the framework is meant to be trimmed.
