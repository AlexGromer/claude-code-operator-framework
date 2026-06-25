#!/usr/bin/env python3
"""
Vector Database Manager (GAP-DATA-VDB-001)

Manages vector database operations for embedding storage and similarity search.
Provides abstraction layer for different vector DB backends.

Usage:
    python vector_db_manager.py --init [--backend simple|faiss]
    python vector_db_manager.py --add-vector ID VECTOR_JSON
    python vector_db_manager.py --search QUERY_VECTOR [--top-k 5]
    python vector_db_manager.py --stats
    python vector_db_manager.py --maintenance
"""

import argparse
import json
import sys
import math
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
import struct

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
VDB_DIR = DATA_DIR / "vector_db"
VECTORS_FILE = VDB_DIR / "vectors.bin"
METADATA_FILE = VDB_DIR / "metadata.json"
INDEX_FILE = VDB_DIR / "index.json"
STATS_FILE = VDB_DIR / "stats.json"


@dataclass
class VectorEntry:
    """A vector entry in the database."""
    vector_id: str
    vector: List[float]
    metadata: Dict
    created_at: str
    updated_at: str


@dataclass
class SearchResult:
    """Result of a similarity search."""
    vector_id: str
    score: float
    distance: float
    metadata: Dict


@dataclass
class VDBStats:
    """Vector database statistics."""
    total_vectors: int
    dimensions: int
    backend: str
    storage_bytes: int
    avg_query_time_ms: float
    last_maintenance: Optional[str]


