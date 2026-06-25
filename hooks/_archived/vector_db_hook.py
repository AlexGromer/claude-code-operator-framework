#!/usr/bin/env python3
"""
Vector DB Hook (PostToolUse)

Tracks vector database operations for monitoring.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "vdb_operations.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")

    # Check if vector DB related
    if "vector" not in tool_input.lower() and "embedding" not in tool_input.lower():
        return 0

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "event": "vdb_operation",
        "tool": tool_name,
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
