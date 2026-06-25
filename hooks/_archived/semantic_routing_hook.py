#!/usr/bin/env python3
"""
Semantic Routing Hook (PreToolUse)

Logs routing decisions for analysis and optimization.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "routing_decisions.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "event": "tool_routing",
        "tool": tool_name,
        "input_length": len(tool_input),
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
