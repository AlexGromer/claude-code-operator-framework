#!/usr/bin/env python3
"""
Staleness Checker - Content Freshness Analysis Tool

Scans configuration files for staleness indicators and generates reports.
Part of the Relevance Maintenance Protocol.

Usage:
    python staleness_checker.py --mode weekly
    python staleness_checker.py --mode monthly --report
    python staleness_checker.py --mode quarterly --full-audit
    python staleness_checker.py --file path/to/file.md
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
CLAUDE_DIR = Path.home() / ".claude"
MODULES_DIR = CLAUDE_DIR / "modules"
RULES_DIR = CLAUDE_DIR / "rules"
EXAMPLES_DIR = CLAUDE_DIR / "examples"
TOOLS_DIR = CLAUDE_DIR / "tools"
LOGS_DIR = CLAUDE_DIR / "logs"
DATA_DIR = CLAUDE_DIR / "evaluation" / "data"

# Staleness thresholds (days)
THRESHOLDS = {
    "fresh": 90,        # 0-3 months
    "aging": 180,       # 3-6 months
    "stale": 365,       # 6-12 months
    "critical": 365     # >12 months
}

# Score thresholds
SCORE_THRESHOLDS = {
    "healthy": 20,
    "attention": 40,
    "stale": 60,
    "critical": 80,
    "dangerous": 100
}


def get_file_age_days(file_path: Path) -> int:
    """Get file age in days based on modification time."""
    if not file_path.exists():
        return 999
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    return (datetime.now() - mtime).days


def get_git_last_modified(file_path: Path) -> Optional[datetime]:
    """Get last git commit date for a file."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", str(file_path)],
            capture_output=True,
            text=True,
            cwd=CLAUDE_DIR
        )
        if result.returncode == 0 and result.stdout.strip():
            date_str = result.stdout.strip().split()[0]
            return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        pass
    return None


