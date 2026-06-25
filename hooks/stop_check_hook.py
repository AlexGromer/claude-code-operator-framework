#!/usr/bin/env python3
"""
Stop hook — fires when Claude is about to stop responding.
Checks stop_hook_active to prevent infinite loop.
Returns {} to allow stop, or {"decision": "block", "reason": "..."} to force continue.

TODO (future): inspect active BACKLOG.md for uncompleted plan steps and block stop
if critical steps remain unexecuted within the current session.
"""
import json
import sys


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw or "{}")
    except Exception:
        print(json.dumps({}))
        return

    try:
        # Guard: if Claude Code already set stop_hook_active=true, we MUST allow stop
        # to prevent an infinite loop of block → stop_hook_active=true → block...
        if data.get("stop_hook_active", False):
            print(json.dumps({}))
            return

        # TODO: future plan-checking logic
        # backlog_path = os.path.expanduser("~/.claude/evaluation/data/current_backlog.md")
        # if os.path.exists(backlog_path):
        #     content = open(backlog_path).read()
        #     uncompleted = [l for l in content.splitlines() if l.strip().startswith("- [ ]")]
        #     if uncompleted:
        #         print(json.dumps({"decision": "block", "reason": f"{len(uncompleted)} plan steps uncompleted"}))
        #         return

        # Simple version: allow stop
        print(json.dumps({}))

    except Exception as e:
        print(f"[stop_check_hook] error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
