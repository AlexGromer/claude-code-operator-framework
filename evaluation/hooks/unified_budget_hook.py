#!/usr/bin/env python3
"""
Unified Budget and Usage Limit Hook (PreToolUse)

Merges budget_check_hook.py and usage_limit_hook.py into one file.
Performs both checks in sequence:
1. Usage limit check (atomic load+increment+save with file locking)
2. Budget check (cost estimation + budget_manager validation)

Returns the most restrictive result:
- If either blocks → return block decision
- If either warns → output warning to stderr
- Otherwise → return {"decision": "approve"}

Hook Type: PreToolUse (blocking)
Logs: usage counts + budget spending
"""

import sys
import json
import os
import fcntl
from pathlib import Path
from datetime import datetime, timezone

# Add evaluation directory to path for budget_manager import
eval_dir = Path.home() / ".claude" / "evaluation"
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(eval_dir / "costs"))

try:
    from budget_manager import BudgetManager, BudgetType
    BUDGET_AVAILABLE = True
except ImportError:
    BUDGET_AVAILABLE = False

# Directories and files
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
USAGE_FILE = DATA_DIR / "tool_usage_counts.json"
SESSION_ID_FILE = DATA_DIR / "current_session_id"

# Tool limits per session (from usage_limit_hook)
TOOL_LIMITS = {
    "WebSearch": 50,
    "WebFetch": 100,
    "Task": 150,
    "Bash": 500,
    "Edit": 200,
    "Write": 100,
    "default": 1000,
}

# Tool cost estimates (USD per call, from budget_check_hook)
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

# Tools that bypass budget check (cheap or essential — blocking them locks out recovery)
# Usage limits still apply to all tools
BUDGET_BYPASS_TOOLS = {
    "Read", "Grep", "Glob",              # Read-only
    "TaskList", "TaskGet", "TaskCreate", "TaskUpdate",  # Task management
    "Edit", "Write",                       # File ops (cheap, blocking causes lockout)
    "NotebookEdit",                        # Notebook ops
    "AskUserQuestion",                     # User interaction
    "EnterPlanMode", "ExitPlanMode",       # Planning
    "Skill",                               # Skill invocation
}

# Warning threshold for usage limits
WARNING_THRESHOLD = 0.8


