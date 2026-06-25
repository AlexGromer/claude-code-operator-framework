#!/usr/bin/env python3
"""
Configuration Integrity Hook (GAP-CONFIG-INTEGRITY)

PreToolUse hook that validates configuration files before git commits.
Checks YAML/JSON syntax, validates structure, detects secrets.

Trigger: PreToolUse on Bash with git commit commands
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "config_integrity.jsonl"

# Patterns to check
SECRET_PATTERNS = [
    r'password\s*[=:]\s*["\'][^"\']+["\']',
    r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']',
    r'secret\s*[=:]\s*["\'][^"\']+["\']',
    r'token\s*[=:]\s*["\'][^"\']+["\']',
    r'-----BEGIN.*PRIVATE KEY-----',
    r'AKIA[0-9A-Z]{16}',  # AWS Access Key
]

# Files to validate
CONFIG_EXTENSIONS = ['.yaml', '.yml', '.json', '.toml', '.ini', '.env']


def detect_git_commit(tool_input: dict) -> bool:
    """Check if this is a git commit operation."""
    command = tool_input.get("command", "")
    return "git commit" in command or "git add" in command


def check_staged_files() -> list:
    """Get list of staged files."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    except Exception:
        pass
    return []


def validate_yaml(content: str) -> tuple:
    """Validate YAML syntax."""
    try:
        import yaml
        yaml.safe_load(content)
        return True, None
    except yaml.YAMLError as e:
        return False, str(e)
    except ImportError:
        return True, "yaml module not available"


def validate_json(content: str) -> tuple:
    """Validate JSON syntax."""
    try:
        json.loads(content)
        return True, None
    except json.JSONDecodeError as e:
        return False, str(e)


def check_for_secrets(content: str) -> list:
    """Check content for potential secrets."""
    found = []
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            found.append(pattern[:30])
    return found


def validate_config_file(filepath: str) -> dict:
    """Validate a single config file."""
    result = {
        "file": filepath,
        "valid_syntax": True,
        "secrets_found": [],
        "errors": [],
    }

    path = Path(filepath)
    if not path.exists():
        result["errors"].append("File not found")
        return result

    try:
        content = path.read_text()
    except Exception as e:
        result["errors"].append(f"Cannot read: {e}")
        return result

    # Check secrets
    secrets = check_for_secrets(content)
    if secrets:
        result["secrets_found"] = secrets

    # Validate syntax based on extension
    ext = path.suffix.lower()
    if ext in ['.yaml', '.yml']:
        valid, error = validate_yaml(content)
        result["valid_syntax"] = valid
        if error:
            result["errors"].append(f"YAML error: {error}")
    elif ext == '.json':
        valid, error = validate_json(content)
        result["valid_syntax"] = valid
        if error:
            result["errors"].append(f"JSON error: {error}")

    return result


def log_result(result: dict):
    """Log validation result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def main():
    # Get tool input
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input_str = os.environ.get("CLAUDE_TOOL_INPUT", "{}")

    try:
        tool_input = json.loads(tool_input_str)
    except Exception:
        tool_input = {"command": tool_input_str}

    # Only process Bash with git commands
    if tool_name != "Bash":
        sys.exit(0)

    if not detect_git_commit(tool_input):
        sys.exit(0)

    # Get staged files
    staged = check_staged_files()
    if not staged:
        sys.exit(0)

    # Filter config files
    config_files = [f for f in staged if any(f.endswith(ext) for ext in CONFIG_EXTENSIONS)]

    if not config_files:
        sys.exit(0)

    # Validate each file
    issues = []
    for filepath in config_files:
        result = validate_config_file(filepath)
        log_result(result)

        if result["secrets_found"]:
            issues.append(f"⚠️ SECRETS in {filepath}: {result['secrets_found']}")

        if not result["valid_syntax"]:
            issues.append(f"❌ SYNTAX ERROR in {filepath}: {result['errors']}")

    # Output issues
    if issues:
        output = {
            "status": "warning",
            "message": "Configuration issues detected",
            "issues": issues,
            "action": "Review before committing",
        }
        print(json.dumps(output))
        # Don't block, just warn
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
