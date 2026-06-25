#!/usr/bin/env python3
"""
State Persistence Hook (PostToolUse)

Tracks state changes after tool executions for recovery.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "state_changes.jsonl"
STATE_TOOLS = ["Edit", "Write", "Bash", "mcp__github__push_files"]

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")

    if tool_name not in STATE_TOOLS:
        return 0

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "event": "state_change",
        "tool": tool_name,
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
