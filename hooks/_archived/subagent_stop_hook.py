#!/usr/bin/env python3
"""
SubagentStop Hook — Track subagent completion events.

Triggered when a subagent (Task tool) completes.
Logs to subagent_events.jsonl with cost tracking by model tier.
"""

import sys
import json
import fcntl
from datetime import datetime, timezone
from pathlib import Path

EVENTS_FILE = Path.home() / ".claude/evaluation/data/subagent_events.jsonl"
SESSION_FILE = Path.home() / ".claude/evaluation/data/current_session_id"

def get_session_id() -> str:
    """Get session ID from file, fallback to unknown."""
    try:
        if SESSION_FILE.exists():
            return SESSION_FILE.read_text().strip() or "unknown"
    except Exception:
        pass
    return "unknown"

def main():
    try:
        # Read stdin JSON
        stdin_data = sys.stdin.read().strip()
        if not stdin_data:
            sys.exit(0)

        data = json.loads(stdin_data)

        # Extract subagent info
        agent_id = data.get("agent_id", "unknown")
        description = data.get("description", "")
        duration_ms = data.get("duration", 0)
        model = data.get("model", "unknown")
        result = data.get("result", {})
        success = result.get("success", False) if isinstance(result, dict) else False

        # Build event
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": get_session_id(),
            "agent_id": agent_id,
            "description": description,
            "model": model,
            "duration_ms": duration_ms,
            "success": success
        }

        # Append to JSONL with file locking
        EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_FILE, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    except Exception:
        pass  # Silent failure

    sys.exit(0)

if __name__ == "__main__":
    main()
