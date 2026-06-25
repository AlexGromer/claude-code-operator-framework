#!/usr/bin/env python3
"""
Fact Verifier (GAP-SRC-012)

4-level fact verification system for claims validation.
Levels: L1 (Trust), L2 (Verify Once), L3 (Verify Multiple), L4 (Deep Verify).

Usage:
    python fact_verifier.py --verify "Python 3.12 was released in 2023"
    python fact_verifier.py --batch claims.json
    python fact_verifier.py --report
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RESULTS_FILE = DATA_DIR / "fact_verification.jsonl"
KNOWN_FACTS_FILE = DATA_DIR / "known_facts_extended.json"

# Verification levels
VERIFICATION_LEVELS = {
    "L1": {
        "name": "Trust",
        "description": "Well-established facts, no verification needed",
        "sources_required": 0,
        "confidence_threshold": 0.95,
    },
    "L2": {
        "name": "Verify Once",
        "description": "Generally accepted, verify with one authoritative source",
        "sources_required": 1,
        "confidence_threshold": 0.80,
    },
    "L3": {
        "name": "Verify Multiple",
        "description": "Needs cross-reference from multiple sources",
        "sources_required": 2,
        "confidence_threshold": 0.60,
    },
    "L4": {
        "name": "Deep Verify",
        "description": "Controversial or critical, requires thorough verification",
        "sources_required": 3,
        "confidence_threshold": 0.40,
    },
}

# Fact categories and their default verification levels
FACT_CATEGORIES = {
    "mathematical": {"default_level": "L1", "keywords": ["equals", "sum", "product", "formula"]},
    "definitional": {"default_level": "L1", "keywords": ["is defined as", "means", "refers to"]},
    "historical": {"default_level": "L2", "keywords": ["was", "happened", "occurred", "founded"]},
    "technical": {"default_level": "L2", "keywords": ["version", "released", "supports", "API"]},
    "statistical": {"default_level": "L3", "keywords": ["percent", "rate", "average", "median"]},
    "current_events": {"default_level": "L4", "keywords": ["latest", "recent", "new", "announced"]},
    "security": {"default_level": "L4", "keywords": ["CVE", "vulnerability", "exploit", "patch"]},
    "opinion": {"default_level": "L4", "keywords": ["best", "worst", "should", "recommend"]},
}

# Trusted fact patterns (L1)
TRUSTED_PATTERNS = [
    r"Python is a programming language",
    r"HTTP status code \d{3}",
    r"\d+ \+ \d+ = \d+",
    r"\d+ \* \d+ = \d+",
    r"TCP port \d+",
    r"RFC \d+",
]


@dataclass
class VerificationResult:
    """Result of fact verification."""
    claim: str
    category: str
    level: str
    level_name: str
    confidence: float
    verified: bool
    sources_checked: int
    sources_confirmed: int
    conflicts: List[str]
    recommendation: str
    details: Dict
    timestamp: str


def classify_claim(claim: str) -> Tuple[str, str]:
    """Classify claim into category and default verification level."""
    claim_lower = claim.lower()

    for category, config in FACT_CATEGORIES.items():
        for keyword in config["keywords"]:
            if keyword in claim_lower:
                return category, config["default_level"]

    return "general", "L2"


def check_trusted_patterns(claim: str) -> bool:
    """Check if claim matches trusted patterns."""
    for pattern in TRUSTED_PATTERNS:
        if re.search(pattern, claim, re.IGNORECASE):
            return True
    return False


def load_known_facts() -> Dict:
    """Load known facts database."""
    if KNOWN_FACTS_FILE.exists():
        return json.loads(KNOWN_FACTS_FILE.read_text())
    return {"facts": [], "last_updated": None}


def check_known_facts(claim: str, known_facts: Dict) -> Tuple[bool, float, List[str]]:
    """Check claim against known facts database."""
    claim_lower = claim.lower()
    matches = []
    confidence = 0.0

    for fact in known_facts.get("facts", []):
        fact_text = fact.get("fact", "").lower()
        if fact_text in claim_lower or claim_lower in fact_text:
            matches.append(fact.get("source", "known_facts"))
            confidence = max(confidence, fact.get("confidence", 0.8))

    return len(matches) > 0, confidence, matches


def extract_verifiable_parts(claim: str) -> List[Dict]:
    """Extract verifiable parts from a claim."""
    parts = []

    # Extract numbers
    numbers = re.findall(r'\b\d+(?:\.\d+)?\b', claim)
    for num in numbers:
        parts.append({"type": "number", "value": num})

    # Extract dates
    dates = re.findall(r'\b(19|20)\d{2}\b', claim)
    for date in dates:
        parts.append({"type": "year", "value": date})

    # Extract version numbers
    versions = re.findall(r'\b\d+\.\d+(?:\.\d+)?\b', claim)
    for ver in versions:
        parts.append({"type": "version", "value": ver})

    # Extract proper nouns (capitalized words)
    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim)
    for noun in proper_nouns:
        parts.append({"type": "entity", "value": noun})

    return parts


def assess_confidence(claim: str, category: str, level: str) -> float:
    """Assess confidence in claim verification."""
    base_confidence = VERIFICATION_LEVELS[level]["confidence_threshold"]

    # Adjust based on specificity
    verifiable_parts = extract_verifiable_parts(claim)
    if len(verifiable_parts) > 3:
        base_confidence *= 0.9  # More specific = harder to verify fully

    # Adjust based on category
    if category in ["mathematical", "definitional"]:
        base_confidence = min(1.0, base_confidence * 1.2)
    elif category in ["current_events", "security"]:
        base_confidence *= 0.8

    return min(1.0, base_confidence)


def verify_claim(
    claim: str,
    level_override: str = None,
    sources: List[str] = None
) -> VerificationResult:
    """Verify a claim."""
    # Classify claim
    category, default_level = classify_claim(claim)
    level = level_override or default_level

    # Check trusted patterns first
    if check_trusted_patterns(claim):
        level = "L1"

    # Load known facts
    known_facts = load_known_facts()
    found_in_known, known_confidence, known_sources = check_known_facts(claim, known_facts)

    # Extract verifiable parts
    verifiable_parts = extract_verifiable_parts(claim)

    # Calculate confidence
    confidence = assess_confidence(claim, category, level)

    # Adjust confidence based on known facts match
    if found_in_known:
        confidence = max(confidence, known_confidence)
        level = "L1" if known_confidence > 0.9 else level

    # Check if verified
    level_config = VERIFICATION_LEVELS[level]
    sources_checked = len(known_sources) + (len(sources) if sources else 0)
    verified = (
        sources_checked >= level_config["sources_required"] and
        confidence >= level_config["confidence_threshold"]
    )

    # Generate recommendation
    if verified:
        recommendation = "Claim verified - safe to use"
    elif level == "L4":
        recommendation = "High-risk claim - manual verification required"
    elif sources_checked < level_config["sources_required"]:
        needed = level_config["sources_required"] - sources_checked
        recommendation = f"Need {needed} more source(s) to verify"
    else:
        recommendation = "Confidence below threshold - use with caution"

    return VerificationResult(
        claim=claim,
        category=category,
        level=level,
        level_name=level_config["name"],
        confidence=round(confidence, 3),
        verified=verified,
        sources_checked=sources_checked,
        sources_confirmed=len(known_sources),
        conflicts=[],
        recommendation=recommendation,
        details={
            "verifiable_parts": verifiable_parts,
            "known_facts_match": found_in_known,
            "known_sources": known_sources,
        },
        timestamp=datetime.now().isoformat(),
    )


def batch_verify(claims: List[str]) -> List[VerificationResult]:
    """Verify multiple claims."""
    return [verify_claim(claim) for claim in claims]


def generate_report(results: List[VerificationResult]) -> Dict:
    """Generate verification report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_claims": len(results),
        "verified": sum(1 for r in results if r.verified),
        "unverified": sum(1 for r in results if not r.verified),
        "by_level": {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
        "by_category": {},
        "average_confidence": 0,
        "high_risk_claims": [],
    }

    for result in results:
        report["by_level"][result.level] += 1

        if result.category not in report["by_category"]:
            report["by_category"][result.category] = 0
        report["by_category"][result.category] += 1

        report["average_confidence"] += result.confidence

        if result.level == "L4" and not result.verified:
            report["high_risk_claims"].append(result.claim[:100])

    if results:
        report["average_confidence"] = round(report["average_confidence"] / len(results), 3)

    return report


