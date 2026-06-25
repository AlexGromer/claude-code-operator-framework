#!/usr/bin/env python3
"""
Session Health Check - Inline Warning Generator

Checks current session metrics and returns inline warning if thresholds exceeded.
Includes debouncing mechanism (max once per 50 responses).

Usage:
    python check_session_health.py

Returns:
    - Empty string if session healthy or debounced
    - Inline warning message if thresholds exceeded

Integration:
    Called periodically by Claude via Bash tool to display inline warnings.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from metrics_tracker import MetricsTracker
except ImportError:
    sys.exit(0)


# Configuration
THRESHOLDS = {
    'user_messages': 100,      # Warn after 100+ user messages
    'assistant_messages': 100, # Warn after 100+ assistant responses
    'total_lines': 500,        # Warn after 500+ lines in JSONL (indicates long session)
    'tokens': 50000,           # Warn after 50k+ tokens (5% of 1M)
    'token_utilization': 0.25  # 25% context window usage
}

DEBOUNCE_RESPONSES = 50  # Max once per 50 responses
DEBOUNCE_FILE = Path.home() / ".claude" / "evaluation" / ".session_health_last_warning"


def load_last_warning_data():
    """Load timestamp, response count, and session_id of last warning."""
    if not DEBOUNCE_FILE.exists():
        return None

    try:
        with open(DEBOUNCE_FILE, 'r') as f:
            data = json.load(f)
            return {
                'timestamp': datetime.fromisoformat(data['timestamp']),
                'response_count': data['response_count'],
                'session_id': data.get('session_id', None)  # Session-awareness fix
            }
    except Exception:
        return None


def save_warning_data(response_count: int, session_id: str = None):
    """Save current warning timestamp, response count, and session_id."""
    DEBOUNCE_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        'timestamp': datetime.now().astimezone().isoformat(),
        'response_count': response_count,
        'session_id': session_id  # Session-awareness fix
    }

    with open(DEBOUNCE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def should_show_warning(current_message_count: int, current_session_id: str = None) -> bool:
    """
    Check if warning should be shown based on debouncing logic.

    SESSION-AWARE FIX (GAP-EVAL-HEALTH-001):
    - If session_id changed, reset debounce (new session = new warnings allowed)
    - This prevents blocking warnings when message_count resets in new session

    Returns True if:
    - No previous warning, OR
    - Session ID changed (new session), OR
    - At least 50 user messages since last warning in SAME session
    """
    last_warning = load_last_warning_data()

    if last_warning is None:
        return True

    # SESSION-AWARENESS FIX: If session changed, reset debounce
    last_session_id = last_warning.get('session_id')
    if current_session_id and last_session_id and current_session_id != last_session_id:
        # New session - allow warning immediately
        return True

    # Same session - check message count delta
    messages_since_last = current_message_count - last_warning['response_count']

    # FIX: Handle negative delta (shouldn't happen in same session, but safety check)
    if messages_since_last < 0:
        # Session was compacted or something unusual - allow warning
        return True

    return messages_since_last >= DEBOUNCE_RESPONSES


def get_current_session_metrics():
    """
    Get current session metrics from active session JSONL file.

    Returns dict with:
    - message_count
    - total_lines (approximation for response count)
    - session_id
    - session_file
    """
    import os

    # Get current working directory
    cwd = os.getcwd()

    # Encode to project name (same way Claude Code does)
    encoded = cwd.replace('/', '-').replace('_', '-')

    # Find project directory
    projects_dir = Path.home() / ".claude" / "projects"
    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir() and encoded in d.name]

    if not project_dirs:
        return None

    project_dir = project_dirs[0]

    # Find most recent session file (by mtime)
    session_files = sorted(project_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime, reverse=True)

    if not session_files:
        return None

    session_file = session_files[0]
    session_id = session_file.stem

    try:
        # Count total lines and user messages
        with open(session_file, 'r') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Count user messages
        user_message_count = 0
        assistant_message_count = 0

        for line in lines:
            try:
                entry = json.loads(line)
                msg_type = entry.get('type', '')

                if msg_type == 'user':
                    # Check if it's actual user message (not tool result)
                    message = entry.get('message', {})
                    if message.get('role') == 'user':
                        content = message.get('content', [])
                        # Filter out tool_result entries
                        if content and not any(isinstance(c, dict) and c.get('type') == 'tool_result' for c in content):
                            user_message_count += 1

                elif msg_type == 'assistant':
                    assistant_message_count += 1

            except json.JSONDecodeError:
                continue

        # Approximate token count (very rough estimate: 1000 tokens per user message)
        estimated_tokens = user_message_count * 1000

        # Calculate utilization
        max_tokens = 1_000_000
        utilization = estimated_tokens / max_tokens

        return {
            'message_count': user_message_count,
            'assistant_count': assistant_message_count,
            'total_lines': total_lines,
            'token_count': estimated_tokens,
            'session_id': session_id,
            'session_file': str(session_file),
            'utilization': utilization
        }

    except Exception as e:
        print(f"Error reading session file: {e}", file=sys.stderr)
        return None


def generate_warning(metrics: dict) -> str:
    """
    Generate inline warning message based on metrics.

    Returns formatted warning for inline display.
    """
    msg_count = metrics['message_count']
    assistant_count = metrics.get('assistant_count', 0)
    total_lines = metrics.get('total_lines', 0)
    token_count = metrics['token_count']
    utilization = metrics.get('utilization', 0.0)

    # Determine warning level
    if utilization >= 0.80 or assistant_count >= 500:
        level = "CRITICAL"
        emoji = "🔴"
    elif utilization >= 0.60 or assistant_count >= 200:
        level = "HIGH"
        emoji = "🟠"
    elif utilization >= 0.25 or assistant_count >= 100 or total_lines >= 500:
        level = "MODERATE"
        emoji = "🟡"
    else:
        return ""  # No warning needed

    warning = f"""
