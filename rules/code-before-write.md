# Rule: Code Quality & Verification
# Auto-loaded by Claude Code from ~/.claude/rules/

## Read Before Write
Read the file first, verify the method exists, check the signature, then write code.

## Self-Check (before delivering code)
1. Every called function — defined or imported?
2. Call arguments match definition parameters?
3. Counters/indices — correctly initialized and incremented?
4. No off-by-one errors? All imports resolve?

## Failing Tests
Default: test is RIGHT, code is WRONG. Only change test if logic is flawed or requirements changed.

## Automated Review
Hook `code_review_hook.py` runs on Write/Edit. Fix CRITICAL/HIGH before continuing.

## Read-Once Rule (Context Passing)
If the main process already read a file, don't re-read it in a subagent. Instead:
- Pass file content or summary directly in the agent's prompt
- For large files (>200 lines): pass summary + key sections with line ranges
- For config files: pass full content (they're small)
- For code files: pass relevant functions/classes, not the entire file
- Format: "File `path/to/file.py` contains: [content or summary]"

This applies to:
- Task()/Agent subagents — include read content in prompt
- Teammates (implicit team) — include in initial task description
- Background agents — include snapshot of relevant state

Exception: agent needs CURRENT state of a rapidly-changing file (e.g., during concurrent edits).

## File Map Usage
Before searching for files with Glob/Grep, check FILEMAP.md if it exists in the project.
FILEMAP.md provides file purposes, key exports, and relationships — faster than searching.
Update FILEMAP.md when creating/deleting/significantly changing files.

## Parallel Tool Calls
When one parallel Bash call fails (exit code != 0), siblings get `Sibling tool call errored`.
Prevention: use `;` (not `&&`) when calls may independently fail.
Recovery: re-run failed calls individually with `;` separators.
