#!/usr/bin/env python3
"""
MemGPT/Letta Context Tool (GAP-MEM-001)

Implements tiered memory management inspired by MemGPT/Letta.
Manages core memory, archival memory, and recall mechanisms.

Usage:
    python memgpt_context_tool.py --add-core KEY VALUE
    python memgpt_context_tool.py --archive DATA
    python memgpt_context_tool.py --recall QUERY
    python memgpt_context_tool.py --status
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
import hashlib

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
MEMORY_DIR = DATA_DIR / "memgpt_memory"
CORE_FILE = MEMORY_DIR / "core_memory.json"
ARCHIVAL_FILE = MEMORY_DIR / "archival_memory.jsonl"
RECALL_INDEX = MEMORY_DIR / "recall_index.json"

# Memory limits (tokens approximated as chars/4)
CORE_MEMORY_LIMIT = 2000  # ~500 tokens
WORKING_MEMORY_LIMIT = 8000  # ~2000 tokens


@dataclass
class CoreMemoryBlock:
    """A block in core memory."""
    key: str
    value: str
    created_at: str
    updated_at: str
    access_count: int = 0
    priority: int = 0


@dataclass
class ArchivalEntry:
    """An entry in archival memory."""
    entry_id: str
    content: str
    tags: List[str]
    created_at: str
    source: str
    embedding_hash: str = ""


@dataclass
class RecallResult:
    """Result of a recall query."""
    query: str
    results: List[Dict]
    source: str  # core, archival, or both
    relevance_scores: List[float]
    timestamp: str


def generate_entry_id() -> str:
    """Generate unique entry ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"arch-{timestamp[:17]}"


def simple_hash(text: str) -> str:
    """Generate simple hash for text (placeholder for embeddings)."""
    return hashlib.md5(text.encode()).hexdigest()[:16]


def load_core_memory() -> Dict[str, CoreMemoryBlock]:
    """Load core memory."""
    if CORE_FILE.exists():
        data = json.loads(CORE_FILE.read_text())
        return {k: CoreMemoryBlock(**v) for k, v in data.items()}
    return {}


def save_core_memory(memory: Dict[str, CoreMemoryBlock]):
    """Save core memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    data = {k: asdict(v) for k, v in memory.items()}
    with open(CORE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_core_memory_size(memory: Dict[str, CoreMemoryBlock]) -> int:
    """Get total size of core memory."""
    total = 0
    for block in memory.values():
        total += len(block.key) + len(block.value)
    return total


def add_to_core(key: str, value: str, priority: int = 0) -> bool:
    """Add or update core memory."""
    memory = load_core_memory()
    now = datetime.now().isoformat()

    if key in memory:
        memory[key].value = value
        memory[key].updated_at = now
        memory[key].priority = priority
    else:
        memory[key] = CoreMemoryBlock(
            key=key,
            value=value,
            created_at=now,
            updated_at=now,
            priority=priority,
        )

    # Check size limit
    while get_core_memory_size(memory) > CORE_MEMORY_LIMIT:
        # Evict lowest priority, oldest item
        candidates = sorted(
            memory.items(),
            key=lambda x: (x[1].priority, -x[1].access_count)
        )
        if candidates:
            evict_key = candidates[0][0]
            # Archive before eviction
            archive_entry(memory[evict_key].value, tags=["evicted", evict_key])
            del memory[evict_key]

    save_core_memory(memory)
    return True


def get_from_core(key: str) -> Optional[str]:
    """Get value from core memory."""
    memory = load_core_memory()
    if key in memory:
        memory[key].access_count += 1
        save_core_memory(memory)
        return memory[key].value
    return None


def archive_entry(content: str, tags: List[str] = None, source: str = "manual") -> str:
    """Archive content to archival memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    entry = ArchivalEntry(
        entry_id=generate_entry_id(),
        content=content,
        tags=tags or [],
        created_at=datetime.now().isoformat(),
        source=source,
        embedding_hash=simple_hash(content),
    )

    with open(ARCHIVAL_FILE, "a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")

    # Update recall index
    update_recall_index(entry)

    return entry.entry_id


def update_recall_index(entry: ArchivalEntry):
    """Update recall index with new entry."""
    index = {}
    if RECALL_INDEX.exists():
        index = json.loads(RECALL_INDEX.read_text())

    # Index by tags
    for tag in entry.tags:
        if tag not in index:
            index[tag] = []
        index[tag].append(entry.entry_id)

    # Index by words (simple)
    words = entry.content.lower().split()
    for word in set(words):
        if len(word) > 3:  # Skip short words
            if word not in index:
                index[word] = []
            if entry.entry_id not in index[word]:
                index[word].append(entry.entry_id)

    with open(RECALL_INDEX, "w") as f:
        json.dump(index, f)


