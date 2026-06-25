#!/usr/bin/env python3
"""
FILEMAP Auto-Update Hook — PostToolUse
Updates FILEMAP.md when files are created via Write tool.

Hook Type: PostToolUse
Trigger: After Write tool completes successfully
Action: ALLOW-ONLY (PostToolUse cannot block)
"""

import json
import os
import sys
from pathlib import Path

BYPASS_TOOLS = {"Edit", "Read", "Glob", "Grep"}


def find_filemap(file_path: str) -> str | None:
    """Find FILEMAP.md in the project root containing the file."""
    path = Path(file_path).resolve()
    for _ in range(10):
        path = path.parent
        filemap = path / "FILEMAP.md"
        if filemap.exists():
            return str(filemap)
        if path == path.parent:
            break
    return None


def is_in_filemap(filemap_content: str, rel_path: str) -> bool:
    """Check if the file is already listed in FILEMAP.md."""
    return rel_path in filemap_content


def guess_purpose(rel_path: str) -> str:
    """Guess file purpose from path and extension."""
    ext = Path(rel_path).suffix.lower()
    name = Path(rel_path).name.lower()

    if "test" in name:
        return "Tests"
    if name in ("readme.md", "readme"):
        return "Project documentation"
    if name in ("changelog.md", "changes.md"):
        return "Version history"
    if name.startswith("dockerfile"):
        return "Container definition"

    purpose_map = {
        ".py": "Python source",
        ".go": "Go source",
        ".rs": "Rust source",
        ".js": "JavaScript source",
        ".ts": "TypeScript source",
        ".jsx": "React component",
        ".tsx": "React component (TS)",
        ".vue": "Vue component",
        ".md": "Documentation",
        ".json": "Configuration",
        ".yaml": "Configuration",
        ".yml": "Configuration",
        ".toml": "Configuration",
        ".sql": "Database schema/migration",
        ".sh": "Shell script",
        ".dockerfile": "Container definition",
        ".tf": "Terraform config",
        ".html": "Web page",
        ".css": "Stylesheet",
    }
    return purpose_map.get(ext, "Project file")


def add_to_filemap(filemap_path: str, file_path: str) -> bool:
    """Add a new file entry to FILEMAP.md Quick Reference table."""
    try:
        filemap = Path(filemap_path)
        project_root = filemap.parent
        rel_path = os.path.relpath(file_path, project_root)

        # Skip non-significant files
        skip_patterns = [
            ".git/", "__pycache__", ".pyc", ".tmp", ".swp",
            "node_modules/", ".claude/", ".env",
        ]
        if any(p in rel_path for p in skip_patterns):
            return False

        content = filemap.read_text(encoding="utf-8")

        if is_in_filemap(content, rel_path):
            return False

        lines = content.split("\n")
        insert_idx = None
        for i, line in enumerate(lines):
            if line.startswith("## Directory Structure") or line.startswith("## Module Dependency"):
                insert_idx = i
                break

        if insert_idx is None:
            return False

        purpose = guess_purpose(rel_path)
        new_row = f"| {rel_path} | {purpose} | — |"
        lines.insert(insert_idx, new_row)

        filemap.write_text("\n".join(lines), encoding="utf-8")
        return True

    except Exception as e:
        print(f"[filemap_update_hook] add_to_filemap error: {e}", file=sys.stderr)
        return False


def main():
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from hook_stdin import read_hook_stdin
        data = read_hook_stdin()
    except Exception:
        return

    try:
        tool_name = data.get("tool_name", "")

        if tool_name in BYPASS_TOOLS:
            return

        # Only process Write tool (new file creation)
        if tool_name != "Write":
            return

        # Extract file path from tool input
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")
        if not file_path:
            return

        # Check tool result is present (indicates success)
        tool_result = data.get("tool_result", {})
        if tool_result is None:
            return

        # Find FILEMAP.md
        filemap_path = find_filemap(file_path)
        if not filemap_path:
            return

        if add_to_filemap(filemap_path, file_path):
            print(f"[filemap_update_hook] Added {file_path} to {filemap_path}", file=sys.stderr)

    except Exception as e:
        print(f"[filemap_update_hook] error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
