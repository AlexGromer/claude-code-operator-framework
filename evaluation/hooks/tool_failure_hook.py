#!/usr/bin/env python3
"""
Tool Failure Hook — Lightweight error logging.

Called by Claude Code on PostToolUseFailure events.
Append-only JSONL logging, no heavy imports.

Version: 2.0.0 (v6.0 — rewritten for performance: 1340ms → <100ms)
"""

import sys
import json
import fcntl
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
METRICS_FILE = DATA_DIR / "metrics.jsonl"


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)

        data = json.loads(input_data)

        tool_name = data.get("tool_name", "unknown")
        session_id = data.get("session_id", "unknown")[:8]
        error = data.get("error", {})
        error_type = error.get("type", "unknown")
        error_msg = str(error.get("message", ""))[:200]

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "session": session_id,
            "type": "tool_error",
            "error_type": error_type,
            "error_msg": error_msg,
        }

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)

    except Exception as e:
        print(f"Tool failure hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
