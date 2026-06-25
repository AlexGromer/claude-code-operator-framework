#!/usr/bin/env python3
"""
Research Source Monitoring Tool
Automated weekly digest generation from AI research sources.

Usage:
    python research_monitor.py [--since-days N] [--output FILE]

Integration:
    Add to cron: 0 9 * * 1 cd ~/.claude/tools && python research_monitor.py

Version: 1.1.0
Created: 2026-01-27
Updated: 2026-02-04
"""

import feedparser
import requests
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RSS Feeds Configuration (from RESEARCH_SOURCE_MONITORING.md)
FEEDS = {
    # Weekly monitoring - Research papers
    "arxiv_cl": {
        "url": "http://export.arxiv.org/rss/cs.CL",
        "category": "Research Papers",
        "priority": "HIGH",
        "frequency": "Weekly"
    },
    "arxiv_ai": {
        "url": "http://export.arxiv.org/rss/cs.AI",
        "category": "Research Papers",
        "priority": "HIGH",
        "frequency": "Weekly"
    },
    "arxiv_lg": {
        "url": "http://export.arxiv.org/rss/cs.LG",
        "category": "Research Papers",
        "priority": "MEDIUM",
        "frequency": "Weekly"
    },

    # Weekly monitoring - Model releases
    "anthropic_blog": {
        "url": "https://www.anthropic.com/news/rss",
        "category": "Model Releases",
        "priority": "CRITICAL",
        "frequency": "Weekly"
    },
    "openai_blog": {
        "url": "https://openai.com/blog/rss.xml",
        "category": "Model Releases",
        "priority": "CRITICAL",
        "frequency": "Weekly"
    },

    # Weekly monitoring - Frameworks
    "papers_with_code": {
        "url": "https://paperswithcode.com/feeds/trending.rss",
        "category": "Benchmarks",
        "priority": "HIGH",
        "frequency": "Weekly"
    },

    # Weekly monitoring - Community
    "deeplearning_ai": {
        "url": "https://www.deeplearning.ai/the-batch/rss/",
        "category": "Community",
        "priority": "MEDIUM",
        "frequency": "Weekly"
    }
}

# GitHub repositories to monitor (from AUTHORITATIVE_SOURCES.md)
GITHUB_REPOS = [
    {"repo": "anthropics/anthropic-sdk-python", "category": "Frameworks", "priority": "HIGH"},
    {"repo": "langchain-ai/langchain", "category": "Frameworks", "priority": "HIGH"},
    {"repo": "run-llama/llama_index", "category": "Frameworks", "priority": "MEDIUM"},
    {"repo": "huggingface/transformers", "category": "Frameworks", "priority": "MEDIUM"}
]

# Alert thresholds (from RESEARCH_SOURCE_MONITORING.md Section 4)
ALERT_THRESHOLDS = {
    "CRITICAL": {
        "keywords": ["claude", "opus", "sonnet", "haiku", "breaking", "security", "vulnerability"],
        "response_time": "< 24h"
    },
    "HIGH": {
        "keywords": ["api", "deprecat", "migration", "major release", "benchmark", "sota"],
        "response_time": "< 7 days"
    },
    "MEDIUM": {
        "keywords": ["tutorial", "guide", "best practice", "optimization"],
        "response_time": "< 30 days"
    },
    "LOW": {
        "keywords": ["blog", "discussion", "opinion"],
        "response_time": "Quarterly review"
    }
}


