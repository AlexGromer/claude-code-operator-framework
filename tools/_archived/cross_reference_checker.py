#!/usr/bin/env python3
"""
Cross-Reference Checker (GAP-SRC-013)

Cross-reference claims across multiple sources:
- Verify claims with multiple sources
- Find contradictions between sources
- Confidence scoring based on agreement
- Verification level assignment (L1-L4)

Usage:
    python cross_reference_checker.py --check "claim" --sources url1 url2 url3
    python cross_reference_checker.py --report
    python cross_reference_checker.py --conflicts
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Import source registry
sys.path.insert(0, str(Path(__file__).parent))
from source_registry import (
    load_registry, lookup_source, normalize_url, TIERS
)

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
VERIFICATION_LOG = DATA_DIR / "cross_reference_checks.jsonl"


@dataclass
class VerificationResult:
    """Cross-reference verification result."""
    claim: str
    sources: List[str]
    verification_level: str  # L0, L1, L2, L3, L4
    confidence: float  # 0.0 - 1.0
    agreement_level: str  # unanimous, majority, split, contradiction
    contradictions: List[Dict]
    verified_at: str
    details: Dict


class CrossReferenceChecker:
    """Cross-reference checker for claims across sources."""

    def __init__(self):
        """Initialize checker."""
        self.registry = load_registry()

    def get_source_tier_weight(self, url: str) -> float:
        """
        Get source tier weight for confidence calculation.

        TIER_1: 1.0 (highest weight)
        TIER_2: 0.8
        TIER_3: 0.6
        TIER_4: 0.4
        """
        source = lookup_source(url)

        if source:
            tier = source.get("tier", "TIER_4")
            return TIERS.get(tier, {}).get("quality_score", 0.4)

        # Unknown source - default to TIER_4 weight
        return 0.4

    def calculate_confidence(self, sources: List[str], agreement: str) -> float:
        """
        Calculate confidence score based on:
        - Number of sources
        - Source tier weights
        - Agreement level
        """
        if not sources:
            return 0.0

        # Base confidence from source count
        source_count_factor = min(len(sources) / 3.0, 1.0)  # Max at 3+ sources

        # Average tier weight
        tier_weights = [self.get_source_tier_weight(url) for url in sources]
        avg_tier_weight = sum(tier_weights) / len(tier_weights)

        # Agreement factor
        agreement_factors = {
            "unanimous": 1.0,
            "majority": 0.8,
            "split": 0.5,
            "contradiction": 0.2,
        }
        agreement_factor = agreement_factors.get(agreement, 0.5)

        # Combined confidence
        confidence = source_count_factor * avg_tier_weight * agreement_factor

        return round(confidence, 3)

    def determine_verification_level(self, sources: List[str], confidence: float) -> str:
        """
        Determine verification level (L0-L4).

        L0: No sources (0 sources)
        L1: Single source (1 source, low confidence)
        L2: Cross-referenced (2+ sources, medium confidence)
        L3: Verified by official docs (TIER_1 source involved, high confidence)
        L4: Tested/validated locally (not determined here, requires manual flag)
        """
        if len(sources) == 0:
            return "L0"

        if len(sources) == 1:
            # Check if single source is TIER_1
            tier_weight = self.get_source_tier_weight(sources[0])
            if tier_weight >= 0.9:  # TIER_1
                return "L3"  # Official doc verification
            return "L1"  # Single source

        # 2+ sources
        # Check if any TIER_1 sources
        has_tier1 = any(self.get_source_tier_weight(url) >= 0.9 for url in sources)

        if has_tier1 and confidence >= 0.7:
            return "L3"  # Verified by official documentation
        elif confidence >= 0.5:
            return "L2"  # Cross-referenced
        else:
            return "L1"  # Low confidence despite multiple sources

    def detect_contradictions(self, sources: List[Dict]) -> List[Dict]:
        """
        Detect contradictions between source claims.

        Args:
            sources: List of dicts with {"url": str, "claim": str}

        Returns:
            List of contradictions
        """
        contradictions = []

        # Simple contradiction detection based on negation keywords
        negation_patterns = [
            ("is", "is not"),
            ("does", "does not"),
            ("can", "cannot"),
            ("will", "will not"),
            ("fast", "slow"),
            ("good", "bad"),
            ("secure", "insecure"),
            ("stable", "unstable"),
        ]

        for i, source1 in enumerate(sources):
            for source2 in sources[i+1:]:
                claim1 = source1.get("claim", "").lower()
                claim2 = source2.get("claim", "").lower()

                # Check for negation patterns
                for pos, neg in negation_patterns:
                    if (pos in claim1 and neg in claim2) or \
                       (neg in claim1 and pos in claim2):
                        contradictions.append({
                            "source1": source1["url"],
                            "source2": source2["url"],
                            "claim1": source1.get("claim"),
                            "claim2": source2.get("claim"),
                            "conflict": f"Contradictory terms: {pos} vs {neg}",
                        })

        return contradictions

    def determine_agreement_level(
        self,
        sources: List[str],
        contradictions: List[Dict]
    ) -> str:
        """
        Determine agreement level among sources.

        - unanimous: All sources agree (no contradictions)
        - majority: Most sources agree (few contradictions)
        - split: Sources evenly split
        - contradiction: Direct contradictions found
        """
        if not sources:
            return "none"

        if len(contradictions) > 0:
            # Calculate contradiction ratio
            total_pairs = len(sources) * (len(sources) - 1) / 2
            contradiction_ratio = len(contradictions) / max(total_pairs, 1)

            if contradiction_ratio > 0.5:
                return "contradiction"
            elif contradiction_ratio > 0.2:
                return "split"
            else:
                return "majority"

        # No contradictions detected
        if len(sources) == 1:
            return "single"

        return "unanimous"

    def check(
        self,
        claim: str,
        sources: List[str],
        source_claims: List[Dict] = None
    ) -> VerificationResult:
        """
        Check claim across multiple sources.

        Args:
            claim: Claim to verify
            sources: List of source URLs
            source_claims: Optional list of {"url": str, "claim": str} for contradiction detection

        Returns:
            VerificationResult
        """
        # Normalize source URLs
        normalized_sources = [normalize_url(url) for url in sources]

        # Detect contradictions if source_claims provided
        contradictions = []
        if source_claims:
            contradictions = self.detect_contradictions(source_claims)

        # Determine agreement level
        agreement = self.determine_agreement_level(normalized_sources, contradictions)

        # Calculate confidence
        confidence = self.calculate_confidence(normalized_sources, agreement)

        # Determine verification level
        verification_level = self.determine_verification_level(
            normalized_sources,
            confidence
        )

        # Get source details
        source_details = []
        for url in normalized_sources:
            source = lookup_source(url)
            if source:
                source_details.append({
                    "url": url,
                    "tier": source.get("tier", "TIER_4"),
                    "quality_score": source.get("quality_score", 0.0),
                })
            else:
                source_details.append({
                    "url": url,
                    "tier": "TIER_4",
                    "quality_score": 0.4,
                })

        result = VerificationResult(
            claim=claim,
            sources=normalized_sources,
            verification_level=verification_level,
            confidence=confidence,
            agreement_level=agreement,
            contradictions=contradictions,
            verified_at=datetime.now().isoformat(),
            details={
                "source_count": len(normalized_sources),
                "source_details": source_details,
                "tier_weights": [self.get_source_tier_weight(url) for url in normalized_sources],
            }
        )

        # Log verification
        self._log_verification(result)

        return result

    def _log_verification(self, result: VerificationResult):
        """Log verification to file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(VERIFICATION_LOG, "a") as f:
            f.write(json.dumps(asdict(result)) + "\n")

    def get_source_modules(self, source_url: str) -> List[str]:
        """Get modules that reference this source (stub for linker integration)."""
        # This will be implemented via source_module_linker integration
        return []


