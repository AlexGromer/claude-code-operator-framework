#!/usr/bin/env python3
"""
Context Manager (GAP-DATA-AGENT-001)

Manages agent memory and context persistence.
Implements tiered memory with TTL and prioritization.

Usage:
    python context_manager.py --save "key" "value"
    python context_manager.py --load "key"
    python context_manager.py --list
    python context_manager.py --cleanup
"""

import argparse
import json
import sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
CONTEXT_DIR = DATA_DIR / "context"
INDEX_FILE = CONTEXT_DIR / "index.json"

# Memory tiers
MEMORY_TIERS = {
    "working": {"ttl_hours": 1, "max_items": 100},      # Short-term working memory
    "session": {"ttl_hours": 24, "max_items": 500},    # Session-level memory
    "persistent": {"ttl_hours": 720, "max_items": 1000}, # Long-term (30 days)
    "permanent": {"ttl_hours": None, "max_items": None},  # Never expires
}


@dataclass
class ContextEntry:
    """Single context entry."""
    key: str
    value: Any
    tier: str
    created: str
    accessed: str
    access_count: int
    expires: Optional[str]
    tags: List[str]
    hash: str


def ensure_dirs():
    """Ensure directories exist."""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


def compute_hash(value: Any) -> str:
    """Compute hash of value."""
    content = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def load_index() -> Dict[str, Dict]:
    """Load context index."""
    ensure_dirs()
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return {}


def save_index(index: Dict):
    """Save context index."""
    ensure_dirs()
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def save_context(key: str, value: Any, tier: str = "session", tags: List[str] = None) -> ContextEntry:
    """Save context entry."""
    now = datetime.now()
    tier_config = MEMORY_TIERS.get(tier, MEMORY_TIERS["session"])

    # Calculate expiry
    expires = None
    if tier_config["ttl_hours"]:
        expires = (now + timedelta(hours=tier_config["ttl_hours"])).isoformat()

    entry = ContextEntry(
        key=key,
        value=value,
        tier=tier,
        created=now.isoformat(),
        accessed=now.isoformat(),
        access_count=1,
        expires=expires,
        tags=tags or [],
        hash=compute_hash(value),
    )

    # Save to file
    entry_file = CONTEXT_DIR / f"{key}.json"
    with open(entry_file, "w") as f:
        json.dump(asdict(entry), f, indent=2)

    # Update index
    index = load_index()
    index[key] = {
        "tier": tier,
        "created": entry.created,
        "expires": entry.expires,
        "hash": entry.hash,
    }
    save_index(index)

    return entry


def load_context(key: str) -> Optional[ContextEntry]:
    """Load context entry."""
    entry_file = CONTEXT_DIR / f"{key}.json"
    if not entry_file.exists():
        return None

    data = json.loads(entry_file.read_text())
    entry = ContextEntry(**data)

    # Check expiry
    if entry.expires:
        if datetime.fromisoformat(entry.expires) < datetime.now():
            # Expired - remove
            delete_context(key)
            return None

    # Update access stats
    entry.accessed = datetime.now().isoformat()
    entry.access_count += 1

    with open(entry_file, "w") as f:
        json.dump(asdict(entry), f, indent=2)

    return entry


def delete_context(key: str) -> bool:
    """Delete context entry."""
    entry_file = CONTEXT_DIR / f"{key}.json"
    if entry_file.exists():
        entry_file.unlink()

    index = load_index()
    if key in index:
        del index[key]
        save_index(index)
        return True
    return False


def list_context(tier: str = None, tag: str = None) -> List[Dict]:
    """List context entries."""
    ensure_dirs()
    entries = []

    for f in CONTEXT_DIR.glob("*.json"):
        if f.name == "index.json":
            continue

        try:
            data = json.loads(f.read_text())

            # Filter by tier
            if tier and data.get("tier") != tier:
                continue

            # Filter by tag
            if tag and tag not in data.get("tags", []):
                continue

            entries.append({
                "key": data["key"],
                "tier": data["tier"],
                "created": data["created"],
                "accessed": data["accessed"],
                "access_count": data["access_count"],
                "expires": data.get("expires"),
                "expired": data.get("expires") and datetime.fromisoformat(data["expires"]) < datetime.now(),
            })
        except Exception:
            pass

    # Sort by access count (most accessed first)
    entries.sort(key=lambda x: x["access_count"], reverse=True)
    return entries