def fetch_rss_entries(feed_url: str, since_days: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch RSS entries from the last N days.

    Args:
        feed_url: RSS feed URL
        since_days: Number of days to look back

    Returns:
        List of entry dictionaries with title, link, published, summary
    """
    try:
        logger.info(f"Fetching feed: {feed_url}")
        feed = feedparser.parse(feed_url)

        if feed.bozo:
            logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

        cutoff = datetime.now() - timedelta(days=since_days)
        new_entries = []

        for entry in feed.entries:
            try:
                # Try multiple date fields
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])

                if pub_date and pub_date >= cutoff:
                    new_entries.append({
                        "title": entry.get("title", "No title"),
                        "link": entry.get("link", ""),
                        "published": pub_date,
                        "summary": entry.get("summary", "")[:300]
                    })
            except Exception as e:
                logger.warning(f"Error parsing entry: {e}")
                continue

        logger.info(f"Found {len(new_entries)} entries from last {since_days} days")
        return new_entries

    except Exception as e:
        logger.error(f"Error fetching feed {feed_url}: {e}")
        return []


def check_github_releases(repo: str, since_days: int = 7) -> List[Dict[str, Any]]:
    """
    Check GitHub repository for new releases.

    Args:
        repo: Repository in format "owner/repo"
        since_days: Number of days to look back

    Returns:
        List of release dictionaries
    """
    try:
        api_url = f"https://api.github.com/repos/{repo}/releases"
        headers = {"Accept": "application/vnd.github.v3+json"}

        # Add GitHub token if available (increases rate limit)
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        logger.info(f"Checking GitHub releases: {repo}")
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()

        releases = response.json()
        cutoff = datetime.now() - timedelta(days=since_days)
        new_releases = []

        for release in releases:
            pub_date = datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ")
            if pub_date >= cutoff:
                new_releases.append({
                    "title": f"{repo} {release['name']}",
                    "link": release["html_url"],
                    "published": pub_date,
                    "summary": release.get("body", "")[:300]
                })

        logger.info(f"Found {len(new_releases)} releases from last {since_days} days")
        return new_releases

    except Exception as e:
        logger.error(f"Error checking GitHub releases for {repo}: {e}")
        return []


def calculate_priority(entry: Dict[str, Any], feed_priority: str) -> str:
    """
    Calculate priority level based on content analysis.

    Args:
        entry: Entry dictionary with title and summary
        feed_priority: Default priority from feed configuration

    Returns:
        Priority level (CRITICAL/HIGH/MEDIUM/LOW)
    """
    text = f"{entry['title']} {entry['summary']}".lower()

    # Check for CRITICAL keywords
    for keyword in ALERT_THRESHOLDS["CRITICAL"]["keywords"]:
        if keyword.lower() in text:
            return "CRITICAL"

    # Check for HIGH keywords
    for keyword in ALERT_THRESHOLDS["HIGH"]["keywords"]:
        if keyword.lower() in text:
            return "HIGH"

    # Check for MEDIUM keywords
    for keyword in ALERT_THRESHOLDS["MEDIUM"]["keywords"]:
        if keyword.lower() in text:
            return "MEDIUM"

    # Default to feed priority
    return feed_priority


def generate_digest(since_days: int = 7, output_format: str = "markdown") -> str:
    """
    Generate weekly digest from all configured sources.

    Args:
        since_days: Number of days to look back
        output_format: Output format (markdown/json)

    Returns:
        Formatted digest string
    """
    logger.info(f"Generating digest for last {since_days} days")

    all_entries = []

    # Fetch RSS feeds
    for feed_name, feed_config in FEEDS.items():
        entries = fetch_rss_entries(feed_config["url"], since_days)
        for entry in entries:
            entry["source"] = feed_name
            entry["category"] = feed_config["category"]
            entry["priority"] = calculate_priority(entry, feed_config["priority"])
            all_entries.append(entry)

    # Fetch GitHub releases
    for repo_config in GITHUB_REPOS:
        releases = check_github_releases(repo_config["repo"], since_days)
        for release in releases:
            release["source"] = repo_config["repo"]
            release["category"] = repo_config["category"]
            release["priority"] = calculate_priority(release, repo_config["priority"])
            all_entries.append(release)

    # Sort by priority and date
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_entries.sort(key=lambda x: (priority_order[x["priority"]], -x["published"].timestamp()))

    if output_format == "json":
        return json.dumps({
            "generated": datetime.now().isoformat(),
            "period_days": since_days,
            "total_entries": len(all_entries),
            "entries": [
                {
                    "title": e["title"],
                    "link": e["link"],
                    "published": e["published"].isoformat(),
                    "category": e["category"],
                    "priority": e["priority"],
                    "source": e["source"]
                }
                for e in all_entries
            ]
        }, indent=2)

    # Markdown format
    digest = f"# AI Research Weekly Digest\n\n"
    digest += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    digest += f"**Period:** Last {since_days} days\n"
    digest += f"**Total Entries:** {len(all_entries)}\n\n"
    digest += "---\n\n"

    # Group by priority
    for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        priority_entries = [e for e in all_entries if e["priority"] == priority]
        if not priority_entries:
            continue

        icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}[priority]
        digest += f"## {icon} {priority} Priority ({len(priority_entries)} entries)\n\n"

        # Group by category
        categories = {}
        for entry in priority_entries:
            cat = entry["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)

        for category, entries in categories.items():
            digest += f"### {category}\n\n"
            for entry in entries[:10]:  # Limit to 10 per category
                digest += f"- **{entry['title']}**\n"
                digest += f"  - 🔗 [{entry['link']}]({entry['link']})\n"
                digest += f"  - 📅 {entry['published'].strftime('%Y-%m-%d')}\n"
                digest += f"  - 📦 Source: {entry['source']}\n"
                if entry['summary']:
                    digest += f"  - 📝 {entry['summary'][:150]}...\n"
                digest += "\n"

        digest += "---\n\n"

    # Add footer with next steps
    digest += "## 📋 Next Steps\n\n"
    digest += "1. **CRITICAL items**: Review within 24h, assess for immediate integration\n"
    digest += "2. **HIGH items**: Review within 7 days, schedule PoC if relevant\n"
    digest += "3. **MEDIUM items**: Add to backlog for quarterly review\n"
    digest += "4. **LOW items**: Archive for reference\n\n"
    digest += "---\n\n"
    digest += f"*Generated by Research Monitor v1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    return digest


def create_notification_flag(digest_path: str, entry_count: int, critical_count: int) -> None:
    """
    Create notification flag file for session startup hook.

    Args:
        digest_path: Path to generated digest
        entry_count: Total number of entries
        critical_count: Number of CRITICAL priority entries
    """
    flag_dir = Path.home() / ".claude" / "evaluation" / "data" / "notifications"
    flag_dir.mkdir(parents=True, exist_ok=True)

    flag_file = flag_dir / "new_research_digest.json"
    flag_data = {
        "timestamp": datetime.now().isoformat(),
        "digest_path": digest_path,
        "entry_count": entry_count,
        "critical_count": critical_count,
        "acknowledged": False
    }

    flag_file.write_text(json.dumps(flag_data, indent=2), encoding="utf-8")
    logger.info(f"Notification flag created: {flag_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Research Source Monitoring Tool - Weekly AI research digest"
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        digest = generate_digest(since_days=args.since_days, output_format=args.format)

        if args.output:
            output_path = Path(args.output).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(digest, encoding="utf-8")
            logger.info(f"Digest saved to {output_path}")

            # Extract stats and create notification flag
            if args.format == "json":
                data = json.loads(digest)
                entry_count = data.get("total_entries", 0)
                critical_count = sum(1 for e in data.get("entries", [])
                                     if e.get("priority") == "CRITICAL")
            else:
                # Parse markdown for stats
                import re
                match = re.search(r"Total Entries:\*\*\s*(\d+)", digest)
                entry_count = int(match.group(1)) if match else 0
                critical_match = re.search(r"CRITICAL Priority \((\d+)", digest)
                critical_count = int(critical_match.group(1)) if critical_match else 0

            create_notification_flag(str(output_path), entry_count, critical_count)
        else:
            print(digest)

        return 0

    except Exception as e:
        logger.error(f"Error generating digest: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
