#!/usr/bin/env python3
"""Diagnostic PreToolUse hook — logs stdin, env, timing."""
import sys
import json
import time
import os
from pathlib import Path

LOG = Path.home() / ".claude" / "evaluation" / "data" / "pretool_diag.log"

def main():
    start = time.time()
    stdin_raw = ""
    try:
        stdin_raw = sys.stdin.read()
    except Exception as e:
        stdin_raw = f"STDIN_ERROR: {e}"

    elapsed = (time.time() - start) * 1000

    entry = {
        "ts": time.strftime("%H:%M:%S"),
        "stdin_len": len(stdin_raw),
        "stdin_preview": stdin_raw[:300],
        "stdin_valid_json": False,
        "elapsed_ms": round(elapsed, 1),
        "pid": os.getpid(),
        "ppid": os.getppid(),
    }

    try:
        json.loads(stdin_raw)
        entry["stdin_valid_json"] = True
    except Exception as e:
        entry["json_error"] = str(e)

    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    print(json.dumps({"decision": "approve"}))

if __name__ == "__main__":
    main()
