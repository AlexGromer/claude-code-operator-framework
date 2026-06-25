#!/usr/bin/env python3
"""
Parse Claude Code session transcript and collect cache metrics.
Called automatically by claude_wrapper.sh on session exit.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

def find_latest_session_file(project_path: Path) -> Path:
    """
    Find the most recently modified session JSONL file in project directory.

    Args:
        project_path: Path to the Claude project directory

    Returns:
        Path to the latest session file
    """
    session_files = list(project_path.glob("*.jsonl"))

    if not session_files:
        raise FileNotFoundError(f"No session files found in {project_path}")

    # Return the most recently modified file
    return max(session_files, key=lambda f: f.stat().st_mtime)


def parse_session_file(session_file: Path) -> Dict[str, Any]:
    """
    Parse session JSONL file and extract usage metrics.

    Args:
        session_file: Path to session JSONL file

    Returns:
        Dict with aggregated session metrics
    """
    api_calls = []
    session_start = None
    session_end = None
    session_id = None
    tool_calls = []

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                # Extract session ID
                if session_id is None and 'sessionId' in entry:
                    session_id = entry['sessionId']

                # Track timestamps
                if 'timestamp' in entry:
                    ts = entry['timestamp']
                    if session_start is None:
                        session_start = ts
                    session_end = ts

                # Extract API usage data
                if entry.get('type') == 'assistant' and 'message' in entry:
                    msg = entry['message']

                    if 'usage' in msg:
                        usage = msg['usage']

                        # Calculate fresh tokens (input_tokens in API response)
                        fresh_tokens = usage.get('input_tokens', 0)

                        # Cache read tokens
                        cache_read = usage.get('cache_read_input_tokens', 0)

                        # Cache creation tokens (new content added to cache)
                        cache_creation = usage.get('cache_creation_input_tokens', 0)

                        # Output tokens
                        output_tokens = usage.get('output_tokens', 0)

                        # Total input = fresh + cache_read + cache_creation
                        total_input = fresh_tokens + cache_read + cache_creation

                        api_calls.append({
                            'timestamp': entry.get('timestamp'),
                            'model': msg.get('model', 'unknown'),
                            'fresh_tokens': fresh_tokens,
                            'cache_read_tokens': cache_read,
                            'cache_creation_tokens': cache_creation,
                            'output_tokens': output_tokens,
                            'total_input_tokens': total_input,
                            'request_id': entry.get('requestId')
                        })

                # Track tool calls
                if entry.get('type') == 'assistant' and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        for item in msg.get('content', []):
                            if isinstance(item, dict) and item.get('type') == 'tool_use':
                                tool_calls.append({
                                    'tool': item.get('name', 'unknown'),
                                    'timestamp': entry.get('timestamp')
                                })

            except (json.JSONDecodeError, KeyError) as e:
                # Skip malformed lines
                continue

    # Aggregate metrics
    total_fresh = sum(call['fresh_tokens'] for call in api_calls)
    total_cache_read = sum(call['cache_read_tokens'] for call in api_calls)
    total_cache_creation = sum(call['cache_creation_tokens'] for call in api_calls)
    total_output = sum(call['output_tokens'] for call in api_calls)
    total_input = total_fresh + total_cache_read + total_cache_creation

    # Calculate cache hit rate (excluding cache creation tokens)
    # Hit rate = cache_read / (fresh + cache_read)
    usable_input = total_fresh + total_cache_read
    cache_hit_rate = total_cache_read / usable_input if usable_input > 0 else 0

    # Group by model
    models = {}
    for call in api_calls:
        model = call['model']
        if model not in models:
            models[model] = {
                'requests': 0,
                'fresh_tokens': 0,
                'cache_read_tokens': 0,
                'cache_creation_tokens': 0,
                'output_tokens': 0
            }
        models[model]['requests'] += 1
        models[model]['fresh_tokens'] += call['fresh_tokens']
        models[model]['cache_read_tokens'] += call['cache_read_tokens']
        models[model]['cache_creation_tokens'] += call['cache_creation_tokens']
        models[model]['output_tokens'] += call['output_tokens']

    return {
        'session_id': session_id,
        'session_start': session_start,
        'session_end': session_end,
        'api_calls_count': len(api_calls),
        'tool_calls_count': len(tool_calls),
        'tool_calls': tool_calls,
        'total_fresh_tokens': total_fresh,
        'total_cache_read_tokens': total_cache_read,
        'total_cache_creation_tokens': total_cache_creation,
        'total_output_tokens': total_output,
        'total_input_tokens': total_input,
        'cache_hit_rate': cache_hit_rate,
        'models': models,
        'api_calls': api_calls
    }


def collect_session_metrics(session_data: Dict[str, Any]) -> None:
    """
    Collect cache metrics from parsed session data.

    Args:
        session_data: Aggregated session metrics
    """
    # Add parent directory to path to import metrics_tracker
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from metrics_tracker import MetricsTracker

        tracker = MetricsTracker()

        # Collect aggregate session metric
        # For cache metric: cached_tokens = cache_read, fresh_tokens = fresh
        tracker.collect_cache_metric(
            cached_tokens=session_data['total_cache_read_tokens'],
            fresh_tokens=session_data['total_fresh_tokens'],
            latency_ms=0,  # We don't have latency from session file
            model=list(session_data['models'].keys())[0] if session_data['models'] else 'unknown'
        )

        # Also collect per-model metrics if multiple models used
        if len(session_data['models']) > 1:
            for model, stats in session_data['models'].items():
                tracker.collect_cache_metric(
                    cached_tokens=stats['cache_read_tokens'],
                    fresh_tokens=stats['fresh_tokens'],
                    latency_ms=0,
                    model=model
                )

    except ImportError as e:
        print(f"⚠️  Failed to import metrics_tracker: {e}", file=sys.stderr)


def main():
    """
    Main entry point.
    Usage: python parse_session_metrics.py [project_path]
    """
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        # Try to find the current project from CWD
        # Claude encodes paths as: /path/to/dir -> -path-to-dir
        # Also replaces underscores with hyphens
        cwd = Path.cwd().resolve()
        claude_projects = Path.home() / ".claude" / "projects"

        # Encode current path for project directory name
        encoded_path = str(cwd).replace('/', '-').replace('_', '-')
        project_path = claude_projects / encoded_path

    # Ensure path is resolved
    project_path = Path(project_path).resolve()

    if not project_path.exists() or not project_path.is_dir():
        print(f"⚠️  Project path not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Find latest session file
        session_file = find_latest_session_file(project_path)

        # Parse session
        session_data = parse_session_file(session_file)

        # Collect metrics
        collect_session_metrics(session_data)

        # Print summary (for debugging)
        print(f"✅ Collected metrics from session {session_data['session_id']}", file=sys.stderr)
        print(f"   API calls: {session_data['api_calls_count']}", file=sys.stderr)
        print(f"   Cache hit rate: {session_data['cache_hit_rate']*100:.1f}%", file=sys.stderr)
        print(f"   Total input: {session_data['total_input_tokens']:,} tokens", file=sys.stderr)
        print(f"   Total output: {session_data['total_output_tokens']:,} tokens", file=sys.stderr)

    except Exception as e:
        print(f"❌ Error parsing session: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
