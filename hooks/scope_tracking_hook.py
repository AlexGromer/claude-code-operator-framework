#!/usr/bin/env python3
"""
Scope Tracking Hook — PostToolUse (Write|Edit)

Thin proxy: extracts file_path from stdin, calls tools-mcp --scope-track,
returns warning as additionalContext.

All logic (state, scoring, domain detection) lives in Go MCP server tools-mcp.
"""

import json
import subprocess
from pathlib import Path
import sys

from pathlib import Path
MCP_BINARY = str(Path.home() / ".claude" / "mcp-servers" / "tools-mcp" / "tools-mcp")


def main():
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        from hook_stdin import read_hook_stdin
        input_data = read_hook_stdin()

        tool_name = input_data.get("tool_name", "")
        if tool_name not in ("Write", "Edit"):
            print(json.dumps({}))
            return

        file_path = input_data.get("tool_input", {}).get("file_path", "")
        if not file_path:
            print(json.dumps({}))
            return

        proc = subprocess.run(
            [MCP_BINARY, "--scope-track", file_path],
            capture_output=True, text=True, timeout=3,
        )

        if proc.returncode != 0 or not proc.stdout.strip():
            print(json.dumps({}))
            return

        result_data = json.loads(proc.stdout)
        warning = result_data.get("warning", "")

        if warning:
            print(json.dumps({"additionalContext": warning}))
        else:
            print(json.dumps({}))

    except Exception:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
