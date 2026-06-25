#!/usr/bin/env python3
"""
PermissionRequest hook — fires when Claude Code needs to ask user permission.
Currently a passthrough: returns {} so the normal permission dialog is shown.

stdin fields (PermissionRequest event):
  tool_name    — name of the tool requesting permission
  tool_input   — input parameters for the tool
  permission   — the specific permission being requested

TODO (future auto-approve/deny patterns):
- Auto-approve: Read(*), Glob(*), Grep(*) — always safe, never need prompt.
- Auto-deny: rm -rf, dd, mkfs — already covered by settings.json deny list,
  but hook could add a second layer with a clear reason message.
- Auto-approve: git status/log/diff in known project directories.
- Pattern: {"decision": "approve"} to auto-approve without dialog.
- Pattern: {"decision": "deny", "reason": "..."} to auto-deny with reason.
"""
import json
import sys


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw or "{}")  # noqa: F841 — available for future use
    except Exception:
        print(json.dumps({}))
        return

    try:
        # Simple passthrough: let normal permission dialog handle it
        print(json.dumps({}))

    except Exception as e:
        print(f"[auto_permission_hook] error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
