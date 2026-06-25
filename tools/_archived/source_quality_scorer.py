#!/usr/bin/env python3
"""
Source Quality Scorer (GAP-SRC-002)

Evaluates quality of information sources using 4-dimension rubric.
Scores: Authority (30%), Currency (25%), Accuracy (25%), Relevance (20%).

Usage:
    python source_quality_scorer.py --evaluate "https://example.com"
    python source_quality_scorer.py --batch sources.json
    python source_quality_scorer.py --report
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RESULTS_FILE = DATA_DIR / "source_quality.jsonl"
REGISTRY_FILE = DATA_DIR / "source_registry.json"

# Quality dimensions with weights
QUALITY_DIMENSIONS = {
    "authority": {
        "weight": 0.30,
        "description": "Credibility and expertise of source",
        "factors": ["domain_reputation", "author_credentials", "peer_review", "citations"],
    },
    "currency": {
        "weight": 0.25,
        "description": "Timeliness and update frequency",
        "factors": ["last_updated", "update_frequency", "version_tracking", "changelog"],
    },
    "accuracy": {
        "weight": 0.25,
        "description": "Correctness and verifiability",
        "factors": ["fact_checkable", "references_provided", "error_rate", "corrections"],
    },
    "relevance": {
        "weight": 0.20,
        "description": "Applicability to our use cases",
        "factors": ["topic_match", "scope_alignment", "actionable", "cli_applicable"],
    },
}

# Domain reputation tiers
DOMAIN_TIERS = {
    "tier1": {
        "score": 1.0,
        "domains": [
            "arxiv.org", "acm.org", "ieee.org", "nature.com", "science.org",
            "anthropic.com", "openai.com", "deepmind.com", "google.ai",
            "github.com/anthropics", "github.com/openai", "github.com/google",
            "docs.anthropic.com", "platform.openai.com",
        ],
    },
    "tier2": {
        "score": 0.8,
        "domains": [
            "huggingface.co", "paperswithcode.com", "github.com",
            "pytorch.org", "tensorflow.org", "langchain.com",
            "docs.python.org", "developer.mozilla.org",
            "kubernetes.io", "docker.com", "terraform.io",
        ],
    },
    "tier3": {
        "score": 0.6,
        "domains": [
            "medium.com", "dev.to", "towardsdatascience.com",
            "stackoverflow.com", "reddit.com/r/MachineLearning",
            "news.ycombinator.com", "techcrunch.com",
        ],
    },
    "tier4": {
        "score": 0.4,
        "domains": [
            "wikipedia.org", "blogs", "personal sites",
        ],
    },
}


@dataclass
class SourceScore:
    """Quality score for a source."""
    url: str
    domain: str
    authority: float
    currency: float
    accuracy: float
    relevance: float
    total_score: float
    tier: str
    recommendation: str
    details: Dict
    timestamp: str


def get_domain_tier(url: str) -> Tuple[str, float]:
    """Determine domain tier and base score."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    for tier, config in DOMAIN_TIERS.items():
        for known in config["domains"]:
            if known in domain or known in url:
                return tier, config["score"]

    return "tier4", 0.4


def score_authority(url: str, metadata: Dict = None) -> Tuple[float, Dict]:
    """Score source authority (0-1)."""
    details = {}
    scores = []

    # Domain reputation
    tier, domain_score = get_domain_tier(url)
    details["domain_tier"] = tier
    details["domain_score"] = domain_score
    scores.append(domain_score)

    # Author credentials (if provided)
    if metadata and metadata.get("author"):
        author = metadata["author"]
        if any(cred in author.lower() for cred in ["phd", "dr.", "professor", "researcher"]):
            details["author_credentialed"] = True
            scores.append(1.0)
        else:
            details["author_credentialed"] = False
            scores.append(0.5)

    # Peer review indicator
    if metadata and metadata.get("peer_reviewed"):
        details["peer_reviewed"] = True
        scores.append(1.0)
    elif "arxiv" in url or "acm.org" in url or "ieee.org" in url:
        details["peer_reviewed"] = True
        scores.append(0.9)
    else:
        details["peer_reviewed"] = False
        scores.append(0.3)

    # Citations (if available)
    if metadata and metadata.get("citations", 0) > 0:
        citations = metadata["citations"]
        citation_score = min(1.0, citations / 100)
        details["citations"] = citations
        scores.append(citation_score)

    return sum(scores) / len(scores), details


