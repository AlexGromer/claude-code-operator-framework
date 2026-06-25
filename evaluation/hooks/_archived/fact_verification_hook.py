#!/usr/bin/env python3
"""
Fact Verification Hook (GAP-SRC-012)

PostToolUse hook that flags claims needing verification.
Integrates with fact_verifier.py for claim validation.

Trigger: PostToolUse on all response-generating tools
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "fact_verification_flags.jsonl"

# Patterns that indicate verifiable claims
CLAIM_PATTERNS = [
    r'\b(in|since|as of)\s+\d{4}\b',                    # Year references
    r'\b\d+(\.\d+)?%\b',                                # Percentages
    r'\b(version|v)\s*\d+\.\d+',                        # Version numbers
    r'\b(CVE-\d{4}-\d+)\b',                             # CVE numbers
    r'\b(released|launched|announced)\s+',              # Event claims
    r'\b(study|research|paper)\s+(shows?|found|demonstrates?)', # Research claims
    r'\b(always|never|all|none|every)\b',               # Absolute claims
    r'\b(best|worst|fastest|slowest|most|least)\b',     # Superlatives
]

# High-risk claim categories
HIGH_RISK_PATTERNS = [
    (r'\bCVE-\d{4}-\d+\b', "security_advisory"),
    (r'\b(vulnerability|exploit|attack)\b', "security_claim"),
    (r'\b\d+(\.\d+)?%\s+(increase|decrease|growth)', "statistical_claim"),
    (r'\b(always|never|guaranteed)\b', "absolute_claim"),
]


def extract_claims(text: str) -> list:
    """Extract potential claims from text."""
    claims = []

    for pattern in CLAIM_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get surrounding context (50 chars before and after)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]

            claims.append({
                "match": match.group(),
                "context": context.strip(),
                "position": match.start(),
            })

    return claims[:20]  # Limit to 20 claims


def assess_risk(text: str) -> list:
    """Assess high-risk claims."""
    risks = []

    for pattern, category in HIGH_RISK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            risks.append(category)

    return list(set(risks))


def log_flags(result: dict):
    """Log flagged claims."""
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
    skip_tools = ["Glob", "Grep", "Bash", "Edit", "Write"]
    if tool_name in skip_tools:
        sys.exit(0)

    if not tool_output or len(tool_output) < 100:
        sys.exit(0)

    # Extract claims
    claims = extract_claims(tool_output)
    risks = assess_risk(tool_output)

    if not claims and not risks:
        sys.exit(0)

    # Log findings
    result = {
        "tool": tool_name,
        "claims_found": len(claims),
        "high_risk_categories": risks,
        "sample_claims": [c["context"][:100] for c in claims[:5]],
    }
    log_flags(result)

    # Output warning if high-risk
    if risks:
        output = {
            "status": "verification_needed",
            "high_risk_categories": risks,
            "claims_detected": len(claims),
            "recommendation": "Verify these claims with authoritative sources",
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
