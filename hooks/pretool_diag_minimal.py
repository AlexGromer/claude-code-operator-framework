#!/usr/bin/env python3
"""Minimal diagnostic hook - outputs allow and logs what it received."""
import sys
import json
from pathlib import Path
from datetime import datetime

LOG = Path.home() / ".claude" / "logs" / "pretool_diag.log"

try:
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception as e:
        raw = f"STDIN_ERROR: {e}"

    # Log what we received
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "stdin_len": len(raw),
            "stdin_preview": raw[:200] if raw else "EMPTY",
            "argv": sys.argv,
        }) + "\n")

    # Always output valid JSON
    print(json.dumps({"decision": "approve"}))
except Exception as e:
    # Last resort
    print(json.dumps({"decision": "approve"}))
