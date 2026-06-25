#!/usr/bin/env python3
"""
Unified Tool Metrics Hook (PostToolUse)

Lightweight metrics collection — append-only JSONL logging.
No heavy imports, no file reads, no pattern analysis.

Version: 2.0.0 (v6.0 — rewritten for performance: 1474ms → <100ms)
Date: 2026-02-25
"""

import os
import sys
import json
import fcntl
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
METRICS_FILE = DATA_DIR / "metrics.jsonl"


def main():
    try:
        hooks_dir = str(Path(__file__).resolve().parent.parent.parent / "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        from hook_stdin import read_hook_stdin
        data = read_hook_stdin()
        if not data:
            sys.exit(0)

        # Extract fields (flat or nested format)
        tool_name = data.get("tool_name") or (data.get("tool", {}) or {}).get("name", "unknown")
        session_id = data.get("session_id") or (data.get("session", {}) or {}).get("id", "")
        duration_ms = data.get("duration_ms", 0) or (data.get("tool", {}) or {}).get("duration_ms", 0)

        if not session_id:
            sid_file = DATA_DIR / "current_session_id"
            if sid_file.exists():
                session_id = sid_file.read_text().strip()[:36]
            else:
                session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        # Single append-only write
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "session": session_id[:8],
            "dur_ms": duration_ms,
        }
        # Attribute subagent spawns by type so per-agent usage is observable
        # (complements the SubagentStart recorder in agent_metrics.jsonl).
        if tool_name in ("Agent", "Task"):
            ti = data.get("tool_input") or (data.get("tool", {}) or {}).get("input", {})
            if isinstance(ti, dict) and ti.get("subagent_type"):
                entry["subagent_type"] = ti["subagent_type"]

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)

    except Exception as e:
        print(f"Tool metrics hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
