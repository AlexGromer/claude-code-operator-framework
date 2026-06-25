#!/usr/bin/env python3
"""
UEP Step Tracker Hook — Tracks pipeline state transitions via Task tool usage.

Detects when Task() subagents complete and logs step progress to pipeline_state.json.
This enables context recovery after compaction via UserPromptSubmit hook.

Hook Type: PostToolUse
Matcher: Task
Input: JSON from stdin with tool_name, tool_input, tool_response
Output: JSON to stdout (empty — non-blocking observation hook)

Version: 1.0.0
Created: 2026-02-09
"""

import os
import sys
import json
import fcntl
import time
from pathlib import Path

AGENT_WORK_DIR = Path("/opt/agent_work_directory")


def get_session_id() -> str:
    """Get current session ID from file or env."""
    # Try file first (more reliable — env vars don't propagate to hooks)
    sid_file = Path.home() / ".claude" / "evaluation" / "data" / "current_session_id"
    if sid_file.exists():
        try:
            return sid_file.read_text().strip()
        except Exception:
            pass
    return os.environ.get("CLAUDE_SESSION_ID", "unknown")


def get_state_file(session_id: str) -> Path:
    """Get path to pipeline state file, creating directory if needed."""
    session_dir = AGENT_WORK_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / "pipeline_state.json"


def load_state(state_file: Path) -> dict:
    """Load existing state or return empty state."""
    if state_file.exists():
        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "goal": "",
        "criteria": [],
        "tier": 0,
        "current_step": "",
        "completed_steps": [],
        "pending_steps": [],
        "step_results": {},
        "scratchpad_dir": "",
        "updated_at": "",
        "subagent_count": 0
    }


def save_state(state_file: Path, state: dict):
    """Atomically save pipeline state with file locking."""
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    tmp_file = state_file.with_suffix(".tmp")
    try:
        with open(tmp_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        tmp_file.rename(state_file)
    except Exception as e:
        print(f"State save error: {e}", file=sys.stderr)
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass


def extract_task_info(tool_input: dict) -> dict:
    """Extract relevant info from Task tool input."""
    return {
        "description": tool_input.get("description", ""),
        "subagent_type": tool_input.get("subagent_type", ""),
        "model": tool_input.get("model", ""),
        "prompt_preview": tool_input.get("prompt", "")[:200] if tool_input.get("prompt") else ""
    }


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({}))
        return 0

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Task":
        print(json.dumps({}))
        return 0

    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response", "")

    session_id = get_session_id()
    state_file = get_state_file(session_id)
    state = load_state(state_file)

    # Track subagent completion
    task_info = extract_task_info(tool_input)
    task_desc = task_info["description"]

    state["subagent_count"] = state.get("subagent_count", 0) + 1

    # Store result summary (truncated)
    response_str = str(tool_response)
    if len(response_str) > 500:
        response_str = response_str[:500] + "..."

    step_key = f"task_{state['subagent_count']}_{task_desc[:30]}"
    state["step_results"][step_key] = {
        "description": task_desc,
        "model": task_info.get("model", ""),
        "result_preview": response_str[:200],
        "completed_at": time.strftime("%H:%M:%S")
    }

    # Keep only last 10 step results to avoid bloat
    if len(state["step_results"]) > 10:
        keys = list(state["step_results"].keys())
        for old_key in keys[:-10]:
            del state["step_results"][old_key]

    state["scratchpad_dir"] = str(AGENT_WORK_DIR / session_id / "scratchpad")

    save_state(state_file, state)
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