def cleanup_expired() -> int:
    """Remove expired entries."""
    removed = 0
    now = datetime.now()

    for f in CONTEXT_DIR.glob("*.json"):
        if f.name == "index.json":
            continue

        try:
            data = json.loads(f.read_text())
            if data.get("expires"):
                if datetime.fromisoformat(data["expires"]) < now:
                    delete_context(data["key"])
                    removed += 1
        except Exception:
            pass

    return removed


def enforce_limits():
    """Enforce tier limits by removing least accessed items."""
    for tier, config in MEMORY_TIERS.items():
        if config["max_items"] is None:
            continue

        entries = list_context(tier=tier)
        if len(entries) > config["max_items"]:
            # Remove least accessed
            to_remove = entries[config["max_items"]:]
            for entry in to_remove:
                delete_context(entry["key"])


def get_stats() -> Dict:
    """Get context storage statistics."""
    entries = list_context()

    stats = {
        "total_entries": len(entries),
        "by_tier": {},
        "expired": 0,
        "total_accesses": 0,
    }

    for tier in MEMORY_TIERS:
        tier_entries = [e for e in entries if e["tier"] == tier]
        stats["by_tier"][tier] = len(tier_entries)

    stats["expired"] = len([e for e in entries if e.get("expired")])
    stats["total_accesses"] = sum(e["access_count"] for e in entries)

    return stats


def search_context(query: str) -> List[Dict]:
    """Search context by key pattern."""
    entries = list_context()
    return [e for e in entries if query.lower() in e["key"].lower()]


def print_entries(entries: List[Dict]):
    """Print context entries."""
    print("\n" + "="*60)
    print("CONTEXT ENTRIES")
    print("="*60)

    if not entries:
        print("\nNo entries found")
        return

    for entry in entries[:20]:
        status = "❌ EXPIRED" if entry.get("expired") else "✅"
        print(f"\n  {status} {entry['key']} [{entry['tier']}]")
        print(f"      Accesses: {entry['access_count']}")
        print(f"      Created: {entry['created'][:10]}")
        if entry.get("expires"):
            print(f"      Expires: {entry['expires'][:10]}")

    if len(entries) > 20:
        print(f"\n  ... and {len(entries) - 20} more")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Context Manager")
    parser.add_argument("--save", "-s", nargs=2, metavar=("KEY", "VALUE"), help="Save context")
    parser.add_argument("--load", "-l", help="Load context by key")
    parser.add_argument("--delete", "-d", help="Delete context by key")
    parser.add_argument("--list", action="store_true", help="List all entries")
    parser.add_argument("--tier", "-t", choices=list(MEMORY_TIERS.keys()), help="Filter by tier")
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument("--search", help="Search by key pattern")
    parser.add_argument("--cleanup", "-c", action="store_true", help="Cleanup expired")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.save:
        key, value = args.save
        # Try to parse as JSON
        try:
            value = json.loads(value)
        except Exception:
            pass
        entry = save_context(key, value, tier=args.tier or "session")
        print(f"Saved: {entry.key} [{entry.tier}]")
        return 0

    if args.load:
        entry = load_context(args.load)
        if entry:
            if args.json:
                print(json.dumps(asdict(entry), indent=2))
            else:
                print(f"\nKey: {entry.key}")
                print(f"Tier: {entry.tier}")
                print(f"Value: {entry.value}")
                print(f"Accesses: {entry.access_count}")
        else:
            print(f"Not found: {args.load}")
        return 0

    if args.delete:
        if delete_context(args.delete):
            print(f"Deleted: {args.delete}")
        else:
            print(f"Not found: {args.delete}")
        return 0

    if args.cleanup:
        removed = cleanup_expired()
        enforce_limits()
        print(f"Cleaned up {removed} expired entries")
        return 0

    if args.stats:
        stats = get_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"\nTotal entries: {stats['total_entries']}")
            print(f"By tier: {stats['by_tier']}")
            print(f"Expired: {stats['expired']}")
            print(f"Total accesses: {stats['total_accesses']}")
        return 0

    if args.search:
        entries = search_context(args.search)
        if args.json:
            print(json.dumps(entries, indent=2))
        else:
            print_entries(entries)
        return 0

    if args.list:
        entries = list_context(tier=args.tier, tag=args.tag)
        if args.json:
            print(json.dumps(entries, indent=2))
        else:
            print_entries(entries)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
