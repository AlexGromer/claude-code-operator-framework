#!/usr/bin/env python3
"""
Unified Cost Hook (PostToolUse)

Cost tracking via budget_manager (budget_spending.jsonl).

Hook Type: PostToolUse (non-blocking)
Registered for: All tools

Note: User is on Claude Code Max 5x subscription (not per-API billing).
API cost estimates are tracked for reference and optimization purposes only.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone  # used by budget_manager

# Add evaluation directory to path
eval_dir = Path.home() / ".claude" / "evaluation"
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(eval_dir / "costs"))

try:
    from budget_manager import BudgetManager
    BUDGET_AVAILABLE = True
except ImportError:
    BUDGET_AVAILABLE = False

# Constants
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
SESSION_ID_FILE = DATA_DIR / "current_session_id"

# Tool cost estimates (USD per call, API-equivalent for reference)
TOOL_COST_ESTIMATES = {
    "Task": 0.05,
    "WebSearch": 0.02,
    "WebFetch": 0.01,
    "Bash": 0.005,
    "Edit": 0.003,
    "Write": 0.003,
    "Read": 0.002,
    "Grep": 0.001,
    "Glob": 0.001,
    "mcp__github__create_pull_request": 0.01,
    "mcp__github__push_files": 0.01,
    "mcp__github__create_issue": 0.005,
    "mcp__github__search_code": 0.005,
    "default": 0.002,
}


def get_session_id() -> str:
    """Get session ID from file (wrapper writes it) or env var fallback."""
    # Primary: read from file (env vars don't propagate to Claude Code hooks)
    try:
        if SESSION_ID_FILE.exists():
            sid = SESSION_ID_FILE.read_text().strip()
            if sid:
                return sid
    except Exception:
        pass
    # Fallback: env var (works if launched directly)
    return os.environ.get("CLAUDE_SESSION_ID", "unknown")


def estimate_tool_cost(tool_name: str) -> float:
    """Estimate API-equivalent cost for a tool call."""
    return TOOL_COST_ESTIMATES.get(tool_name, TOOL_COST_ESTIMATES["default"])


def get_tool_description(tool_name: str, tool_input: dict) -> str:
    """Generate description from tool input."""
    if tool_name == "Bash":
        return tool_input.get("command", "")[:100]
    elif tool_name == "Read":
        return tool_input.get("file_path", "")
    elif tool_name == "Edit":
        return f"Edit: {tool_input.get('file_path', '')}"
    elif tool_name == "Write":
        return f"Write: {tool_input.get('file_path', '')}"
    elif tool_name == "Task":
        return tool_input.get("description", "")[:100]
    else:
        return tool_name


def track_cost(tool_name: str, tool_input: dict, session_id: str, task_id: str):
    """Track tool cost via budget_manager."""
    try:
        cost = estimate_tool_cost(tool_name)
        description = get_tool_description(tool_name, tool_input)

        manager = BudgetManager()
        manager.record_spending(
            amount=cost,
            session_id=session_id,
            category="tools",
            description=description,
            task_id=task_id
        )
    except Exception as e:
        print(f"⚠️ Cost tracking error: {e}", file=sys.stderr)


def main():
    """Unified hook: cost tracking via budget_manager."""
    try:
        # Read stdin with timeout protection
        hooks_dir = Path(__file__).resolve().parent.parent.parent / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from hook_stdin import read_hook_stdin
        input_data = read_hook_stdin()

        # Extract data from stdin JSON
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", "")

        # Get session ID from file (wrapper writes it) or env var
        session_id = get_session_id()
        task_id = os.environ.get("CLAUDE_TASK_ID")

        # Track cost
        track_cost(tool_name, tool_input, session_id, task_id)

        # Always output empty JSON (non-blocking)
        print(json.dumps({}))

    except Exception as e:
        # Non-blocking failure
        print(f"⚠️ Unified cost hook error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
