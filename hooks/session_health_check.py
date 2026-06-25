#!/usr/bin/env python3
"""
SessionStart Hook - Session Health Check
Displays session reopen recommendation if session has accumulated too much history.

GAP-EVAL-HEALTH-001 FIX: Added session_id tracking to debounce mechanism.
Debounce now resets when session_id changes (on session reopen).
"""

import os
import sys
import json
from pathlib import Path
_sys_path_set = True  # hook_stdin import below
from datetime import datetime, timedelta

import sys as _hsys
from pathlib import Path as _HPath
_hsys.path.insert(0, str(_HPath(__file__).parent))
from hook_stdin import read_hook_stdin

# Debounce configuration
DEBOUNCE_FILE = Path.home() / ".claude" / "evaluation" / "data" / "health_check_debounce.json"
DEBOUNCE_MINUTES = 30  # Don't show warning more than once per 30 minutes


def load_debounce() -> dict:
    """Load debounce state from file."""
    if DEBOUNCE_FILE.exists():
        try:
            return json.loads(DEBOUNCE_FILE.read_text())
        except Exception:
            pass
    return {"last_shown": None, "session_id": None}


def save_debounce(state: dict):
    """Save debounce state to file."""
    DEBOUNCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DEBOUNCE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def should_show_warning(current_session_id: str) -> bool:
    """Check if warning should be shown based on debounce state."""
    state = load_debounce()

    # If session_id changed, reset debounce (GAP-EVAL-HEALTH-001 fix)
    if state.get("session_id") != current_session_id:
        return True

    # Check time-based debounce
    last_shown = state.get("last_shown")
    if last_shown:
        last_time = datetime.fromisoformat(last_shown)
        if datetime.now() - last_time < timedelta(minutes=DEBOUNCE_MINUTES):
            return False

    return True


def update_debounce(session_id: str):
    """Update debounce state after showing warning."""
    save_debounce({
        "last_shown": datetime.now().isoformat(),
        "session_id": session_id,
    })


def main():
    """Main execution."""
    try:
        # Read input (required for hooks)
        try:
            input_data = read_hook_stdin(timeout_sec=5)
        except Exception:
            input_data = {}

        # Check settings.json integrity
        settings_path = Path.home() / ".claude" / "settings.json"
        backup_path = Path.home() / ".claude" / "settings.json.bak"
        try:
            with open(settings_path) as f:
                json.load(f)
        except Exception:
            if backup_path.exists():
                try:
                    with open(backup_path) as f:
                        json.load(f)
                    print(json.dumps({"additionalContext":
                        "WARNING: settings.json is corrupt! Backup available at settings.json.bak. "
                        "Restore with: cp ~/.claude/settings.json.bak ~/.claude/settings.json"}))
                    sys.exit(0)
                except Exception:
                    pass

        # Import session_summary to check current session health
        sys.path.insert(0, str(Path.home() / ".claude" / "evaluation"))
        from session_summary import find_latest_session_file, parse_session_file

        # Get current project path from stdin JSON (not Path.cwd() which may be wrong)
        cwd = Path(input_data.get("cwd", "") or os.environ.get("CLAUDE_WORKING_DIRECTORY", "") or str(Path.cwd())).resolve()
        claude_projects = Path.home() / ".claude" / "projects"
        encoded_path = str(cwd).replace('/', '-').replace('_', '-')
        project_path = claude_projects / encoded_path

        if not project_path.exists():
            # No session data yet
            print(json.dumps({}))
            sys.exit(0)

        try:
            session_file = find_latest_session_file(project_path)
            session_data = parse_session_file(session_file)

            # Get session ID from filename or environment
            current_session_id = session_file.stem if session_file else os.environ.get("CLAUDE_SESSION_ID", "unknown")

            # Check if session reopen is recommended
            # Opus 4.6 default context is 1M tokens; reopen at ~800K history
            # (conservative — allows for cache overhead and autocompact)
            if session_data['estimated_history'] > 800_000 or session_data['session_efficiency'] > 9500:
                # Check debounce before showing warning
                if not should_show_warning(current_session_id):
                    print(json.dumps({}))
                    sys.exit(0)

                lines = [
                    f"SESSION REOPEN RECOMMENDED. History: {session_data['estimated_history']:,} tokens, Cache: {session_data['session_efficiency']:.0f}%.",
                    "Use /exit to save and reopen. Progress will be preserved in MEMORY.md.",
                ]

                # Update debounce after showing
                update_debounce(current_session_id)

                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": "\n".join(lines)
                    }
                }
                print(json.dumps(output))
            else:
                # Session healthy, no output
                print(json.dumps({}))

        except FileNotFoundError:
            # No session file yet (first session)
            print(json.dumps({}))

    except Exception as e:
        # Non-blocking failure
        print(json.dumps({}), file=sys.stderr)

    sys.exit(0)


if __name__ == '__main__':
    main()