def score_currency(url: str, metadata: Dict = None) -> Tuple[float, Dict]:
    """Score source currency/timeliness (0-1)."""
    details = {}
    scores = []

    now = datetime.now()

    # Last updated
    if metadata and metadata.get("last_updated"):
        try:
            updated = datetime.fromisoformat(metadata["last_updated"])
            age_days = (now - updated).days

            if age_days <= 30:
                score = 1.0
            elif age_days <= 90:
                score = 0.8
            elif age_days <= 180:
                score = 0.6
            elif age_days <= 365:
                score = 0.4
            else:
                score = 0.2

            details["last_updated"] = metadata["last_updated"]
            details["age_days"] = age_days
            scores.append(score)
        except Exception:
            scores.append(0.5)
    else:
        # Default based on domain type
        if any(d in url for d in ["docs.", "documentation", "api"]):
            scores.append(0.7)  # Docs usually maintained
        else:
            scores.append(0.5)

    # Update frequency
    if metadata and metadata.get("update_frequency"):
        freq = metadata["update_frequency"].lower()
        if freq in ["daily", "weekly"]:
            scores.append(1.0)
        elif freq in ["monthly", "bi-weekly"]:
            scores.append(0.8)
        elif freq in ["quarterly"]:
            scores.append(0.6)
        else:
            scores.append(0.4)
        details["update_frequency"] = freq

    # Version tracking
    if metadata and metadata.get("version"):
        details["version"] = metadata["version"]
        scores.append(0.8)

    return sum(scores) / len(scores) if scores else 0.5, details


def score_accuracy(url: str, metadata: Dict = None) -> Tuple[float, Dict]:
    """Score source accuracy (0-1)."""
    details = {}
    scores = []

    # Fact-checkable indicators
    if "arxiv" in url or ".gov" in url or "edu" in url:
        details["fact_checkable"] = True
        scores.append(0.9)
    elif metadata and metadata.get("references"):
        details["fact_checkable"] = True
        details["references_count"] = len(metadata["references"])
        scores.append(0.8)
    else:
        details["fact_checkable"] = False
        scores.append(0.5)

    # Error rate (if tracked)
    if metadata and "error_rate" in metadata:
        error_rate = metadata["error_rate"]
        details["error_rate"] = error_rate
        scores.append(1.0 - error_rate)

    # Corrections published
    if metadata and metadata.get("publishes_corrections"):
        details["publishes_corrections"] = True
        scores.append(0.9)

    # Default for official docs
    if any(d in url for d in ["docs.anthropic", "docs.openai", "docs.python"]):
        scores.append(0.95)

    return sum(scores) / len(scores) if scores else 0.5, details


def score_relevance(url: str, metadata: Dict = None, context: str = "claude_code") -> Tuple[float, Dict]:
    """Score source relevance to our use case (0-1)."""
    details = {}
    scores = []

    # Topic match keywords
    relevant_keywords = [
        "llm", "ai", "claude", "anthropic", "language model", "agent",
        "prompt", "safety", "security", "devops", "automation",
        "python", "cli", "command line", "terminal"
    ]

    url_lower = url.lower()
    matched = [kw for kw in relevant_keywords if kw in url_lower]
    if matched:
        details["keyword_matches"] = matched
        scores.append(min(1.0, len(matched) * 0.2))
    else:
        scores.append(0.3)

    # CLI applicability
    if metadata and metadata.get("cli_applicable"):
        details["cli_applicable"] = True
        scores.append(1.0)
    elif any(t in url_lower for t in ["cli", "terminal", "command", "shell", "bash"]):
        details["cli_applicable"] = True
        scores.append(0.9)
    else:
        details["cli_applicable"] = False
        scores.append(0.5)

    # Actionable content
    if metadata and metadata.get("actionable"):
        details["actionable"] = True
        scores.append(1.0)
    elif any(t in url_lower for t in ["tutorial", "guide", "how-to", "example"]):
        details["actionable"] = True
        scores.append(0.8)

    return sum(scores) / len(scores) if scores else 0.5, details


def evaluate_source(url: str, metadata: Dict = None) -> SourceScore:
    """Evaluate source quality comprehensively."""
    # Score each dimension
    authority, auth_details = score_authority(url, metadata)
    currency, curr_details = score_currency(url, metadata)
    accuracy, acc_details = score_accuracy(url, metadata)
    relevance, rel_details = score_relevance(url, metadata)

    # Calculate weighted total
    total = (
        authority * QUALITY_DIMENSIONS["authority"]["weight"] +
        currency * QUALITY_DIMENSIONS["currency"]["weight"] +
        accuracy * QUALITY_DIMENSIONS["accuracy"]["weight"] +
        relevance * QUALITY_DIMENSIONS["relevance"]["weight"]
    )

    # Determine tier
    if total >= 0.8:
        tier = "TIER_1"
        recommendation = "Highly recommended - primary source"
    elif total >= 0.6:
        tier = "TIER_2"
        recommendation = "Recommended - reliable source"
    elif total >= 0.4:
        tier = "TIER_3"
        recommendation = "Acceptable - verify with other sources"
    else:
        tier = "TIER_4"
        recommendation = "Caution - use for reference only"

    parsed = urlparse(url)

    return SourceScore(
        url=url,
        domain=parsed.netloc,
        authority=round(authority, 3),
        currency=round(currency, 3),
        accuracy=round(accuracy, 3),
        relevance=round(relevance, 3),
        total_score=round(total, 3),
        tier=tier,
        recommendation=recommendation,
        details={
            "authority": auth_details,
            "currency": curr_details,
            "accuracy": acc_details,
            "relevance": rel_details,
        },
        timestamp=datetime.now().isoformat(),
    )


