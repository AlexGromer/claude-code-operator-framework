#!/usr/bin/env python3
"""
SubagentStart hook — fires when a subagent or teammate is spawned.

Two jobs:
1. Inject additionalContext with key behavioral rules every subagent must follow.
2. Record the spawned subagent's identity to agent_metrics.jsonl for usage
   attribution. This closes the observability gap behind the "0/102 agents
   invoked" myth (the dedicated recorder was archived as a 4-line stub and
   budget_spending.jsonl carries no agent id).
"""
import json
import sys
import os
import fcntl
from datetime import datetime, timezone
from pathlib import Path

METRICS_FILE = Path.home() / ".claude" / "evaluation" / "data" / "agent_metrics.jsonl"

# The exact stdin field carrying the agent type is not documented for SubagentStart,
# so probe several plausible names. Until one is confirmed empirically, we also log
# the available keys (see record_identity) so the real schema can be learned.
_IDENTITY_KEYS = ("subagent_type", "agent_type", "agentType", "subagentType",
                  "agent", "name", "teammate_name")


def record_identity(data: dict) -> None:
    """Append the spawned subagent's identity to agent_metrics.jsonl (fail-open)."""
    try:
        identity = ""
        for k in _IDENTITY_KEYS:
            v = data.get(k)
            if isinstance(v, str) and v:
                identity = v
                break

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "SubagentStart",
            "subagent_type": identity or "unknown",
            "session_id": data.get("session_id", ""),
        }
        # Self-documenting fallback: if no known identity key matched, record the
        # available top-level keys so the real field name can be confirmed.
        if not identity:
            entry["available_keys"] = sorted(
                str(k) for k in data.keys()
            )[:20]

        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(entry) + "\n")
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        # Never block subagent spawn on telemetry failure.
        pass


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw or "{}")
    except Exception:
        print(json.dumps({}))
        return

    if isinstance(data, dict):
        record_identity(data)

    try:
        context_lines = [
            "Subagent behavioral rules (mandatory):",
            "1. mode: acceptEdits — auto-accept all file edits without prompting.",
            "2. Language: Russian primary for user-facing output. English for code, logs, identifiers.",
            "3. Follow project conventions: FILEMAP.md for file map, BACKLOG.md for task tracking.",
            "4. Never re-read files already passed in the prompt (Read-Once Rule).",
            "5. On permission boundary: escalate to team lead via SendMessage, do not retry.",
            "6. Fail-open on errors: always return a result, never hang or silently fail.",
        ]
        additional_context = " ".join(context_lines)

        output = {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": additional_context,
            }
        }
        print(json.dumps(output))

    except Exception as e:
        print(f"[subagent_context_hook] error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
