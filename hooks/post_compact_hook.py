#!/usr/bin/env python3
"""
PostCompact hook — fires after context compaction completes.
Logs compaction event to compact_events.jsonl with timestamp and summary metadata.

stdin fields (PostCompact event):
  compact_summary — text summary of what was compacted
"""
import json
import os
import sys
from datetime import datetime, timezone


LOG_PATH = os.path.expanduser("~/.claude/evaluation/data/compact_events.jsonl")


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw or "{}")
    except Exception:
        print(json.dumps({}))
        return

    try:
        compact_summary = data.get("compact_summary", "")

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary_length": len(compact_summary),
            "summary_preview": compact_summary[:200] if compact_summary else "",
        }

        # Ensure log directory exists
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception as e:
        print(f"[post_compact_hook] error: {e}", file=sys.stderr)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
