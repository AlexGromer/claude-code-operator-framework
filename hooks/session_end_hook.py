#!/usr/bin/env python3
"""
SessionEnd Hook — Consolidated session cleanup and summary.

Combines:
1. Session summary display (metrics, efficiency)
2. Session quality evaluation
3. Session continuity data (git branch, last commit for resume)
4. Pipeline state cleanup (mark as ended)

Version: 2.0.0
Created: 2026-01-27
Updated: 2026-02-09 — Consolidated with session_continuity_hook + pipeline state cleanup
"""

import sys
import json
import os
import fcntl
import subprocess
import time
from pathlib import Path
_sys_path_set = True  # hook_stdin import below
from datetime import datetime, timezone

import sys as _hsys
from pathlib import Path as _HPath
_hsys.path.insert(0, str(_HPath(__file__).parent))
from hook_stdin import read_hook_stdin


EVAL_DIR = Path.home() / ".claude" / "evaluation"
DATA_DIR = EVAL_DIR / "data"
CONTINUITY_FILE = DATA_DIR / "session_continuity.jsonl"
AGENT_WORK_DIR = Path("/opt/agent_work_directory")


def run_session_summary():
    """Call session_summary.py for formatted output."""
    summary_script = EVAL_DIR / "session_summary.py"
    if not summary_script.exists():
        return

    try:
        result = subprocess.run(
            ["python3", str(summary_script)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout:
            print(result.stdout, file=sys.stderr, flush=True)
        if result.stderr:
            print(result.stderr, file=sys.stderr, flush=True)
    except subprocess.TimeoutExpired:
        print("Session summary timeout", file=sys.stderr)
    except Exception as e:
        print(f"Session summary error: {e}", file=sys.stderr)


def run_session_eval():
    """Call session_eval_hook.py for quality evaluation."""
    eval_script = EVAL_DIR / "hooks" / "session_eval_hook.py"
    if not eval_script.exists():
        return

    try:
        result = subprocess.run(
            ["python3", str(eval_script)],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.stdout:
            print(result.stdout, file=sys.stderr, flush=True)
        if result.stderr:
            print(result.stderr, file=sys.stderr, flush=True)
    except subprocess.TimeoutExpired:
        print("Session evaluation timeout", file=sys.stderr)
    except Exception as e:
        print(f"Session evaluation error: {e}", file=sys.stderr)


def save_continuity_data(session_id: str):
    """Save session continuity data with task context for seamless transitions."""
    cwd = os.environ.get("CLAUDE_WORKING_DIRECTORY", os.getcwd())

    context = {
        "session_id": session_id,
        "working_directory": cwd,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Get git state
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5
        )
        if result.returncode == 0:
            context["git_branch"] = result.stdout.strip()

        result = subprocess.run(
            ["git", "log", "-1", "--format=%h %s"],
            capture_output=True, text=True, cwd=cwd, timeout=5
        )
        if result.returncode == 0:
            context["last_commit"] = result.stdout.strip()

        # Modified files (task context)
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, cwd=cwd, timeout=5
        )
        if result.returncode == 0:
            files = [f for f in result.stdout.strip().split("\n") if f][:10]
            if files:
                context["files_modified"] = files
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass

    # Check for active plan file
    plans_dir = Path.home() / ".claude" / "plans"
    if plans_dir.exists():
        plans = sorted(plans_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if plans:
            context["plan_file"] = str(plans[0])

    # Check MEMORY.md for In-Progress section (task description)
    try:
        memory_dirs = list(Path.home().glob(".claude/projects/*/memory/MEMORY.md"))
        if memory_dirs:
            mem_text = memory_dirs[0].read_text(encoding="utf-8")
            import re
            m = re.search(r'## In-Progress\n(.*?)(?=\n## |\Z)', mem_text, re.DOTALL)
            if m:
                context["task_description"] = m.group(1).strip()[:200]
    except Exception:
        pass

    # Check for BACKLOG.md in working directory
    backlog_path = Path(cwd) / "BACKLOG.md"
    if backlog_path.exists():
        context["backlog_file"] = str(backlog_path)
        try:
            backlog_text = backlog_path.read_text(encoding="utf-8")
            import re as _re2
            # Count active tasks
            active = _re2.findall(r'- \[ \]', backlog_text)
            completed = _re2.findall(r'- \[x\]', backlog_text)
            context["backlog_summary"] = f"{len(active)} active, {len(completed)} completed"
        except Exception:
            pass

    # Extract next_steps from plan file if available
    if context.get("plan_file"):
        try:
            plan_text = Path(context["plan_file"]).read_text(encoding="utf-8")
            import re as _re
            # Find uncompleted phases/tasks
            phases = _re.findall(r'## Фаза \d+[^\n]*', plan_text)
            if phases:
                context["next_steps"] = phases[-1].strip()[:200]
        except Exception:
            pass

    # Write to JSONL with file locking
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONTINUITY_FILE, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(context) + "\n")
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        print(f"Continuity save error: {e}", file=sys.stderr)


def cleanup_pipeline_state(session_id: str):
    """Mark pipeline state as session-ended (not delete — may be needed for resume)."""
    if not session_id or session_id == "unknown":
        return

    state_file = AGENT_WORK_DIR / session_id / "pipeline_state.json"
    if not state_file.exists():
        return

    try:
        with open(state_file) as f:
            state = json.load(f)
        state["session_ended"] = True
        state["ended_at"] = datetime.now(timezone.utc).isoformat()
        tmp = state_file.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        tmp.rename(state_file)
    except Exception as e:
        print(f"Pipeline state cleanup error: {e}", file=sys.stderr)


def cleanup_mcp_profiles():
    """Remove non-essential MCP servers for the current project on session end.

    Essential servers remain. Domain-specific servers (security, osint, etc.)
    are unloaded to prevent accumulation across sessions.
    """
    try:
        cwd = os.environ.get("CLAUDE_WORKING_DIRECTORY", os.getcwd())

        # Skip paths that shouldn't have MCP servers
        skip_prefixes = ("/tmp", str(Path.home() / ".claude"))
        if any(cwd.startswith(p) for p in skip_prefixes):
            return

        config_file = Path.home() / ".claude.json"
        if not config_file.exists():
            return

        # Essential servers list — source of truth: profile-mcp Go binary (profiles.go)
        # Keep in sync manually. Run: profile-mcp --list to verify.
        essential_names = {
            "github", "fetch", "filesystem", "memory", "git",
            "sequential-thinking", "sqlite",
            "backlog-mcp", "profile-mcp", "doctor-mcp", "gc-mcp",
            "score-mcp", "tools-mcp"
        }

        with open(config_file, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            data = json.loads(f.read())

            project_cfg = data.get("projects", {}).get(cwd, {})
            servers = project_cfg.get("mcpServers", {})

            to_remove = [name for name in servers if name not in essential_names]
            if not to_remove:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return

            for name in to_remove:
                del servers[name]

            f.seek(0)
            f.truncate()
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            print(f"MCP cleanup: removed {len(to_remove)} non-essential servers for {cwd}", file=sys.stderr)
    except Exception as e:
        print(f"MCP cleanup error: {e}", file=sys.stderr)


def main():
    """Main execution — consolidated session end operations."""
    try:
        # Read input (required for hooks)
        try:
            input_data = read_hook_stdin(timeout_sec=5)
        except Exception:
            input_data = {}

        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

        # 1. Session summary
        run_session_summary()

        # 2. Session quality evaluation
        run_session_eval()

        # 3. Save continuity data
        save_continuity_data(session_id)

        # 4. Cleanup pipeline state
        cleanup_pipeline_state(session_id)

        # 5. Cleanup non-essential MCP servers
        cleanup_mcp_profiles()

        print(json.dumps({}))

    except Exception as e:
        print(f"Session end hook error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == '__main__':
    main()
