#!/usr/bin/env python3
"""
TaskCompleted hook — fires when a Task() subagent completes.
Quality gate: currently a passthrough (exit 0 = accept completion).
Exit code 0 = accept completion.
Exit code 2 = reject completion (subagent re-runs or error reported).

TODO (future):
- Check if files listed in task output were actually created/modified.
- Run a quick pytest invocation if task touched test files.
- Verify BACKLOG.md was updated if the task was BACKLOG-tracked.
"""
import json
import sys


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw or "{}")
    except Exception:
        # Fail open: allow completion on parse error
        sys.exit(0)

    try:
        # TODO: future quality gate logic
        # task_output = data.get("output", "")
        # task_files = data.get("files_modified", [])
        # if task_files:
        #     for f in task_files:
        #         if not os.path.exists(f):
        #             print(f"[task_quality_gate] file missing: {f}", file=sys.stderr)
        #             sys.exit(2)

        # Simple version: always allow completion
        sys.exit(0)

    except Exception as e:
        print(f"[task_quality_gate_hook] error: {e}", file=sys.stderr)
        # Fail open
        sys.exit(0)


if __name__ == "__main__":
    main()
