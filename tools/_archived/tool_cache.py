#!/usr/bin/env python3
"""
Tool Call Cache (GAP-GATEWAY-AGENT-003)

Caches tool call results to avoid redundant executions.
Implements TTL, invalidation, and cache statistics.

Usage:
    python tool_cache.py --get "tool:args_hash"
    python tool_cache.py --set "tool:args_hash" "result"
    python tool_cache.py --stats
    python tool_cache.py --cleanup
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
CACHE_DIR = DATA_DIR / "tool_cache"
INDEX_FILE = CACHE_DIR / "index.json"

# Cache configuration
CACHE_CONFIG = {
    "default_ttl_seconds": 300,  # 5 minutes default
    "max_entries": 1000,
    "max_size_bytes": 50 * 1024 * 1024,  # 50MB
    "tool_ttls": {
        # Tool-specific TTLs
        "Read": 60,           # File reads - 1 minute
        "Glob": 120,          # File patterns - 2 minutes
        "Grep": 120,          # Search results - 2 minutes
        "Bash": 30,           # Command results - 30 seconds (more volatile)
        "WebFetch": 600,      # Web content - 10 minutes
        "WebSearch": 900,     # Search results - 15 minutes
        "mcp__github__": 300, # GitHub API - 5 minutes
    },
    # Non-cacheable tools (side effects)
    "no_cache": [
        "Write", "Edit", "NotebookEdit",
        "Task", "TaskCreate", "TaskUpdate",
        "AskUserQuestion", "Bash",  # Bash with side effects
    ],
}


@dataclass
class CacheEntry:
    """Single cache entry."""
    key: str
    tool: str
    args_hash: str
    result: Any
    created: str
    expires: str
    hits: int
    size_bytes: int


@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int
    total_size_bytes: int
    hits: int
    misses: int
    hit_rate: float
    oldest_entry: str
    newest_entry: str
    by_tool: Dict[str, int]


def ensure_dirs():
    """Ensure directories exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def compute_key(tool: str, args: Any) -> str:
    """Compute cache key from tool and args."""
    args_str = json.dumps(args, sort_keys=True, default=str)
    args_hash = hashlib.sha256(args_str.encode()).hexdigest()[:16]
    return f"{tool}:{args_hash}"


def get_ttl(tool: str) -> int:
    """Get TTL for tool."""
    for prefix, ttl in CACHE_CONFIG["tool_ttls"].items():
        if tool.startswith(prefix):
            return ttl
    return CACHE_CONFIG["default_ttl_seconds"]


def is_cacheable(tool: str, args: Any = None) -> bool:
    """Check if tool call is cacheable."""
    # Check no-cache list
    for nc in CACHE_CONFIG["no_cache"]:
        if tool.startswith(nc):
            return False

    # Special case: Bash is cacheable only for read-only commands
    if tool == "Bash" and args:
        command = args.get("command", "") if isinstance(args, dict) else str(args)
        read_only_patterns = ["ls", "cat", "head", "tail", "grep", "find", "which", "echo", "pwd", "date"]
        is_read_only = any(command.strip().startswith(p) for p in read_only_patterns)
        return is_read_only

    return True


def load_index() -> Dict:
    """Load cache index."""
    ensure_dirs()
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return {"entries": {}, "stats": {"hits": 0, "misses": 0}}


def save_index(index: Dict):
    """Save cache index."""
    ensure_dirs()
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def get(key: str) -> Optional[Any]:
    """Get cached result."""
    index = load_index()

    if key not in index["entries"]:
        index["stats"]["misses"] = index["stats"].get("misses", 0) + 1
        save_index(index)
        return None

    entry = index["entries"][key]

    # Check expiry
    if datetime.fromisoformat(entry["expires"]) < datetime.now():
        # Expired
        del index["entries"][key]
        index["stats"]["misses"] = index["stats"].get("misses", 0) + 1
        save_index(index)
        return None

    # Valid hit
    entry["hits"] = entry.get("hits", 0) + 1
    index["entries"][key] = entry
    index["stats"]["hits"] = index["stats"].get("hits", 0) + 1
    save_index(index)

    return entry["result"]


