#!/usr/bin/env python3
"""
Session Startup Script

Displays statistics on session startup if configured day matches.
Called automatically by Claude Code wrapper on session start.

Configuration:
- Shows stats on: Monday (default)
- Configurable via ~/.claude/evaluation/config.json

Usage:
    python session_startup.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics_tracker import MetricsTracker


def load_config() -> dict:
    """Load configuration."""
    config_file = Path.home() / ".claude" / "evaluation" / "config.json"

    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)

    # Default config
    return {
        "show_stats_on_days": ["monday"],  # lowercase day names
        "show_tier2_report": True,
        "show_gap_summary": True
    }


def should_show_stats(config: dict) -> bool:
    """Check if stats should be shown today."""
    today = datetime.now().strftime("%A").lower()
    return today in config.get("show_stats_on_days", [])


def get_latest_report(report_type: str = "weekly") -> str:
    """Get latest report file content."""
    reports_dir = Path.home() / ".claude" / "evaluation" / "reports"

    if not reports_dir.exists():
        return None

    # Find latest report
    pattern = f"{report_type}_stats_*.txt" if report_type == "weekly" else f"{report_type}_report_*.txt"
    reports = sorted(reports_dir.glob(pattern), reverse=True)

    if not reports:
        return None

    with open(reports[0], 'r') as f:
        return f.read()


def get_gap_summary() -> str:
    """Get summary of active gaps."""
    gaps_file = Path.home() / ".claude" / "GAPS.md"

    if not gaps_file.exists():
        return "No GAPS.md found"

    with open(gaps_file, 'r') as f:
        content = f.read()

    # Count active gaps by priority
    lines = content.split('\n')

    p1_count = sum(1 for line in lines if '**Status:** 🔴' in line or '**Status:** 📊' in line)
    p2_count = sum(1 for line in lines if '**Priority:** P2' in line and ('🔴' in content or '📊' in content))
    p3_count = sum(1 for line in lines if '**Priority:** P3' in line and ('🔴' in content or '📊' in content))

    return f"""
📋 **Active GAPS Summary:**
   - P1 (Critical): {p1_count}
   - P2 (High): {p2_count}
   - P3 (Medium): {p3_count}
   - Total: {p1_count + p2_count + p3_count}
"""


def get_project_continuity_summary() -> str:
    """
    Get latest continuity summary for CURRENT PROJECT ONLY.

    Returns summary if:
    - Session ended recently (<3 days)
    - Summary belongs to current project
    - Summary file exists

    Returns None if no recent summary for current project.
    """
    import os

    # Get current working directory and encode to project name
    cwd = os.getcwd()

    # Encode path same way Claude Code does: /opt/project -> -opt-your-project
    encoded_full = cwd.replace('/', '-').replace('_', '-')

    # Find matching project directory
    projects_dir = Path.home() / ".claude" / "projects"
    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir() and encoded_full in d.name]

    if not project_dirs:
        return None

    project_name = project_dirs[0].name

    # Look for summaries in current project directory ONLY
    summaries_dir = Path.home() / ".claude" / "evaluation" / "data" / "summaries" / "session" / project_name

    if not summaries_dir.exists():
        return None

    # Find most recent summary
    summaries = sorted(summaries_dir.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)

    if not summaries:
        return None

    latest_summary = summaries[0]

    # Check age (only show if <3 days old)
    age_seconds = datetime.now().timestamp() - latest_summary.stat().st_mtime
    age_days = age_seconds / 86400

    if age_days > 3:
        return None  # Too old, likely irrelevant

    # Read and return summary preview
    with open(latest_summary, 'r') as f:
        content = f.read()

    # Preview first 600 chars
    preview = content[:600] + ("..." if len(content) > 600 else "")

    return f"""
🔄 **Session Continuity Available** (age: {age_days:.1f} days)
   Project: {project_name}
   File: {latest_summary.name}

   Preview:
   ───────────────────────────────────────────────────────────────
{preview}
   ───────────────────────────────────────────────────────────────

   💡 To continue from this session:
      cat {latest_summary}
"""


def main():
    """Main entry point."""
    try:
        config = load_config()

        # ALWAYS check for project-specific continuity summary (regardless of day)
        continuity_summary = get_project_continuity_summary()
        if continuity_summary:
            print("\n" + "="*80)
            print("🔄 SESSION CONTINUITY AVAILABLE")
            print("="*80 + "\n")
            print(continuity_summary)
            print("="*80 + "\n")

        # Show weekly stats only on configured days
        if not should_show_stats(config):
            # Not configured day, exit (but continuity summary was shown above if available)
            sys.exit(0)

        print("\n" + "="*80)
        print("📊 WEEKLY CLAUDE CODE STATISTICS")
        print("="*80 + "\n")

        # Show weekly report
        weekly_report = get_latest_report("weekly")
        if weekly_report:
            print(weekly_report)
        else:
            print("⚠️  No weekly report available yet. Run: python ~/.claude/evaluation/scripts/generate_weekly_stats.py")

        print("\n" + "-"*80 + "\n")

        # Show Tier 2 report if configured
        if config.get("show_tier2_report", True):
            tier2_report = get_latest_report("tier2")
            if tier2_report:
                print(tier2_report)
                print("\n" + "-"*80 + "\n")

        # Show GAP summary if configured
        if config.get("show_gap_summary", True):
            print(get_gap_summary())

        print("="*80)
        print("💡 Tip: Stats are generated every Monday at 09:00 via systemd timer")
        print("="*80 + "\n")

    except Exception as e:
        print(f"❌ Error loading session stats: {e}", file=sys.stderr)
        # Don't fail session startup on error
        sys.exit(0)


if __name__ == '__main__':
    main()
