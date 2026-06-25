#!/usr/bin/env python3
"""
Session Startup Dashboard Hook
Displays comprehensive metrics dashboard on session start using session_manager.py

Version: 1.2.0
Created: 2026-01-29
Updated: 2026-01-29 (fixed JSON output format, added session_file detection)
"""

import json
import sys
from pathlib import Path

import sys as _hsys
from pathlib import Path as _HPath
_hsys.path.insert(0, str(_HPath(__file__).parent))
from hook_stdin import read_hook_stdin
_sys_path_set = True  # hook_stdin import below

# Add evaluation directory to path
sys.path.insert(0, str(Path.home() / ".claude" / "evaluation"))

try:
    from session_manager import SessionManager
except ImportError as e:
    # Return empty success on import error (non-blocking)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"⚠️ Session dashboard unavailable: {e}"
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def main():
    """Display compact session info on startup."""
    try:
        try:
            input_data = read_hook_stdin(timeout_sec=5)
        except Exception:
            input_data = {}

        projects_dir = Path.home() / ".claude" / "projects"
        session_file = None

        if projects_dir.exists():
            project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]
            for project_dir in project_dirs:
                jsonl_files = list(project_dir.glob("*.jsonl"))
                if jsonl_files:
                    latest = max(jsonl_files, key=lambda p: p.stat().st_mtime)
                    session_file = latest
                    break

        if not session_file:
            print(json.dumps({}))
            return 0

        manager = SessionManager(session_file=session_file)

        # Get dashboard data — extract key metrics
        try:
            dashboard = manager.display_dashboard(session_file)
        except Exception:
            print(json.dumps({}))
            return 0

        # Extract key lines from dashboard using regex
        import re
        requests_match = re.search(r'Total Requests:\s*(\d+)', dashboard)
        history_match = re.search(r'History Size:\s*([\d,]+)', dashboard)
        cache_match = re.search(r'Cache Efficiency:\s*([\d.]+)', dashboard)

        requests = requests_match.group(1) if requests_match else "?"
        history = history_match.group(1) if history_match else "?"
        cache = cache_match.group(1) if cache_match else "?"

        session_id = session_file.stem[:8] if session_file else "unknown"
        summary = f"Session: {session_id} | Requests: {requests} | History: {history} tokens | Cache: {cache}%"

        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": summary
            }
        }
        print(json.dumps(output))
        return 0

    except Exception as e:
        print(json.dumps({}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