def set(key: str, tool: str, args: Any, result: Any, ttl: int = None) -> bool:
    """Set cache entry."""
    if not is_cacheable(tool, args):
        return False

    index = load_index()

    # Enforce max entries
    if len(index["entries"]) >= CACHE_CONFIG["max_entries"]:
        # Remove oldest entries
        sorted_entries = sorted(
            index["entries"].items(),
            key=lambda x: x[1].get("created", "")
        )
        for old_key, _ in sorted_entries[:100]:  # Remove 100 oldest
            del index["entries"][old_key]

    # Calculate TTL
    if ttl is None:
        ttl = get_ttl(tool)

    now = datetime.now()
    expires = now + timedelta(seconds=ttl)

    # Serialize result
    result_str = json.dumps(result, default=str)
    size_bytes = len(result_str.encode())

    entry = {
        "key": key,
        "tool": tool,
        "args_hash": key.split(":")[-1],
        "result": result,
        "created": now.isoformat(),
        "expires": expires.isoformat(),
        "hits": 0,
        "size_bytes": size_bytes,
    }

    index["entries"][key] = entry
    save_index(index)
    return True


def delete(key: str) -> bool:
    """Delete cache entry."""
    index = load_index()
    if key in index["entries"]:
        del index["entries"][key]
        save_index(index)
        return True
    return False


def invalidate_tool(tool: str) -> int:
    """Invalidate all entries for a tool."""
    index = load_index()
    removed = 0

    keys_to_remove = [k for k in index["entries"] if k.startswith(f"{tool}:")]
    for key in keys_to_remove:
        del index["entries"][key]
        removed += 1

    if removed > 0:
        save_index(index)
    return removed


def cleanup_expired() -> int:
    """Remove expired entries."""
    index = load_index()
    now = datetime.now()
    removed = 0

    keys_to_remove = []
    for key, entry in index["entries"].items():
        if datetime.fromisoformat(entry["expires"]) < now:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del index["entries"][key]
        removed += 1

    if removed > 0:
        save_index(index)
    return removed


def clear_all() -> int:
    """Clear entire cache."""
    index = load_index()
    count = len(index["entries"])
    index["entries"] = {}
    index["stats"] = {"hits": 0, "misses": 0}
    save_index(index)
    return count


def get_stats() -> CacheStats:
    """Get cache statistics."""
    index = load_index()
    entries = index["entries"]

    total_size = sum(e.get("size_bytes", 0) for e in entries.values())
    total_hits = index["stats"].get("hits", 0)
    total_misses = index["stats"].get("misses", 0)

    # Count by tool
    by_tool = {}
    for entry in entries.values():
        tool = entry.get("tool", "unknown")
        by_tool[tool] = by_tool.get(tool, 0) + 1

    # Find oldest/newest
    if entries:
        sorted_by_created = sorted(entries.values(), key=lambda x: x.get("created", ""))
        oldest = sorted_by_created[0]["created"]
        newest = sorted_by_created[-1]["created"]
    else:
        oldest = newest = ""

    return CacheStats(
        total_entries=len(entries),
        total_size_bytes=total_size,
        hits=total_hits,
        misses=total_misses,
        hit_rate=total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0,
        oldest_entry=oldest,
        newest_entry=newest,
        by_tool=by_tool,
    )


def list_entries(limit: int = 20) -> List[Dict]:
    """List cache entries."""
    index = load_index()
    entries = list(index["entries"].values())

    # Sort by hits (most used first)
    entries.sort(key=lambda x: x.get("hits", 0), reverse=True)

    return entries[:limit]


