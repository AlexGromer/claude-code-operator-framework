#!/usr/bin/env python3
"""
Pattern Extraction Hook (GAP-PATTERN-*)

PostToolUse hook that extracts patterns from successful operations.
Builds pattern library for future reference.

Trigger: PostToolUse on successful tool executions
"""

import json
import os
import re
import sys
import fcntl
from pathlib import Path
from datetime import datetime
from hashlib import md5

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
PATTERNS_FILE = DATA_DIR / "extracted_patterns.jsonl"
PATTERN_INDEX = DATA_DIR / "pattern_index.json"

# Pattern categories to extract
PATTERN_TYPES = {
    "command": {
        "tools": ["Bash"],
        "extract": r'^([a-z_-]+(?:\s+[a-z_-]+)?)',  # First command words
    },
    "file_operation": {
        "tools": ["Read", "Write", "Edit"],
        "extract": r'([a-z_]+\.(py|js|ts|yaml|yml|json|md|sh))$',  # File types
    },
    "api_pattern": {
        "tools": ["WebFetch", "WebSearch"],
        "extract": r'(https?://[^/]+)',  # Domain patterns
    },
    "error_recovery": {
        "tools": ["Bash"],
        "extract": r'(error|failed|exception)',  # Error patterns
    },
}


def generate_pattern_id(pattern: str, category: str) -> str:
    """Generate unique pattern ID."""
    content = f"{category}:{pattern}"
    return f"PAT-{md5(content.encode()).hexdigest()[:8].upper()}"


def extract_patterns(tool_name: str, tool_input: str, tool_output: str) -> list:
    """Extract patterns from tool execution."""
    patterns = []

    for category, config in PATTERN_TYPES.items():
        if tool_name not in config["tools"]:
            continue

        # Extract from input
        matches = re.findall(config["extract"], tool_input, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            if len(match) > 2:  # Filter tiny matches
                patterns.append({
                    "category": category,
                    "pattern": match,
                    "source": "input",
                })

        # Extract from output (if short enough)
        if len(tool_output) < 5000:
            matches = re.findall(config["extract"], tool_output, re.IGNORECASE)
            for match in matches[:5]:  # Limit output patterns
                if isinstance(match, tuple):
                    match = match[0]
                if len(match) > 2:
                    patterns.append({
                        "category": category,
                        "pattern": match,
                        "source": "output",
                    })

    return patterns[:10]  # Limit total patterns


def is_successful_execution(tool_output: str) -> bool:
    """Check if execution was successful."""
    error_indicators = [
        "error:", "Error:", "ERROR",
        "failed", "Failed", "FAILED",
        "exception", "Exception",
        "not found", "No such file",
        "permission denied",
    ]
    return not any(indicator in tool_output for indicator in error_indicators)


def update_pattern_index(patterns: list):
    """Update pattern frequency index."""
    index = {}
    if PATTERN_INDEX.exists():
        try:
            index = json.loads(PATTERN_INDEX.read_text())
        except Exception:
            index = {}

    for p in patterns:
        pattern_id = generate_pattern_id(p["pattern"], p["category"])
        if pattern_id not in index:
            index[pattern_id] = {
                "pattern": p["pattern"],
                "category": p["category"],
                "count": 0,
                "first_seen": datetime.now().isoformat(),
                "last_seen": None,
            }

        index[pattern_id]["count"] += 1
        index[pattern_id]["last_seen"] = datetime.now().isoformat()

    # Write updated index with file locking
    tmp_path = str(PATTERN_INDEX) + ".tmp"
    with open(tmp_path, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(index, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    os.replace(tmp_path, str(PATTERN_INDEX))

    return index


def log_extraction(result: dict):
    """Log pattern extraction."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PATTERNS_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_input_str = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

    # Skip if no output
    if not tool_output:
        sys.exit(0)

    # Only process successful executions
    if not is_successful_execution(tool_output):
        sys.exit(0)

    # Parse input
    try:
        tool_input = json.loads(tool_input_str)
        if isinstance(tool_input, dict):
            tool_input_text = tool_input.get("command", "") or tool_input.get("file_path", "") or str(tool_input)
        else:
            tool_input_text = str(tool_input)
    except Exception:
        tool_input_text = tool_input_str

    # Extract patterns
    patterns = extract_patterns(tool_name, tool_input_text, tool_output)

    if not patterns:
        sys.exit(0)

    # Update index
    update_pattern_index(patterns)

    # Log extraction
    result = {
        "tool": tool_name,
        "patterns_extracted": len(patterns),
        "categories": list(set(p["category"] for p in patterns)),
        "patterns": [p["pattern"][:50] for p in patterns],
    }
    log_extraction(result)

    # Silent operation - no output to avoid noise
    sys.exit(0)


if __name__ == "__main__":
    main()
