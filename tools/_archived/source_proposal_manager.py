#!/usr/bin/env python3
"""
Source Proposal Manager (GAP-SRC-001)

Manages the workflow for proposing and approving new sources.
Implements proposal template, evaluation criteria, and approval matrix.

Usage:
    python source_proposal_manager.py --propose "https://example.com"
    python source_proposal_manager.py --review
    python source_proposal_manager.py --approve PROP-001
    python source_proposal_manager.py --reject PROP-001 --reason "Low quality"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
PROPOSALS_FILE = DATA_DIR / "source_proposals.json"
REGISTRY_FILE = DATA_DIR / "source_registry.json"

# Proposal status
STATUS = {
    "PENDING": "Awaiting review",
    "UNDER_REVIEW": "Being evaluated",
    "APPROVED": "Accepted into registry",
    "REJECTED": "Not accepted",
    "DEFERRED": "Postponed for later review",
}

# Evaluation criteria
EVALUATION_CRITERIA = {
    "authority": {
        "description": "Source credibility and expertise",
        "weight": 0.30,
        "questions": [
            "Is the source from a recognized authority?",
            "Does the author have relevant credentials?",
            "Is the content peer-reviewed or edited?",
        ],
    },
    "relevance": {
        "description": "Applicability to Claude Code use cases",
        "weight": 0.25,
        "questions": [
            "Is the content relevant to LLM/AI topics?",
            "Is it applicable to CLI/developer workflows?",
            "Does it align with security/DevOps focus?",
        ],
    },
    "currency": {
        "description": "Timeliness and maintenance",
        "weight": 0.20,
        "questions": [
            "Is the content recently updated?",
            "Is there a regular update schedule?",
            "Is the information current?",
        ],
    },
    "accuracy": {
        "description": "Correctness and verifiability",
        "weight": 0.15,
        "questions": [
            "Can claims be verified?",
            "Are references provided?",
            "Is there error tracking?",
        ],
    },
    "accessibility": {
        "description": "Ease of access and use",
        "weight": 0.10,
        "questions": [
            "Is the content freely accessible?",
            "Is it machine-readable?",
            "Is the format consistent?",
        ],
    },
}


@dataclass
class SourceProposal:
    """A source proposal."""
    id: str
    url: str
    name: str
    description: str
    proposed_tier: str
    proposer: str
    status: str
    created: str
    updated: str
    evaluation: Optional[Dict]
    decision_reason: Optional[str]


def generate_proposal_id() -> str:
    """Generate unique proposal ID."""
    now = datetime.now()
    return f"PROP-{now.strftime('%Y%m%d%H%M%S')}"


def load_proposals() -> Dict:
    """Load proposals from file."""
    if PROPOSALS_FILE.exists():
        return json.loads(PROPOSALS_FILE.read_text())
    return {"proposals": [], "last_updated": None}


def save_proposals(data: Dict):
    """Save proposals to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    with open(PROPOSALS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_registry() -> Dict:
    """Load source registry."""
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {"sources": [], "last_updated": None}


def save_registry(data: Dict):
    """Save source registry."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    with open(REGISTRY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def suggest_tier(url: str) -> str:
    """Suggest initial tier based on URL."""
    domain = urlparse(url).netloc.lower()

    tier1_domains = ["anthropic.com", "openai.com", "arxiv.org", "acm.org", "ieee.org"]
    tier2_domains = ["github.com", "huggingface.co", "pytorch.org", "kubernetes.io"]
    tier3_domains = ["medium.com", "dev.to", "stackoverflow.com"]

    for d in tier1_domains:
        if d in domain:
            return "TIER_1"
    for d in tier2_domains:
        if d in domain:
            return "TIER_2"
    for d in tier3_domains:
        if d in domain:
            return "TIER_3"

    return "TIER_4"


def create_proposal(
    url: str,
    name: str = None,
    description: str = None,
    tier: str = None,
    proposer: str = "system"
) -> SourceProposal:
    """Create a new source proposal."""
    parsed = urlparse(url)
    now = datetime.now().isoformat()

    proposal = SourceProposal(
        id=generate_proposal_id(),
        url=url,
        name=name or parsed.netloc,
        description=description or f"Proposed source from {parsed.netloc}",
        proposed_tier=tier or suggest_tier(url),
        proposer=proposer,
        status="PENDING",
        created=now,
        updated=now,
        evaluation=None,
        decision_reason=None,
    )

    # Save to proposals
    data = load_proposals()
    data["proposals"].append(asdict(proposal))
    save_proposals(data)

    return proposal


def evaluate_proposal(proposal_id: str, scores: Dict[str, float]) -> Optional[Dict]:
    """Evaluate a proposal with criteria scores."""
    data = load_proposals()

    for p in data["proposals"]:
        if p["id"] == proposal_id:
            # Calculate weighted score
            total_score = 0
            evaluation = {"scores": scores, "timestamp": datetime.now().isoformat()}

            for criterion, config in EVALUATION_CRITERIA.items():
                score = scores.get(criterion, 0.5)
                weighted = score * config["weight"]
                total_score += weighted
                evaluation[f"{criterion}_weighted"] = round(weighted, 3)

            evaluation["total_score"] = round(total_score, 3)

            # Recommend tier based on score
            if total_score >= 0.8:
                evaluation["recommended_tier"] = "TIER_1"
            elif total_score >= 0.6:
                evaluation["recommended_tier"] = "TIER_2"
            elif total_score >= 0.4:
                evaluation["recommended_tier"] = "TIER_3"
            else:
                evaluation["recommended_tier"] = "TIER_4"

            p["evaluation"] = evaluation
            p["status"] = "UNDER_REVIEW"
            p["updated"] = datetime.now().isoformat()

            save_proposals(data)
            return evaluation

    return None


def approve_proposal(proposal_id: str, final_tier: str = None) -> bool:
    """Approve a proposal and add to registry."""
    data = load_proposals()

    for p in data["proposals"]:
        if p["id"] == proposal_id:
            if p["status"] not in ["PENDING", "UNDER_REVIEW"]:
                return False

            # Determine final tier
            if final_tier:
                tier = final_tier
            elif p.get("evaluation", {}).get("recommended_tier"):
                tier = p["evaluation"]["recommended_tier"]
            else:
                tier = p["proposed_tier"]

            # Update proposal status
            p["status"] = "APPROVED"
            p["updated"] = datetime.now().isoformat()
            p["decision_reason"] = f"Approved as {tier}"
            save_proposals(data)

            # Add to registry
            registry = load_registry()
            registry["sources"].append({
                "url": p["url"],
                "name": p["name"],
                "tier": tier,
                "added": datetime.now().isoformat(),
                "proposal_id": proposal_id,
            })
            save_registry(registry)

            return True

    return False


def reject_proposal(proposal_id: str, reason: str) -> bool:
    """Reject a proposal."""
    data = load_proposals()

    for p in data["proposals"]:
        if p["id"] == proposal_id:
            p["status"] = "REJECTED"
            p["updated"] = datetime.now().isoformat()
            p["decision_reason"] = reason
            save_proposals(data)
            return True

    return False


def defer_proposal(proposal_id: str, reason: str = None) -> bool:
    """Defer a proposal for later review."""
    data = load_proposals()

    for p in data["proposals"]:
        if p["id"] == proposal_id:
            p["status"] = "DEFERRED"
            p["updated"] = datetime.now().isoformat()
            p["decision_reason"] = reason or "Deferred for future review"
            save_proposals(data)
            return True

    return False


def get_pending_proposals() -> List[Dict]:
    """Get all pending proposals."""
    data = load_proposals()
    return [p for p in data["proposals"] if p["status"] in ["PENDING", "UNDER_REVIEW"]]


def print_proposal(proposal: Dict):
    """Print a proposal."""
    status_icons = {
        "PENDING": "⏳",
        "UNDER_REVIEW": "🔍",
        "APPROVED": "✅",
        "REJECTED": "❌",
        "DEFERRED": "⏸️",
    }

    print(f"\n{status_icons.get(proposal['status'], '❓')} [{proposal['id']}] {proposal['name']}")
    print(f"   URL: {proposal['url']}")
    print(f"   Status: {proposal['status']}")
    print(f"   Proposed Tier: {proposal['proposed_tier']}")
    print(f"   Created: {proposal['created'][:10]}")

    if proposal.get("evaluation"):
        eval_data = proposal["evaluation"]
        print(f"   Score: {eval_data.get('total_score', 0):.0%}")
        print(f"   Recommended: {eval_data.get('recommended_tier', 'N/A')}")

    if proposal.get("decision_reason"):
        print(f"   Reason: {proposal['decision_reason']}")


def print_criteria():
    """Print evaluation criteria."""
    print("\n" + "="*60)
    print("EVALUATION CRITERIA")
    print("="*60)

    for name, config in EVALUATION_CRITERIA.items():
        print(f"\n  {name.upper()} (Weight: {config['weight']:.0%})")
        print(f"    {config['description']}")
        print("    Questions:")
        for q in config["questions"]:
            print(f"      • {q}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Source Proposal Manager")
    parser.add_argument("--propose", "-p", help="Propose new source URL")
    parser.add_argument("--name", "-n", help="Source name")
    parser.add_argument("--description", "-d", help="Source description")
    parser.add_argument("--tier", "-t", choices=["TIER_1", "TIER_2", "TIER_3", "TIER_4"])
    parser.add_argument("--review", "-r", action="store_true", help="Show pending proposals")
    parser.add_argument("--evaluate", "-e", help="Evaluate proposal ID")
    parser.add_argument("--approve", "-a", help="Approve proposal ID")
    parser.add_argument("--reject", help="Reject proposal ID")
    parser.add_argument("--defer", help="Defer proposal ID")
    parser.add_argument("--reason", help="Reason for rejection/deferral")
    parser.add_argument("--criteria", "-c", action="store_true", help="Show evaluation criteria")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.criteria:
        print_criteria()
        return 0

    if args.propose:
        proposal = create_proposal(
            url=args.propose,
            name=args.name,
            description=args.description,
            tier=args.tier,
        )
        if args.json:
            print(json.dumps(asdict(proposal), indent=2))
        else:
            print(f"\n✅ Proposal created: {proposal.id}")
            print_proposal(asdict(proposal))
        return 0

    if args.review:
        pending = get_pending_proposals()
        if args.json:
            print(json.dumps(pending, indent=2))
        else:
            print("\n" + "="*60)
            print("PENDING PROPOSALS")
            print("="*60)
            if not pending:
                print("\nNo pending proposals")
            else:
                for p in pending:
                    print_proposal(p)
        return 0

    if args.evaluate:
        # Interactive evaluation
        print(f"\nEvaluating proposal: {args.evaluate}")
        print_criteria()

        scores = {}
        for criterion in EVALUATION_CRITERIA:
            while True:
                try:
                    score = float(input(f"  {criterion} (0.0-1.0): "))
                    if 0 <= score <= 1:
                        scores[criterion] = score
                        break
                except ValueError:
                    pass
                print("    Invalid. Enter a number between 0 and 1")

        evaluation = evaluate_proposal(args.evaluate, scores)
        if evaluation:
            print(f"\n✅ Evaluation complete")
            print(f"   Total Score: {evaluation['total_score']:.0%}")
            print(f"   Recommended Tier: {evaluation['recommended_tier']}")
        else:
            print("❌ Proposal not found")
        return 0

    if args.approve:
        if approve_proposal(args.approve, args.tier):
            print(f"✅ Proposal {args.approve} approved")
        else:
            print(f"❌ Could not approve {args.approve}")
        return 0

    if args.reject:
        if not args.reason:
            print("❌ Reason required for rejection (--reason)")
            return 1
        if reject_proposal(args.reject, args.reason):
            print(f"✅ Proposal {args.reject} rejected")
        else:
            print(f"❌ Could not reject {args.reject}")
        return 0

    if args.defer:
        if defer_proposal(args.defer, args.reason):
            print(f"✅ Proposal {args.defer} deferred")
        else:
            print(f"❌ Could not defer {args.defer}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
