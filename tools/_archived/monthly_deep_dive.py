#!/usr/bin/env python3
"""
Monthly Deep-Dive Analysis Tool
Analysis of frameworks, benchmarks, and BigTech documentation updates.

Usage:
    python monthly_deep_dive.py [--output FILE] [--quick]

Integration:
    Add to cron: 0 9 1 * * cd ~/.claude/tools && python monthly_deep_dive.py

Version: 1.0.0
Created: 2026-02-04
"""

import json
import requests
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# GitHub repositories for framework version tracking
FRAMEWORKS = {
    "langchain-ai/langchain": {"category": "Agent Framework", "priority": "HIGH"},
    "run-llama/llama_index": {"category": "RAG Framework", "priority": "HIGH"},
    "crewAIInc/crewAI": {"category": "Multi-Agent", "priority": "MEDIUM"},
    "stanfordnlp/dspy": {"category": "Optimization", "priority": "MEDIUM"},
    "Aider-AI/aider": {"category": "Coding Assistant", "priority": "HIGH"},
    "anthropics/anthropic-sdk-python": {"category": "SDK", "priority": "CRITICAL"},
    "openai/openai-python": {"category": "SDK", "priority": "HIGH"},
    "huggingface/transformers": {"category": "ML Framework", "priority": "MEDIUM"},
}

# Benchmark sources (API endpoints or scraping targets)
BENCHMARKS = {
    "lmsys_arena": {
        "name": "LMSYS Chatbot Arena",
        "url": "https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard",
        "type": "elo_ranking",
        "priority": "HIGH"
    },
    "swe_bench": {
        "name": "SWE-bench",
        "url": "https://www.swebench.com/",
        "type": "coding_benchmark",
        "priority": "HIGH"
    },
    "open_llm": {
        "name": "Open LLM Leaderboard",
        "url": "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard",
        "type": "model_comparison",
        "priority": "MEDIUM"
    }
}

# BigTech documentation sources
BIGTECH_DOCS = {
    "anthropic": {
        "name": "Anthropic Developer Docs",
        "changelog_url": "https://docs.anthropic.com/en/release-notes",
        "priority": "CRITICAL"
    },
    "openai": {
        "name": "OpenAI API Reference",
        "changelog_url": "https://platform.openai.com/docs/changelog",
        "priority": "HIGH"
    },
    "google_ai": {
        "name": "Google AI Studio",
        "changelog_url": "https://ai.google.dev/gemini-api/docs/changelog",
        "priority": "HIGH"
    }
}


def get_latest_release(repo: str) -> Optional[Dict[str, Any]]:
    """
    Fetch latest release info from GitHub.

    Args:
        repo: Repository in format "owner/repo"

    Returns:
        Dict with release info or None if error
    """
    try:
        import os
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"

        url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return {
                "version": data.get("tag_name", "unknown"),
                "published": data.get("published_at", "")[:10],
                "url": data.get("html_url", ""),
                "body": data.get("body", "")[:500]  # First 500 chars
            }
        elif response.status_code == 404:
            # No releases, try tags
            tags_url = f"https://api.github.com/repos/{repo}/tags"
            tags_response = requests.get(tags_url, headers=headers, timeout=10)
            if tags_response.status_code == 200:
                tags = tags_response.json()
                if tags:
                    return {
                        "version": tags[0].get("name", "unknown"),
                        "published": "N/A",
                        "url": f"https://github.com/{repo}/releases/tag/{tags[0].get('name', '')}",
                        "body": "(Tag, no release notes)"
                    }
        return None
    except Exception as e:
        logger.warning(f"Error fetching release for {repo}: {e}")
        return None


