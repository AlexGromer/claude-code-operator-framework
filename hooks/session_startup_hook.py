#!/usr/bin/env python3
"""
Session Startup Hook - Research Digest Check
Automatically checks for new research digest on session startup.

Triggers:
- New Claude Code session started
- Checks for unread digest from last 7 days
- Displays reminder if found

Note: Session continuity summaries are handled by scripts/session_startup.py

Version: 1.1.0
Created: 2026-01-27
Updated: 2026-01-29 (Fixed JSON output format)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

DIGEST_DIR = Path.home() / ".claude" / "evaluation" / "data" / "research_digests"
DIGEST_READ_TRACKER = Path.home() / ".claude" / "evaluation" / "data" / ".digest_read"

def get_latest_digest():
    """Get the most recent digest file."""
    if not DIGEST_DIR.exists():
        return None

    digests = sorted(DIGEST_DIR.glob("digest_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return digests[0] if digests else None

def is_digest_unread(digest_path):
    """Check if digest has been marked as read."""
    if not DIGEST_READ_TRACKER.exists():
        return True

    try:
        with open(DIGEST_READ_TRACKER, 'r') as f:
            read_digests = json.load(f)
        return str(digest_path) not in read_digests
    except Exception:
        return True

def get_digest_age(digest_path):
    """Get age of digest in days."""
    mtime = datetime.fromtimestamp(digest_path.stat().st_mtime)
    age = datetime.now() - mtime
    return age.days

def count_priority_items(digest_path):
    """Count CRITICAL and HIGH priority items."""
    try:
        content = digest_path.read_text()
        critical = content.count('🔴')  # Red circle for CRITICAL
        high = content.count('🟠')  # Orange circle for HIGH
        return critical, high
    except Exception:
        return 0, 0

def extract_date_from_filename(filename):
    """Extract date from digest filename."""
    return filename.replace('digest_', '').replace('.md', '')

def main():
    """Main hook execution."""
    latest_digest = get_latest_digest()

    if not latest_digest:
        return 0

    age_days = get_digest_age(latest_digest)

    if age_days > 7:
        return 0

    unread = is_digest_unread(latest_digest)
    if not unread:
        return 0

    critical_count, high_count = count_priority_items(latest_digest)
    if critical_count == 0 and high_count == 0:
        return 0

    # Compact 3-line summary instead of full workflow prompt
    digest_date = extract_date_from_filename(latest_digest.name)
    summary = f"New research digest: {digest_date}. CRITICAL: {critical_count}, HIGH: {high_count}. Run /research-digest to review."

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": summary
        }
    }
    print(json.dumps(output))
    return 0

if __name__ == "__main__":
    sys.exit(main())