def extract_version_from_file(file_path: Path) -> Optional[str]:
    """Extract version number from file header."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(500)  # First 500 chars
            # Look for Version: X.Y.Z pattern
            match = re.search(r'Version:\s*(\d+\.\d+\.\d+)', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def calculate_staleness_score(
    file_path: Path,
    usage_rate: float = 10.0,
    has_security_issues: bool = False,
    upstream_deprecated: bool = False
) -> Tuple[int, List[str]]:
    """
    Calculate staleness score (0-100, higher = more stale).

    Returns:
        Tuple of (score, list of issues)
    """
    score = 0
    issues = []

    # Time factor (0-40 points)
    age_days = get_file_age_days(file_path)
    months = age_days / 30

    if months > 12:
        score += 40
        issues.append(f"Not updated for {int(months)} months (>12)")
    elif months > 6:
        score += 30
        issues.append(f"Not updated for {int(months)} months (6-12)")
    elif months > 3:
        score += 15
        issues.append(f"Not updated for {int(months)} months (3-6)")

    # Usage factor (0-20 points)
    if usage_rate < 5:
        score += 20
        issues.append(f"Very low usage ({usage_rate:.1f}%)")
    elif usage_rate < 10:
        score += 10
        issues.append(f"Low usage ({usage_rate:.1f}%)")

    # External factors (0-20 points)
    if has_security_issues:
        score += 10
        issues.append("Has security issues")
    if upstream_deprecated:
        score += 10
        issues.append("Upstream deprecated")

    return min(score, 100), issues


def get_status_emoji(score: int) -> str:
    """Get status emoji based on score."""
    if score <= 20:
        return "🟢"
    elif score <= 40:
        return "🟡"
    elif score <= 60:
        return "🟠"
    elif score <= 80:
        return "🔴"
    else:
        return "⛔"


def get_status_text(score: int) -> str:
    """Get status text based on score."""
    if score <= 20:
        return "Healthy"
    elif score <= 40:
        return "Attention"
    elif score <= 60:
        return "Stale"
    elif score <= 80:
        return "Critical"
    else:
        return "Dangerous"


def scan_directory(
    directory: Path,
    pattern: str = "*.md"
) -> List[Dict]:
    """Scan directory for files and calculate staleness."""
    results = []

    if not directory.exists():
        return results

    for file_path in directory.glob(pattern):
        if file_path.is_file():
            score, issues = calculate_staleness_score(file_path)
            age_days = get_file_age_days(file_path)

            results.append({
                "file": str(file_path.relative_to(CLAUDE_DIR)),
                "score": score,
                "status": get_status_text(score),
                "emoji": get_status_emoji(score),
                "age_days": age_days,
                "last_modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).strftime("%Y-%m-%d"),
                "issues": issues,
                "version": extract_version_from_file(file_path)
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)


def scan_all() -> Dict[str, List[Dict]]:
    """Scan all configuration directories."""
    return {
        "modules": scan_directory(MODULES_DIR),
        "rules": scan_directory(RULES_DIR),
        "protocols": scan_directory(CLAUDE_DIR / "protocols"),
        "tools": scan_directory(TOOLS_DIR, "*.py"),
    }


def generate_summary(results: Dict[str, List[Dict]]) -> Dict:
    """Generate summary statistics."""
    all_items = []
    for items in results.values():
        all_items.extend(items)

    summary = {
        "total": len(all_items),
        "healthy": sum(1 for i in all_items if i["score"] <= 20),
        "attention": sum(1 for i in all_items if 20 < i["score"] <= 40),
        "stale": sum(1 for i in all_items if 40 < i["score"] <= 60),
        "critical": sum(1 for i in all_items if 60 < i["score"] <= 80),
        "dangerous": sum(1 for i in all_items if i["score"] > 80),
        "average_score": sum(i["score"] for i in all_items) / len(all_items) if all_items else 0,
        "oldest_file": max(all_items, key=lambda x: x["age_days"]) if all_items else None,
    }

    return summary


def generate_markdown_report(results: Dict[str, List[Dict]], summary: Dict) -> str:
    """Generate markdown report."""
    report = []
    report.append(f"# Staleness Report - {datetime.now().strftime('%Y-%m-%d')}\n")

    # Summary
    report.append("## Summary\n")
    report.append(f"- **Total files scanned:** {summary['total']}")
    report.append(f"- 🟢 Healthy (0-20): {summary['healthy']}")
    report.append(f"- 🟡 Attention (21-40): {summary['attention']}")
    report.append(f"- 🟠 Stale (41-60): {summary['stale']}")
    report.append(f"- 🔴 Critical (61-80): {summary['critical']}")
    report.append(f"- ⛔ Dangerous (81-100): {summary['dangerous']}")
    report.append(f"- **Average score:** {summary['average_score']:.1f}")
    report.append("")

    # Critical items
    critical_items = []
    for category, items in results.items():
        for item in items:
            if item["score"] > 60:
                critical_items.append(item)

    if critical_items:
        report.append("## 🔴 Critical Items (Immediate Action)\n")
        report.append("| File | Score | Last Update | Issues |")
        report.append("|------|-------|-------------|--------|")
        for item in sorted(critical_items, key=lambda x: x["score"], reverse=True):
            issues_str = "; ".join(item["issues"][:2]) if item["issues"] else "-"
            report.append(f"| {item['file']} | {item['emoji']} {item['score']} | {item['last_modified']} | {issues_str} |")
        report.append("")

    # Stale items
    stale_items = []
    for category, items in results.items():
        for item in items:
            if 40 < item["score"] <= 60:
                stale_items.append(item)

    if stale_items:
        report.append("## 🟠 Stale Items (Update Within 2 Weeks)\n")
        report.append("| File | Score | Last Update | Issues |")
        report.append("|------|-------|-------------|--------|")
        for item in sorted(stale_items, key=lambda x: x["score"], reverse=True):
            issues_str = "; ".join(item["issues"][:2]) if item["issues"] else "-"
            report.append(f"| {item['file']} | {item['emoji']} {item['score']} | {item['last_modified']} | {issues_str} |")
        report.append("")

    # By category
    report.append("## By Category\n")
    for category, items in results.items():
        if items:
            avg_score = sum(i["score"] for i in items) / len(items)
            report.append(f"### {category.title()} (avg: {avg_score:.1f})\n")
            report.append("| File | Score | Last Update |")
            report.append("|------|-------|-------------|")
            for item in items[:10]:  # Top 10 per category
                report.append(f"| {item['file']} | {item['emoji']} {item['score']} | {item['last_modified']} |")
            report.append("")

    # Recommendations
    report.append("## Recommendations\n")
    if summary["dangerous"] > 0:
        report.append(f"1. ⛔ **URGENT:** {summary['dangerous']} files require immediate attention")
    if summary["critical"] > 0:
        report.append(f"2. 🔴 Update {summary['critical']} critical files within 1 week")
    if summary["stale"] > 0:
        report.append(f"3. 🟠 Schedule updates for {summary['stale']} stale files")
    if summary["average_score"] > 30:
        report.append(f"4. Consider running quarterly audit (average score: {summary['average_score']:.1f})")

    return "\n".join(report)


def save_report(report: str, mode: str):
    """Save report to file."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"staleness_{mode}_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = LOGS_DIR / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Report saved to: {filepath}")


