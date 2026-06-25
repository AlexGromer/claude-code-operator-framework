# Rule: Mandatory Checks
# Auto-loaded by Claude Code from ~/.claude/rules/

## Before ANY Git Commit/Push

1. **Secrets scan**: `gitleaks detect --source . --verbose` — HALT if found
2. **Verify .claude/ in .gitignore** — NEVER commit Claude Code settings
3. **Run tests** (if test suite exists) — BLOCK if failing without user approval

## Critical .gitignore Patterns

Always ensure present: `.claude/`, `.env`, `.env.*`, `*.key`, `*.pem`, `credentials.json`, `*_secret*`

## Test Requirements

Run tests: after new features, bug fixes, refactoring, before commits/PRs.
Never: skip tests silently, commit with failing tests, comment out tests.

