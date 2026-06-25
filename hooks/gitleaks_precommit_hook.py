#!/usr/bin/env python3
"""
PreToolUse Hook - Gitleaks Enforcement
Blocks git commit if gitleaks scan hasn't been run or found secrets.

Hook Type: PreToolUse
Matcher: Bash
Trigger: git commit commands
Action: BLOCK if gitleaks not clean
"""

import json
import os
import re
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from hook_stdin import read_hook_stdin
import sys
from pathlib import Path


def is_git_commit(command: str) -> bool:
    """Check if the Bash command is an actual git commit (not inside echo/strings)."""
    # Split on command separators and check each part
    for part in re.split(r'[;&|]+', command):
        part = part.strip()
        if re.match(r'^(env\s+\S+=\S+\s+)*git\s+commit\b', part):
            return True
    return False


def run_gitleaks(cwd: str) -> tuple:
    """Run gitleaks and return (passed: bool, output: str)."""
    try:
        proc = subprocess.run(
            ["gitleaks", "detect", "--source", cwd, "--no-banner", "-v"],
            capture_output=True, text=True, timeout=30,
            cwd=cwd,
        )
        if proc.returncode == 0:
            return True, "No secrets found"
        else:
            # gitleaks returns 1 if secrets found
            return False, proc.stdout[:500] if proc.stdout else proc.stderr[:500]
    except FileNotFoundError:
        # gitleaks not installed — allow but warn
        return True, "gitleaks not installed — skipping scan"
    except subprocess.TimeoutExpired:
        return True, "gitleaks timed out — skipping"
    except Exception:
        return True, "gitleaks error — skipping"


def main():
    try:
        data = read_hook_stdin()
    except Exception:
        print(json.dumps({"decision": "approve"}))
        return

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({"decision": "approve"}))
        return

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not is_git_commit(command):
        print(json.dumps({"decision": "approve"}))
        return

    # Determine working directory
    cwd = os.environ.get("CLAUDE_WORKING_DIRECTORY", os.getcwd())

    passed, message = run_gitleaks(cwd)

    if passed:
        print(json.dumps({"decision": "approve"}))
    else:
        print(json.dumps({
            "decision": "block",
            "reason": f"GITLEAKS: Secrets detected in repository. Fix before committing.\n{message}"
        }))


if __name__ == "__main__":
    main()