def print_stats(stats: CacheStats):
    """Print cache statistics."""
    print("\n" + "="*60)
    print("TOOL CACHE STATISTICS")
    print("="*60)

    print(f"\nEntries: {stats.total_entries}")
    print(f"Size: {stats.total_size_bytes / 1024:.1f} KB")
    print(f"Hits: {stats.hits}")
    print(f"Misses: {stats.misses}")
    print(f"Hit Rate: {stats.hit_rate:.1%}")

    if stats.oldest_entry:
        print(f"\nOldest: {stats.oldest_entry[:19]}")
        print(f"Newest: {stats.newest_entry[:19]}")

    if stats.by_tool:
        print(f"\nBy Tool:")
        for tool, count in sorted(stats.by_tool.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {tool}: {count}")

    print("\n" + "="*60)


def print_entries(entries: List[Dict]):
    """Print cache entries."""
    print("\n" + "="*60)
    print("CACHE ENTRIES")
    print("="*60)

    if not entries:
        print("\nNo entries found")
        return

    for entry in entries:
        expired = datetime.fromisoformat(entry["expires"]) < datetime.now()
        status = "❌ EXPIRED" if expired else "✅"
        print(f"\n  {status} {entry['key'][:50]}")
        print(f"      Tool: {entry['tool']}")
        print(f"      Hits: {entry['hits']}")
        print(f"      Size: {entry['size_bytes']} bytes")
        print(f"      Expires: {entry['expires'][:19]}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Tool Call Cache")
    parser.add_argument("--get", "-g", help="Get cached result by key")
    parser.add_argument("--set", "-s", nargs=3, metavar=("KEY", "TOOL", "RESULT"), help="Set cache entry")
    parser.add_argument("--delete", "-d", help="Delete entry by key")
    parser.add_argument("--invalidate", "-i", help="Invalidate all entries for tool")
    parser.add_argument("--cleanup", "-c", action="store_true", help="Cleanup expired")
    parser.add_argument("--clear", action="store_true", help="Clear all cache")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--list", "-l", action="store_true", help="List entries")
    parser.add_argument("--limit", type=int, default=20, help="Limit for list")
    parser.add_argument("--config", action="store_true", help="Show configuration")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.config:
        if args.json:
            print(json.dumps(CACHE_CONFIG, indent=2))
        else:
            print("\nCache Configuration:")
            print(f"  Default TTL: {CACHE_CONFIG['default_ttl_seconds']}s")
            print(f"  Max Entries: {CACHE_CONFIG['max_entries']}")
            print(f"  Max Size: {CACHE_CONFIG['max_size_bytes'] / 1024 / 1024:.0f}MB")
            print(f"\n  Tool TTLs:")
            for tool, ttl in CACHE_CONFIG["tool_ttls"].items():
                print(f"    {tool}: {ttl}s")
            print(f"\n  Non-Cacheable:")
            for tool in CACHE_CONFIG["no_cache"]:
                print(f"    {tool}")
        return 0

    if args.stats:
        stats = get_stats()
        if args.json:
            print(json.dumps(asdict(stats), indent=2))
        else:
            print_stats(stats)
        return 0

    if args.list:
        entries = list_entries(args.limit)
        if args.json:
            print(json.dumps(entries, indent=2))
        else:
            print_entries(entries)
        return 0

    if args.get:
        result = get(args.get)
        if result is not None:
            if args.json:
                print(json.dumps({"hit": True, "result": result}))
            else:
                print(f"Hit: {result}")
            return 0
        else:
            if args.json:
                print(json.dumps({"hit": False}))
            else:
                print("Miss")
            return 1

    if args.set:
        key, tool, result_str = args.set
        try:
            result = json.loads(result_str)
        except Exception:
            result = result_str
        success = set(key, tool, {}, result)
        print(f"Set: {'success' if success else 'failed (not cacheable)'}")
        return 0 if success else 1

    if args.delete:
        success = delete(args.delete)
        print(f"Delete: {'success' if success else 'not found'}")
        return 0 if success else 1

    if args.invalidate:
        count = invalidate_tool(args.invalidate)
        print(f"Invalidated {count} entries for {args.invalidate}")
        return 0

    if args.cleanup:
        count = cleanup_expired()
        print(f"Cleaned up {count} expired entries")
        return 0

    if args.clear:
        count = clear_all()
        print(f"Cleared {count} entries")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
