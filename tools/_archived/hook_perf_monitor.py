#!/usr/bin/env python3
"""
Hook Performance Monitor
Analyzes hook execution times from latency tracking data.

Usage:
    python3 hook_perf_monitor.py [--report] [--slow-threshold 100]
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LATENCY_FILE = DATA_DIR / "latency_metrics.jsonl"
HOOK_PERF_FILE = DATA_DIR / "hook_performance.jsonl"


def load_latency_data(days: int = 7) -> list:
    """Load latency data from the last N days."""
    records = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    if not LATENCY_FILE.exists():
        return records

    with open(LATENCY_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                ts_str = record.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts >= cutoff:
                        records.append(record)
            except (json.JSONDecodeError, ValueError):
                continue

    return records


def analyze_hook_performance(records: list) -> dict:
    """Analyze hook performance from latency records."""
    hook_stats = defaultdict(lambda: {
        "count": 0,
        "total_ms": 0.0,
        "max_ms": 0.0,
        "min_ms": float('inf'),
        "timeouts": 0,
        "errors": 0,
    })

    for record in records:
        hook_name = record.get("hook_name") or record.get("tool_name", "unknown")
        duration_ms = record.get("duration_ms", 0)
        timed_out = record.get("timed_out", False)
        error = record.get("error", False)

        stats = hook_stats[hook_name]
        stats["count"] += 1
        stats["total_ms"] += duration_ms
        if duration_ms > stats["max_ms"]:
            stats["max_ms"] = duration_ms
        if duration_ms < stats["min_ms"]:
            stats["min_ms"] = duration_ms
        if timed_out:
            stats["timeouts"] += 1
        if error:
            stats["errors"] += 1

    # Calculate averages
    for name, stats in hook_stats.items():
        if stats["count"] > 0:
            stats["avg_ms"] = round(stats["total_ms"] / stats["count"], 2)
        else:
            stats["avg_ms"] = 0
        if stats["min_ms"] == float('inf'):
            stats["min_ms"] = 0

    return dict(hook_stats)


def generate_report(hook_stats: dict, slow_threshold: float = 100.0) -> str:
    """Generate a performance report."""
    lines = []
    lines.append("=" * 70)
    lines.append("HOOK PERFORMANCE REPORT")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("=" * 70)

    if not hook_stats:
        lines.append("\nNo latency data available.")
        return "\n".join(lines)

    # Sort by avg_ms descending
    sorted_hooks = sorted(
        hook_stats.items(),
        key=lambda x: x[1]["avg_ms"],
        reverse=True
    )

    # Summary
    total_calls = sum(s["count"] for _, s in sorted_hooks)
    total_time = sum(s["total_ms"] for _, s in sorted_hooks)
    total_timeouts = sum(s["timeouts"] for _, s in sorted_hooks)
    total_errors = sum(s["errors"] for _, s in sorted_hooks)

    lines.append(f"\nTotal calls: {total_calls}")
    lines.append(f"Total time: {total_time:.0f}ms")
    lines.append(f"Timeouts: {total_timeouts}")
    lines.append(f"Errors: {total_errors}")

    # Slow hooks
    slow_hooks = [(n, s) for n, s in sorted_hooks if s["avg_ms"] > slow_threshold]
    if slow_hooks:
        lines.append(f"\n{'='*70}")
        lines.append(f"SLOW HOOKS (avg > {slow_threshold}ms)")
        lines.append(f"{'='*70}")
        for name, stats in slow_hooks:
            lines.append(
                f"  {name}: avg={stats['avg_ms']}ms "
                f"max={stats['max_ms']:.0f}ms "
                f"calls={stats['count']} "
                f"timeouts={stats['timeouts']}"
            )

    # All hooks table
    lines.append(f"\n{'='*70}")
    lines.append("ALL HOOKS BY AVERAGE LATENCY")
    lines.append(f"{'='*70}")
    lines.append(f"{'Hook':<40} {'Avg(ms)':>8} {'Max(ms)':>8} {'Calls':>6} {'Err':>4}")
    lines.append("-" * 70)

    for name, stats in sorted_hooks:
        marker = " *" if stats["avg_ms"] > slow_threshold else ""
        lines.append(
            f"{name:<40} {stats['avg_ms']:>8.1f} "
            f"{stats['max_ms']:>8.0f} {stats['count']:>6} "
            f"{stats['errors']:>4}{marker}"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Hook Performance Monitor")
    parser.add_argument("--report", action="store_true", help="Generate performance report")
    parser.add_argument("--days", type=int, default=7, help="Days of data to analyze")
    parser.add_argument("--slow-threshold", type=float, default=100.0, help="Slow hook threshold (ms)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    records = load_latency_data(days=args.days)
    stats = analyze_hook_performance(records)

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        report = generate_report(stats, slow_threshold=args.slow_threshold)
        print(report)


if __name__ == "__main__":
    main()
