#!/usr/bin/env python3
"""
Usage Limit Hook (PreToolUse)
Checks and tracks usage limits before tool execution.

Hook Type: PreToolUse (blocking if limit exceeded)
Module: usage_limit_tracker.py
"""

import sys
import json
import os
import fcntl
from pathlib import Path
from datetime import datetime, timezone

eval_dir = Path.home() / ".claude" / "evaluation"
sys.path.insert(0, str(eval_dir))

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
USAGE_FILE = DATA_DIR / "tool_usage_counts.json"


# Tool limits per session (configurable)
TOOL_LIMITS = {
    "WebSearch": 50,
    "WebFetch": 100,
    "Task": 150,
    "Bash": 500,
    "Edit": 200,
    "Write": 100,
    "default": 1000,
}

WARNING_THRESHOLD = 0.8


def load_and_update_counts(session_id: str, tool_name: str) -> int:
    """Atomically load, increment, and save usage counts with file locking.

    Returns the new count for the tool.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = USAGE_FILE.with_suffix(".lock")

    with open(lock_file, "w") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            # Load
            counts = {}
            if USAGE_FILE.exists():
                try:
                    with open(USAGE_FILE, "r") as f:
                        counts = json.load(f)
                except (json.JSONDecodeError, OSError):
                    counts = {}

            # Update
            if session_id not in counts:
                counts[session_id] = {}
            new_count = counts[session_id].get(tool_name, 0) + 1
            counts[session_id][tool_name] = new_count

            # Save
            with open(USAGE_FILE, "w") as f:
                json.dump(counts, f)

            return new_count
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def main():
    """Check usage limits before tool execution."""
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "unknown")
        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        # Atomically load, increment, and save counts
        new_count = load_and_update_counts(session_id, tool_name)

        # Get limit for this tool
        limit = TOOL_LIMITS.get(tool_name, TOOL_LIMITS["default"])
        usage_ratio = new_count / limit

        if usage_ratio >= 1.0:
            # Limit exceeded - block for certain expensive tools
            if tool_name in ["WebSearch", "Task"]:
                print(json.dumps({
                    "decision": "block",
                    "reason": f"Usage limit exceeded: {tool_name} ({new_count}/{limit})"
                }))
                print(f"⚠️ BLOCKED: {tool_name} limit exceeded ({new_count}/{limit})", file=sys.stderr)
                return

        elif usage_ratio >= WARNING_THRESHOLD:
            remaining = limit - new_count
            print(f"⚠️ Usage warning: {tool_name} {new_count}/{limit} (remaining: {remaining})", file=sys.stderr)

        print(json.dumps({}))

    except Exception as e:
        print(f"Usage limit hook error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
