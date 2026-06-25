#!/usr/bin/env python3
"""
{Hook Name} ({GAP-ID or purpose})

{Brief description of what this hook does.}

Hook Type: {PreToolUse|PostToolUse|SessionStart|SessionEnd|UserPromptSubmit}
Matcher: {*|Bash|Edit|Write|specific_tool}
Blocking: {true|false}
Timeout: {1000-2000}ms
"""

import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Configuration
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "{hook_name}.jsonl"


def main():
    """Main hook entry point."""
    try:
        # Read hook input from stdin (JSON)
        try:
            input_data = json.load(sys.stdin)
        except Exception:
            input_data = {}

        tool_name = input_data.get("tool_name", os.environ.get("CLAUDE_TOOL_NAME", ""))
        tool_input = input_data.get("tool_input", {})

        # === HOOK LOGIC HERE ===

        # For PreToolUse: decide allow/block
        # result = {"decision": "allow"}  # or "block"
        # For PostToolUse: log/analyze
        result = {}

        # === END HOOK LOGIC ===

        # Log (optional)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                **result,
            }) + "\n")

        # Output result
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
