#!/usr/bin/env python3
"""
Computer Use Hook (PreToolUse)

Safety checks for computer use operations.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "computer_use.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")

    # Check if computer use related
    cu_keywords = ["screenshot", "mouse", "click", "type", "xdotool"]
    if not any(kw in tool_input.lower() for kw in cu_keywords):
        return 0

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "event": "computer_use",
        "tool": tool_name,
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
