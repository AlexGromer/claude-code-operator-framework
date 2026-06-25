#!/usr/bin/env python3
"""
Red Team Hook (PreToolUse)

Scans tool inputs for potential security threats.
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "redteam_detections.jsonl"

THREAT_PATTERNS = [
    (r"ignore.*previous", "prompt_injection"),
    (r"system\s*prompt", "prompt_extraction"),
    (r"eval\s*\(", "code_injection"),
    (r"/etc/passwd", "sensitive_file"),
]

def main():
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")

    for pattern, threat_type in THREAT_PATTERNS:
        if re.search(pattern, tool_input, re.IGNORECASE):
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

            entry = {
                "event": "threat_detected",
                "threat_type": threat_type,
                "tool": tool_name,
                "pattern": pattern,
                "timestamp": datetime.now().isoformat(),
            }

            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            print(f"⚠️ Security: Potential {threat_type} detected")
            break

    return 0

if __name__ == "__main__":
    sys.exit(main())
