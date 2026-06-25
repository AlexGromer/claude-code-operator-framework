#!/usr/bin/env python3
"""
Unified Source Registry (GAP-SRC-*)

Central registry for all authoritative sources.
Manages source tiers, domains, and quality metadata.

Usage:
    python source_registry.py --list
    python source_registry.py --add URL --tier TIER --domain DOMAIN
    python source_registry.py --lookup URL
    python source_registry.py --search QUERY
    python source_registry.py --stats
    python source_registry.py --export [json|csv]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import re

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
REGISTRY_FILE = DATA_DIR / "source_registry.json"
HISTORY_FILE = DATA_DIR / "source_registry_history.jsonl"

# Source tiers
TIERS = {
    "TIER_1": {
        "name": "Authoritative Primary",
        "description": "Official documentation, academic papers, vendor sources",
        "quality_score": 1.0,
        "verification_required": False,
    },
    "TIER_2": {
        "name": "Trusted Secondary",
        "description": "Major platforms, established projects, curated content",
        "quality_score": 0.8,
        "verification_required": False,
    },
    "TIER_3": {
        "name": "Community Sources",
        "description": "Forums, blogs, community wikis",
        "quality_score": 0.6,
        "verification_required": True,
    },
    "TIER_4": {
        "name": "Unknown/Unverified",
        "description": "New or unclassified sources",
        "quality_score": 0.4,
        "verification_required": True,
    },
}

# Domain categories
DOMAINS = [
    "security", "devops", "programming", "research",
    "documentation", "compliance", "tools", "general",
]


@dataclass
class Source:
    """Source registry entry."""
    url: str
    domain: str
    tier: str
    name: str
    description: str
    added_at: str
    last_verified: Optional[str]
    verification_status: str  # verified, pending, failed
    quality_score: float
    tags: List[str]
    metadata: Dict


def load_registry() -> Dict:
    """Load registry from file."""
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {
        "sources": {},
        "created_at": datetime.now().isoformat(),
        "last_updated": None,
        "version": "1.0",
    }


def save_registry(registry: Dict):
    """Save registry to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    registry["last_updated"] = datetime.now().isoformat()
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)


def log_change(action: str, source_url: str, details: Dict):
    """Log registry changes."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "source_url": source_url,
            "details": details,
        }) + "\n")


def normalize_url(url: str) -> str:
    """Normalize URL for consistent lookup."""
    parsed = urlparse(url)
    # Remove trailing slash, lowercase domain
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    return normalized


def extract_domain_from_url(url: str) -> str:
    """Extract domain name from URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def auto_detect_tier(url: str) -> str:
    """Auto-detect source tier based on URL patterns."""
    domain = extract_domain_from_url(url)

    # TIER_1 patterns
    tier1_patterns = [
        r'arxiv\.org', r'acm\.org', r'ieee\.org',
        r'anthropic\.com', r'openai\.com',
        r'docs\.python\.org', r'developer\.mozilla\.org',
        r'kubernetes\.io/docs', r'terraform\.io/docs',
    ]

    # TIER_2 patterns
    tier2_patterns = [
        r'github\.com', r'huggingface\.co',
        r'pytorch\.org', r'tensorflow\.org',
        r'docker\.com', r'aws\.amazon\.com',
    ]

    # TIER_3 patterns
    tier3_patterns = [
        r'stackoverflow\.com', r'reddit\.com',
        r'medium\.com', r'dev\.to',
    ]

    for pattern in tier1_patterns:
        if re.search(pattern, domain):
            return "TIER_1"

    for pattern in tier2_patterns:
        if re.search(pattern, domain):
            return "TIER_2"

    for pattern in tier3_patterns:
        if re.search(pattern, domain):
            return "TIER_3"

    return "TIER_4"


def add_source(
    url: str,
    tier: str = None,
    domain: str = "general",
    name: str = None,
    description: str = "",
    tags: List[str] = None,
) -> Source:
    """Add a new source to registry."""
    registry = load_registry()

    normalized_url = normalize_url(url)

    # Auto-detect tier if not provided
    if tier is None:
        tier = auto_detect_tier(url)

    # Auto-generate name if not provided
    if name is None:
        name = extract_domain_from_url(url)

    source = Source(
        url=normalized_url,
        domain=domain,
        tier=tier,
        name=name,
        description=description,
        added_at=datetime.now().isoformat(),
        last_verified=None,
        verification_status="pending",
        quality_score=TIERS[tier]["quality_score"],
        tags=tags or [],
        metadata={},
    )

    registry["sources"][normalized_url] = asdict(source)
    save_registry(registry)

    log_change("add", normalized_url, {"tier": tier, "domain": domain})

    return source


