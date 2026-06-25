#!/usr/bin/env python3
"""
Browser Test Hook (PostToolUse)

Monitors browser automation operations.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "browser_tests.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")

    # Check if browser-related
    browser_keywords = ["playwright", "browser", "screenshot", "navigate", "http"]
    if not any(kw in tool_input.lower() for kw in browser_keywords):
        return 0

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "event": "browser_operation",
        "tool": tool_name,
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
