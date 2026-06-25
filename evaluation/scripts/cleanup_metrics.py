#!/usr/bin/env python3
"""
Metrics Cleanup Script with Data Retention Policy
Version: 1.1.0

Retention Policy:
- Raw metrics (metrics.jsonl): Keep 30 days, then aggregate to weekly summaries
- Session files: Keep 7 days, then archive
- Session continuity summaries: Keep 30 days, then delete
- Weekly metric summaries: Keep indefinitely for progression tracking
- Archive files: Keep 90 days, then delete

Usage:
    python cleanup_metrics.py [--dry-run] [--verbose]
"""

import argparse
import json
import os
import gzip
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
import sys


# Configuration
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
METRICS_FILE = DATA_DIR / "metrics.jsonl"
SESSIONS_DIR = DATA_DIR / "sessions"
ARCHIVE_DIR = SESSIONS_DIR / "archive"
SUMMARIES_DIR = DATA_DIR / "summaries"

# Retention periods
RAW_METRICS_RETENTION_DAYS = 30
SESSION_RETENTION_DAYS = 7
ARCHIVE_RETENTION_DAYS = 90


def ensure_directories():
    """Ensure required directories exist."""
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def parse_timestamp(ts_str: str) -> datetime:
    """Parse various timestamp formats."""
    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
        try:
            return datetime.strptime(ts_str.rstrip('Z'), fmt.rstrip('Z'))
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: {ts_str}")


def aggregate_metrics_to_weekly(dry_run: bool = False, verbose: bool = False) -> dict:
    """
    Aggregate old metrics (>30 days) to weekly summaries.
    Returns statistics about what was done.
    """
    stats = {
        'raw_lines_processed': 0,
        'raw_lines_kept': 0,
        'raw_lines_aggregated': 0,
        'weeks_summarized': 0
    }

    if not METRICS_FILE.exists():
        if verbose:
            print(f"No metrics file found at {METRICS_FILE}")
        return stats

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=RAW_METRICS_RETENTION_DAYS)

    # Read all metrics
    recent_metrics = []
    old_metrics_by_week = defaultdict(list)

    with open(METRICS_FILE, 'r') as f:
        for line in f:
            stats['raw_lines_processed'] += 1
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                ts = parse_timestamp(entry.get('timestamp', ''))

                if ts >= cutoff_date:
                    recent_metrics.append(line)
                    stats['raw_lines_kept'] += 1
                else:
                    # Group by week (ISO week number)
                    week_key = ts.strftime('%Y-W%V')
                    old_metrics_by_week[week_key].append(entry)
                    stats['raw_lines_aggregated'] += 1
            except (json.JSONDecodeError, ValueError) as e:
                if verbose:
                    print(f"Warning: Invalid line: {line[:50]}... ({e})")
                recent_metrics.append(line)  # Keep invalid lines

    if verbose:
        print(f"Processed {stats['raw_lines_processed']} lines")
        print(f"Keeping {stats['raw_lines_kept']} recent lines")
        print(f"Aggregating {stats['raw_lines_aggregated']} old lines into {len(old_metrics_by_week)} weeks")

    # Create weekly summaries
    for week_key, metrics in old_metrics_by_week.items():
        summary = create_weekly_summary(week_key, metrics)
        summary_file = SUMMARIES_DIR / f"summary_{week_key}.json"

        if not dry_run:
            # Merge with existing summary if exists
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    existing = json.load(f)
                summary = merge_summaries(existing, summary)

            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)

        stats['weeks_summarized'] += 1
        if verbose:
            print(f"  Created summary for {week_key}: {len(metrics)} metrics")

    # Rewrite metrics file with only recent data
    if not dry_run and stats['raw_lines_aggregated'] > 0:
        backup_file = METRICS_FILE.with_suffix('.jsonl.bak')
        shutil.copy2(METRICS_FILE, backup_file)

        with open(METRICS_FILE, 'w') as f:
            f.writelines(recent_metrics)

        if verbose:
            print(f"Metrics file updated. Backup: {backup_file}")

    return stats