def lookup_source(url: str) -> Optional[Dict]:
    """Lookup a source in registry."""
    registry = load_registry()
    normalized_url = normalize_url(url)

    if normalized_url in registry["sources"]:
        return registry["sources"][normalized_url]

    # Try partial match
    for source_url, source in registry["sources"].items():
        if extract_domain_from_url(url) in source_url:
            return source

    return None


def search_sources(query: str) -> List[Dict]:
    """Search sources by query."""
    registry = load_registry()
    query_lower = query.lower()
    results = []

    for url, source in registry["sources"].items():
        # Search in URL, name, description, tags
        searchable = (
            url.lower() +
            source.get("name", "").lower() +
            source.get("description", "").lower() +
            " ".join(source.get("tags", []))
        )

        if query_lower in searchable:
            results.append(source)

    # Sort by quality score
    results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

    return results


def list_sources(tier: str = None, domain: str = None) -> List[Dict]:
    """List all sources, optionally filtered."""
    registry = load_registry()
    sources = list(registry["sources"].values())

    if tier:
        sources = [s for s in sources if s.get("tier") == tier]

    if domain:
        sources = [s for s in sources if s.get("domain") == domain]

    # Sort by tier, then quality score
    tier_order = {"TIER_1": 1, "TIER_2": 2, "TIER_3": 3, "TIER_4": 4}
    sources.sort(key=lambda x: (
        tier_order.get(x.get("tier"), 5),
        -x.get("quality_score", 0)
    ))

    return sources


def get_statistics() -> Dict:
    """Get registry statistics."""
    registry = load_registry()
    sources = list(registry["sources"].values())

    stats = {
        "total_sources": len(sources),
        "by_tier": {},
        "by_domain": {},
        "by_status": {},
        "avg_quality_score": 0,
        "last_updated": registry.get("last_updated"),
    }

    # Count by tier
    for tier in TIERS.keys():
        count = len([s for s in sources if s.get("tier") == tier])
        stats["by_tier"][tier] = count

    # Count by domain
    for domain in DOMAINS:
        count = len([s for s in sources if s.get("domain") == domain])
        if count > 0:
            stats["by_domain"][domain] = count

    # Count by status
    for status in ["verified", "pending", "failed"]:
        count = len([s for s in sources if s.get("verification_status") == status])
        stats["by_status"][status] = count

    # Average quality
    if sources:
        stats["avg_quality_score"] = round(
            sum(s.get("quality_score", 0) for s in sources) / len(sources), 3
        )

    return stats


def update_source(url: str, updates: Dict) -> Optional[Dict]:
    """Update source in registry."""
    registry = load_registry()
    normalized_url = normalize_url(url)

    if normalized_url not in registry["sources"]:
        return None

    source = registry["sources"][normalized_url]
    source.update(updates)
    source["metadata"]["last_modified"] = datetime.now().isoformat()

    save_registry(registry)
    log_change("update", normalized_url, updates)

    return source


def remove_source(url: str) -> bool:
    """Remove source from registry."""
    registry = load_registry()
    normalized_url = normalize_url(url)

    if normalized_url in registry["sources"]:
        del registry["sources"][normalized_url]
        save_registry(registry)
        log_change("remove", normalized_url, {})
        return True

    return False


def export_registry(format: str = "json") -> str:
    """Export registry to specified format."""
    registry = load_registry()
    sources = list(registry["sources"].values())

    if format == "json":
        return json.dumps(sources, indent=2)

    elif format == "csv":
        headers = ["url", "name", "tier", "domain", "quality_score", "verification_status"]
        lines = [",".join(headers)]
        for source in sources:
            row = [str(source.get(h, "")) for h in headers]
            lines.append(",".join(row))
        return "\n".join(lines)

    return json.dumps(sources, indent=2)


