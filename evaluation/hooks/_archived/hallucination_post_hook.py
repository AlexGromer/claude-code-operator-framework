#!/usr/bin/env python3
"""
Hallucination Detection Post-Hook (GAP-ANTI-HALL-*)

PostToolUse hook that detects potential hallucinations in responses.
Integrates with hallucination_detector.py for comprehensive analysis.

Trigger: PostToolUse on response-generating tools
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "hallucination_flags.jsonl"

# Hallucination indicators
HALLUCINATION_PATTERNS = [
    # Fabricated citations
    (r'\(\d{4}\)\s+found\s+that', "fabricated_citation"),
    (r'according\s+to\s+[A-Z][a-z]+\s+et\s+al\.', "fabricated_author"),
    (r'study\s+by\s+[A-Z][a-z]+\s+University', "fabricated_institution"),

    # Overly precise statistics
    (r'\b\d{2}\.\d{3,}%\b', "overly_precise_stat"),
    (r'exactly\s+\d+\.\d+', "false_precision"),

    # Unverifiable claims
    (r'always\s+results?\s+in', "absolute_claim"),
    (r'never\s+fails?\s+to', "absolute_claim"),
    (r'100%\s+(guaranteed|certain|effective)', "impossible_guarantee"),

    # Fabricated technical details
    (r'CVE-\d{4}-\d{5,}', "suspicious_cve"),  # CVE numbers typically 4-5 digits
    (r'version\s+\d+\.\d+\.\d+\.\d+\.\d+', "suspicious_version"),  # Too many version parts

    # Hedging that might hide uncertainty
    (r'it\s+is\s+well\s+known\s+that', "appeal_to_common_knowledge"),
    (r'everyone\s+knows\s+that', "appeal_to_common_knowledge"),
    (r'obviously', "false_obviousness"),
]

# Confidence indicators (reduce hallucination score)
CONFIDENCE_PHRASES = [
    "based on my training data",
    "I'm not certain",
    "this needs verification",
    "according to documentation",
    "let me search",
    "I don't have information",
]


def detect_hallucination_patterns(text: str) -> list:
    """Detect patterns that might indicate hallucination."""
    findings = []

    for pattern, category in HALLUCINATION_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get surrounding context
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]

            findings.append({
                "category": category,
                "match": match.group(),
                "context": context.strip(),
                "position": match.start(),
            })

    return findings[:15]  # Limit findings


def check_confidence_indicators(text: str) -> dict:
    """Check for proper confidence/uncertainty expressions."""
    text_lower = text.lower()

    indicators_found = []
    for phrase in CONFIDENCE_PHRASES:
        if phrase in text_lower:
            indicators_found.append(phrase)

    return {
        "has_confidence_markers": len(indicators_found) > 0,
        "markers_found": indicators_found,
        "marker_count": len(indicators_found),
    }


def calculate_risk_score(findings: list, confidence: dict, text_length: int) -> float:
    """Calculate hallucination risk score (0-1)."""
    if text_length < 100:
        return 0.0  # Too short to assess

    # Base score from findings
    base_score = min(len(findings) * 0.15, 0.8)

    # Category weights
    category_weights = {
        "fabricated_citation": 0.25,
        "fabricated_author": 0.25,
        "fabricated_institution": 0.2,
        "overly_precise_stat": 0.15,
        "false_precision": 0.15,
        "absolute_claim": 0.2,
        "impossible_guarantee": 0.25,
        "suspicious_cve": 0.3,
        "suspicious_version": 0.15,
        "appeal_to_common_knowledge": 0.1,
        "false_obviousness": 0.1,
    }

    weighted_score = sum(
        category_weights.get(f["category"], 0.1)
        for f in findings
    )

    # Reduce score if confidence markers present
    if confidence["has_confidence_markers"]:
        weighted_score *= 0.5

    # Normalize
    risk_score = min(base_score + weighted_score, 1.0)

    return round(risk_score, 3)


def log_result(result: dict):
    """Log hallucination detection result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            **result
        }) + "\n")


def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_output = os.environ.get("CLAUDE_TOOL_OUTPUT", "")

    # Skip certain tools
    skip_tools = ["Glob", "Grep", "Bash", "Edit", "Write", "Read"]
    if tool_name in skip_tools:
        sys.exit(0)

    if not tool_output or len(tool_output) < 200:
        sys.exit(0)

    # Detect patterns
    findings = detect_hallucination_patterns(tool_output)
    confidence = check_confidence_indicators(tool_output)
    risk_score = calculate_risk_score(findings, confidence, len(tool_output))

    # Log result
    result = {
        "tool": tool_name,
        "text_length": len(tool_output),
        "findings_count": len(findings),
        "risk_score": risk_score,
        "has_confidence_markers": confidence["has_confidence_markers"],
        "categories": list(set(f["category"] for f in findings)),
    }
    log_result(result)

    # Output warning if high risk
    if risk_score >= 0.5:
        output = {
            "status": "hallucination_risk",
            "risk_score": risk_score,
            "findings": len(findings),
            "categories": result["categories"][:5],
            "recommendation": "Verify claims with authoritative sources",
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
