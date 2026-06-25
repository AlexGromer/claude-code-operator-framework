#!/usr/bin/env python3
"""
Multi-Turn Optimization Hook (PostToolUse)
Tracks multi-turn conversation patterns for optimization.

Hook Type: PostToolUse (non-blocking)
Module: multi_turn_optimizer.py
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone

eval_dir = Path.home() / ".claude" / "evaluation"
sys.path.insert(0, str(eval_dir))

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
MULTI_TURN_FILE = DATA_DIR / "multi_turn_patterns.jsonl"


def analyze_patterns(session_id: str, window: int = 10) -> list:
    """Analyze recent tool patterns for optimization opportunities."""
    if not MULTI_TURN_FILE.exists():
        return []

    # Load recent entries for this session
    recent = []
    try:
        with open(MULTI_TURN_FILE, "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("session_id") == session_id:
                    recent.append(entry)
    except Exception:
        return []

    recent = recent[-window:]
    if len(recent) < 3:
        return []

    patterns = []

    # Check for repeated reads of same file
    read_files = [e.get("tool_input_hash") for e in recent if e.get("tool_name") == "Read"]
    if len(read_files) != len(set(read_files)):
        patterns.append({"type": "repeated_reads"})

    # Check for sequential edits
    edit_sequence = [e for e in recent if e.get("tool_name") in ["Edit", "Write"]]
    if len(edit_sequence) >= 3:
        patterns.append({"type": "sequential_edits"})

    return patterns


def main():
    """Track multi-turn patterns after tool execution."""
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})

        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        # Write to JSONL
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input_size": len(str(tool_input)),
            "tool_output_size": len(str(tool_response)),
            "tool_input_hash": hash(str(tool_input)) % 10000000  # Simple hash for pattern detection
        }

        with open(MULTI_TURN_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Check for patterns
        patterns = analyze_patterns(session_id)

        if patterns:
            for pattern in patterns:
                if pattern.get("type") == "repeated_reads":
                    print(f"💡 Optimization: Consider caching repeated file reads", file=sys.stderr)
                elif pattern.get("type") == "sequential_edits":
                    print(f"💡 Optimization: Batch edits to same file", file=sys.stderr)

        print(json.dumps({}))

    except Exception as e:
        print(f"Multi-turn hook error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