def check_claim(claim: str, sources: List[str]) -> Dict:
    """
    Check claim across sources (convenience function).

    Args:
        claim: Claim to verify
        sources: List of source URLs

    Returns:
        Verification result dict
    """
    checker = CrossReferenceChecker()
    result = checker.check(claim, sources)
    return asdict(result)


def find_contradictions(source_claims: List[Dict]) -> List[Dict]:
    """
    Find contradictions between source claims.

    Args:
        source_claims: List of {"url": str, "claim": str}

    Returns:
        List of contradictions
    """
    checker = CrossReferenceChecker()
    return checker.detect_contradictions(source_claims)


def print_verification(result: Dict):
    """Print verification result in formatted output."""
    print("\n" + "="*70)
    print("CROSS-REFERENCE VERIFICATION")
    print("="*70)

    print(f"\nClaim: {result['claim']}")
    print(f"\nSources ({len(result['sources'])}):")
    for i, source in enumerate(result['sources'], 1):
        print(f"  {i}. {source}")

    print(f"\nVerification Level: {result['verification_level']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Agreement: {result['agreement_level']}")

    if result.get("contradictions"):
        print(f"\n⚠️  Contradictions Found ({len(result['contradictions'])}):")
        for i, contradiction in enumerate(result["contradictions"], 1):
            print(f"\n  {i}. Source 1: {contradiction['source1']}")
            print(f"     Claim: {contradiction.get('claim1', 'N/A')}")
            print(f"     Source 2: {contradiction['source2']}")
            print(f"     Claim: {contradiction.get('claim2', 'N/A')}")
            print(f"     Conflict: {contradiction['conflict']}")

    print(f"\nVerified At: {result['verified_at']}")
    print("="*70 + "\n")


