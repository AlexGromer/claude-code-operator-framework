#!/usr/bin/env python3
"""
Cost Tracking Hook (PostToolUse)
TIER 3 Phase 5 Tasks 29-30: Automation

Records tool costs AFTER execution for budget tracking and task analysis.

Hook Type: PostToolUse (non-blocking)
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone

# Add evaluation directory to path
eval_dir = Path.home() / ".claude" / "evaluation"
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(eval_dir / "costs"))

from budget_manager import BudgetManager


# Tool cost estimates (USD per call) - same as budget_check_hook
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


def estimate_tool_cost(tool_name: str) -> float:
    """Estimate cost for a tool call."""
    return TOOL_COST_ESTIMATES.get(tool_name, TOOL_COST_ESTIMATES["default"])


def main():
    """Record cost after tool execution."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "unknown")
        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        # Get tool input for description
        tool_input = input_data.get("tool_input", {})
        description = ""

        if tool_name == "Bash":
            description = tool_input.get("command", "")[:100]
        elif tool_name == "Read":
            description = tool_input.get("file_path", "")
        elif tool_name == "Edit":
            description = f"Edit: {tool_input.get('file_path', '')}"
        elif tool_name == "Write":
            description = f"Write: {tool_input.get('file_path', '')}"
        elif tool_name == "Task":
            description = tool_input.get("description", "")[:100]
        else:
            description = tool_name

        # Estimate cost
        cost = estimate_tool_cost(tool_name)

        # Record spending
        manager = BudgetManager()
        manager.record_spending(
            amount=cost,
            session_id=session_id,
            category="tools",
            description=description,
            task_id=os.environ.get("CLAUDE_TASK_ID")
        )

        # Return empty response (non-blocking)
        print(json.dumps({}))

    except Exception as e:
        # Non-blocking failure
        print(f"⚠️ Cost tracking error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
