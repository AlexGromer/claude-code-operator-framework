#!/usr/bin/env python3
"""
PreToolUse Hook - Settings Backup
Backs up ~/.claude/settings.json before any Edit or Write to that file.

Design:
- Fast path: shutil.copy2 only, no JSON parsing
- Never blocks: always outputs {"decision": "approve"}
- Fail open: outer except catches all errors silently
- Concurrent sessions: backup path includes session_id to avoid overwrite races.
  Falls back to settings.json.bak when session_id is not available.
"""

import json
import os
from pathlib import Path as _P
import sys
sys.path.insert(0, str(_P(__file__).parent))
from hook_stdin import read_hook_stdin
import shutil
import sys
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
SESSION_ID_FILE = Path.home() / ".claude" / "evaluation" / "data" / "current_session_id"


def _backup_path() -> Path:
    """Return a per-session backup path, falling back to shared .bak."""
    try:
        if SESSION_ID_FILE.exists():
            sid = SESSION_ID_FILE.read_text().strip()
            if sid:
                return Path.home() / ".claude" / f"settings.json.bak.{sid[:8]}"
    except Exception:
        pass
    return Path.home() / ".claude" / "settings.json.bak"


def main():
    try:
        data = read_hook_stdin()
    except Exception:
        print(json.dumps({"decision": "approve"}))
        return

    try:
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if file_path and file_path.endswith("settings.json") and not file_path.endswith("settings.local.json"):
            if SETTINGS_PATH.exists():
                shutil.copy2(str(SETTINGS_PATH), str(_backup_path()))
    except Exception:
        pass

    print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
