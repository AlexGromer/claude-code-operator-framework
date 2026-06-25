"""Shared stdin reader for Claude Code hooks with timeout protection.

Problem: json.load(sys.stdin) and sys.stdin.read() block indefinitely
if Claude Code doesn't close the stdin pipe promptly. When the hook is
killed by Claude Code's timeout, || true produces empty stdout, which
Claude Code can't parse → "PreToolUse hook error".

Solution: signal.alarm() based timeout for stdin reading.
"""

import json
import signal
import sys


def read_hook_stdin(timeout_sec: int = 2) -> dict:
    """Read JSON from stdin with timeout protection.

    Args:
        timeout_sec: Maximum seconds to wait for stdin data.

    Returns:
        Parsed JSON dict, or empty dict on any failure.
    """
    def _timeout_handler(signum, frame):
        raise TimeoutError("stdin read timeout")

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_sec)
    try:
        raw = sys.stdin.read()
        signal.alarm(0)
        if raw and raw.strip():
            return json.loads(raw)
        return {}
    except (TimeoutError, json.JSONDecodeError, ValueError, OSError):
        signal.alarm(0)
        return {}
    except Exception:
        signal.alarm(0)
        return {}
    finally:
        signal.signal(signal.SIGALRM, old_handler)
