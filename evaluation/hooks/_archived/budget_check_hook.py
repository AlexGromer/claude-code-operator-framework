#!/usr/bin/env python3
"""
Budget Check Hook (PreToolUse)
TIER 3 Phase 5 Task 29: GAP-COST-AG-003 Automation

Checks budget BEFORE tool execution to prevent overspend.
Blocks expensive operations if budget exceeded.

Hook Type: PreToolUse (blocking)
"""

import sys
import json
import os
from pathlib import Path

# Add evaluation directory to path
eval_dir = Path.home() / ".claude" / "evaluation"
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(eval_dir / "costs"))

from budget_manager import BudgetManager, BudgetType


# Tool cost estimates (USD per call)
TOOL_COST_ESTIMATES = {
    # High cost tools
    "Task": 0.05,           # Subagent spawn
    "WebSearch": 0.02,      # External API
    "WebFetch": 0.01,       # External API

    # Medium cost tools
    "Bash": 0.005,          # Compute
    "Edit": 0.003,          # File I/O + tokens
    "Write": 0.003,         # File I/O + tokens
    "Read": 0.002,          # File I/O

    # Low cost tools
    "Grep": 0.001,
    "Glob": 0.001,

    # MCP tools (GitHub)
    "mcp__github__create_pull_request": 0.01,
    "mcp__github__push_files": 0.01,
    "mcp__github__create_issue": 0.005,
    "mcp__github__search_code": 0.005,

    # Default
    "default": 0.002,
}


def estimate_tool_cost(tool_name: str) -> float:
    """Estimate cost for a tool call."""
    return TOOL_COST_ESTIMATES.get(tool_name, TOOL_COST_ESTIMATES["default"])


def main():
    """Check budget before tool execution."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "unknown")
        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        # Skip budget check for read-only tools
        readonly_tools = {"Read", "Grep", "Glob", "TaskList", "TaskGet"}
        if tool_name in readonly_tools:
            # Allow without check
            print(json.dumps({}))
            return

        # Skip session budget if session ID not properly set
        if session_id == "unknown":
            print("⚠️ CLAUDE_SESSION_ID not set — skipping session budget check", file=sys.stderr)
            print(json.dumps({}))
            return

        # Initialize budget manager
        manager = BudgetManager()

        # Estimate cost for this tool
        estimated_cost = estimate_tool_cost(tool_name)

        # Check if we can spend this amount
        can_proceed, blocking_reasons = manager.can_spend(
            amount=estimated_cost,
            session_id=session_id
        )

        if not can_proceed:
            # Budget exceeded - block operation
            reason = "; ".join(blocking_reasons)
            print(json.dumps({
                "decision": "block",
                "reason": f"Budget exceeded: {reason}"
            }))

            # Log to stderr for visibility
            print(f"⚠️ BUDGET BLOCK: {tool_name} blocked - {reason}", file=sys.stderr)
            return

        # Check for soft limit (requires confirmation but allows)
        for budget_type in [BudgetType.SESSION, BudgetType.DAILY]:
            status = manager.check_budget(budget_type, session_id, proposed_spend=estimated_cost)

            if status.requires_confirmation:
                # Soft limit reached - warn but allow
                print(f"⚠️ BUDGET WARNING: {status.message}", file=sys.stderr)

            # Log alerts if any triggered
            for alert in status.alerts_triggered:
                print(f"🔔 BUDGET ALERT: {alert}", file=sys.stderr)

        # Allow operation
        print(json.dumps({}))

    except Exception as e:
        # Non-blocking failure - allow operation
        print(f"⚠️ Budget check error (allowing): {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
