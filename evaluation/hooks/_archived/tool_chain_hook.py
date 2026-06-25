#!/usr/bin/env python3
"""
Tool Chain Collection Hook
TIER 3 Phase 2 Task 27: GAP-EVAL-AG-003 Integration

Collects tool usage data for chain analysis during session.
Called automatically via PostToolUse hook in settings.json.

Features:
- Real-time tool call collection to JSONL file
- Automatic session tracking
- Low-overhead append-only logging
- Used by tool_chain_analyzer.py for analysis

Usage:
    Automatically called by Claude Code via PostToolUse hook.
    Data is stored in data/tool_chains/session_<id>.jsonl

Version: 1.0.0
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Data directory for tool chain logs
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data" / "tool_chains"


def main():
    """
    Main hook execution.

    Receives JSON data from Claude Code via stdin with format:
    {
        "session_id": "abc123",
        "transcript_path": "/path/to/session.jsonl",
        "cwd": "/working/directory",
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "/path/to/file"},
        "tool_response": {"content": "..."},
        "tool_use_id": "toolu_xxx"
    }
    """
    try:
        # Read JSON data from stdin
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)

        data = json.loads(input_data)

        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Extract session ID
        session_id = data.get('session_id', 'unknown')

        # Create log file path for this session
        log_file = DATA_DIR / f"session_{session_id}.jsonl"

        # Prepare tool call entry
        tool_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "tool_name": data.get('tool_name', 'Unknown'),
            "tool_use_id": data.get('tool_use_id', ''),
            "arguments": data.get('tool_input', {}),
            "result_summary": _summarize_result(data.get('tool_response', {})),
            "success": _determine_success(data.get('tool_response', {}), data.get('tool_name', ''))
        }

        # Append to session log file
        with open(log_file, 'a') as f:
            f.write(json.dumps(tool_entry) + '\n')

    except Exception as e:
        # Silently fail - hooks should never break Claude Code
        print(f"Tool chain hook error: {e}", file=sys.stderr)
        sys.exit(0)


def _summarize_result(response: dict) -> str:
    """Create brief summary of tool response."""
    if not response:
        return "empty"

    # For Bash tool
    if 'stdout' in response:
        stdout = response.get('stdout', '')
        if len(stdout) > 100:
            return f"stdout: {len(stdout)} chars"
        return f"stdout: {stdout[:50]}..." if stdout else "no output"

    # For Read tool
    if 'content' in response:
        content = response.get('content', '')
        if isinstance(content, str):
            return f"content: {len(content)} chars"
        return "content: data"

    # For file operations
    if 'success' in response:
        return "success" if response['success'] else "failed"

    # Generic
    return f"keys: {list(response.keys())}"


def _determine_success(response: dict, tool_name: str) -> bool:
    """Determine if tool call was successful."""
    if not response:
        return False

    # For Bash tool
    if tool_name == "Bash":
        # Check for interruption or error indicators
        if response.get('interrupted', False):
            return False
        # Presence of stderr doesn't always mean failure
        return True

    # For tools with explicit success indicator
    if 'success' in response:
        return response['success']

    # For tools with error indicator
    if 'error' in response:
        return False

    # Default: assume success if we got a response
    return True


if __name__ == '__main__':
    main()
