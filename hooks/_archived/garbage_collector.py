#!/usr/bin/env python3
# DEPRECATED: Use gc-mcp Go server instead (~/.claude/mcp-servers/gc-mcp/)
# Kept as fallback. Will be removed in v7.5.
"""
Garbage Collector for Claude Code artifacts.
Runs on SessionStart. Cleans stale task dirs, team configs, plans,
session-env, Python caches, debug files, spending archives,
security logs, and rotates BACKLOG.md.

Version: 2.1.0 (v7.4 — 11 cleanup targets, +empty dirs)
Hook event: SessionStart
"""

import json
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"


def clean_stale_tasks(max_age_hours: int = 24) -> int:
    """Remove task directories from sessions older than max_age_hours."""
    tasks_dir = CLAUDE_DIR / "tasks"
    if not tasks_dir.exists():
        return 0

    removed = 0
    now = datetime.now()
    cutoff = now - timedelta(hours=max_age_hours)

    for d in tasks_dir.iterdir():
        if not d.is_dir():
            continue
        # UUID-named dirs are session task lists
        name = d.name
        # Check if it looks like a UUID (8-4-4-4-12 hex pattern)
        parts = name.split("-")
        is_uuid = len(parts) == 5 and all(
            len(p) in (8, 4, 4, 4, 12) for p in parts
        )
        if not is_uuid:
            # Named team tasks — check age too
            pass

        # Check modification time
        try:
            mtime = datetime.fromtimestamp(d.stat().st_mtime)
            if mtime < cutoff:
                shutil.rmtree(d)
                removed += 1
        except (OSError, PermissionError):
            continue

    return removed


def clean_stale_teams(max_age_hours: int = 24) -> int:
    """Remove team configs from ended sessions."""
    teams_dir = CLAUDE_DIR / "teams"
    if not teams_dir.exists():
        return 0

    removed = 0
    now = datetime.now()
    cutoff = now - timedelta(hours=max_age_hours)

    for d in teams_dir.iterdir():
        if not d.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(d.stat().st_mtime)
            if mtime < cutoff:
                shutil.rmtree(d)
                removed += 1
        except (OSError, PermissionError):
            continue

    return removed


def rotate_spending_archive(max_files: int = 30) -> int:
    """Keep only the latest N spending archive files."""
    archive_dir = CLAUDE_DIR / "evaluation" / "data" / "spending_archive"
    if not archive_dir.exists():
        return 0

    files = sorted(archive_dir.glob("spending_*.jsonl"), key=lambda f: f.stat().st_mtime)
    removed = 0
    while len(files) > max_files:
        oldest = files.pop(0)
        try:
            oldest.unlink()
            removed += 1
        except OSError:
            continue

    return removed


def rotate_spending_tracker(max_entries: int = 500) -> int:
    """Trim spending tracker to last N entries."""
    tracker = CLAUDE_DIR / "evaluation" / "data" / "spending_tracker.jsonl"
    if not tracker.exists():
        return 0

    try:
        lines = tracker.read_text().strip().split("\n")
        if len(lines) <= max_entries:
            return 0
        trimmed = len(lines) - max_entries
        tracker.write_text("\n".join(lines[-max_entries:]) + "\n")
        return trimmed
    except (OSError, PermissionError):
        return 0


def rotate_backlog(project_dir: str) -> dict:
    """Move completed items from Active to Archive. Enforce limits."""
    backlog_path = Path(project_dir) / "BACKLOG.md"
    if not backlog_path.exists():
        return {"moved": 0, "pruned": 0}

    try:
        content = backlog_path.read_text()
    except OSError:
        return {"moved": 0, "pruned": 0}

    lines = content.split("\n")
    active_section = []
    archive_section = []
    deferred_section = []
    current_section = None
    other_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Active"):
            current_section = "active"
            other_lines.append(line)
            continue
        elif stripped.startswith("## Deferred"):
            current_section = "deferred"
            other_lines.append(line)
            continue
        elif stripped.startswith("## Completed Archive"):
            current_section = "archive"
            other_lines.append(line)
            continue
        elif stripped.startswith("## "):
            current_section = "other"

        if current_section == "active":
            active_section.append(line)
        elif current_section == "deferred":
            deferred_section.append(line)
        elif current_section == "archive":
            archive_section.append(line)
        else:
            other_lines.append(line)

    # Move completed from Active to Archive
    moved = 0
    new_active = []
    for line in active_section:
        if line.strip().startswith("- [x]"):
            archive_section.append(line)
            moved += 1
        else:
            new_active.append(line)

    # Prune archive to last 50
    pruned = 0
    archive_items = [l for l in archive_section if l.strip().startswith("- [")]
    archive_other = [l for l in archive_section if not l.strip().startswith("- [")]
    if len(archive_items) > 50:
        pruned = len(archive_items) - 50
        archive_items = archive_items[-50:]

    if moved == 0 and pruned == 0:
        return {"moved": 0, "pruned": 0}

    # Rebuild file
    rebuilt = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Active"):
            rebuilt.append(line)
            rebuilt.extend(new_active)
            continue
        elif stripped.startswith("## Deferred"):
            rebuilt.append(line)
            rebuilt.extend(deferred_section)
            continue
        elif stripped.startswith("## Completed Archive"):
            rebuilt.append(line)
            rebuilt.extend(archive_other)
            rebuilt.extend(archive_items)
            continue

    # Simple rebuild: header + active + deferred + archive
    header = [l for l in lines if not any(
        l.strip().startswith(s) for s in ["- [", "## Active", "## Deferred", "## Completed"]
    ) or l.strip().startswith("# BACKLOG")]

    output = f"# BACKLOG — {Path(project_dir).name}\n\n"
    output += "## Active\n"
    output += "\n".join(new_active).strip() + "\n"
    output += "\n## Deferred\n"
    output += "\n".join(deferred_section).strip() + "\n"
    output += "\n## Completed Archive\n"
    output += "\n".join(archive_other + archive_items).strip() + "\n"

    try:
        backlog_path.write_text(output)
    except OSError:
        pass

    return {"moved": moved, "pruned": pruned}