def init_default_sources():
    """Initialize with default authoritative sources."""
    defaults = [
        ("https://arxiv.org", "TIER_1", "research", "arXiv", "Academic preprints"),
        ("https://docs.python.org", "TIER_1", "documentation", "Python Docs", "Official Python documentation"),
        ("https://developer.mozilla.org", "TIER_1", "documentation", "MDN", "Web development reference"),
        ("https://kubernetes.io/docs", "TIER_1", "devops", "Kubernetes Docs", "Kubernetes documentation"),
        ("https://github.com", "TIER_2", "tools", "GitHub", "Code hosting platform"),
        ("https://huggingface.co", "TIER_2", "research", "HuggingFace", "ML models and datasets"),
        ("https://nvd.nist.gov", "TIER_1", "security", "NVD", "National Vulnerability Database"),
        ("https://cve.mitre.org", "TIER_1", "security", "CVE", "CVE database"),
        ("https://owasp.org", "TIER_1", "security", "OWASP", "Security standards"),
    ]

    for url, tier, domain, name, desc in defaults:
        existing = lookup_source(url)
        if not existing:
            add_source(url, tier, domain, name, desc)


def print_sources(sources: List[Dict]):
    """Print sources in formatted table."""
    print("\n" + "="*80)
    print("SOURCE REGISTRY")
    print("="*80)

    if not sources:
        print("\nNo sources found")
        return

    for source in sources:
        tier_icon = {"TIER_1": "🟢", "TIER_2": "🔵", "TIER_3": "🟡", "TIER_4": "⚪"}.get(source["tier"], "⚪")
        status_icon = {"verified": "✅", "pending": "⏳", "failed": "❌"}.get(source["verification_status"], "⏳")

        print(f"\n{tier_icon} [{source['tier']}] {source['name']}")
        print(f"   URL: {source['url'][:60]}...")
        print(f"   Domain: {source['domain']} | Quality: {source['quality_score']} | Status: {status_icon}")
        if source.get("tags"):
            print(f"   Tags: {', '.join(source['tags'])}")

    print("\n" + "="*80)


def print_stats(stats: Dict):
    """Print statistics."""
    print("\n" + "="*60)
    print("SOURCE REGISTRY STATISTICS")
    print("="*60)

    print(f"\nTotal Sources: {stats['total_sources']}")
    print(f"Average Quality: {stats['avg_quality_score']}")

    print("\nBy Tier:")
    for tier, count in stats["by_tier"].items():
        print(f"  {tier}: {count}")

    print("\nBy Domain:")
    for domain, count in stats["by_domain"].items():
        print(f"  {domain}: {count}")

    print("\nBy Status:")
    for status, count in stats["by_status"].items():
        print(f"  {status}: {count}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Unified Source Registry")
    parser.add_argument("--list", "-l", action="store_true", help="List all sources")
    parser.add_argument("--add", "-a", help="Add source URL")
    parser.add_argument("--tier", help="Source tier (TIER_1-4)")
    parser.add_argument("--domain", help="Source domain category")
    parser.add_argument("--name", help="Source name")
    parser.add_argument("--description", help="Source description")
    parser.add_argument("--lookup", help="Lookup source by URL")
    parser.add_argument("--search", "-s", help="Search sources")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--remove", help="Remove source by URL")
    parser.add_argument("--export", help="Export format (json|csv)")
    parser.add_argument("--init", action="store_true", help="Initialize default sources")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.init:
        init_default_sources()
        print("✅ Default sources initialized")
        return 0

    if args.add:
        source = add_source(
            args.add,
            tier=args.tier,
            domain=args.domain or "general",
            name=args.name,
            description=args.description or "",
        )
        if args.json:
            print(json.dumps(asdict(source), indent=2))
        else:
            print(f"✅ Added: {source.name} ({source.tier})")
        return 0

    if args.lookup:
        source = lookup_source(args.lookup)
        if source:
            if args.json:
                print(json.dumps(source, indent=2))
            else:
                print_sources([source])
        else:
            print(f"❌ Source not found: {args.lookup}")
        return 0

    if args.search:
        results = search_sources(args.search)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_sources(results)
        return 0

    if args.remove:
        if remove_source(args.remove):
            print(f"✅ Removed: {args.remove}")
        else:
            print(f"❌ Source not found: {args.remove}")
        return 0

    if args.export:
        output = export_registry(args.export)
        print(output)
        return 0

    if args.stats:
        stats = get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print_stats(stats)
        return 0

    if args.list:
        sources = list_sources(tier=args.tier, domain=args.domain)
        if args.json:
            print(json.dumps(sources, indent=2))
        else:
            print_sources(sources)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
