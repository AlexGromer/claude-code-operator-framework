#!/usr/bin/env python3
"""
InstructionsLoaded hook — fires when CLAUDE.md, rules, or modules are loaded.
Appends a structured log entry to instructions_loaded.jsonl for audit/analytics.

stdin fields (InstructionsLoaded event):
  file_path   — path to the loaded file
  memory_type — "claudeMd" | "rules" | "module" | etc.
  load_reason — why it was loaded
"""
import json
import os
import sys
from datetime import datetime, timezone


LOG_PATH = os.path.expanduser("~/.claude/evaluation/data/instructions_loaded.jsonl")


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw or "{}")
    except Exception:
        print(json.dumps({}))
        return

    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_path": data.get("file_path", ""),
            "memory_type": data.get("memory_type", ""),
            "load_reason": data.get("load_reason", ""),
        }

        # Ensure log directory exists
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception as e:
        print(f"[instructions_audit_hook] error: {e}", file=sys.stderr)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