def get_previous_versions() -> Dict[str, str]:
    """Load previous version tracking data."""
    versions_file = Path.home() / ".claude" / "evaluation" / "data" / "framework_versions.json"
    if versions_file.exists():
        try:
            return json.loads(versions_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_current_versions(versions: Dict[str, str]) -> None:
    """Save current version tracking data."""
    versions_file = Path.home() / ".claude" / "evaluation" / "data" / "framework_versions.json"
    versions_file.parent.mkdir(parents=True, exist_ok=True)
    versions_file.write_text(json.dumps(versions, indent=2), encoding="utf-8")


def analyze_frameworks() -> List[Dict[str, Any]]:
    """
    Analyze framework versions and detect updates.

    Returns:
        List of framework analysis results
    """
    logger.info("Analyzing framework versions...")
    previous = get_previous_versions()
    results = []
    current_versions = {}

    for repo, config in FRAMEWORKS.items():
        release = get_latest_release(repo)
        if release:
            prev_version = previous.get(repo, "unknown")
            current_versions[repo] = release["version"]

            is_updated = prev_version != release["version"] and prev_version != "unknown"

            results.append({
                "repo": repo,
                "name": repo.split("/")[1],
                "category": config["category"],
                "priority": config["priority"],
                "current_version": release["version"],
                "previous_version": prev_version,
                "is_updated": is_updated,
                "published": release["published"],
                "url": release["url"],
                "notes_preview": release["body"][:200] if release["body"] else ""
            })

    # Save current versions for next comparison
    save_current_versions(current_versions)

    return results


def generate_benchmark_section() -> str:
    """Generate benchmark monitoring section (placeholder for scraping)."""
    section = "### Benchmarks & Leaderboards\n\n"
    section += "| Benchmark | Status | Action Required |\n"
    section += "|-----------|--------|----------------|\n"

    for key, config in BENCHMARKS.items():
        section += f"| [{config['name']}]({config['url']}) | ⏳ Manual check | Review rankings |\n"

    section += "\n**Note:** Automated benchmark scraping requires browser automation. "
    section += "Visit links above for current rankings.\n"

    return section


def generate_bigtech_section() -> str:
    """Generate BigTech documentation section."""
    section = "### BigTech Documentation Updates\n\n"
    section += "| Provider | Changelog | Priority |\n"
    section += "|----------|-----------|----------|\n"

    for key, config in BIGTECH_DOCS.items():
        icon = "🔴" if config["priority"] == "CRITICAL" else "🟠" if config["priority"] == "HIGH" else "🟡"
        section += f"| {config['name']} | [View]({config['changelog_url']}) | {icon} {config['priority']} |\n"

    section += "\n**Note:** Review changelogs manually for breaking changes and new features.\n"

    return section


def generate_report(framework_results: List[Dict], output_format: str = "markdown") -> str:
    """
    Generate monthly deep-dive report.

    Args:
        framework_results: Framework analysis results
        output_format: Output format (markdown/json)

    Returns:
        Formatted report string
    """
    if output_format == "json":
        return json.dumps({
            "generated": datetime.now().isoformat(),
            "frameworks": framework_results,
            "benchmarks": list(BENCHMARKS.keys()),
            "bigtech_docs": list(BIGTECH_DOCS.keys())
        }, indent=2)

    # Markdown format
    report = f"# Monthly Deep-Dive Report\n\n"
    report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += "---\n\n"

    # Framework Updates Section
    report += "## Framework Version Updates\n\n"

    updated = [f for f in framework_results if f.get("is_updated")]
    if updated:
        report += f"### 🆕 Updated This Month ({len(updated)})\n\n"
        for fw in updated:
            report += f"#### {fw['name']} ({fw['category']})\n"
            report += f"- **Version:** {fw['previous_version']} → **{fw['current_version']}**\n"
            report += f"- **Priority:** {fw['priority']}\n"
            report += f"- **Published:** {fw['published']}\n"
            report += f"- **Release:** [{fw['url']}]({fw['url']})\n"
            if fw.get('notes_preview'):
                report += f"- **Notes:** {fw['notes_preview']}...\n"
            report += "\n"
    else:
        report += "No framework updates detected this month.\n\n"

    # All Frameworks Table
    report += "### All Tracked Frameworks\n\n"
    report += "| Framework | Category | Version | Priority | Last Published |\n"
    report += "|-----------|----------|---------|----------|----------------|\n"

    for fw in sorted(framework_results, key=lambda x: x["priority"], reverse=False):
        icon = "🆕" if fw.get("is_updated") else "✓"
        report += f"| {icon} {fw['name']} | {fw['category']} | {fw['current_version']} | {fw['priority']} | {fw['published']} |\n"

    report += "\n---\n\n"

    # Benchmarks
    report += generate_benchmark_section()
    report += "\n---\n\n"

    # BigTech Docs
    report += generate_bigtech_section()
    report += "\n---\n\n"

    # Action Items
    report += "## Action Items\n\n"

    if updated:
        report += "### High Priority\n"
        for fw in updated:
            if fw["priority"] in ["CRITICAL", "HIGH"]:
                report += f"- [ ] Review {fw['name']} {fw['current_version']} changelog for breaking changes\n"
        report += "\n"

    report += "### Standard\n"
    report += "- [ ] Check LMSYS Arena for model ranking changes\n"
    report += "- [ ] Review SWE-bench for coding agent updates\n"
    report += "- [ ] Check Anthropic docs for Claude/MCP updates\n"
    report += "- [ ] Update tech-stack.md if needed\n\n"

    report += "---\n\n"
    report += f"*Generated by Monthly Deep-Dive Tool v1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    return report


def create_notification_flag(report_path: str, updated_count: int, critical_updates: int) -> None:
    """Create notification flag for session startup."""
    flag_dir = Path.home() / ".claude" / "evaluation" / "data" / "notifications"
    flag_dir.mkdir(parents=True, exist_ok=True)

    flag_file = flag_dir / "monthly_deep_dive.json"
    flag_data = {
        "timestamp": datetime.now().isoformat(),
        "report_path": report_path,
        "updated_count": updated_count,
        "critical_updates": critical_updates,
        "acknowledged": False
    }

    flag_file.write_text(json.dumps(flag_data, indent=2), encoding="utf-8")
    logger.info(f"Notification flag created: {flag_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Monthly Deep-Dive Analysis Tool"
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
        "--quick",
        action="store_true",
        help="Quick mode (skip slow operations)"
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
        # Analyze frameworks
        framework_results = analyze_frameworks()

        # Generate report
        report = generate_report(framework_results, args.format)

        if args.output:
            output_path = Path(args.output).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            logger.info(f"Report saved to {output_path}")

            # Create notification
            updated = [f for f in framework_results if f.get("is_updated")]
            critical = [f for f in updated if f["priority"] in ["CRITICAL", "HIGH"]]
            create_notification_flag(str(output_path), len(updated), len(critical))
        else:
            print(report)

        return 0

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
