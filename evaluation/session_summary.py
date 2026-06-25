#!/usr/bin/env python3
"""
Display summary of the most recent Claude Code session.
Gemini-style output with session metrics, token usage, and model breakdown.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

def find_latest_session_file(project_path: Path) -> Path:
    """Find the most recently modified session JSONL file."""
    session_files = list(project_path.glob("*.jsonl"))

    if not session_files:
        raise FileNotFoundError(f"No session files found in {project_path}")

    return max(session_files, key=lambda f: f.stat().st_mtime)


def parse_session_file(session_file: Path) -> Dict[str, Any]:
    """Parse session JSONL file and extract all metrics."""
    api_calls = []
    session_start = None
    session_end = None
    session_id = None
    tool_calls = []
    tool_successes = 0
    tool_failures = 0

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                # Extract session ID
                if session_id is None and 'sessionId' in entry:
                    session_id = entry['sessionId']

                # Track timestamps for wall time
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

                        api_calls.append({
                            'timestamp': entry.get('timestamp'),
                            'model': msg.get('model', 'unknown'),
                            'fresh_tokens': usage.get('input_tokens', 0),
                            'cache_read_tokens': usage.get('cache_read_input_tokens', 0),
                            'cache_creation_tokens': usage.get('cache_creation_input_tokens', 0),
                            'output_tokens': usage.get('output_tokens', 0),
                        })

                # Track tool calls and their outcomes
                if entry.get('type') == 'user' and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        for item in msg.get('content', []):
                            if isinstance(item, dict) and item.get('type') == 'tool_result':
                                tool_id = item.get('tool_use_id', 'unknown')
                                is_error = item.get('is_error', False)

                                if is_error:
                                    tool_failures += 1
                                else:
                                    tool_successes += 1

                # Detect subagent spawning (Task tool with subagent_type)
                if entry.get('type') == 'assistant' and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        for item in msg.get('content', []):
                            if isinstance(item, dict) and item.get('type') == 'tool_use':
                                tool_name = item.get('name', '')
                                if tool_name == 'Task':
                                    tool_input = item.get('input', {})
                                    if 'subagent_type' in tool_input:
                                        tool_calls.append({
                                            'type': 'subagent',
                                            'subagent_type': tool_input.get('subagent_type'),
                                            'description': tool_input.get('description', 'No description'),
                                            'timestamp': entry.get('timestamp')
                                        })
                                else:
                                    tool_calls.append({
                                        'type': 'tool',
                                        'name': tool_name,
                                        'timestamp': entry.get('timestamp')
                                    })

            except (json.JSONDecodeError, KeyError):
                continue

    # Calculate wall time
    wall_time_ms = 0
    if session_start and session_end:
        start_dt = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
        wall_time_ms = int((end_dt - start_dt).total_seconds() * 1000)

    # Aggregate by model
    models = {}
    total_fresh = 0
    total_cache_read = 0
    total_cache_creation = 0
    total_output = 0

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

        total_fresh += call['fresh_tokens']
        total_cache_read += call['cache_read_tokens']
        total_cache_creation += call['cache_creation_tokens']
        total_output += call['output_tokens']

    total_input = total_fresh + total_cache_read + total_cache_creation

    # Calculate savings (90% discount on cached tokens)
    # Pricing: $0.03/1k tokens (fresh), $0.003/1k tokens (cached)
    cost_with_cache = (total_fresh + total_cache_creation) * 0.03 / 1000 + total_cache_read * 0.003 / 1000
    cost_without_cache = total_input * 0.03 / 1000
    savings = cost_without_cache - cost_with_cache

    # Success rate
    total_tool_calls = tool_successes + tool_failures
    success_rate = (tool_successes / total_tool_calls * 100) if total_tool_calls > 0 else 0

    # Session Token Tracking
    # Estimate baseline input (first request or average cache size)
    baseline_input = total_cache_read + total_cache_creation if len(api_calls) > 0 else 0

    # Calculate average input per request
    avg_input_per_request = total_input / len(api_calls) if len(api_calls) > 0 else 0

    # Estimate history accumulation (total_input - baseline)
    # This is approximate: assumes cache stays constant, growth is history
    estimated_history = total_fresh if len(api_calls) > 1 else 0

    # Session efficiency: ideal is 100% (no history growth)
    # Efficiency = baseline / avg_input_per_request
    session_efficiency = (baseline_input / avg_input_per_request * 100) if avg_input_per_request > 0 else 100

    # Growth rate: tokens added per request (on average)
    growth_rate_per_request = estimated_history / len(api_calls) if len(api_calls) > 0 else 0

    # Estimate requests until context full (1M limit)
    context_limit = 1_000_000
    requests_until_full = 0
    if growth_rate_per_request > 0 and avg_input_per_request < context_limit:
        remaining_capacity = context_limit - avg_input_per_request
        requests_until_full = int(remaining_capacity / growth_rate_per_request)

    # Recommendation
    reopen_recommendation = ""
    if len(api_calls) > 50 and session_efficiency < 90:
        reopen_recommendation = "Consider reopening session to reset history"
    elif estimated_history > 20000:
        reopen_recommendation = "High history accumulation - reopen recommended"
    elif requests_until_full > 0 and requests_until_full < 30:
        reopen_recommendation = f"Context nearly full - reopen in ~{requests_until_full} requests"

    return {
        'session_id': session_id or 'unknown',
        'wall_time_ms': wall_time_ms,
        'api_calls_count': len(api_calls),
        'tool_calls_count': total_tool_calls,
        'tool_successes': tool_successes,
        'tool_failures': tool_failures,
        'success_rate': success_rate,
        'total_fresh_tokens': total_fresh,
        'total_cache_read_tokens': total_cache_read,
        'total_cache_creation_tokens': total_cache_creation,
        'total_input_tokens': total_input,
        'total_output_tokens': total_output,
        'cost_with_cache': cost_with_cache,
        'cost_without_cache': cost_without_cache,
        'savings': savings,
        'models': models,
        'subagents': [tc for tc in tool_calls if tc['type'] == 'subagent'],
        # Session token tracking metrics
        'avg_input_per_request': int(avg_input_per_request),
        'baseline_input': int(baseline_input),
        'estimated_history': int(estimated_history),
        'session_efficiency': session_efficiency,
        'growth_rate_per_request': int(growth_rate_per_request),
        'requests_until_full': requests_until_full,
        'reopen_recommendation': reopen_recommendation
    }


def format_time(ms: int) -> str:
    """Format milliseconds to human-readable time."""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms // 1000}s"
    else:
        mins = ms // 60000
        secs = (ms % 60000) // 1000
        return f"{mins}m {secs}s"


def display_summary(data: Dict[str, Any]) -> None:
    """Display session summary in Gemini-style format."""
    # Calculate cache hit rate for display
    usable_input = data['total_fresh_tokens'] + data['total_cache_read_tokens']
    cache_hit_rate = (data['total_cache_read_tokens'] / usable_input * 100) if usable_input > 0 else 0

    # Calculate API time percentage (we don't have tool time, so assume all time is API)
    api_time_pct = 100.0

    print("╭─────────────────────────────────────────────────────────────╮")
    print("│ 📊 Session Summary                                          │")
    print(f"│ Session ID:      {data['session_id'][:36]:36} │")
    print(f"│ Tool Calls:      {data['tool_calls_count']:3d} ( ✓ {data['tool_successes']:3d} ✗ {data['tool_failures']:3d} )                           │")
    print(f"│ Success Rate:    {data['success_rate']:5.1f}%                                        │")
    print("│                                                             │")
    print("│ ⏱️  Performance                                              │")
    print(f"│ Wall Time:       {format_time(data['wall_time_ms']):>15}                            │")
    print(f"│ API Calls:       {data['api_calls_count']:3d} requests                                   │")
    print("│                                                             │")
    print("│ 📊 Session Token Tracking                                   │")
    print(f"│ Request #:       {data['api_calls_count']:3d}                                           │")
    print(f"│ Avg Input:       {data['avg_input_per_request']:>8,} tokens/request                    │")
    print(f"│ History Est:     {data['estimated_history']:>8,} tokens (accumulated)                │")
    print(f"│ Efficiency:      {data['session_efficiency']:5.1f}% (target: 100%)                     │")
    if data['growth_rate_per_request'] > 0:
        print(f"│ Growth Rate:     +{data['growth_rate_per_request']:>5,} tokens/request                         │")
    if data['requests_until_full'] > 0:
        print(f"│ Capacity:        ~{data['requests_until_full']:3d} requests until context full              │")
    if data['reopen_recommendation']:
        print(f"│ 💡 {data['reopen_recommendation']:<59} │")
    print("│                                                             │")
    print("│ 💰 Token Usage                                               │")
    print(f"│ Input (Fresh):   {data['total_fresh_tokens']:>8,} tokens                           │")
    print(f"│ Input (Cached):  {data['total_cache_read_tokens']:>8,} tokens ({cache_hit_rate:5.1f}% hit rate)      │")
    print(f"│ Cache Creation:  {data['total_cache_creation_tokens']:>8,} tokens                           │")
    print(f"│ Output:          {data['total_output_tokens']:>8,} tokens                           │")
    print(f"│ Total Input:     {data['total_input_tokens']:>8,} tokens                           │")
    print("│                                                             │")
    print("│ 💵 Cost Analysis                                             │")
    print(f"│ With Caching:    ${data['cost_with_cache']:>8.4f}                               │")
    print(f"│ Without Caching: ${data['cost_without_cache']:>8.4f}                               │")
    print(f"│ Savings:         ${data['savings']:>8.4f} ({data['savings']/data['cost_without_cache']*100 if data['cost_without_cache'] > 0 else 0:5.1f}% saved)               │")
    print("│                                                             │")
    print("│ 🤖 Model Usage    Reqs  Input   Cache   Output              │")
    print("│ ───────────────────────────────────────────────────────────│")

    for model, stats in data['models'].items():
        # Shorten model name for display
        model_short = model.replace('claude-', '').replace('-20250929', '')[:15]
        total_in = stats['fresh_tokens'] + stats['cache_read_tokens'] + stats['cache_creation_tokens']

        # Format numbers with K/M suffix for large values
        def fmt_num(n):
            if n >= 1000000:
                return f"{n/1000000:.1f}M"
            elif n >= 1000:
                return f"{n/1000:.1f}K"
            else:
                return str(n)

        print(f"│ {model_short:15} {stats['requests']:4d}  {fmt_num(total_in):>6}  {fmt_num(stats['cache_read_tokens']):>6}  {fmt_num(stats['output_tokens']):>6}            │")

    # Display subagents if any
    if data['subagents']:
        print("│                                                             │")
        print("│ 🔄 Subagents Spawned                                        │")
        for i, subagent in enumerate(data['subagents'], 1):
            subagent_type = subagent['subagent_type'][:20]
            print(f"│   {i}. {subagent_type:20} - {subagent['description'][:25]:25} │")

    print("╰─────────────────────────────────────────────────────────────╯")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        # Try to find project from CWD
        # Claude encodes paths as: /path/to/dir -> -path-to-dir
        # Also replaces underscores with hyphens
        cwd = Path.cwd().resolve()
        claude_projects = Path.home() / ".claude" / "projects"
        encoded_path = str(cwd).replace('/', '-').replace('_', '-')
        project_path = claude_projects / encoded_path

    # Ensure path is resolved
    project_path = Path(project_path).resolve()

    if not project_path.exists() or not project_path.is_dir():
        print(f"⚠️  Project path not found: {project_path}", file=sys.stderr)
        print("   No session data available for this directory.", file=sys.stderr)
        sys.exit(1)

    try:
        session_file = find_latest_session_file(project_path)
        session_data = parse_session_file(session_file)
        display_summary(session_data)

        # Check if session reopen is recommended
        if session_data['estimated_history'] > 10000 or session_data['session_efficiency'] > 5000:
            print()
            print("╔═══════════════════════════════════════════════════════════════╗")
            print("║  🔄 SESSION REOPEN RECOMMENDED                                ║")
            print("╠═══════════════════════════════════════════════════════════════╣")
            print("║  High token accumulation detected. Generating continuity      ║")
            print("║  summary for seamless session transition...                   ║")
            print("╚═══════════════════════════════════════════════════════════════╝")
            print()

            # Generate continuity summary
            try:
                from session_continuity import generate_continuity_summary

                # Generate summary markdown
                summary_content = generate_continuity_summary(project_path)

                # Save to file
                summaries_dir = Path.home() / ".claude" / "evaluation" / "data" / "summaries" / "session" / project_path.name
                summaries_dir.mkdir(parents=True, exist_ok=True)
                summary_file = summaries_dir / f"{session_data['session_id']}.md"

                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(summary_content)

                print(f"📄 Session Continuity Summary generated at:")
                print(f"   {summary_file}")
                print()

            except Exception as e:
                print(f"⚠️ Error generating summary: {e}")
                summary_file = None

            # Show context recovery instructions
            print("╔═══════════════════════════════════════════════════════════════╗")
            print("║  📋 CONTEXT RECOVERY INSTRUCTIONS                             ║")
            print("╠═══════════════════════════════════════════════════════════════╣")
            print("║  To continue work in a new session:                           ║")
            print("║                                                               ║")
            print("║  1. Start new Claude session:                                 ║")
            print("║     $ claude                                                  ║")
            print("║                                                               ║")
            print("║  2. In first message, paste this command:                     ║")
            print('║     "Continue from summary: <copy summary below>"              ║')
            print("║                                                               ║")
            print("║  3. Copy summary using:                                       ║")
            if summary_file:
                summary_path = str(summary_file)
                if len(summary_path) > 54:
                    summary_path_short = "..." + summary_path[-51:]
                else:
                    summary_path_short = summary_path
                print(f"║     $ cat {summary_path_short:<54} ║")
            else:
                print("║     $ cat <summary-file-path>                                  ║")
            print("║                                                               ║")
            print("║  OR use one-line recovery:                                    ║")
            print("║     $ claude                                                  ║")
            print("║     > Продолжай с места, где остановился. Summary:           ║")
            if summary_file:
                summary_cmd = f"$(cat {summary_file})"
                if len(summary_cmd) > 47:
                    summary_cmd_short = summary_cmd[:44] + "..."
                else:
                    summary_cmd_short = summary_cmd
                print(f"║     > {summary_cmd_short:<60} ║")
            else:
                print("║     > $(cat <summary-file-path>)                               ║")
            print("║                                                               ║")
            print("╚═══════════════════════════════════════════════════════════════╝")
            print()

            # Show summary preview if generated
            if summary_file and summary_file.exists():
                try:
                    with open(summary_file, 'r') as f:
                        preview = f.read(500)
                    print("💡 Summary preview (first 500 chars):")
                    print("─" * 63)
                    print(preview)
                    if len(preview) == 500:
                        print("...")
                    print()
                except:
                    pass

    except FileNotFoundError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
