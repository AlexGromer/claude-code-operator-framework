#!/usr/bin/env python3
"""
HITL Workflow Hook (PreToolUse)

Checks HITL requirements before high-risk operations.
Triggers approval workflow for CREDENTIAL/DESTRUCTIVE operations.
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "hitl_decisions.jsonl"

HIGH_RISK_PATTERNS = [
    r"rm\s+-rf",
    r"DROP\s+(TABLE|DATABASE)",
    r"DELETE\s+FROM",
    r"git\s+push\s+--force",
    r"terraform\s+destroy",
]

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")

    if tool_name != "Bash":
        return 0

    # Check for high-risk patterns
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, tool_input, re.IGNORECASE):
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

            entry = {
                "event": "hitl_required",
                "tool": tool_name,
                "pattern": pattern,
                "input_preview": tool_input[:100],
                "timestamp": datetime.now().isoformat(),
            }

            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Note: In production, this would trigger actual approval flow
            print(f"⚠️ HITL: High-risk operation detected (pattern: {pattern})")
            break

    return 0

if __name__ == "__main__":
    sys.exit(main())