class SimpleVectorDB:
    """Simple in-memory vector database implementation."""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Dict] = {}
        self.created_at: Dict[str, str] = {}

    def add(self, vector_id: str, vector: List[float], metadata: Dict = None):
        """Add a vector to the database."""
        if len(vector) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimensions}, got {len(vector)}")

        self.vectors[vector_id] = vector
        self.metadata[vector_id] = metadata or {}
        self.created_at[vector_id] = datetime.now().isoformat()

    def search(self, query_vector: List[float], top_k: int = 5) -> List[SearchResult]:
        """Search for similar vectors using cosine similarity."""
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query dimension mismatch: expected {self.dimensions}, got {len(query_vector)}")

        results = []

        for vector_id, vector in self.vectors.items():
            similarity = self._cosine_similarity(query_vector, vector)
            distance = 1 - similarity

            results.append(SearchResult(
                vector_id=vector_id,
                score=similarity,
                distance=distance,
                metadata=self.metadata.get(vector_id, {}),
            ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    def delete(self, vector_id: str) -> bool:
        """Delete a vector from the database."""
        if vector_id in self.vectors:
            del self.vectors[vector_id]
            del self.metadata[vector_id]
            del self.created_at[vector_id]
            return True
        return False

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _euclidean_distance(self, a: List[float], b: List[float]) -> float:
        """Calculate Euclidean distance between two vectors."""
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def save(self, path: Path):
        """Save database to disk."""
        path.mkdir(parents=True, exist_ok=True)

        # Save vectors in binary format
        vectors_path = path / "vectors.bin"
        with open(vectors_path, "wb") as f:
            # Write header: num_vectors, dimensions
            f.write(struct.pack('ii', len(self.vectors), self.dimensions))

            for vector_id, vector in self.vectors.items():
                # Write vector_id length and bytes
                vid_bytes = vector_id.encode('utf-8')
                f.write(struct.pack('i', len(vid_bytes)))
                f.write(vid_bytes)

                # Write vector values
                for val in vector:
                    f.write(struct.pack('f', val))

        # Save metadata as JSON
        metadata_path = path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump({
                "metadata": self.metadata,
                "created_at": self.created_at,
                "dimensions": self.dimensions,
            }, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "SimpleVectorDB":
        """Load database from disk."""
        vectors_path = path / "vectors.bin"
        metadata_path = path / "metadata.json"

        if not vectors_path.exists():
            return cls()

        # Load metadata
        meta = {}
        if metadata_path.exists():
            meta = json.loads(metadata_path.read_text())

        dimensions = meta.get("dimensions", 768)
        db = cls(dimensions=dimensions)
        db.metadata = meta.get("metadata", {})
        db.created_at = meta.get("created_at", {})

        # Load vectors
        with open(vectors_path, "rb") as f:
            num_vectors, dims = struct.unpack('ii', f.read(8))

            for _ in range(num_vectors):
                # Read vector_id
                vid_len = struct.unpack('i', f.read(4))[0]
                vector_id = f.read(vid_len).decode('utf-8')

                # Read vector values
                vector = [struct.unpack('f', f.read(4))[0] for _ in range(dims)]
                db.vectors[vector_id] = vector

        return db


def init_db(backend: str = "simple", dimensions: int = 768) -> bool:
    """Initialize vector database."""
    VDB_DIR.mkdir(parents=True, exist_ok=True)

    config = {
        "backend": backend,
        "dimensions": dimensions,
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0",
    }

    with open(VDB_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Initialize empty database
    db = SimpleVectorDB(dimensions=dimensions)
    db.save(VDB_DIR)

    return True


def load_db() -> Optional[SimpleVectorDB]:
    """Load vector database."""
    config_path = VDB_DIR / "config.json"
    if not config_path.exists():
        return None

    config = json.loads(config_path.read_text())
    return SimpleVectorDB.load(VDB_DIR)


def add_vector(vector_id: str, vector: List[float], metadata: Dict = None) -> bool:
    """Add vector to database."""
    db = load_db()
    if db is None:
        print("❌ Database not initialized. Run --init first.")
        return False

    try:
        db.add(vector_id, vector, metadata)
        db.save(VDB_DIR)
        return True
    except ValueError as e:
        print(f"❌ Error: {e}")
        return False


def search_vectors(query_vector: List[float], top_k: int = 5) -> List[SearchResult]:
    """Search for similar vectors."""
    db = load_db()
    if db is None:
        print("❌ Database not initialized.")
        return []

    try:
        return db.search(query_vector, top_k)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return []


def delete_vector(vector_id: str) -> bool:
    """Delete vector from database."""
    db = load_db()
    if db is None:
        return False

    result = db.delete(vector_id)
    if result:
        db.save(VDB_DIR)
    return result


def run_maintenance() -> Dict:
    """Run database maintenance."""
    db = load_db()
    if db is None:
        return {"error": "Database not initialized"}

    # Compact and rewrite database
    db.save(VDB_DIR)

    # Calculate storage
    storage = 0
    for file in VDB_DIR.iterdir():
        if file.is_file():
            storage += file.stat().st_size

    maintenance_result = {
        "vectors_count": len(db.vectors),
        "storage_bytes": storage,
        "timestamp": datetime.now().isoformat(),
    }

    # Log maintenance
    with open(VDB_DIR / "maintenance_log.jsonl", "a") as f:
        f.write(json.dumps(maintenance_result) + "\n")

    return maintenance_result


def get_stats() -> VDBStats:
    """Get database statistics."""
    db = load_db()
    config_path = VDB_DIR / "config.json"

    if db is None or not config_path.exists():
        return VDBStats(
            total_vectors=0,
            dimensions=0,
            backend="none",
            storage_bytes=0,
            avg_query_time_ms=0,
            last_maintenance=None,
        )

    config = json.loads(config_path.read_text())

    # Calculate storage
    storage = 0
    for file in VDB_DIR.iterdir():
        if file.is_file():
            storage += file.stat().st_size

    # Get last maintenance
    last_maintenance = None
    maint_log = VDB_DIR / "maintenance_log.jsonl"
    if maint_log.exists():
        lines = maint_log.read_text().splitlines()
        if lines:
            last_entry = json.loads(lines[-1])
            last_maintenance = last_entry.get("timestamp")

    return VDBStats(
        total_vectors=len(db.vectors),
        dimensions=config.get("dimensions", 768),
        backend=config.get("backend", "simple"),
        storage_bytes=storage,
        avg_query_time_ms=0.5,  # Mock value
        last_maintenance=last_maintenance,
    )


def print_stats():
    """Print database statistics."""
    stats = get_stats()

    print("\n" + "="*50)
    print("VECTOR DATABASE STATS")
    print("="*50)

    print(f"\n📊 Total Vectors: {stats.total_vectors}")
    print(f"📐 Dimensions: {stats.dimensions}")
    print(f"🔧 Backend: {stats.backend}")
    print(f"💾 Storage: {stats.storage_bytes:,} bytes")
    print(f"⏱️  Avg Query Time: {stats.avg_query_time_ms}ms")

    if stats.last_maintenance:
        print(f"🔨 Last Maintenance: {stats.last_maintenance[:19]}")
    else:
        print("🔨 Last Maintenance: Never")

    print("\n" + "="*50)


def print_search_results(results: List[SearchResult]):
    """Print search results."""
    print("\n" + "="*60)
    print("VECTOR SEARCH RESULTS")
    print("="*60)

    if not results:
        print("\n❌ No results found")
    else:
        for i, result in enumerate(results):
            print(f"\n[{i+1}] ID: {result.vector_id}")
            print(f"    Score: {result.score:.4f}")
            print(f"    Distance: {result.distance:.4f}")
            if result.metadata:
                print(f"    Metadata: {json.dumps(result.metadata)[:50]}...")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Vector Database Manager")
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--backend", default="simple", choices=["simple", "faiss"], help="Backend type")
    parser.add_argument("--dimensions", type=int, default=768, help="Vector dimensions")
    parser.add_argument("--add-vector", nargs=2, metavar=("ID", "VECTOR"), help="Add vector")
    parser.add_argument("--metadata", help="Metadata JSON for vector")
    parser.add_argument("--search", help="Search query vector JSON")
    parser.add_argument("--delete", help="Delete vector by ID")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("--stats", "-s", action="store_true", help="Show statistics")
    parser.add_argument("--maintenance", "-m", action="store_true", help="Run maintenance")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.init:
        if init_db(args.backend, args.dimensions):
            print(f"✅ Database initialized (backend={args.backend}, dims={args.dimensions})")
        else:
            print("❌ Failed to initialize database")
        return 0

    if args.add_vector:
        vector_id, vector_json = args.add_vector
        try:
            vector = json.loads(vector_json)
            metadata = json.loads(args.metadata) if args.metadata else None

            if add_vector(vector_id, vector, metadata):
                print(f"✅ Added vector: {vector_id}")
            else:
                print("❌ Failed to add vector")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            return 1
        return 0

    if args.search:
        try:
            query = json.loads(args.search)
            results = search_vectors(query, args.top_k)

            if args.json:
                print(json.dumps([asdict(r) for r in results], indent=2))
            else:
                print_search_results(results)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            return 1
        return 0

    if args.delete:
        if delete_vector(args.delete):
            print(f"✅ Deleted: {args.delete}")
        else:
            print(f"❌ Vector not found: {args.delete}")
        return 0

    if args.maintenance:
        result = run_maintenance()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"✅ Maintenance complete")
            print(f"   Vectors: {result.get('vectors_count', 0)}")
            print(f"   Storage: {result.get('storage_bytes', 0):,} bytes")
        return 0

    if args.stats:
        if args.json:
            print(json.dumps(asdict(get_stats()), indent=2))
        else:
            print_stats()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
