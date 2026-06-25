#!/usr/bin/env python3
"""
SessionStart Reinforcement Hook
Injects critical instructions + config drift warnings at session start.
Version: 3.0.0 (v7.3 — AUTO_ACTION for project-init)
"""

import json
import os
import sys
from pathlib import Path

REINFORCEMENT = """
SESSION ACTIVE. Rules from ~/.claude/rules/ loaded. Gap detection: AUTOMATIC. Log to GAPS.md.
"""

def check_config_drift() -> str:
    """Lightweight drift check: count modules/agents/skills vs CLAUDE.md claims."""
    try:
        claude_dir = Path.home() / ".claude"
        warnings = []

        # Count actual files (fast glob, ~10ms)
        modules = len([f for f in (claude_dir / "modules").glob("*.md") if "_archived" not in str(f)])
        agents = len(list((claude_dir / "agents").glob("*.md")))
        skills = len([d for d in (claude_dir / "skills").iterdir() if d.is_dir() and not d.name.startswith(("_", "."))])
        rules = len([f for f in (claude_dir / "rules").glob("*.md") if "_archived" not in str(f)])

        # Read CLAUDE.md and extract claimed counts
        claude_md = claude_dir / "CLAUDE.md"
        if not claude_md.exists():
            return ""
        text = claude_md.read_text(encoding="utf-8")

        import re
        def extract_count(pattern):
            m = re.search(pattern, text)
            return int(m.group(1)) if m else None

        claimed_modules = extract_count(r"(\d+) modules")
        claimed_agents = extract_count(r"(\d+) (?:custom )?subagents|(\d+) agents")
        if claimed_agents is None:
            m = re.search(r"(\d+) agents", text)
            claimed_agents = int(m.group(1)) if m else None
        claimed_rules = extract_count(r"(\d+) (?:behavior )?rules")

        # Compare
        if claimed_modules and abs(modules - claimed_modules) > 1:
            warnings.append(f"Modules: CLAUDE.md says {claimed_modules}, actual {modules}")
        if claimed_agents and abs(agents - claimed_agents) > 2:
            warnings.append(f"Agents: CLAUDE.md says {claimed_agents}, actual {agents}")
        if claimed_rules and abs(rules - claimed_rules) > 1:
            warnings.append(f"Rules: CLAUDE.md says {claimed_rules}, actual {rules}")

        if warnings:
            return "\n⚠️ CONFIG DRIFT DETECTED:\n" + "\n".join(f"  - {w}" for w in warnings) + "\nUpdate CLAUDE.md counts to match reality."
        return ""
    except Exception:
        return ""

def _mechanically_bootstrap(project_path: Path, ver_text: str, missing: list) -> list:
    """Create essential files from templates deterministically.

    Returns list of filenames that were successfully created.
    Only creates files that can be produced without LLM judgment:
    - ARCHITECTURE.md: base template with placeholder substitution
    - BACKLOG.md: empty backlog from template
    """
    created = []
    templates_dir = Path.home() / ".claude" / "templates" / "project-init"
    if not templates_dir.exists():
        return created

    # Extract metadata from .claude-ver for placeholder substitution
    import re
    project_name = project_path.name
    project_type = "unknown"
    m = re.search(r'project-type:\s*(\S+)', ver_text)
    if m:
        project_type = m.group(1)

    from datetime import date
    today = str(date.today())

    replacements = {
        "{{project_name}}": project_name,
        "{{project_type}}": project_type,
        "{{date}}": today,
        "{{project_purpose}}": "<!-- Fill in project purpose -->",
        "{{in_scope}}": "<!-- Define scope -->",
        "{{out_of_scope}}": "<!-- Define exclusions -->",
    }

    # ARCHITECTURE.md — base template (no type extension, LLM can enhance later)
    if "ARCHITECTURE.md" in missing:
        tmpl = templates_dir / "ARCHITECTURE.md.template"
        if tmpl.exists():
            try:
                content = tmpl.read_text(encoding="utf-8")
                for key, val in replacements.items():
                    content = content.replace(key, val)
                (project_path / "ARCHITECTURE.md").write_text(content, encoding="utf-8")
                created.append("ARCHITECTURE.md")
            except Exception:
                pass

    # BACKLOG.md — empty backlog
    if "BACKLOG.md" in missing:
        tmpl = templates_dir / "BACKLOG.md.template"
        if tmpl.exists():
            try:
                content = tmpl.read_text(encoding="utf-8")
                for key, val in replacements.items():
                    content = content.replace(key, val)
                (project_path / "BACKLOG.md").write_text(content, encoding="utf-8")
                created.append("BACKLOG.md")
            except Exception:
                pass

    return created


