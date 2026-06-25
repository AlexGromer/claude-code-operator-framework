#!/usr/bin/env python3
"""
MemGPT Context Hook (PostToolUse)

Archives important tool outputs to MemGPT archival memory.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ARCHIVAL_FILE = Path.home() / ".claude" / "evaluation" / "data" / "memgpt_memory" / "archival_memory.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

    # Only archive significant outputs
    if len(tool_output) < 100:
        return 0

    ARCHIVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "entry_id": f"hook-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}",
        "content": tool_output[:500],
        "tags": ["auto-archived", tool_name],
        "source": "memgpt_context_hook",
        "created_at": datetime.now().isoformat(),
    }

    with open(ARCHIVAL_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
