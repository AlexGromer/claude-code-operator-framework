#!/usr/bin/env python3
"""
Source Quality Hook (GAP-SRC-002)

PostToolUse hook that evaluates source quality for WebSearch/WebFetch results.
Automatically scores sources and flags low-quality content.

Trigger: PostToolUse on WebSearch, WebFetch
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "source_quality_alerts.jsonl"

# Quick domain scoring
TIER1_DOMAINS = [
    "arxiv.org", "acm.org", "ieee.org", "anthropic.com", "openai.com",
    "docs.python.org", "developer.mozilla.org", "github.com/anthropics",
]

TIER2_DOMAINS = [
    "github.com", "huggingface.co", "pytorch.org", "kubernetes.io",
    "docker.com", "terraform.io", "langchain.com",
]

TIER3_DOMAINS = [
    "stackoverflow.com", "medium.com", "dev.to", "reddit.com",
]

# Warning patterns in content
WARNING_PATTERNS = [
    "outdated", "deprecated", "no longer supported", "this article is old",
    "last updated 20", "archived", "legacy",
]


def get_domain_tier(url: str) -> tuple:
    """Get domain tier and score."""
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return "TIER_4", 0.4

    for d in TIER1_DOMAINS:
        if d in domain or d in url:
            return "TIER_1", 1.0

    for d in TIER2_DOMAINS:
        if d in domain or d in url:
            return "TIER_2", 0.8

    for d in TIER3_DOMAINS:
        if d in domain or d in url:
            return "TIER_3", 0.6

    return "TIER_4", 0.4


def check_content_warnings(content: str) -> list:
    """Check content for warning patterns."""
    warnings = []
    content_lower = content.lower()

    for pattern in WARNING_PATTERNS:
        if pattern in content_lower:
            warnings.append(pattern)

    return warnings


def log_result(result: dict):
    """Log quality assessment."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

    # Only process WebSearch and WebFetch
    if tool_name not in ["WebSearch", "WebFetch"]:
        sys.exit(0)

    # Extract URLs from output
    urls_found = []
    try:
        # Try to parse as JSON
        output_data = json.loads(tool_output)
        if isinstance(output_data, dict):
            if "url" in output_data:
                urls_found.append(output_data["url"])
            if "results" in output_data:
                for r in output_data.get("results", []):
                    if isinstance(r, dict) and "url" in r:
                        urls_found.append(r["url"])
    except Exception:
        # Extract URLs with regex
        import re
        urls_found = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', tool_output)

    if not urls_found:
        sys.exit(0)

    # Assess each URL
    low_quality = []
    assessments = []

    for url in urls_found[:10]:  # Limit to first 10
        tier, score = get_domain_tier(url)
        assessment = {
            "url": url[:100],
            "tier": tier,
            "score": score,
        }

        if score < 0.6:
            low_quality.append(url)

        assessments.append(assessment)

    # Check content for warnings
    content_warnings = check_content_warnings(tool_output)

    # Log results
    result = {
        "tool": tool_name,
        "urls_assessed": len(assessments),
        "low_quality_count": len(low_quality),
        "content_warnings": content_warnings,
        "assessments": assessments,
    }
    log_result(result)

    # Output warnings if needed
    if low_quality or content_warnings:
        output = {
            "status": "quality_alert",
            "low_quality_sources": len(low_quality),
            "content_warnings": content_warnings[:3],
            "recommendation": "Verify with higher-tier sources" if low_quality else "Content may be outdated",
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