def clean_stale_plans(max_age_days: int = 7) -> int:
    """Remove plan files older than max_age_days."""
    plans_dir = CLAUDE_DIR / "plans"
    if not plans_dir.exists():
        return 0

    removed = 0
    cutoff = datetime.now() - timedelta(days=max_age_days)

    for f in plans_dir.glob("*.md"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                removed += 1
        except (OSError, PermissionError):
            continue

    return removed


def clean_stale_session_env(max_age_days: int = 3) -> int:
    """Remove session-env directories older than max_age_days."""
    session_env_dir = CLAUDE_DIR / "session-env"
    if not session_env_dir.exists():
        return 0

    removed = 0
    cutoff = datetime.now() - timedelta(days=max_age_days)

    for d in session_env_dir.iterdir():
        if not d.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(d.stat().st_mtime)
            if mtime < cutoff:
                shutil.rmtree(d)
                removed += 1
        except (OSError, PermissionError):
            continue

    return removed


def clean_python_caches() -> int:
    """Remove __pycache__ and .pytest_cache directories under ~/.claude/."""
    removed = 0

    for pattern in ["__pycache__", ".pytest_cache"]:
        for d in CLAUDE_DIR.rglob(pattern):
            if d.is_dir():
                try:
                    shutil.rmtree(d)
                    removed += 1
                except (OSError, PermissionError):
                    continue

    return removed


def rotate_security_log(max_size_mb: int = 5) -> bool:
    """Rotate security_audit.log if it exceeds max_size_mb."""
    log_file = CLAUDE_DIR / "security_audit.log"
    if not log_file.exists():
        return False

    try:
        size_mb = log_file.stat().st_size / (1024 * 1024)
        if size_mb <= max_size_mb:
            return False

        # Keep last 1000 lines, archive the rest
        lines = log_file.read_text(encoding="utf-8", errors="replace").split("\n")
        if len(lines) > 1000:
            log_file.write_text("\n".join(lines[-1000:]) + "\n")
            return True
    except (OSError, PermissionError):
        pass

    return False


def clean_empty_dirs() -> int:
    """Remove empty directories in agent-memory/ and other known locations."""
    removed = 0
    targets = [
        CLAUDE_DIR / "agent-memory",
        CLAUDE_DIR / "commands",
    ]
    for target in targets:
        if not target.exists():
            continue
        # Walk bottom-up to remove nested empty dirs
        for dirpath, dirnames, filenames in os.walk(str(target), topdown=False):
            if not dirnames and not filenames:
                try:
                    os.rmdir(dirpath)
                    removed += 1
                except OSError:
                    continue
    return removed


def clean_debug_files(max_age_hours: int = 48) -> int:
    """Remove debug log/txt files older than max_age_hours."""
    removed = 0
    cutoff = datetime.now() - timedelta(hours=max_age_hours)

    # Debug logs in ~/.claude/
    for pattern in ["*_debug.log", "*_debug.txt"]:
        for f in CLAUDE_DIR.glob(pattern):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    removed += 1
            except (OSError, PermissionError):
                continue

    # Debug/session txt files in evaluation/data/
    eval_data = CLAUDE_DIR / "evaluation" / "data"
    if eval_data.exists():
        for f in eval_data.glob("*.txt"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    removed += 1
            except (OSError, PermissionError):
                continue

    return removed


def main():
    """Run all garbage collection tasks."""
    # Read stdin for hook context
    try:
        context = json.loads(sys.stdin.read())
    except Exception:
        context = {}

    cwd = context.get("cwd", os.getcwd())

    results = {}

    # 1. Clean stale task dirs (older than 24h)
    results["tasks_removed"] = clean_stale_tasks(max_age_hours=24)

    # 2. Clean stale team configs (older than 24h)
    results["teams_removed"] = clean_stale_teams(max_age_hours=24)

    # 3. Rotate spending archive (keep last 30)
    results["archives_pruned"] = rotate_spending_archive(max_files=30)

    # 4. Trim spending tracker (keep last 500 entries)
    results["tracker_trimmed"] = rotate_spending_tracker(max_entries=500)

    # 5. Rotate BACKLOG.md (move completed to archive, prune)
    backlog = rotate_backlog(cwd)
    results["backlog_moved"] = backlog["moved"]
    results["backlog_pruned"] = backlog["pruned"]

    # 6. Clean stale plan files (older than 7 days)
    results["plans_removed"] = clean_stale_plans(max_age_days=7)

    # 7. Clean stale session-env dirs (older than 3 days)
    results["session_env_removed"] = clean_stale_session_env(max_age_days=3)

    # 8. Clean Python caches
    results["caches_removed"] = clean_python_caches()

    # 9. Rotate security audit log (>5MB)
    if rotate_security_log(max_size_mb=5):
        results["security_log"] = "rotated"

    # 10. Clean debug files (older than 48h)
    results["debug_files_removed"] = clean_debug_files(max_age_hours=48)

    # 11. Clean empty directories (agent-memory, commands, etc.)
    results["empty_dirs_removed"] = clean_empty_dirs()

    # Only output if something was cleaned
    actions = [f"{k}: {v}" for k, v in results.items() if v > 0]
    if actions:
        print(f"GC: {', '.join(actions)}", file=sys.stderr)


if __name__ == "__main__":
    main()
