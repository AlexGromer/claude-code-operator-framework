#!/usr/bin/env python3
"""
Semantic Router (GAP-GATEWAY-008)

Routes requests to appropriate handlers based on semantic intent.
Uses keyword matching and pattern recognition for intent classification.

Usage:
    python semantic_router.py --route "How do I deploy to Kubernetes?"
    python semantic_router.py --analyze "Fix the bug in login.py"
    python semantic_router.py --config
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
ROUTING_LOG = DATA_DIR / "routing_decisions.jsonl"

# Route definitions with keywords and patterns
ROUTES = {
    "devops": {
        "name": "DevOps Engineer",
        "module": "modules/03-devops.md",
        "primary_keywords": [
            "terraform", "ansible", "kubernetes", "k8s", "helm", "docker",
            "docker-compose", "jenkins", "gitlab-ci", "argocd", "prometheus",
            "grafana", "aws", "gcp", "azure", "ci/cd", "pipeline"
        ],
        "secondary_keywords": [
            "deploy", "infrastructure", "container", "orchestration", "cloud",
            "scaling", "monitoring", "automation", "release", "rollout"
        ],
        "patterns": [
            r"deploy\s+to\s+\w+",
            r"set\s*up\s+(ci|cd|pipeline)",
            r"configure\s+(cluster|server)",
            r"infrastructure\s+as\s+code",
        ],
        "weight": 3,
    },
    "security": {
        "name": "Security Researcher",
        "module": "modules/02-security.md",
        "primary_keywords": [
            "nmap", "burp", "nuclei", "sqlmap", "metasploit", "owasp",
            "vulnerability", "exploit", "cve", "pentest", "security",
            "injection", "xss", "csrf", "authentication"
        ],
        "secondary_keywords": [
            "scan", "audit", "attack", "defend", "patch", "harden",
            "secure", "encrypt", "decrypt", "firewall", "ids", "siem"
        ],
        "patterns": [
            r"security\s+(audit|scan|test)",
            r"find\s+vulnerabilities",
            r"penetration\s+test",
            r"secure\s+the\s+\w+",
        ],
        "weight": 3,
    },
    "engineering": {
        "name": "Software Engineer",
        "module": "modules/07-engineering.md",
        "primary_keywords": [
            "pytest", "jest", "unittest", "test", "debug", "refactor",
            "code", "function", "class", "module", "api", "lint",
            "sonarqube", "coverage", "benchmark"
        ],
        "secondary_keywords": [
            "write", "implement", "fix", "bug", "feature", "optimize",
            "performance", "algorithm", "data structure", "review"
        ],
        "patterns": [
            r"write\s+(a\s+)?(function|class|test)",
            r"fix\s+(the\s+)?bug",
            r"implement\s+\w+",
            r"add\s+(a\s+)?feature",
            r"refactor\s+\w+",
        ],
        "weight": 2,
    },
    "writing": {
        "name": "Technical Writer",
        "module": "modules/05-writing.md",
        "primary_keywords": [
            "document", "documentation", "readme", "article", "paper",
            "thesis", "report", "tutorial", "guide", "latex", "markdown"
        ],
        "secondary_keywords": [
            "write", "explain", "describe", "summarize", "format",
            "publish", "edit", "review", "proofread"
        ],
        "patterns": [
            r"write\s+(a\s+)?(documentation|readme|article)",
            r"document\s+(the\s+)?\w+",
            r"create\s+(a\s+)?guide",
        ],
        "weight": 2,
    },
    "education": {
        "name": "Educator",
        "module": "modules/04-education.md",
        "primary_keywords": [
            "teach", "learn", "explain", "tutorial", "course", "lesson",
            "ctf", "hackthebox", "tryhackme", "workshop", "training"
        ],
        "secondary_keywords": [
            "understand", "beginner", "advanced", "concept", "example",
            "practice", "exercise", "student", "curriculum"
        ],
        "patterns": [
            r"explain\s+(how|what|why)",
            r"teach\s+me",
            r"learn\s+\w+",
            r"tutorial\s+(for|on)",
        ],
        "weight": 2,
    },
    "planning": {
        "name": "Project Planner",
        "module": "modules/06-planning.md",
        "primary_keywords": [
            "plan", "estimate", "roadmap", "sprint", "okr", "milestone",
            "jira", "confluence", "notion", "timeline", "gantt"
        ],
        "secondary_keywords": [
            "schedule", "deadline", "priority", "task", "project",
            "effort", "resource", "track", "progress"
        ],
        "patterns": [
            r"plan\s+(the\s+)?\w+",
            r"estimate\s+(time|effort|hours)",
            r"create\s+(a\s+)?roadmap",
            r"set\s+up\s+(a\s+)?sprint",
        ],
        "weight": 2,
    },
    "compliance": {
        "name": "Compliance Specialist",
        "module": "modules/01-compliance.md",
        "primary_keywords": [
            "gdpr", "hipaa", "pci-dss", "iso27001", "nist", "soc2",
            "compliance", "audit", "certification", "regulation", "фз-152"
        ],
        "secondary_keywords": [
            "policy", "standard", "requirement", "control", "framework",
            "assessment", "privacy", "data protection"
        ],
        "patterns": [
            r"comply\s+with\s+\w+",
            r"gdpr\s+(compliant|compliance)",
            r"audit\s+(for|against)\s+\w+",
        ],
        "weight": 3,
    },
    "lowlevel": {
        "name": "Low-Level Developer",
        "module": "modules/07-engineering.md",
        "primary_keywords": [
            "ebpf", "kernel", "syscall", "assembly", "gdb", "driver",
            "rust", "c", "go", "memory", "binary", "reverse"
        ],
        "secondary_keywords": [
            "disassemble", "debug", "trace", "hook", "patch", "optimize",
            "performance", "hardware", "embedded"
        ],
        "patterns": [
            r"kernel\s+\w+",
            r"write\s+(a\s+)?driver",
            r"(dis)?assemble\s+\w+",
            r"low[- ]?level\s+\w+",
        ],
        "weight": 3,
    },
}


@dataclass
class RoutingDecision:
    """Routing decision result."""
    query: str
    primary_route: str
    confidence: float
    scores: Dict[str, float]
    modules_to_load: List[str]
    timestamp: str
    reasoning: str


def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text."""
    # Normalize
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s-]', ' ', text)
    # Split and filter
    words = [w.strip() for w in text.split() if len(w.strip()) > 2]
    return words


