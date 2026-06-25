#!/usr/bin/env python3
"""
Data Cleanup Tool for Claude Code Evaluation Data

Scans evaluation data files and performs cleanup operations:
- Archives files > 10MB
- Truncates files > 50MB to last 1000 entries
- Reports what was cleaned
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import gzip


# Configuration
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
LOGS_DIR = Path.home() / ".claude" / "logs"

# Thresholds
ARCHIVE_THRESHOLD_MB = 10
TRUNCATE_THRESHOLD_MB = 50
TRUNCATE_KEEP_ENTRIES = 1000


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB."""
    return file_path.stat().st_size / (1024 * 1024)


def scan_jsonl_files() -> List[Tuple[Path, float]]:
    """
    Scan all JSONL files in evaluation data directory.

    Returns:
        List of (file_path, size_mb) tuples
    """
    files = []

    # Main data directory
    for jsonl_file in DATA_DIR.glob("*.jsonl"):
        size_mb = get_file_size_mb(jsonl_file)
        files.append((jsonl_file, size_mb))

    # Subdirectories
    for subdir in ["tool_chains", "benchmarks", "red_team", "agent_harness"]:
        subdir_path = DATA_DIR / subdir
        if subdir_path.exists():
            for jsonl_file in subdir_path.glob("*.jsonl"):
                size_mb = get_file_size_mb(jsonl_file)
                files.append((jsonl_file, size_mb))

    return files


def archive_file(file_path: Path) -> bool:
    """
    Archive a file by moving it to archive directory.

    Args:
        file_path: Path to file to archive

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure archive directory exists
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        # Generate archive filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        archive_path = ARCHIVE_DIR / archive_name

        # Move file
        shutil.move(str(file_path), str(archive_path))

        # Create empty replacement file
        file_path.touch()
        os.chmod(file_path, 0o644)

        print(f"✓ Archived: {file_path.name} → {archive_name}")
        return True

    except Exception as e:
        print(f"✗ Failed to archive {file_path.name}: {e}")
        return False


def truncate_jsonl_file(file_path: Path, keep_entries: int = TRUNCATE_KEEP_ENTRIES) -> bool:
    """
    Truncate JSONL file to last N entries.

    Args:
        file_path: Path to JSONL file
        keep_entries: Number of entries to keep (from end)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read all entries
        entries = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(line)

        total_entries = len(entries)

        # Keep only last N entries
        kept_entries = entries[-keep_entries:] if len(entries) > keep_entries else entries

        # Archive original
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
        shutil.copy2(file_path, backup_path)

        # Compress backup
        with open(backup_path, 'rb') as f_in:
            with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        backup_path.unlink()  # Remove uncompressed backup

        # Write truncated file
        with open(file_path, 'w') as f:
            for entry in kept_entries:
                f.write(entry + '\n')

        print(f"✓ Truncated: {file_path.name} ({total_entries} → {len(kept_entries)} entries)")
        return True

    except Exception as e:
        print(f"✗ Failed to truncate {file_path.name}: {e}")
        return False


def cleanup_old_archives() -> int:
    """
    Remove archived files older than 6 months.

    Returns:
        Number of files removed
    """
    removed_count = 0

    if not ARCHIVE_DIR.exists():
        return 0

    try:
        # Find old files (older than 180 days)
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(days=180)

        for archive_file in ARCHIVE_DIR.glob("*"):
            if archive_file.is_file():
                mtime = datetime.fromtimestamp(archive_file.stat().st_mtime)
                if mtime < cutoff_time:
                    archive_file.unlink()
                    removed_count += 1

        if removed_count > 0:
            print(f"✓ Removed {removed_count} old archived files (>6 months)")

    except Exception as e:
        print(f"✗ Failed to cleanup old archives: {e}")

    return removed_count