---

{emoji} **Session Health: {level}**

Текущая сессия:
- User messages: **{msg_count}**
- Assistant responses: **{assistant_count}**
- Total lines: **{total_lines:,}**
- Estimated tokens: **{token_count:,}** ({utilization*100:.1f}% от 1M)

💡 **Рекомендация:** Переоткройте сессию для оптимизации.
   При завершении wrapper автоматически создаст continuity summary.

   Для переоткрытия: `exit` → new session → summary будет показан автоматически.

---
"""

    return warning


def main():
    """Main execution."""
    try:
        # Get current session metrics
        metrics = get_current_session_metrics()

        if metrics is None:
            # No metrics available
            sys.exit(0)

        # Check if thresholds exceeded
        exceeds_thresholds = (
            metrics['message_count'] >= THRESHOLDS['user_messages'] or
            metrics.get('assistant_count', 0) >= THRESHOLDS['assistant_messages'] or
            metrics.get('total_lines', 0) >= THRESHOLDS['total_lines'] or
            metrics['token_count'] >= THRESHOLDS['tokens'] or
            metrics.get('utilization', 0.0) >= THRESHOLDS['token_utilization']
        )

        if not exceeds_thresholds:
            # Session healthy, no warning needed
            sys.exit(0)

        # Check debouncing (SESSION-AWARE FIX: pass session_id)
        message_count = metrics.get('message_count', 0)
        session_id = metrics.get('session_id', None)

        if not should_show_warning(message_count, session_id):
            # Too soon since last warning (in same session)
            sys.exit(0)

        # Generate and print warning
        warning = generate_warning(metrics)

        if warning:
            print(warning)

            # Update debounce tracker (SESSION-AWARE FIX: save session_id)
            save_warning_data(message_count, session_id)

    except Exception as e:
        # Silently fail
        print(f"Health check error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
