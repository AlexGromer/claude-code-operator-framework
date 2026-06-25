#!/usr/bin/env python3
"""
Tool Success Hook - Collect metrics on successful tool calls.

Called automatically by Claude Code after each successful tool execution.
Records: latency, tool type, success rate, and COST (Task 22).

Task 22: Tool Execution Cost Tracking (GAP-COST-AG-002)
Version: 1.1.0
Date: 2026-02-03
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from metrics_tracker import MetricsTracker
except ImportError:
    # Silently fail if metrics_tracker not available
    MetricsTracker = None

try:
    from costs.agent_cost_tracker import AgentCostTracker
except ImportError:
    AgentCostTracker = None

# External API tools
EXTERNAL_API_TOOLS = {
    "WebFetch", "WebSearch",
    "mcp__github__search_code", "mcp__github__search_repositories",
    "mcp__github__search_issues", "mcp__github__get_file_contents",
    "mcp__github__list_commits", "mcp__github__list_issues",
    "mcp__github__list_pull_requests", "mcp__github__get_issue",
    "mcp__github__get_pull_request", "mcp__github__create_issue",
    "mcp__github__create_pull_request", "mcp__github__push_files",
}


def extract_tool_metadata(tool_data: dict) -> dict:
    """Extract relevant metadata from tool call data."""
    return {
        'tool_name': tool_data.get('name', 'unknown'),
        'duration_ms': tool_data.get('duration_ms', 0),
        'input_size': len(str(tool_data.get('input', ''))),
        'output_size': len(str(tool_data.get('output', ''))),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }


def log_tool_cost(tool_data: dict, session_data: dict) -> float:
    """
    Log tool execution cost (Task 22: GAP-COST-AG-002).

    Args:
        tool_data: Tool call information
        session_data: Session information

    Returns:
        Cost in USD (0 if tracking unavailable)
    """
    if AgentCostTracker is None:
        return 0.0

    try:
        tracker = AgentCostTracker()

        tool_name = tool_data.get('name', 'unknown')
        execution_time_ms = tool_data.get('duration_ms', 0)
        session_id = session_data.get('id', os.environ.get('CLAUDE_SESSION_ID', 'unknown'))

        # Skip Task tool (handled separately as subagent costs)
        if tool_name == 'Task':
            return 0.0

        is_external = tool_name in EXTERNAL_API_TOOLS

        cost = tracker.log_tool_cost(
            session_id=session_id,
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            external_api=is_external
        )

        # Check for alerts (log to stderr, don't block)
        alerts = tracker.get_tool_alerts(session_id)
        for alert in alerts:
            if alert['tool'] == tool_name:
                severity = alert['severity'].upper()
                print(
                    f"[TOOL_COST_{severity}] {tool_name}: "
                    f"${alert['total_cost']:.4f} (threshold: ${alert['threshold']:.2f})",
                    file=sys.stderr
                )

        return cost

    except Exception as e:
        print(f"Tool cost tracking error: {e}", file=sys.stderr)
        return 0.0


def main():
    """
    Main hook execution.

    Receives JSON data from Claude Code via stdin:
    {
        "tool": {
            "name": "Read",
            "input": {...},
            "output": {...},
            "duration_ms": 120
        },
        "session": {
            "id": "abc123",
            "message_count": 45,
            "token_count": 15000
        }
    }
    """
    try:
        # Read JSON data from stdin
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)

        data = json.loads(input_data)

        # Initialize tracker (may be None)
        tracker = MetricsTracker() if MetricsTracker else None

        # Extract tool data
        tool_data = data.get('tool', {})
        session_data = data.get('session', {})

        # Record latency metric
        duration_ms = tool_data.get('duration_ms', 0)
        if duration_ms > 0 and tracker:
            tracker.collect_metric(
                metric_type='latency',
                value=duration_ms / 1000.0,  # Convert to seconds
                metadata=extract_tool_metadata(tool_data)
            )

        # Record tool success (for error rate calculation)
        if tracker:
            tracker.collect_metric(
                metric_type='tool_error',
                value=0,  # Success = 0, failure = 1
                metadata={
                    'tool_name': tool_data.get('name', 'unknown'),
                    'session_id': session_data.get('id', 'unknown')
                }
            )

        # === Task 22: Log tool cost ===
        log_tool_cost(tool_data, session_data)

        # Record context budget if available
        token_count = session_data.get('token_count', 0)
        message_count = session_data.get('message_count', 0)

        if token_count > 0 and tracker:
            max_tokens = 200000  # Sonnet 4.5 context window
            utilization = token_count / max_tokens

            # Determine status
            if utilization < 0.60:
                status = 'healthy'
            elif utilization < 0.80:
                status = 'warning'
            elif utilization < 0.95:
                status = 'critical'
            else:
                status = 'exceeded'

            tracker.collect_context_budget_metric(
                current_tokens=token_count,
                max_tokens=max_tokens,
                utilization=utilization,
                status=status,
                message_count=message_count
            )

    except Exception as e:
        # Silently fail - hooks should never break Claude Code
        # Log to stderr for debugging
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