def check_new_project(cwd: str = "") -> str:
    """Check if current project has been initialized (.ver file + project memory).
    Returns AUTO_ACTION directives for project-init when needed."""
    try:
        import os
        if not cwd:
            cwd = os.environ.get("CLAUDE_WORKING_DIRECTORY", os.getcwd())
        project_path = Path(cwd)
        ver_file = project_path / ".claude-ver"
        version_file = Path.home() / ".claude" / "VERSION"
        try:
            current_version = version_file.read_text(encoding="utf-8").strip()
        except Exception:
            current_version = "7.6.0"

        # Mechanical bootstrap runs BEFORE cooldown — ensures files always exist
        # even when wrapper just created .claude-ver + cooldown marker
        if ver_file.exists():
            ver_text_early = ver_file.read_text(encoding="utf-8")
            essential_quick = ["ARCHITECTURE.md", "BACKLOG.md"]
            missing_quick = [f for f in essential_quick if not (project_path / f).exists()]
            if missing_quick:
                _mechanically_bootstrap(project_path, ver_text_early, missing_quick)

        # Cooldown: skip LLM-based AUTO_ACTION if project-init recently completed
        init_marker = project_path / ".claude-init-attempted"
        if init_marker.exists():
            from datetime import datetime, timedelta
            try:
                mtime = datetime.fromtimestamp(init_marker.stat().st_mtime)
                if datetime.now() - mtime < timedelta(hours=1):
                    return ""  # Cooldown active (project-init ran recently)
            except OSError:
                pass

        # Check .ver file for version migration
        if ver_file.exists():
            ver_text = ver_file.read_text(encoding="utf-8")
            import re
            m = re.search(r'config-version:\s*([\d.]+)', ver_text)
            if m:
                old_ver = m.group(1)
                if old_ver != current_version:
                    return f"\nAUTO_ACTION: /project-init --upgrade\nProject config outdated (v{old_ver} → v{current_version})."

            # Check for missing essential project files — delegate to project-init --check
            # These files are required for ALL project types (infrastructure, not content)
            essential_in_project = [
                "BACKLOG.md",
                "FILEMAP.md",
                "ARCHITECTURE.md",
            ]
            # settings.local.json lives in .claude/ subdir
            essential_in_claude_dir = [
                (".claude/settings.local.json", "settings.local.json"),
            ]
            missing = []
            for fname in essential_in_project:
                if not (project_path / fname).exists():
                    missing.append(fname)
            for fpath, display_name in essential_in_claude_dir:
                if not (project_path / fpath).exists():
                    missing.append(display_name)

            # Project memory (outside project dir, in ~/.claude/projects/)
            project_hash = cwd.replace("/", "-").replace("_", "-")
            project_memory = Path.home() / ".claude" / "projects" / project_hash / "memory" / "MEMORY.md"
            if not project_memory.exists():
                missing.append("project MEMORY.md")

            # Mechanical bootstrap: create files from templates deterministically
            # before delegating to LLM. Ensures files always exist.
            if missing:
                created = _mechanically_bootstrap(project_path, ver_text, missing)
                # Remove mechanically created files from missing list
                missing = [f for f in missing if f not in created]

            if missing:
                return f"\nAUTO_ACTION: /project-init --check\nMissing files: {', '.join(missing)}"

            return ""  # Everything OK

        # No .ver file — check if old or new project
        project_hash = cwd.replace("/", "-").replace("_", "-")
        project_memory = Path.home() / ".claude" / "projects" / project_hash / "memory" / "MEMORY.md"

        if project_memory.exists():
            # Old project with memory but no .claude-ver (pre-v7.0)
            return (
                "\nAUTO_ACTION: /project-init --upgrade"
                f"\nProject at {cwd} has memory but no .claude-ver (pre-v7.0). Upgrade needed."
            )
        else:
            # Completely new project — only trigger for non-system dirs
            skip_prefixes = ["/tmp", str(Path.home() / ".claude"), "/proc", "/sys"]
            if any(cwd.startswith(p) for p in skip_prefixes):
                return ""

            return (
                "\nAUTO_ACTION: /project-init"
                f"\nNew project detected at {cwd}. Initialize with project-init."
            )
    except Exception:
        pass
    return ""