def load_and_update_counts(session_id: str, tool_name: str) -> int:
    """Atomically load, increment, and save usage counts with file locking.

    Returns:
        int: The new count for the tool after increment.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = USAGE_FILE.with_suffix(".lock")

    with open(lock_file, "w") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            # Load existing counts
            counts = {}
            if USAGE_FILE.exists():
                try:
                    with open(USAGE_FILE, "r") as f:
                        counts = json.load(f)
                except (json.JSONDecodeError, OSError):
                    counts = {}

            # Update count for this tool
            if session_id not in counts:
                counts[session_id] = {}
            new_count = counts[session_id].get(tool_name, 0) + 1
            counts[session_id][tool_name] = new_count

            # Save updated counts
            with open(USAGE_FILE, "w") as f:
                json.dump(counts, f)

            return new_count
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def check_usage_limits(session_id: str, tool_name: str, new_count: int) -> tuple:
    """Check if usage limits are exceeded.

    Returns:
        tuple: (should_block: bool, warning_message: str or None)
    """
    limit = TOOL_LIMITS.get(tool_name, TOOL_LIMITS["default"])
    usage_ratio = new_count / limit

    if usage_ratio >= 1.0:
        # Limit exceeded - block for certain expensive tools
        if tool_name in ["WebSearch", "Task"]:
            return (
                True,
                f"Usage limit exceeded: {tool_name} ({new_count}/{limit})"
            )

    elif usage_ratio >= WARNING_THRESHOLD:
        remaining = limit - new_count
        return (
            False,
            f"Usage warning: {tool_name} {new_count}/{limit} (remaining: {remaining})"
        )

    return (False, None)


def estimate_tool_cost(tool_name: str) -> float:
    """Estimate cost for a tool call."""
    return TOOL_COST_ESTIMATES.get(tool_name, TOOL_COST_ESTIMATES["default"])


def check_budget(tool_name: str, session_id: str) -> tuple:
    """Check budget limits using budget_manager.

    Returns:
        tuple: (should_block: bool, warning_messages: list)
    """
    if not BUDGET_AVAILABLE:
        return (False, [])

    # Skip budget check for read-only tools
    if tool_name in BUDGET_BYPASS_TOOLS:
        return (False, [])

    # Skip session budget if session ID not properly set
    if session_id == "unknown":
        return (False, ["CLAUDE_SESSION_ID not set — skipping session budget check"])

    try:
        # Initialize budget manager
        manager = BudgetManager()

        # Estimate cost for this tool
        estimated_cost = estimate_tool_cost(tool_name)

        # Check if we can spend this amount
        can_proceed, blocking_reasons = manager.can_spend(
            amount=estimated_cost,
            session_id=session_id
        )

        warnings = []

        if not can_proceed:
            # Budget exceeded - block operation
            reason = "; ".join(blocking_reasons)
            return (True, [f"Budget exceeded: {reason}"])

        # Check for soft limits (requires confirmation but allows)
        for budget_type in [BudgetType.SESSION, BudgetType.DAILY]:
            status = manager.check_budget(budget_type, session_id, proposed_spend=estimated_cost)

            if status.requires_confirmation:
                warnings.append(f"BUDGET WARNING: {status.message}")

            # Log alerts if any triggered
            for alert in status.alerts_triggered:
                warnings.append(f"BUDGET ALERT: {alert}")

        return (False, warnings)

    except Exception as e:
        # Non-blocking failure - allow operation
        return (False, [f"Budget check error (allowing): {e}"])


def main():
    """
    Unified PreToolUse hook: check both usage limits and budget.

    Returns the most restrictive result:
    - If either check blocks → return block decision
    - If either check warns → output warning to stderr
    - Otherwise → return {"decision": "approve"}
    """
    try:
        # Read hook input with timeout protection
        hooks_dir = Path(__file__).resolve().parent.parent.parent / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from hook_stdin import read_hook_stdin
        input_data = read_hook_stdin()

        tool_name = input_data.get("tool_name", "unknown")
        # Get session ID from file (wrapper writes it) or env var fallback
        session_id = "unknown"
        try:
            if SESSION_ID_FILE.exists():
                sid = SESSION_ID_FILE.read_text().strip()
                if sid:
                    session_id = sid
        except Exception:
            pass
        if session_id == "unknown":
            session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        # STEP 1: Usage limit check (atomic increment + check)
        new_count = load_and_update_counts(session_id, tool_name)
        usage_should_block, usage_warning = check_usage_limits(session_id, tool_name, new_count)

        if usage_should_block:
            # Usage limit blocks - return block decision
            print(json.dumps({
                "decision": "block",
                "reason": usage_warning
            }))
            print(f"⚠️ USAGE BLOCK: {usage_warning}", file=sys.stderr)
            return

        # STEP 2: Budget check
        budget_should_block, budget_warnings = check_budget(tool_name, session_id)

        if budget_should_block:
            # Budget blocks - return block decision
            reason = budget_warnings[0] if budget_warnings else "Budget exceeded"
            print(json.dumps({
                "decision": "block",
                "reason": reason
            }))
            print(f"⚠️ BUDGET BLOCK: {tool_name} blocked - {reason}", file=sys.stderr)
            return

        # STEP 3: Output warnings (if any)
        if usage_warning:
            print(f"⚠️ {usage_warning}", file=sys.stderr)

        for warning in budget_warnings:
            print(f"⚠️ {warning}", file=sys.stderr)

        # STEP 4: Allow operation (no blocks)
        print(json.dumps({"decision": "approve"}))

    except Exception as e:
        # Non-blocking failure - allow operation
        print(f"⚠️ Unified budget hook error (allowing): {e}", file=sys.stderr)
        print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
