#!/usr/bin/env python3
"""
UEP Bootstrap Hook — SessionStart

Initializes Universal Execution Pipeline state at session start.
Loads nomenclature registry, checks resume state, creates session directories.

Hook Type: SessionStart
Matcher: (none — SessionStart hooks don't have matchers)
Blocking: false
Timeout: 2000ms
"""

import sys
import json
import os
import shutil
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
REGISTRY_PATH = Path.home() / ".claude" / "nomenclature" / "registry.json"
RESUME_STATE_PATH = DATA_DIR / "uep_resume_state.json"
WORK_DIR = Path("/opt/agent_work_directory")

def get_session_id():
    """Get session ID from env or file."""
    sid = os.environ.get("CLAUDE_SESSION_ID", "")
    if not sid:
        sid_file = DATA_DIR / "current_session_id"
        try:
            sid = sid_file.read_text().strip()
        except Exception:
            sid = "unknown"
    return sid

def load_registry():
    """Load nomenclature registry and return component count."""
    try:
        if not REGISTRY_PATH.exists():
            print(f"⚠️  UEP: Nomenclature registry not found at {REGISTRY_PATH}", file=sys.stderr)
            return 0

        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)

        # Count components
        components = registry.get("components", [])
        return len(components)
    except json.JSONDecodeError:
        print(f"⚠️  UEP: Invalid JSON in nomenclature registry", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"⚠️  UEP: Error loading registry: {e}", file=sys.stderr)
        return 0

def check_resume_state():
    """Check for resume state and return status."""
    try:
        if not RESUME_STATE_PATH.exists():
            return "none", None

        stat = RESUME_STATE_PATH.stat()
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(stat.st_mtime, timezone.utc)

        if age > timedelta(days=1):
            # Stale — delete
            RESUME_STATE_PATH.unlink()
            return "none", None

        # Fresh — load and return info
        with open(RESUME_STATE_PATH, 'r') as f:
            state = json.load(f)

        return "available", state
    except Exception as e:
        print(f"⚠️  UEP: Error checking resume state: {e}", file=sys.stderr)
        return "none", None

def create_session_dir(session_id):
    """Create session work directory with subdirs."""
    try:
        session_dir = WORK_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        for subdir in ["scratchpad", "research", "artifacts"]:
            (session_dir / subdir).mkdir(exist_ok=True)

        return True
    except Exception as e:
        print(f"⚠️  UEP: Error creating session dir: {e}", file=sys.stderr)
        return False

def cleanup_old_sessions():
    """Remove session directories older than 7 days."""
    try:
        if not WORK_DIR.exists():
            return 0

        # UUID regex pattern (8-4-4-4-12)
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        removed = 0

        for item in WORK_DIR.iterdir():
            if not item.is_dir():
                continue

            # Check if directory name looks like a session ID (UUID)
            if not uuid_pattern.match(item.name):
                continue

            # Check age
            stat = item.stat()
            age = datetime.fromtimestamp(stat.st_mtime, timezone.utc)

            if age < cutoff:
                try:
                    shutil.rmtree(item)
                    removed += 1
                except Exception:
                    pass  # Skip if can't delete

        return removed
    except Exception as e:
        print(f"⚠️  UEP: Error during cleanup: {e}", file=sys.stderr)
        return 0

def main():
    try:
        # Read stdin (Claude Code passes input via JSON)
        try:
            stdin_data = sys.stdin.read()
            if stdin_data.strip():
                input_data = json.loads(stdin_data)
            else:
                input_data = {}
        except json.JSONDecodeError:
            input_data = {}

        # Get session ID
        session_id = get_session_id()

        # Load nomenclature registry
        component_count = load_registry()

        # Check resume state
        resume_status, resume_data = check_resume_state()

        # Create session directory
        session_created = create_session_dir(session_id)

        # Cleanup old sessions
        removed = cleanup_old_sessions()

        # Output resume info if available
        if resume_status == "available" and resume_data:
            print(f"\n📋 UEP Resume State Available:", file=sys.stderr)
            print(f"   Pipeline: {resume_data.get('pipeline_name', 'unknown')}", file=sys.stderr)
            print(f"   Stage: {resume_data.get('current_stage', 'unknown')}", file=sys.stderr)
            print(f"   Last action: {resume_data.get('last_action', 'unknown')}\n", file=sys.stderr)

        # Output compact dashboard
        awb_status = "28 blocks"  # TODO: Load from AWB when implemented
        session_status = "created" if session_created else "failed"

        print(f"UEP: Active | AWB: {awb_status} | Nomenclature: {component_count} components", file=sys.stderr)
        print(f"Resume: {resume_status} | Session dir: {session_status}", file=sys.stderr)

        if removed > 0:
            print(f"Cleanup: {removed} old session dirs removed", file=sys.stderr)

        # Output empty JSON (no-op for SessionStart)
        print(json.dumps({}))
        sys.exit(0)

    except Exception as e:
        # Never fail — always allow session to start
        print(f"⚠️  UEP Bootstrap Hook Error: {e}", file=sys.stderr)
        print(json.dumps({}))
        sys.exit(0)

if __name__ == "__main__":
    main()
