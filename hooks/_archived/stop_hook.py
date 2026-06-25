#!/usr/bin/env python3
"""
Stop Hook — Logs agent stop events
Trigger: Stop event (response complete or session end)
"""
import sys, json, fcntl
from datetime import datetime, timezone
from pathlib import Path

SESSION_ID_FILE = Path.home() / ".claude/evaluation/data/current_session_id"
STOP_LOG = Path.home() / ".claude/evaluation/data/stop_events.jsonl"

def get_session_id() -> str:
    try:
        if SESSION_ID_FILE.exists():
            return SESSION_ID_FILE.read_text().strip() or "unknown"
    except Exception:
        pass
    return "unknown"

def log_stop_event(event: dict):
    try:
        STOP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(STOP_LOG, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass

def main():
    try:
        stdin_data = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
        stop_reason = stdin_data.get("stop_reason", "unknown")
        tool_count = stdin_data.get("tool_count")

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": get_session_id(),
            "stop_reason": stop_reason,
        }
        if tool_count is not None:
            event["tool_count"] = tool_count

        log_stop_event(event)
    except Exception:
        pass

    sys.exit(0)

if __name__ == "__main__":
    main()
