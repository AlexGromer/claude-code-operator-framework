#!/usr/bin/env python3
"""
PreCompact Hook — Saves task state before context compression.

Version: 2.0.0 (v6.0 — added task state saving to MEMORY.md)
"""

import sys
import json
import fcntl
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SESSION_ID_FILE = Path.home() / ".claude/evaluation/data/current_session_id"
COMPACT_LOG = Path.home() / ".claude/evaluation/data/compact_events.jsonl"


def read_session_id() -> str:
    try:
        if SESSION_ID_FILE.exists():
            return SESSION_ID_FILE.read_text().strip()[:36]
    except Exception:
        pass
    return "unknown"


def get_git_state() -> dict:
    """Get current git branch and modified files."""
    state = {"branch": "unknown", "files": []}
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            state["branch"] = result.stdout.strip()

        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            state["files"] = [f for f in result.stdout.strip().split("\n") if f][:10]
    except Exception:
        pass
    return state


def save_detailed_summary(git_state: dict, memory_file: Path) -> str:
    """Save detailed session summary to separate file, return path."""
    try:
        summary_path = memory_file.parent / "session_summary.md"
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        summary = f"# Session Summary ({now})\n\n"
        summary += f"## Branch: {git_state.get('branch', 'unknown')}\n"
        files = git_state.get('files', [])
        summary += f"## Modified: {', '.join(files[:10]) if files else 'none'}\n\n"

        # Try to read plan file for completed/pending items
        plans_dir = Path.home() / ".claude" / "plans"
        if plans_dir.exists():
            plans = sorted(plans_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if plans:
                try:
                    plan_content = plans[0].read_text(encoding="utf-8")
                    completed = [l.strip() for l in plan_content.split('\n') if '[x]' in l.lower()][:20]
                    pending = [l.strip() for l in plan_content.split('\n') if '[ ]' in l.lower()][:20]
                    if completed:
                        summary += "## Completed\n" + '\n'.join(f"- {c}" for c in completed) + "\n\n"
                    if pending:
                        summary += "## Pending\n" + '\n'.join(f"- {p}" for p in pending) + "\n\n"
                except Exception:
                    pass

        summary_path.write_text(summary, encoding="utf-8")
        return str(summary_path)
    except Exception:
        return ""


def save_to_memory(git_state: dict) -> None:
    """Save in-progress state to MEMORY.md for quick recovery."""
    try:
        # Find project memory
        cwd = Path.cwd()
        memory_dirs = list(Path.home().glob(".claude/projects/*/memory/MEMORY.md"))
        if not memory_dirs:
            return

        memory_file = memory_dirs[0]
        content = memory_file.read_text(encoding="utf-8")

        # Remove old In-Progress section if present
        import re
        content = re.sub(r'\n## In-Progress\n.*?(?=\n## |\Z)', '', content, flags=re.DOTALL)

        # Check for plan file and BACKLOG.md
        plan_file = ""
        plans_dir = Path.home() / ".claude" / "plans"
        if plans_dir.exists():
            plans = sorted(plans_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if plans:
                plan_file = str(plans[0])

        backlog = ""
        backlog_path = cwd / "BACKLOG.md"
        if backlog_path.exists():
            backlog = str(backlog_path)

        # Add new In-Progress section
        files_str = ", ".join(git_state.get("files", [])[:5]) or "none"
        in_progress = f"""
## In-Progress
- Branch: {git_state.get('branch', 'unknown')}
- Modified files: {files_str}
- Compacted at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
"""
        if plan_file:
            in_progress += f"- Plan: {plan_file}\n"
        if backlog:
            in_progress += f"- Backlog: {backlog}\n"
        in_progress += "- Action: Read BACKLOG.md and MEMORY.md In-Progress to resume.\n"
        # Save detailed summary to separate file
        summary_path = save_detailed_summary(git_state, memory_file)
        if summary_path:
            in_progress += f"- Summary: {Path(summary_path).name}\n"
        content = content.rstrip() + "\n" + in_progress

        with open(memory_file, "w") as f:
            f.write(content)
    except Exception:
        pass


def log_compact_event(session_id: str, context_info: dict) -> None:
    try:
        COMPACT_LOG.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session": session_id[:8],
            "info": {k: v for k, v in context_info.items() if k in ("message_count", "token_count")}
        }
        with open(COMPACT_LOG, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(event, separators=(",", ":")) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass


def main():
    try:
        stdin_data = sys.stdin.read().strip()
        context_info = json.loads(stdin_data) if stdin_data else {}

        session_id = read_session_id()
        git_state = get_git_state()

        # Save state to MEMORY.md
        save_to_memory(git_state)

        # Log event
        log_compact_event(session_id, context_info)

        # Output recovery context
        files_str = ", ".join(git_state.get("files", [])[:5]) or "none"
        output = {
            "additionalContext": (
                f"⚠️ CONTEXT COMPACTED. Task state saved to MEMORY.md. "
                f"Branch: {git_state['branch']}. Modified: {files_str}. "
                f"Resume from last step. Check MEMORY.md In-Progress section."
            )
        }
        print(json.dumps(output))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