def create_weekly_summary(week_key: str, metrics: list) -> dict:
    """Create a summary from a list of metrics."""
    summary = {
        'week': week_key,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'total_metrics': len(metrics),
        'metric_types': defaultdict(lambda: {'count': 0, 'sum': 0, 'min': float('inf'), 'max': float('-inf')}),
        'sessions': set(),
        'tools_used': defaultdict(int)
    }

    for m in metrics:
        metric_type = m.get('metric_type', 'unknown')
        value = m.get('value', 0)

        stats = summary['metric_types'][metric_type]
        stats['count'] += 1
        stats['sum'] += value
        stats['min'] = min(stats['min'], value)
        stats['max'] = max(stats['max'], value)

        # Track sessions
        if 'session_id' in m:
            summary['sessions'].add(m['session_id'])

        # Track tools
        metadata = m.get('metadata', {})
        if 'tool_name' in metadata:
            summary['tools_used'][metadata['tool_name']] += 1

    # Convert sets and defaultdicts to serializable types
    summary['sessions'] = list(summary['sessions'])
    summary['session_count'] = len(summary['sessions'])
    del summary['sessions']  # Don't need individual session IDs

    summary['tools_used'] = dict(summary['tools_used'])

    # Calculate averages
    for metric_type, stats in summary['metric_types'].items():
        if stats['count'] > 0:
            stats['avg'] = round(stats['sum'] / stats['count'], 4)
        if stats['min'] == float('inf'):
            stats['min'] = 0
        if stats['max'] == float('-inf'):
            stats['max'] = 0

    summary['metric_types'] = dict(summary['metric_types'])

    return summary


def merge_summaries(existing: dict, new: dict) -> dict:
    """Merge two weekly summaries."""
    merged = existing.copy()
    merged['total_metrics'] = existing.get('total_metrics', 0) + new.get('total_metrics', 0)
    merged['session_count'] = existing.get('session_count', 0) + new.get('session_count', 0)
    merged['updated_at'] = datetime.now(timezone.utc).isoformat()

    # Merge metric_types
    for metric_type, new_stats in new.get('metric_types', {}).items():
        if metric_type in merged.get('metric_types', {}):
            existing_stats = merged['metric_types'][metric_type]
            total_count = existing_stats['count'] + new_stats['count']
            merged['metric_types'][metric_type] = {
                'count': total_count,
                'sum': existing_stats['sum'] + new_stats['sum'],
                'min': min(existing_stats['min'], new_stats['min']),
                'max': max(existing_stats['max'], new_stats['max']),
                'avg': round((existing_stats['sum'] + new_stats['sum']) / total_count, 4) if total_count > 0 else 0
            }
        else:
            if 'metric_types' not in merged:
                merged['metric_types'] = {}
            merged['metric_types'][metric_type] = new_stats

    # Merge tools_used
    for tool, count in new.get('tools_used', {}).items():
        if 'tools_used' not in merged:
            merged['tools_used'] = {}
        merged['tools_used'][tool] = merged['tools_used'].get(tool, 0) + count

    return merged


def cleanup_old_sessions(dry_run: bool = False, verbose: bool = False) -> dict:
    """Archive old session files."""
    stats = {
        'sessions_archived': 0,
        'archives_deleted': 0
    }

    session_cutoff = datetime.now(timezone.utc) - timedelta(days=SESSION_RETENTION_DAYS)
    archive_cutoff = datetime.now(timezone.utc) - timedelta(days=ARCHIVE_RETENTION_DAYS)

    # Archive old active sessions
    if SESSIONS_DIR.exists():
        for session_file in SESSIONS_DIR.glob('session_*.json'):
            if session_file.name.startswith('session_') and not session_file.is_dir():
                try:
                    mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if mtime < session_cutoff:
                        if not dry_run:
                            # Read and archive
                            with open(session_file, 'r') as f:
                                state = json.load(f)

                            session_id = session_file.stem.replace('session_', '')
                            archive_file = ARCHIVE_DIR / f"{session_file.stem}_{mtime.strftime('%Y%m%d')}.json.gz"

                            with gzip.open(archive_file, 'wt') as f:
                                json.dump(state, f)

                            session_file.unlink()

                        stats['sessions_archived'] += 1
                        if verbose:
                            print(f"  Archived: {session_file.name}")
                except Exception as e:
                    if verbose:
                        print(f"  Warning: Failed to process {session_file}: {e}")

    # Delete old archives
    if ARCHIVE_DIR.exists():
        for archive_file in ARCHIVE_DIR.glob('*.json.gz'):
            try:
                mtime = datetime.fromtimestamp(archive_file.stat().st_mtime)
                if mtime < archive_cutoff:
                    if not dry_run:
                        archive_file.unlink()
                    stats['archives_deleted'] += 1
                    if verbose:
                        print(f"  Deleted old archive: {archive_file.name}")
            except Exception as e:
                if verbose:
                    print(f"  Warning: Failed to process {archive_file}: {e}")

    return stats


