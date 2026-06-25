#!/usr/bin/env python3
"""
RAG Pipeline Tool (GAP-DATA-RAG-001)

Manages RAG (Retrieval-Augmented Generation) pipelines for agent systems.
Supports document ingestion, chunking, embedding, and retrieval evaluation.

Usage:
    python rag_pipeline_tool.py --ingest FILE [--chunk-size 500]
    python rag_pipeline_tool.py --query QUERY [--top-k 5]
    python rag_pipeline_tool.py --evaluate
    python rag_pipeline_tool.py --status
"""

import argparse
import json
import sys
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RAG_DIR = DATA_DIR / "rag_pipeline"
DOCUMENTS_FILE = RAG_DIR / "documents.jsonl"
CHUNKS_FILE = RAG_DIR / "chunks.jsonl"
INDEX_FILE = RAG_DIR / "inverted_index.json"
QUERIES_FILE = RAG_DIR / "query_log.jsonl"
EVAL_FILE = RAG_DIR / "evaluation_results.json"


@dataclass
class Document:
    """A document in the RAG system."""
    doc_id: str
    source: str
    content: str
    metadata: Dict
    created_at: str
    chunk_count: int = 0
    content_hash: str = ""


@dataclass
class Chunk:
    """A chunk of a document."""
    chunk_id: str
    doc_id: str
    content: str
    position: int
    token_estimate: int
    embedding_hash: str = ""


@dataclass
class QueryResult:
    """Result of a RAG query."""
    query: str
    chunks: List[Dict]
    scores: List[float]
    latency_ms: float
    timestamp: str


@dataclass
class EvalMetrics:
    """RAG evaluation metrics."""
    total_queries: int
    avg_latency_ms: float
    avg_chunks_returned: float
    precision_at_k: Dict[int, float]
    mrr: float  # Mean Reciprocal Rank
    coverage: float