def generate_report(files: List[Tuple[Path, float]],
                   archived: List[str],
                   truncated: List[str]) -> Dict:
    """
    Generate cleanup report.

    Args:
        files: List of (file_path, size_mb) tuples
        archived: List of archived file names
        truncated: List of truncated file names

    Returns:
        Report dictionary
    """
    total_size_mb = sum(size for _, size in files)
    large_files = [(f.name, size) for f, size in files if size > ARCHIVE_THRESHOLD_MB]

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_files_scanned": len(files),
            "total_size_mb": round(total_size_mb, 2),
            "files_archived": len(archived),
            "files_truncated": len(truncated),
        },
        "large_files": [
            {"name": name, "size_mb": round(size, 2)}
            for name, size in sorted(large_files, key=lambda x: x[1], reverse=True)
        ],
        "actions": {
            "archived": archived,
            "truncated": truncated,
        }
    }

    return report


def main():
    """Main cleanup routine."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Cleanup evaluation data files")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--archive-threshold", type=int, default=ARCHIVE_THRESHOLD_MB,
                       help=f"Archive threshold in MB (default: {ARCHIVE_THRESHOLD_MB})")
    parser.add_argument("--truncate-threshold", type=int, default=TRUNCATE_THRESHOLD_MB,
                       help=f"Truncate threshold in MB (default: {TRUNCATE_THRESHOLD_MB})")
    args = parser.parse_args()

    print("=" * 70)
    print("Claude Code Evaluation Data Cleanup")
    if args.dry_run:
        print("[DRY RUN MODE - No changes will be made]")
    print("=" * 70)
    print()

    # Scan files
    print("Scanning JSONL files...")
    files = scan_jsonl_files()
    print(f"Found {len(files)} JSONL files")
    print()

    # Track actions
    archived_files = []
    truncated_files = []

    # Process files
    for file_path, size_mb in files:
        # Skip already compressed files
        if file_path.suffix == ".gz":
            continue

        # Truncate very large files
        if size_mb > args.truncate_threshold:
            print(f"⚠ Large file detected: {file_path.name} ({size_mb:.1f} MB)")
            if args.dry_run:
                print(f"  [DRY RUN] Would truncate to {TRUNCATE_KEEP_ENTRIES} entries")
                truncated_files.append(file_path.name)
            else:
                if truncate_jsonl_file(file_path, TRUNCATE_KEEP_ENTRIES):
                    truncated_files.append(file_path.name)

        # Archive large files (but not truncated ones)
        elif size_mb > args.archive_threshold:
            print(f"⚠ Archiving: {file_path.name} ({size_mb:.1f} MB)")
            if args.dry_run:
                print(f"  [DRY RUN] Would archive to {ARCHIVE_DIR}")
                archived_files.append(file_path.name)
            else:
                if archive_file(file_path):
                    archived_files.append(file_path.name)

    print()

    # Cleanup old archives
    print("Cleaning up old archives...")
    if args.dry_run:
        print("[DRY RUN] Would remove archives older than 6 months")
        removed_count = 0
    else:
        removed_count = cleanup_old_archives()
    print()

    # Generate report
    report = generate_report(files, archived_files, truncated_files)

    # Save report
    if not args.dry_run:
        report_path = DATA_DIR / "cleanup_reports" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
    else:
        report_path = "[dry run - not saved]"

    # Print summary
    print("=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(f"Total files scanned:  {report['summary']['total_files_scanned']}")
    print(f"Total size:           {report['summary']['total_size_mb']:.2f} MB")
    print(f"Files archived:       {report['summary']['files_archived']}")
    print(f"Files truncated:      {report['summary']['files_truncated']}")
    print(f"Old archives removed: {removed_count}")
    print()
    print(f"Report saved to: {report_path}")
    print("=" * 70)

    # Show large files still remaining
    if report['large_files']:
        print()
        print("Large files (>10MB) still present:")
        for file_info in report['large_files'][:10]:
            print(f"  - {file_info['name']}: {file_info['size_mb']:.2f} MB")

        if len(report['large_files']) > 10:
            print(f"  ... and {len(report['large_files']) - 10} more")


if __name__ == "__main__":
    main()