def calculate_score(text: str, route: Dict) -> Tuple[float, List[str]]:
    """Calculate routing score for a route."""
    text_lower = text.lower()
    keywords = extract_keywords(text)
    matches = []
    score = 0.0

    # Primary keyword matches (weight * 3)
    for kw in route["primary_keywords"]:
        if kw in text_lower:
            score += route["weight"] * 3
            matches.append(f"primary:{kw}")

    # Secondary keyword matches (weight * 1)
    for kw in route["secondary_keywords"]:
        if kw in text_lower:
            score += route["weight"] * 1
            matches.append(f"secondary:{kw}")

    # Pattern matches (weight * 2)
    for pattern in route["patterns"]:
        if re.search(pattern, text_lower):
            score += route["weight"] * 2
            matches.append(f"pattern:{pattern[:30]}")

    return score, matches


def route_request(query: str) -> RoutingDecision:
    """Route a request to appropriate handler."""
    scores = {}
    all_matches = {}

    # Calculate scores for all routes
    for route_name, route_config in ROUTES.items():
        score, matches = calculate_score(query, route_config)
        scores[route_name] = score
        all_matches[route_name] = matches

    # Find primary route (highest score)
    max_score = max(scores.values()) if scores.values() else 0
    primary_route = max(scores, key=scores.get) if max_score > 0 else "engineering"

    # Calculate confidence
    total_score = sum(scores.values())
    if total_score > 0:
        confidence = scores[primary_route] / total_score
    else:
        confidence = 0.5  # Default to medium confidence

    # Determine secondary routes (>50% of primary score)
    threshold = max_score * 0.5
    modules_to_load = [ROUTES[primary_route]["module"]]
    for route_name, score in scores.items():
        if route_name != primary_route and score >= threshold:
            modules_to_load.append(ROUTES[route_name]["module"])

    # Build reasoning
    matches = all_matches.get(primary_route, [])
    if matches:
        reasoning = f"Matched: {', '.join(matches[:5])}"
    else:
        reasoning = "Default routing (no strong signals)"

    return RoutingDecision(
        query=query[:200],
        primary_route=primary_route,
        confidence=round(confidence, 3),
        scores={k: round(v, 2) for k, v in scores.items()},
        modules_to_load=modules_to_load,
        timestamp=datetime.now().isoformat(),
        reasoning=reasoning,
    )


