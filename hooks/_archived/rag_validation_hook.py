#!/usr/bin/env python3
"""
RAG Validation Hook (GAP-RAG-*)

PostToolUse hook that validates RAG retrieval quality.
Checks relevance, recency, and completeness of retrieved context.

Trigger: PostToolUse on Read, Grep, Glob (context retrieval)
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "rag_validation.jsonl"

# Quality thresholds
QUALITY_THRESHOLDS = {
    "min_relevance_score": 0.5,
    "max_context_age_days": 365,
    "min_content_length": 50,
    "max_content_length": 50000,
}

# Relevance indicators (positive)
RELEVANCE_PATTERNS = [
    r'\bdef\s+\w+\s*\(',      # Function definitions
    r'\bclass\s+\w+',          # Class definitions
    r'\bimport\s+',            # Import statements
    r'\b(TODO|FIXME|NOTE)\b',  # Code markers
    r'#.*configuration',       # Config comments
    r'---\s*\n',               # YAML frontmatter
]

# Quality issues (negative)
QUALITY_ISSUES = [
    (r'^\s*$', "empty_content"),
    (r'binary\s+file', "binary_file"),
    (r'permission\s+denied', "access_error"),
    (r'no\s+such\s+file', "file_not_found"),
    (r'(\x00|\xff)', "binary_data"),
]


def calculate_relevance_score(content: str, query_context: str = "") -> float:
    """Calculate content relevance score (0-1)."""
    if not content or len(content) < QUALITY_THRESHOLDS["min_content_length"]:
        return 0.0

    score = 0.3  # Base score for non-empty content

    # Check for code patterns
    code_patterns_found = 0
    for pattern in RELEVANCE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            code_patterns_found += 1

    score += min(code_patterns_found * 0.1, 0.4)

    # Penalize very long content (likely noise)
    if len(content) > QUALITY_THRESHOLDS["max_content_length"]:
        score *= 0.7

    # Check content structure
    lines = content.split('\n')
    if len(lines) > 5:  # Multi-line is good
        score += 0.1

    # Check for documentation
    if '"""' in content or "'''" in content or '/**' in content:
        score += 0.1

    return min(score, 1.0)


def detect_quality_issues(content: str) -> list:
    """Detect quality issues in retrieved content."""
    issues = []

    for pattern, issue_type in QUALITY_ISSUES:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(issue_type)

    # Check for truncation
    if content.endswith('...') or '... truncated' in content.lower():
        issues.append("truncated")

    # Check for error messages in content
    if 'error' in content.lower()[:100]:
        issues.append("error_in_content")

    return list(set(issues))


def assess_retrieval_quality(tool_name: str, tool_output: str) -> dict:
    """Assess overall retrieval quality."""
    assessment = {
        "tool": tool_name,
        "content_length": len(tool_output),
        "relevance_score": 0.0,
        "quality_issues": [],
        "recommendations": [],
    }

    # Calculate relevance
    assessment["relevance_score"] = round(
        calculate_relevance_score(tool_output), 3
    )

    # Detect issues
    assessment["quality_issues"] = detect_quality_issues(tool_output)

    # Generate recommendations
    if assessment["relevance_score"] < QUALITY_THRESHOLDS["min_relevance_score"]:
        assessment["recommendations"].append("Consider refining search query")

    if "truncated" in assessment["quality_issues"]:
        assessment["recommendations"].append("Retrieve full content if needed")

    if assessment["content_length"] < QUALITY_THRESHOLDS["min_content_length"]:
        assessment["recommendations"].append("Content too short, may need more context")

    if assessment["content_length"] > QUALITY_THRESHOLDS["max_content_length"]:
        assessment["recommendations"].append("Content very long, consider filtering")

    return assessment


def log_validation(result: dict):
    """Log RAG validation result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

    # Only process RAG-related tools
    rag_tools = ["Read", "Grep", "Glob"]
    if tool_name not in rag_tools:
        sys.exit(0)

    if not tool_output:
        sys.exit(0)

    # Assess quality
    assessment = assess_retrieval_quality(tool_name, tool_output)

    # Log result
    log_validation(assessment)

    # Output warning if quality issues
    if (assessment["relevance_score"] < QUALITY_THRESHOLDS["min_relevance_score"]
            or assessment["quality_issues"]):
        output = {
            "status": "rag_quality_alert",
            "relevance_score": assessment["relevance_score"],
            "issues": assessment["quality_issues"][:3],
            "recommendations": assessment["recommendations"][:2],
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
