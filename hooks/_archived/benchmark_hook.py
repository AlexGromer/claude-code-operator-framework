#!/usr/bin/env python3
"""
Benchmark Hook (PostToolUse)

Collects latency metrics for benchmark analysis.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "evaluation" / "data" / "benchmark_metrics.jsonl"

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "event": "tool_latency",
        "tool": tool_name,
        "timestamp": datetime.now().isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
