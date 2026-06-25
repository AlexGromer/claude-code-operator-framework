#!/usr/bin/env python3
"""
Orchestration Verify Hook (PostToolUse)

Verifies orchestration patterns after Task tool executions.
Logs subagent performance and routing decisions.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "orchestration_log.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")[:500]

    if tool_name != "Task":
        return 0

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "event": "task_completion",
        "tool": tool_name,
        "output_preview": tool_output[:100],
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
