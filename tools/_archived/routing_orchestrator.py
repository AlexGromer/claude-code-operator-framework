#!/usr/bin/env python3
"""
Routing Orchestrator (GAP-GATEWAY-AGENT-001)

Intelligent routing of requests to appropriate agents/models.
Implements semantic routing, load balancing, and fallback strategies.

Usage:
    python routing_orchestrator.py --route "user query"
    python routing_orchestrator.py --analyze-patterns
    python routing_orchestrator.py --stats
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
ROUTES_FILE = DATA_DIR / "routing_decisions.jsonl"
STATS_FILE = DATA_DIR / "routing_stats.json"


@dataclass
class RouteConfig:
    """Configuration for a route."""
    name: str
    model: str
    keywords: List[str]
    patterns: List[str]
    priority: int = 0
    max_tokens: int = 4096
    temperature: float = 0.0
    fallback: Optional[str] = None


@dataclass
class RoutingDecision:
    """A routing decision."""
    query: str
    selected_route: str
    confidence: float
    matched_keywords: List[str]
    matched_patterns: List[str]
    alternatives: List[Tuple[str, float]]
    timestamp: str


# Default route configurations
DEFAULT_ROUTES = {
    "code_generation": RouteConfig(
        name="code_generation",
        model="sonnet",
        keywords=["write", "create", "implement", "code", "function", "class", "script"],
        patterns=[r"write\s+a?\s*\w+\s+(function|class|script)", r"implement\s+"],
        priority=10,
    ),
    "code_review": RouteConfig(
        name="code_review",
        model="opus",
        keywords=["review", "analyze", "check", "bug", "issue", "security"],
        patterns=[r"review\s+(this|the)\s+code", r"find\s+bugs?"],
        priority=8,
    ),
    "explanation": RouteConfig(
        name="explanation",
        model="haiku",
        keywords=["explain", "what is", "how does", "why", "describe"],
        patterns=[r"what\s+is\s+a?\s*\w+", r"explain\s+"],
        priority=5,
    ),
    "research": RouteConfig(
        name="research",
        model="sonnet",
        keywords=["research", "find", "search", "look up", "investigate"],
        patterns=[r"find\s+(information|details)", r"search\s+for"],
        priority=7,
    ),
    "planning": RouteConfig(
        name="planning",
        model="opus",
        keywords=["plan", "design", "architect", "strategy", "roadmap"],
        patterns=[r"create\s+a?\s*plan", r"design\s+"],
        priority=9,
    ),
    "simple_task": RouteConfig(
        name="simple_task",
        model="haiku",
        keywords=["list", "format", "convert", "simple"],
        patterns=[r"list\s+all", r"convert\s+"],
        priority=3,
    ),
    "default": RouteConfig(
        name="default",
        model="sonnet",
        keywords=[],
        patterns=[],
        priority=0,
    ),
}


def calculate_route_score(query: str, route: RouteConfig) -> Tuple[float, List[str], List[str]]:
    """Calculate routing score for a query."""
    query_lower = query.lower()
    score = route.priority / 10.0  # Base score from priority

    matched_keywords = []
    matched_patterns = []

    # Keyword matching
    for keyword in route.keywords:
        if keyword.lower() in query_lower:
            matched_keywords.append(keyword)
            score += 0.15

    # Pattern matching
    for pattern in route.patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            matched_patterns.append(pattern)
            score += 0.25

    # Normalize score to 0-1
    score = min(1.0, score)

    return score, matched_keywords, matched_patterns


def route_query(query: str, routes: Dict[str, RouteConfig] = None) -> RoutingDecision:
    """Route a query to the best model/agent."""
    if routes is None:
        routes = DEFAULT_ROUTES

    scores = []
    for route_name, route in routes.items():
        if route_name == "default":
            continue
        score, keywords, patterns = calculate_route_score(query, route)
        scores.append((route_name, score, keywords, patterns))

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Select best route
    if scores and scores[0][1] > 0.2:
        selected = scores[0]
    else:
        # Use default
        selected = ("default", 0.1, [], [])

    # Get alternatives
    alternatives = [(name, score) for name, score, _, _ in scores[:3] if name != selected[0]]

    return RoutingDecision(
        query=query[:200],
        selected_route=selected[0],
        confidence=round(selected[1], 3),
        matched_keywords=selected[2],
        matched_patterns=selected[3],
        alternatives=alternatives,
        timestamp=datetime.now().isoformat(),
    )


def log_decision(decision: RoutingDecision):
    """Log routing decision."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ROUTES_FILE, "a") as f:
        f.write(json.dumps(asdict(decision)) + "\n")


def load_stats() -> Dict:
    """Load routing statistics."""
    if STATS_FILE.exists():
        return json.loads(STATS_FILE.read_text())
    return {"total_routes": 0, "by_route": {}, "avg_confidence": 0}