def cleanup_continuity_summaries(dry_run: bool = False, verbose: bool = False) -> dict:
    """Delete old session continuity summaries (>30 days) across all projects."""
    stats = {
        'summaries_deleted': 0,
        'projects_processed': 0
    }

    # Retention: 30 days for continuity summaries
    CONTINUITY_RETENTION_DAYS = 30
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONTINUITY_RETENTION_DAYS)

    continuity_dir = SUMMARIES_DIR / "session"

    if not continuity_dir.exists():
        return stats

    # Process each project directory
    for project_dir in continuity_dir.iterdir():
        if not project_dir.is_dir():
            continue

        stats['projects_processed'] += 1

        for summary_file in project_dir.glob('*.md'):
            try:
                mtime = datetime.fromtimestamp(summary_file.stat().st_mtime)
                if mtime < cutoff:
                    if not dry_run:
                        summary_file.unlink()
                    stats['summaries_deleted'] += 1
                    if verbose:
                        age_days = (datetime.now(timezone.utc) - mtime).days
                        print(f"  Deleted: {project_dir.name}/{summary_file.name} (age: {age_days} days)")
            except Exception as e:
                if verbose:
                    print(f"  Warning: Failed to process {summary_file}: {e}")

        # Remove empty project directories
        if not dry_run:
            try:
                if not any(project_dir.iterdir()):
                    project_dir.rmdir()
                    if verbose:
                        print(f"  Removed empty project directory: {project_dir.name}")
            except Exception:
                pass  # Directory not empty or other error, ignore

    return stats


def generate_progression_report(verbose: bool = False) -> dict:
    """Generate a progression report from all weekly summaries."""
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'weeks': [],
        'trends': {}
    }

    if not SUMMARIES_DIR.exists():
        return report

    # Load all summaries
    summaries = []
    for summary_file in sorted(SUMMARIES_DIR.glob('summary_*.json')):
        try:
            with open(summary_file, 'r') as f:
                summaries.append(json.load(f))
        except Exception as e:
            if verbose:
                print(f"Warning: Failed to load {summary_file}: {e}")

    if not summaries:
        return report

    # Build weekly data
    for s in summaries:
        week_data = {
            'week': s.get('week'),
            'total_metrics': s.get('total_metrics', 0),
            'session_count': s.get('session_count', 0),
            'tools': len(s.get('tools_used', {})),
        }

        # Extract key metrics
        for metric_type in ['tool_execution', 'accuracy', 'hallucination']:
            if metric_type in s.get('metric_types', {}):
                stats = s['metric_types'][metric_type]
                week_data[f'{metric_type}_avg'] = stats.get('avg', 0)
                week_data[f'{metric_type}_count'] = stats.get('count', 0)

        report['weeks'].append(week_data)

    # Calculate trends (comparing last week to previous)
    if len(report['weeks']) >= 2:
        last = report['weeks'][-1]
        prev = report['weeks'][-2]

        for key in ['total_metrics', 'session_count', 'tool_execution_avg']:
            if key in last and key in prev:
                prev_val = prev[key] or 1
                report['trends'][key] = round((last[key] - prev[key]) / prev_val * 100, 1)

    return report


def main():
    parser = argparse.ArgumentParser(description='Metrics Cleanup with Retention Policy')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--report', action='store_true', help='Generate and display progression report')

    args = parser.parse_args()

    ensure_directories()

    if args.report:
        report = generate_progression_report(args.verbose)
        print(json.dumps(report, indent=2))
        return

    print("=" * 60)
    print("Claude Metrics Cleanup")
    print(f"Retention Policy:")
    print(f"  - Raw metrics: {RAW_METRICS_RETENTION_DAYS} days")
    print(f"  - Sessions: {SESSION_RETENTION_DAYS} days")
    print(f"  - Continuity summaries: 30 days")
    print(f"  - Archives: {ARCHIVE_RETENTION_DAYS} days")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY RUN - No changes will be made ***\n")

    # Aggregate old metrics
    print("\n[1/3] Aggregating old metrics to weekly summaries...")
    metrics_stats = aggregate_metrics_to_weekly(args.dry_run, args.verbose)
    print(f"  Processed: {metrics_stats['raw_lines_processed']} lines")
    print(f"  Kept: {metrics_stats['raw_lines_kept']} recent lines")
    print(f"  Aggregated: {metrics_stats['raw_lines_aggregated']} lines into {metrics_stats['weeks_summarized']} weeks")

    # Cleanup old sessions
    print("\n[2/3] Cleaning up old sessions...")
    session_stats = cleanup_old_sessions(args.dry_run, args.verbose)
    print(f"  Sessions archived: {session_stats['sessions_archived']}")
    print(f"  Old archives deleted: {session_stats['archives_deleted']}")

    # Cleanup old continuity summaries
    print("\n[3/3] Cleaning up old continuity summaries...")
    continuity_stats = cleanup_continuity_summaries(args.dry_run, args.verbose)
    print(f"  Projects processed: {continuity_stats['projects_processed']}")
    print(f"  Continuity summaries deleted: {continuity_stats['summaries_deleted']}")

    print("\n" + "=" * 60)
    print("Cleanup complete!")

    if args.dry_run:
        print("\n*** This was a dry run. Run without --dry-run to apply changes. ***")


if __name__ == '__main__':
    main()