def recall(query: str, limit: int = 5) -> RecallResult:
    """Recall relevant memories."""
    results = []
    relevance_scores = []
    source = "both"

    # Search core memory
    memory = load_core_memory()
    query_lower = query.lower()

    for key, block in memory.items():
        if query_lower in key.lower() or query_lower in block.value.lower():
            results.append({
                "type": "core",
                "key": key,
                "value": block.value[:200],
                "priority": block.priority,
            })
            relevance_scores.append(0.9)  # Core memory is highly relevant

    # Search archival memory
    if RECALL_INDEX.exists():
        index = json.loads(RECALL_INDEX.read_text())
        query_words = query_lower.split()

        # Find matching entry IDs
        matching_ids = set()
        for word in query_words:
            if word in index:
                matching_ids.update(index[word])

        # Load matching entries
        if ARCHIVAL_FILE.exists():
            entries = {}
            for line in ARCHIVAL_FILE.read_text().splitlines():
                if line.strip():
                    entry = json.loads(line)
                    if entry["entry_id"] in matching_ids:
                        entries[entry["entry_id"]] = entry

            for entry_id in list(matching_ids)[:limit]:
                if entry_id in entries:
                    entry = entries[entry_id]
                    results.append({
                        "type": "archival",
                        "entry_id": entry_id,
                        "content": entry["content"][:200],
                        "tags": entry["tags"],
                    })
                    relevance_scores.append(0.7)

    return RecallResult(
        query=query,
        results=results[:limit],
        source=source,
        relevance_scores=relevance_scores[:limit],
        timestamp=datetime.now().isoformat(),
    )


def get_memory_status() -> Dict:
    """Get memory status."""
    memory = load_core_memory()

    archival_count = 0
    if ARCHIVAL_FILE.exists():
        archival_count = sum(1 for line in ARCHIVAL_FILE.read_text().splitlines() if line.strip())

    return {
        "core_memory": {
            "entries": len(memory),
            "size": get_core_memory_size(memory),
            "limit": CORE_MEMORY_LIMIT,
            "usage_percent": round(get_core_memory_size(memory) / CORE_MEMORY_LIMIT * 100, 1),
        },
        "archival_memory": {
            "entries": archival_count,
        },
        "working_memory_limit": WORKING_MEMORY_LIMIT,
    }


def print_status():
    """Print memory status."""
    status = get_memory_status()

    print("\n" + "="*50)
    print("MEMGPT CONTEXT STATUS")
    print("="*50)

    core = status["core_memory"]
    print(f"\n📦 Core Memory:")
    print(f"   Entries: {core['entries']}")
    print(f"   Size: {core['size']}/{core['limit']} chars ({core['usage_percent']}%)")

    print(f"\n📚 Archival Memory:")
    print(f"   Entries: {status['archival_memory']['entries']}")

    print(f"\n💭 Working Memory Limit: {status['working_memory_limit']} chars")

    # Show core memory contents
    memory = load_core_memory()
    if memory:
        print("\n" + "-"*40)
        print("Core Memory Contents:")
        for key, block in sorted(memory.items(), key=lambda x: -x[1].priority):
            print(f"   [{block.priority}] {key}: {block.value[:30]}...")

    print("\n" + "="*50)


def main():
    parser = argparse.ArgumentParser(description="MemGPT Context Tool")
    parser.add_argument("--add-core", nargs=2, metavar=("KEY", "VALUE"), help="Add to core memory")
    parser.add_argument("--priority", type=int, default=0, help="Priority for core memory")
    parser.add_argument("--get-core", help="Get from core memory")
    parser.add_argument("--archive", help="Archive to archival memory")
    parser.add_argument("--tags", help="Tags for archival (comma-separated)")
    parser.add_argument("--recall", "-r", help="Recall memories by query")
    parser.add_argument("--limit", type=int, default=5, help="Recall limit")
    parser.add_argument("--status", "-s", action="store_true", help="Show memory status")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.add_core:
        key, value = args.add_core
        if add_to_core(key, value, args.priority):
            print(f"✅ Added to core memory: {key}")
        return 0

    if args.get_core:
        value = get_from_core(args.get_core)
        if value:
            print(value)
        else:
            print(f"❌ Key not found: {args.get_core}")
        return 0

    if args.archive:
        tags = args.tags.split(",") if args.tags else []
        entry_id = archive_entry(args.archive, tags)
        print(f"✅ Archived: {entry_id}")
        return 0

    if args.recall:
        result = recall(args.recall, args.limit)
        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            print(f"\n🔍 Recall: '{args.recall}'")
            print(f"   Found: {len(result.results)} results")
            for i, r in enumerate(result.results):
                if r["type"] == "core":
                    print(f"\n   [{i+1}] Core: {r['key']}")
                    print(f"       {r['value'][:60]}...")
                else:
                    print(f"\n   [{i+1}] Archival: {r['entry_id']}")
                    print(f"       {r['content'][:60]}...")
        return 0

    if args.status:
        if args.json:
            print(json.dumps(get_memory_status(), indent=2))
        else:
            print_status()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