def ensure_essential_servers(cwd: str = "") -> str:
    """Ensure essential MCP servers are provisioned for the current project.

    Calls profile-mcp --ensure-essential CLI to actually install missing servers
    instead of just warning. This runs at session start for every project.
    """
    try:
        import os
        import subprocess
        if not cwd:
            cwd = os.environ.get("CLAUDE_WORKING_DIRECTORY", os.getcwd())

        # Skip for paths that shouldn't have MCP servers
        skip_prefixes = ("/tmp", str(Path.home() / ".claude"))
        if any(cwd.startswith(p) for p in skip_prefixes):
            return ""

        # Daily cache — run ensure_essential only once per day, per project
        import hashlib
        from datetime import date
        cwd_hash = hashlib.md5(cwd.encode()).hexdigest()[:8]
        cache_file = Path.home() / ".claude" / "evaluation" / "data" / f".essential-checked-{cwd_hash}"
        try:
            if cache_file.exists() and cache_file.read_text().strip() == str(date.today()):
                return ""
        except Exception:
            pass

        profile_mcp = Path.home() / ".claude" / "mcp-servers" / "profile-mcp" / "profile-mcp"
        if not profile_mcp.exists():
            return ""

        result = subprocess.run(
            [str(profile_mcp), "--ensure-essential", cwd],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return ""

        data = json.loads(result.stdout)
        added_count = data.get("added_count", 0)
        # Update daily cache
        try:
            cache_file.write_text(str(date.today()))
        except Exception:
            pass

        if added_count > 0:
            return f"\nINFO: Provisioned {added_count} essential MCP servers for {cwd}. Restart may be needed for new servers."
        return ""
    except Exception:
        return ""


def check_session_continuity(cwd: str = "") -> str:
    """Read last session continuity data for seamless resume."""
    try:
        import os
        from datetime import datetime, timezone
        continuity_file = Path.home() / ".claude" / "evaluation" / "data" / "session_continuity.jsonl"
        if not continuity_file.exists():
            return ""

        # Read last entry
        lines = continuity_file.read_text(encoding="utf-8").strip().split("\n")
        if not lines:
            return ""
        last = json.loads(lines[-1])

        # Check: same working directory, not older than 24h
        if not cwd:
            cwd = os.environ.get("CLAUDE_WORKING_DIRECTORY", os.getcwd())
        if last.get("working_directory") != cwd:
            return ""

        ts_str = last.get("timestamp", "")
        if ts_str:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_hours > 24:
                return ""

        # Build resume context
        parts = ["PREVIOUS SESSION:"]
        if last.get("task_description"):
            parts.append(f"Task: {last['task_description'][:150]}")
        if last.get("git_branch"):
            parts.append(f"Branch: {last['git_branch']}")
        if last.get("files_modified"):
            parts.append(f"Modified: {', '.join(last['files_modified'][:5])}")
        if last.get("plan_file"):
            parts.append(f"Plan: {last['plan_file']}")
        if last.get("next_steps"):
            parts.append(f"Next: {last['next_steps'][:100]}")

        if len(parts) > 1:
            return "\n" + " ".join(parts)
    except Exception:
        pass
    return ""


def check_backlog(cwd: str = "") -> str:
    """Check BACKLOG.md for pending tasks and return summary."""
    try:
        if not cwd:
            return ""
        backlog_path = Path(cwd) / "BACKLOG.md"
        if not backlog_path.exists():
            return ""
        content = backlog_path.read_text(encoding="utf-8")
        pending = [l.strip() for l in content.split("\n") if l.strip().startswith("- [ ]")]
        if not pending:
            return ""
        # Extract priorities
        p1 = sum(1 for t in pending if "(P1)" in t)
        p2 = sum(1 for t in pending if "(P2)" in t)
        p3 = sum(1 for t in pending if "(P3)" in t)
        prio_parts = []
        if p1: prio_parts.append(f"{p1}×P1")
        if p2: prio_parts.append(f"{p2}×P2")
        if p3: prio_parts.append(f"{p3}×P3")
        prio_str = f" ({', '.join(prio_parts)})" if prio_parts else ""
        return f"\nBACKLOG: {len(pending)} pending tasks{prio_str}. Use mcp__backlog-mcp__backlog_list to view tasks, or read BACKLOG.md directly."
    except Exception:
        return ""


try:
    sys.path.insert(0, str(Path(__file__).parent))
    from hook_stdin import read_hook_stdin
    input_data = read_hook_stdin(timeout_sec=5)
    # Extract cwd from stdin JSON (Claude Code passes it here)
    hook_cwd = input_data.get("cwd", "") or os.environ.get("CLAUDE_WORKING_DIRECTORY", "") or os.getcwd()
    context = REINFORCEMENT.strip()
    drift = check_config_drift()
    if drift:
        context += drift
    essential = ensure_essential_servers(hook_cwd)
    if essential:
        context += essential
    new_project = check_new_project(hook_cwd)
    if new_project:
        context += new_project
    backlog = check_backlog(hook_cwd)
    if backlog:
        context += backlog
    continuity = check_session_continuity(hook_cwd)
    if continuity:
        context += continuity
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context
        }
    }
    print(json.dumps(output))
    sys.exit(0)
except Exception:
    sys.exit(0)