def batch_evaluate(sources: List[Dict]) -> List[SourceScore]:
    """Evaluate multiple sources."""
    results = []
    for source in sources:
        url = source.get("url", source) if isinstance(source, dict) else source
        metadata = source if isinstance(source, dict) else None
        results.append(evaluate_source(url, metadata))
    return results


def generate_report(scores: List[SourceScore]) -> Dict:
    """Generate quality report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_sources": len(scores),
        "by_tier": {"TIER_1": 0, "TIER_2": 0, "TIER_3": 0, "TIER_4": 0},
        "average_scores": {
            "authority": 0,
            "currency": 0,
            "accuracy": 0,
            "relevance": 0,
            "total": 0,
        },
        "recommendations": [],
    }

    for score in scores:
        report["by_tier"][score.tier] += 1
        report["average_scores"]["authority"] += score.authority
        report["average_scores"]["currency"] += score.currency
        report["average_scores"]["accuracy"] += score.accuracy
        report["average_scores"]["relevance"] += score.relevance
        report["average_scores"]["total"] += score.total_score

        if score.tier == "TIER_4":
            report["recommendations"].append(f"Review or remove: {score.url}")

    if scores:
        for key in report["average_scores"]:
            report["average_scores"][key] = round(report["average_scores"][key] / len(scores), 3)

    return report


def save_result(score: SourceScore):
    """Save evaluation result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(asdict(score)) + "\n")


def print_score(score: SourceScore):
    """Print source score."""
    print("\n" + "="*60)
    print("SOURCE QUALITY ASSESSMENT")
    print("="*60)

    tier_icons = {"TIER_1": "🥇", "TIER_2": "🥈", "TIER_3": "🥉", "TIER_4": "⚠️"}

    print(f"\nURL: {score.url}")
    print(f"Domain: {score.domain}")
    print(f"\n{tier_icons.get(score.tier, '❓')} Tier: {score.tier}")
    print(f"Total Score: {score.total_score:.0%}")

    print(f"\n--- Dimension Scores ---")
    print(f"  Authority (30%):  {score.authority:.0%}")
    print(f"  Currency (25%):   {score.currency:.0%}")
    print(f"  Accuracy (25%):   {score.accuracy:.0%}")
    print(f"  Relevance (20%):  {score.relevance:.0%}")

    print(f"\nRecommendation: {score.recommendation}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Source Quality Scorer")
    parser.add_argument("--evaluate", "-e", help="Evaluate single URL")
    parser.add_argument("--batch", "-b", help="Batch evaluate from JSON file")
    parser.add_argument("--report", "-r", action="store_true", help="Generate report from history")
    parser.add_argument("--metadata", "-m", help="Metadata JSON for evaluation")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save result")

    args = parser.parse_args()

    if args.evaluate:
        metadata = json.loads(args.metadata) if args.metadata else None
        score = evaluate_source(args.evaluate, metadata)

        if args.save:
            save_result(score)

        if args.json:
            print(json.dumps(asdict(score), indent=2))
        else:
            print_score(score)

        return 0 if score.total_score >= 0.6 else 1

    if args.batch:
        sources = json.loads(Path(args.batch).read_text())
        scores = batch_evaluate(sources)

        for score in scores:
            if args.save:
                save_result(score)

        if args.json:
            print(json.dumps([asdict(s) for s in scores], indent=2))
        else:
            for score in scores:
                print(f"{score.tier}: {score.total_score:.0%} - {score.url[:50]}")

        return 0

    if args.report:
        if RESULTS_FILE.exists():
            scores = []
            with open(RESULTS_FILE) as f:
                for line in f:
                    if line.strip():
                        scores.append(SourceScore(**json.loads(line)))

            report = generate_report(scores)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(f"\nSources evaluated: {report['total_sources']}")
                print(f"By tier: {report['by_tier']}")
                print(f"Average score: {report['average_scores']['total']:.0%}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