def generate_report() -> Dict:
    """Generate cross-reference report."""
    if not VERIFICATION_LOG.exists():
        return {"error": "No verifications found"}

    verifications = []
    with open(VERIFICATION_LOG, "r") as f:
        for line in f:
            verifications.append(json.loads(line))

    report = {
        "total_verifications": len(verifications),
        "by_level": {},
        "by_agreement": {},
        "avg_confidence": 0.0,
        "total_contradictions": 0,
        "recent_verifications": verifications[-10:],
    }

    # Count by verification level
    for level in ["L0", "L1", "L2", "L3", "L4"]:
        count = len([v for v in verifications if v.get("verification_level") == level])
        report["by_level"][level] = count

    # Count by agreement
    for agreement in ["unanimous", "majority", "split", "contradiction", "single"]:
        count = len([v for v in verifications if v.get("agreement_level") == agreement])
        report["by_agreement"][agreement] = count

    # Average confidence
    if verifications:
        report["avg_confidence"] = round(
            sum(v["confidence"] for v in verifications) / len(verifications), 3
        )

    # Total contradictions
    report["total_contradictions"] = sum(
        len(v.get("contradictions", [])) for v in verifications
    )

    return report


def get_conflicts() -> List[Dict]:
    """Get all verifications with contradictions."""
    if not VERIFICATION_LOG.exists():
        return []

    conflicts = []
    with open(VERIFICATION_LOG, "r") as f:
        for line in f:
            verification = json.loads(line)
            if verification.get("contradictions"):
                conflicts.append(verification)

    return conflicts


def main():
    parser = argparse.ArgumentParser(description="Cross-Reference Checker")
    parser.add_argument("--check", help="Claim to verify")
    parser.add_argument("--sources", nargs="+", help="Source URLs (space-separated)")
    parser.add_argument("--report", action="store_true", help="Generate verification report")
    parser.add_argument("--conflicts", action="store_true", help="Show all conflicts")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.check:
        if not args.sources:
            print("❌ Error: --sources required with --check", file=sys.stderr)
            return 1

        result = check_claim(args.check, args.sources)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_verification(result)

        return 0

    if args.report:
        report = generate_report()

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("\n" + "="*60)
            print("CROSS-REFERENCE VERIFICATION REPORT")
            print("="*60)

            print(f"\nTotal Verifications: {report['total_verifications']}")
            print(f"Average Confidence: {report['avg_confidence']:.1%}")
            print(f"Total Contradictions: {report['total_contradictions']}")

            print("\nBy Verification Level:")
            for level, count in report.get("by_level", {}).items():
                print(f"  {level}: {count}")

            print("\nBy Agreement:")
            for agreement, count in report.get("by_agreement", {}).items():
                print(f"  {agreement}: {count}")

            print("\n" + "="*60 + "\n")

        return 0

    if args.conflicts:
        conflicts = get_conflicts()

        if args.json:
            print(json.dumps(conflicts, indent=2))
        else:
            print(f"\nFound {len(conflicts)} verifications with contradictions:\n")
            for conflict in conflicts:
                print(f"Claim: {conflict['claim']}")
                print(f"Contradictions: {len(conflict['contradictions'])}")
                print(f"Sources: {len(conflict['sources'])}")
                print(f"Confidence: {conflict['confidence']:.1%}\n")

        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