def analyze_query(query: str) -> Dict:
    """Detailed analysis of query routing."""
    decision = route_request(query)

    analysis = {
        "query": query,
        "keywords_found": extract_keywords(query),
        "decision": asdict(decision),
        "all_routes": {},
    }

    for route_name, route_config in ROUTES.items():
        score, matches = calculate_score(query, route_config)
        analysis["all_routes"][route_name] = {
            "score": round(score, 2),
            "matches": matches,
            "would_load": route_config["module"],
        }

    return analysis


def save_decision(decision: RoutingDecision):
    """Save routing decision to log."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ROUTING_LOG, "a") as f:
        f.write(json.dumps(asdict(decision)) + "\n")


def print_routing_config():
    """Print routing configuration."""
    print("\n" + "="*60)
    print("SEMANTIC ROUTER CONFIGURATION")
    print("="*60)

    for route_name, route_config in ROUTES.items():
        print(f"\n  [{route_name}] {route_config['name']}")
        print(f"    Module: {route_config['module']}")
        print(f"    Weight: {route_config['weight']}")
        print(f"    Primary Keywords: {len(route_config['primary_keywords'])}")
        print(f"    Secondary Keywords: {len(route_config['secondary_keywords'])}")
        print(f"    Patterns: {len(route_config['patterns'])}")

    print("\n" + "="*60)


def print_decision(decision: RoutingDecision):
    """Print routing decision."""
    print("\n" + "="*60)
    print("ROUTING DECISION")
    print("="*60)

    # Confidence indicator
    if decision.confidence >= 0.7:
        conf_indicator = "HIGH"
        conf_symbol = "✅"
    elif decision.confidence >= 0.4:
        conf_indicator = "MEDIUM"
        conf_symbol = "⚠️"
    else:
        conf_indicator = "LOW"
        conf_symbol = "❓"

    print(f"\n{conf_symbol} Route: {ROUTES[decision.primary_route]['name']}")
    print(f"   Confidence: {conf_indicator} ({decision.confidence:.0%})")
    print(f"   Reasoning: {decision.reasoning}")

    print(f"\n   Modules to load:")
    for mod in decision.modules_to_load:
        print(f"     • {mod}")

    # Show competing routes
    sorted_scores = sorted(decision.scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_scores) > 1:
        print(f"\n   Scores:")
        for route, score in sorted_scores[:5]:
            indicator = "◆" if route == decision.primary_route else "◇"
            print(f"     {indicator} {route}: {score}")

    print("\n" + "="*60)


def batch_test():
    """Test router with sample queries."""
    test_queries = [
        "Deploy the application to Kubernetes",
        "Fix the authentication bug in login.py",
        "Scan the website for SQL injection vulnerabilities",
        "Write documentation for the API",
        "Explain how recursion works",
        "Plan the sprint for next week",
        "Make the system GDPR compliant",
        "Write an eBPF probe for syscall tracing",
        "Create a CI/CD pipeline with GitHub Actions",
        "How do I secure my Docker containers?",
    ]

    print("\n" + "="*60)
    print("ROUTING TEST")
    print("="*60)

    results = []
    for query in test_queries:
        decision = route_request(query)
        results.append({
            "query": query[:50],
            "route": decision.primary_route,
            "confidence": f"{decision.confidence:.0%}",
        })
        print(f"\n  Q: {query[:50]}...")
        print(f"  → {decision.primary_route} ({decision.confidence:.0%})")

    print("\n" + "="*60)
    return results


def main():
    parser = argparse.ArgumentParser(description="Semantic Router")
    parser.add_argument("--route", "-r", help="Route a query")
    parser.add_argument("--analyze", "-a", help="Detailed query analysis")
    parser.add_argument("--config", "-c", action="store_true", help="Show config")
    parser.add_argument("--test", "-t", action="store_true", help="Run test queries")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save decision")

    args = parser.parse_args()

    if args.config:
        print_routing_config()
        return 0

    if args.test:
        results = batch_test()
        if args.json:
            print(json.dumps(results, indent=2))
        return 0

    if args.route:
        decision = route_request(args.route)
        if args.save:
            save_decision(decision)
        if args.json:
            print(json.dumps(asdict(decision), indent=2))
        else:
            print_decision(decision)
        return 0

    if args.analyze:
        analysis = analyze_query(args.analyze)
        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            print(f"\nQuery: {args.analyze}")
            print(f"Keywords: {analysis['keywords_found']}")
            print(f"\nPrimary Route: {analysis['decision']['primary_route']}")
            print(f"Confidence: {analysis['decision']['confidence']:.0%}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