def save_result(result: VerificationResult):
    """Save verification result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(asdict(result)) + "\n")


def print_result(result: VerificationResult):
    """Print verification result."""
    print("\n" + "="*60)
    print("FACT VERIFICATION")
    print("="*60)

    status = "✅ VERIFIED" if result.verified else "⚠️ UNVERIFIED"
    level_icons = {"L1": "🟢", "L2": "🟡", "L3": "🟠", "L4": "🔴"}

    print(f"\nClaim: {result.claim}")
    print(f"\n{status}")
    print(f"{level_icons.get(result.level, '⚪')} Level: {result.level} ({result.level_name})")
    print(f"Category: {result.category}")
    print(f"Confidence: {result.confidence:.0%}")

    print(f"\nSources: {result.sources_checked} checked, {result.sources_confirmed} confirmed")

    if result.details.get("verifiable_parts"):
        print(f"\nVerifiable parts:")
        for part in result.details["verifiable_parts"][:5]:
            print(f"  • {part['type']}: {part['value']}")

    print(f"\nRecommendation: {result.recommendation}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Fact Verifier")
    parser.add_argument("--verify", "-v", help="Verify a single claim")
    parser.add_argument("--batch", "-b", help="Batch verify from JSON file")
    parser.add_argument("--level", "-l", choices=["L1", "L2", "L3", "L4"], help="Override verification level")
    parser.add_argument("--report", "-r", action="store_true", help="Generate report from history")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save result")

    args = parser.parse_args()

    if args.verify:
        result = verify_claim(args.verify, args.level)

        if args.save:
            save_result(result)

        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            print_result(result)

        return 0 if result.verified else 1

    if args.batch:
        claims = json.loads(Path(args.batch).read_text())
        results = batch_verify(claims)

        for result in results:
            if args.save:
                save_result(result)

        if args.json:
            print(json.dumps([asdict(r) for r in results], indent=2))
        else:
            verified = sum(1 for r in results if r.verified)
            print(f"\nVerified: {verified}/{len(results)}")

        return 0

    if args.report:
        if RESULTS_FILE.exists():
            results = []
            with open(RESULTS_FILE) as f:
                for line in f:
                    if line.strip():
                        results.append(VerificationResult(**json.loads(line)))

            report = generate_report(results)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(f"\nTotal claims: {report['total_claims']}")
                print(f"Verified: {report['verified']}")
                print(f"Average confidence: {report['average_confidence']:.0%}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
