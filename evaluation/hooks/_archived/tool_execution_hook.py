#!/usr/bin/env python3
"""
Tool Execution Hook - Collect metrics on tool calls.

Called automatically by Claude Code after each tool execution via PostToolUse hook.
Records tool usage for analytics.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from metrics_tracker import MetricsTracker
except ImportError:
    # Silently fail if metrics_tracker not available
    sys.exit(0)


def main():
    """
    Main hook execution.

    Receives JSON data from Claude Code via stdin with actual format:
    {
        "session_id": "abc123",
        "transcript_path": "/path/to/session.jsonl",
        "cwd": "/working/directory",
        "permission_mode": "acceptEdits",
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {...},
        "tool_response": {...},
        "tool_use_id": "toolu_xxx"
    }
    """
    try:
        # Read JSON data from stdin
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)

        data = json.loads(input_data)

        # Initialize tracker
        tracker = MetricsTracker()

        # Extract data from actual format
        tool_name = data.get('tool_name', 'unknown')
        session_id = data.get('session_id', 'unknown')
        tool_input = data.get('tool_input', {})
        tool_response = data.get('tool_response', {})

        # Determine exit_code if available (for Bash tool)
        exit_code = "0"  # Default success
        if tool_name == "Bash":
            # Check if command was interrupted or failed
            if tool_response.get('interrupted', False):
                exit_code = "interrupted"
            elif tool_response.get('stderr', ''):
                # If there's stderr, it might be an error (but not always)
                exit_code = "stderr_present"

        # Record tool execution metric
        tracker.collect_metric(
            metric_type='tool_execution',
            value=1.0,
            metadata={
                'tool_name': tool_name,
                'exit_code': exit_code,
                'source': 'post_tool_hook',
                'session_id': session_id
            }
        )

    except Exception as e:
        # Silently fail - hooks should never break Claude Code
        # Log to stderr for debugging
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