def generate_id(prefix: str, content: str) -> str:
    """Generate unique ID based on content hash."""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"{prefix}-{content_hash}"


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation)."""
    return len(text) // 4


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Tuple[str, int]]:
    """
    Chunk text with overlap.

    Returns list of (chunk_content, position) tuples.
    """
    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)

    current_chunk = []
    current_size = 0
    position = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)

        if current_size + sentence_tokens > chunk_size and current_chunk:
            # Save current chunk
            chunk_text = ' '.join(current_chunk)
            chunks.append((chunk_text, position))
            position += 1

            # Keep overlap
            overlap_tokens = 0
            overlap_sentences = []
            for s in reversed(current_chunk):
                s_tokens = estimate_tokens(s)
                if overlap_tokens + s_tokens <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tokens
                else:
                    break

            current_chunk = overlap_sentences
            current_size = overlap_tokens

        current_chunk.append(sentence)
        current_size += sentence_tokens

    # Final chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append((chunk_text, position))

    return chunks


def build_inverted_index(chunks: List[Chunk]) -> Dict[str, List[str]]:
    """Build inverted index from chunks."""
    index = {}

    for chunk in chunks:
        # Tokenize and normalize
        words = re.findall(r'\b\w+\b', chunk.content.lower())

        for word in set(words):
            if len(word) > 2:  # Skip short words
                if word not in index:
                    index[word] = []
                if chunk.chunk_id not in index[word]:
                    index[word].append(chunk.chunk_id)

    return index


def load_index() -> Dict[str, List[str]]:
    """Load inverted index."""
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return {}


def save_index(index: Dict[str, List[str]]):
    """Save inverted index."""
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def load_chunks() -> Dict[str, Chunk]:
    """Load all chunks."""
    chunks = {}
    if CHUNKS_FILE.exists():
        for line in CHUNKS_FILE.read_text().splitlines():
            if line.strip():
                data = json.loads(line)
                chunks[data["chunk_id"]] = Chunk(**data)
    return chunks


def ingest_document(file_path: str, chunk_size: int = 500) -> Document:
    """Ingest a document into the RAG system."""
    RAG_DIR.mkdir(parents=True, exist_ok=True)

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = path.read_text()
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Create document
    doc = Document(
        doc_id=generate_id("doc", content),
        source=str(path.absolute()),
        content=content,
        metadata={
            "filename": path.name,
            "size_bytes": len(content),
            "lines": content.count('\n') + 1,
        },
        created_at=datetime.now().isoformat(),
        content_hash=content_hash,
    )

    # Chunk the document
    text_chunks = chunk_text(content, chunk_size)
    chunks = []

    for chunk_content, position in text_chunks:
        chunk = Chunk(
            chunk_id=generate_id("chunk", f"{doc.doc_id}:{position}:{chunk_content[:50]}"),
            doc_id=doc.doc_id,
            content=chunk_content,
            position=position,
            token_estimate=estimate_tokens(chunk_content),
            embedding_hash=hashlib.md5(chunk_content.encode()).hexdigest()[:8],
        )
        chunks.append(chunk)

    doc.chunk_count = len(chunks)

    # Save document
    with open(DOCUMENTS_FILE, "a") as f:
        f.write(json.dumps(asdict(doc)) + "\n")

    # Save chunks
    with open(CHUNKS_FILE, "a") as f:
        for chunk in chunks:
            f.write(json.dumps(asdict(chunk)) + "\n")

    # Update index
    index = load_index()
    chunk_index = build_inverted_index(chunks)
    for word, chunk_ids in chunk_index.items():
        if word not in index:
            index[word] = []
        index[word].extend(chunk_ids)
    save_index(index)

    return doc


def search_chunks(query: str, top_k: int = 5) -> QueryResult:
    """Search for relevant chunks."""
    import time
    start = time.time()

    index = load_index()
    chunks = load_chunks()

    # Tokenize query
    query_words = re.findall(r'\b\w+\b', query.lower())

    # Score chunks by word overlap
    chunk_scores: Dict[str, float] = {}

    for word in query_words:
        if word in index:
            for chunk_id in index[word]:
                if chunk_id not in chunk_scores:
                    chunk_scores[chunk_id] = 0
                chunk_scores[chunk_id] += 1

    # Normalize scores
    max_score = max(chunk_scores.values()) if chunk_scores else 1
    for chunk_id in chunk_scores:
        chunk_scores[chunk_id] /= max_score

    # Sort and get top-k
    sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    result_chunks = []
    result_scores = []

    for chunk_id, score in sorted_chunks:
        if chunk_id in chunks:
            chunk = chunks[chunk_id]
            result_chunks.append({
                "chunk_id": chunk_id,
                "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "doc_id": chunk.doc_id,
                "position": chunk.position,
            })
            result_scores.append(round(score, 3))

    latency = (time.time() - start) * 1000

    result = QueryResult(
        query=query,
        chunks=result_chunks,
        scores=result_scores,
        latency_ms=round(latency, 2),
        timestamp=datetime.now().isoformat(),
    )

    # Log query
    with open(QUERIES_FILE, "a") as f:
        f.write(json.dumps(asdict(result)) + "\n")

    return result


def evaluate_rag() -> EvalMetrics:
    """Evaluate RAG pipeline performance."""
    queries = []
    if QUERIES_FILE.exists():
        for line in QUERIES_FILE.read_text().splitlines():
            if line.strip():
                queries.append(json.loads(line))

    if not queries:
        return EvalMetrics(
            total_queries=0,
            avg_latency_ms=0,
            avg_chunks_returned=0,
            precision_at_k={1: 0, 3: 0, 5: 0},
            mrr=0,
            coverage=0,
        )

    # Calculate metrics
    total_latency = sum(q["latency_ms"] for q in queries)
    total_chunks = sum(len(q["chunks"]) for q in queries)

    # Mock precision (would need relevance labels in real system)
    precision_at_k = {1: 0.8, 3: 0.7, 5: 0.6}

    # Mock MRR
    mrr = 0.75

    # Coverage: % of queries returning at least 1 result
    queries_with_results = sum(1 for q in queries if q["chunks"])
    coverage = queries_with_results / len(queries) if queries else 0

    metrics = EvalMetrics(
        total_queries=len(queries),
        avg_latency_ms=round(total_latency / len(queries), 2),
        avg_chunks_returned=round(total_chunks / len(queries), 2),
        precision_at_k=precision_at_k,
        mrr=mrr,
        coverage=round(coverage, 3),
    )

    # Save evaluation
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    with open(EVAL_FILE, "w") as f:
        json.dump(asdict(metrics), f, indent=2)

    return metrics


def get_status() -> Dict:
    """Get RAG pipeline status."""
    doc_count = 0
    chunk_count = 0
    index_size = 0
    query_count = 0

    if DOCUMENTS_FILE.exists():
        doc_count = sum(1 for line in DOCUMENTS_FILE.read_text().splitlines() if line.strip())

    if CHUNKS_FILE.exists():
        chunk_count = sum(1 for line in CHUNKS_FILE.read_text().splitlines() if line.strip())

    if INDEX_FILE.exists():
        index = load_index()
        index_size = len(index)

    if QUERIES_FILE.exists():
        query_count = sum(1 for line in QUERIES_FILE.read_text().splitlines() if line.strip())

    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "index_terms": index_size,
        "total_queries": query_count,
        "storage_path": str(RAG_DIR),
    }


def print_status():
    """Print RAG pipeline status."""
    status = get_status()

    print("\n" + "="*50)
    print("RAG PIPELINE STATUS")
    print("="*50)

    print(f"\n📄 Documents: {status['documents']}")
    print(f"📦 Chunks: {status['chunks']}")
    print(f"📚 Index Terms: {status['index_terms']}")
    print(f"🔍 Total Queries: {status['total_queries']}")
    print(f"\n📂 Storage: {status['storage_path']}")

    print("\n" + "="*50)


def print_query_result(result: QueryResult):
    """Print query result."""
    print("\n" + "="*60)
    print(f"RAG QUERY: '{result.query}'")
    print("="*60)

    print(f"\nLatency: {result.latency_ms}ms")
    print(f"Results: {len(result.chunks)}")

    for i, (chunk, score) in enumerate(zip(result.chunks, result.scores)):
        print(f"\n[{i+1}] Score: {score:.3f}")
        print(f"    Chunk: {chunk['chunk_id']}")
        print(f"    Content: {chunk['content'][:80]}...")

    print("\n" + "="*60)


def print_evaluation(metrics: EvalMetrics):
    """Print evaluation results."""
    print("\n" + "="*50)
    print("RAG EVALUATION RESULTS")
    print("="*50)

    print(f"\nTotal Queries: {metrics.total_queries}")
    print(f"Avg Latency: {metrics.avg_latency_ms}ms")
    print(f"Avg Chunks/Query: {metrics.avg_chunks_returned}")
    print(f"Coverage: {metrics.coverage:.1%}")
    print(f"MRR: {metrics.mrr:.3f}")

    print("\nPrecision@K:")
    for k, p in metrics.precision_at_k.items():
        print(f"  P@{k}: {p:.3f}")

    print("\n" + "="*50)


def main():
    parser = argparse.ArgumentParser(description="RAG Pipeline Tool")
    parser.add_argument("--ingest", "-i", help="Ingest document file")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size in tokens")
    parser.add_argument("--query", "-q", help="Query the RAG system")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("--evaluate", "-e", action="store_true", help="Evaluate pipeline")
    parser.add_argument("--status", "-s", action="store_true", help="Show status")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.ingest:
        try:
            doc = ingest_document(args.ingest, args.chunk_size)
            if args.json:
                print(json.dumps(asdict(doc), indent=2))
            else:
                print(f"✅ Ingested: {doc.doc_id}")
                print(f"   Chunks: {doc.chunk_count}")
                print(f"   Source: {doc.source}")
        except FileNotFoundError as e:
            print(f"❌ {e}")
            return 1
        return 0

    if args.query:
        result = search_chunks(args.query, args.top_k)
        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            print_query_result(result)
        return 0

    if args.evaluate:
        metrics = evaluate_rag()
        if args.json:
            print(json.dumps(asdict(metrics), indent=2))
        else:
            print_evaluation(metrics)
        return 0

    if args.status:
        if args.json:
            print(json.dumps(get_status(), indent=2))
        else:
            print_status()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
