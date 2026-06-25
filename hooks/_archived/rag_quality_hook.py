#!/usr/bin/env python3
"""
RAG Quality Hook (PostToolUse)

Monitors RAG pipeline quality after Read operations.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "rag_quality.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

    if tool_name != "Read":
        return 0

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "event": "rag_read",
        "output_length": len(tool_output),
        "has_content": len(tool_output) > 50,
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