def update_stats(decision: RoutingDecision):
    """Update routing statistics."""
    stats = load_stats()

    stats["total_routes"] += 1
    if decision.selected_route not in stats["by_route"]:
        stats["by_route"][decision.selected_route] = {"count": 0, "total_confidence": 0}

    route_stats = stats["by_route"][decision.selected_route]
    route_stats["count"] += 1
    route_stats["total_confidence"] += decision.confidence

    # Update average confidence
    total_conf = sum(r["total_confidence"] for r in stats["by_route"].values())
    stats["avg_confidence"] = total_conf / stats["total_routes"]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def analyze_patterns() -> Dict:
    """Analyze routing patterns from history."""
    if not ROUTES_FILE.exists():
        return {"error": "No routing history"}

    patterns = {"by_hour": {}, "by_route": {}, "low_confidence": []}

    for line in ROUTES_FILE.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            route = entry["selected_route"]
            confidence = entry["confidence"]

            # Count by route
            if route not in patterns["by_route"]:
                patterns["by_route"][route] = 0
            patterns["by_route"][route] += 1

            # Track low confidence decisions
            if confidence < 0.3:
                patterns["low_confidence"].append({
                    "query": entry["query"][:50],
                    "route": route,
                    "confidence": confidence,
                })

    return patterns


def print_routing(decision: RoutingDecision, routes: Dict[str, RouteConfig]):
    """Print routing decision."""
    route = routes.get(decision.selected_route, DEFAULT_ROUTES["default"])

    print("\n" + "="*60)
    print("ROUTING DECISION")
    print("="*60)

    print(f"\nQuery: {decision.query[:60]}...")
    print(f"\n🎯 Selected Route: {decision.selected_route}")
    print(f"   Model: {route.model}")
    print(f"   Confidence: {decision.confidence:.1%}")

    if decision.matched_keywords:
        print(f"   Keywords: {', '.join(decision.matched_keywords)}")
    if decision.matched_patterns:
        print(f"   Patterns: {len(decision.matched_patterns)} matched")

    if decision.alternatives:
        print("\n   Alternatives:")
        for alt_name, alt_score in decision.alternatives[:2]:
            print(f"      - {alt_name}: {alt_score:.1%}")

    print("\n" + "="*60)


def print_stats():
    """Print routing statistics."""
    stats = load_stats()

    print("\n" + "="*50)
    print("ROUTING STATISTICS")
    print("="*50)

    print(f"\nTotal Routes: {stats['total_routes']}")
    print(f"Avg Confidence: {stats['avg_confidence']:.1%}")

    if stats["by_route"]:
        print("\nBy Route:")
        for route, data in sorted(stats["by_route"].items(), key=lambda x: x[1]["count"], reverse=True):
            avg_conf = data["total_confidence"] / data["count"] if data["count"] > 0 else 0
            print(f"   {route}: {data['count']} ({avg_conf:.1%} avg confidence)")

    print("\n" + "="*50)


def main():
    parser = argparse.ArgumentParser(description="Routing Orchestrator")
    parser.add_argument("--route", "-r", help="Query to route")
    parser.add_argument("--analyze-patterns", action="store_true", help="Analyze routing patterns")
    parser.add_argument("--stats", "-s", action="store_true", help="Show statistics")
    parser.add_argument("--list-routes", "-l", action="store_true", help="List available routes")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", action="store_true", help="Save decision")

    args = parser.parse_args()

    if args.list_routes:
        if args.json:
            print(json.dumps({k: asdict(v) for k, v in DEFAULT_ROUTES.items()}, indent=2))
        else:
            print("\n" + "="*50)
            print("AVAILABLE ROUTES")
            print("="*50)
            for name, route in DEFAULT_ROUTES.items():
                print(f"\n{name}:")
                print(f"   Model: {route.model}")
                print(f"   Priority: {route.priority}")
                print(f"   Keywords: {', '.join(route.keywords[:5])}")
            print("\n" + "="*50)
        return 0

    if args.stats:
        if args.json:
            print(json.dumps(load_stats(), indent=2))
        else:
            print_stats()
        return 0

    if args.analyze_patterns:
        patterns = analyze_patterns()
        if args.json:
            print(json.dumps(patterns, indent=2))
        else:
            print("\n" + "="*50)
            print("ROUTING PATTERNS")
            print("="*50)
            for route, count in patterns.get("by_route", {}).items():
                print(f"   {route}: {count}")
            if patterns.get("low_confidence"):
                print(f"\nLow Confidence: {len(patterns['low_confidence'])} decisions")
            print("\n" + "="*50)
        return 0

    if args.route:
        decision = route_query(args.route)

        if args.save:
            log_decision(decision)
            update_stats(decision)

        if args.json:
            print(json.dumps(asdict(decision), indent=2))
        else:
            print_routing(decision, DEFAULT_ROUTES)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