def save_json_data(results: Dict, summary: Dict):
    """Save JSON data for metrics integration."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "results": results
    }

    filepath = DATA_DIR / "staleness_latest.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="Check configuration content for staleness"
    )
    parser.add_argument(
        "--mode",
        choices=["weekly", "monthly", "quarterly"],
        default="weekly",
        help="Scan mode (default: weekly)"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Check specific file"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate and save full report"
    )
    parser.add_argument(
        "--full-audit",
        action="store_true",
        help="Run full audit (all directories)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output critical items"
    )

    args = parser.parse_args()

    # Single file check
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}")
            return 1

        score, issues = calculate_staleness_score(args.file)
        print(f"File: {args.file}")
        print(f"Score: {get_status_emoji(score)} {score} ({get_status_text(score)})")
        print(f"Age: {get_file_age_days(args.file)} days")
        if issues:
            print("Issues:")
            for issue in issues:
                print(f"  - {issue}")
        return 0

    # Full scan
    print(f"Running {args.mode} staleness check...")
    results = scan_all()
    summary = generate_summary(results)

    # JSON output
    if args.json:
        print(json.dumps({"summary": summary, "results": results}, indent=2, default=str))
        return 0

    # Quiet mode - only critical
    if args.quiet:
        critical_count = summary["critical"] + summary["dangerous"]
        if critical_count > 0:
            print(f"⚠️ {critical_count} files need immediate attention")
            for category, items in results.items():
                for item in items:
                    if item["score"] > 60:
                        print(f"  {item['emoji']} {item['file']} (score: {item['score']})")
        return 0 if critical_count == 0 else 1

    # Generate report
    report = generate_markdown_report(results, summary)

    if args.report or args.full_audit:
        save_report(report, args.mode)
        save_json_data(results, summary)

    # Print summary
    print("\n" + "=" * 60)
    print(f"STALENESS CHECK SUMMARY ({args.mode})")
    print("=" * 60)
    print(f"Total files: {summary['total']}")
    print(f"🟢 Healthy:   {summary['healthy']}")
    print(f"🟡 Attention: {summary['attention']}")
    print(f"🟠 Stale:     {summary['stale']}")
    print(f"🔴 Critical:  {summary['critical']}")
    print(f"⛔ Dangerous: {summary['dangerous']}")
    print(f"Average score: {summary['average_score']:.1f}")
    print("=" * 60)

    # Alert on critical items
    if summary["critical"] + summary["dangerous"] > 0:
        print("\n⚠️  ACTION REQUIRED:")
        for category, items in results.items():
            for item in items:
                if item["score"] > 60:
                    print(f"  {item['emoji']} {item['file']}")
                    for issue in item["issues"]:
                        print(f"      └─ {issue}")

    return 0


if __name__ == "__main__":
    exit(main())
