#!/usr/bin/env python3
"""
RAG Evaluator (GAP-REASON-001)

Evaluates RAG (Retrieval-Augmented Generation) quality.
Measures retrieval relevance, answer accuracy, and faithfulness.

Usage:
    python rag_evaluator.py --evaluate query.json
    python rag_evaluator.py --benchmark
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RESULTS_FILE = DATA_DIR / "rag_evaluation.jsonl"


@dataclass
class RAGQuery:
    """RAG query for evaluation."""
    question: str
    retrieved_docs: List[str]
    generated_answer: str
    reference_answer: Optional[str] = None
    metadata: Dict = None


@dataclass
class RAGMetrics:
    """RAG evaluation metrics."""
    retrieval_relevance: float  # 0-1: How relevant are retrieved docs
    answer_relevance: float     # 0-1: How relevant is answer to question
    faithfulness: float         # 0-1: Is answer grounded in docs
    completeness: float         # 0-1: Does answer cover the question
    conciseness: float          # 0-1: Is answer appropriately concise
    overall_score: float        # Weighted average


def calculate_word_overlap(text1: str, text2: str) -> float:
    """Calculate word overlap ratio."""
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def calculate_retrieval_relevance(question: str, docs: List[str]) -> float:
    """Calculate how relevant retrieved documents are to the question."""
    if not docs:
        return 0.0

    question_words = set(re.findall(r'\w+', question.lower()))
    scores = []

    for doc in docs:
        doc_words = set(re.findall(r'\w+', doc.lower()))
        if question_words:
            overlap = len(question_words & doc_words) / len(question_words)
            scores.append(min(1.0, overlap * 2))  # Scale up

    return sum(scores) / len(scores) if scores else 0.0


def calculate_answer_relevance(question: str, answer: str) -> float:
    """Calculate how relevant the answer is to the question."""
    # Check if answer addresses question keywords
    question_words = set(re.findall(r'\w+', question.lower()))
    answer_words = set(re.findall(r'\w+', answer.lower()))

    # Remove common words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'when', 'where', 'who'}
    question_words -= stop_words
    answer_words -= stop_words

    if not question_words:
        return 0.5

    overlap = len(question_words & answer_words) / len(question_words)
    return min(1.0, overlap * 1.5)


def calculate_faithfulness(answer: str, docs: List[str]) -> float:
    """Calculate if answer is grounded in retrieved documents."""
    if not docs:
        return 0.0

    # Check how much of the answer appears in docs
    answer_sentences = re.split(r'[.!?]', answer)
    grounded_count = 0

    combined_docs = ' '.join(docs).lower()

    for sentence in answer_sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        # Check if key phrases from sentence appear in docs
        words = re.findall(r'\w+', sentence.lower())
        if len(words) < 3:
            continue

        # Check for 3-gram matches
        matched = False
        for i in range(len(words) - 2):
            trigram = ' '.join(words[i:i+3])
            if trigram in combined_docs:
                matched = True
                break

        if matched:
            grounded_count += 1

    total_sentences = len([s for s in answer_sentences if len(s.strip()) >= 10])
    return grounded_count / total_sentences if total_sentences > 0 else 0.5


def calculate_completeness(question: str, answer: str) -> float:
    """Calculate if answer fully addresses the question."""
    # Simple heuristic based on answer length and question type
    question_lower = question.lower()

    # Determine expected answer characteristics
    if question_lower.startswith(('what', 'who', 'where', 'when')):
        # Factual questions - should have clear answer
        min_words = 5
        max_words = 100
    elif question_lower.startswith('how'):
        # Process questions - should have steps
        min_words = 20
        max_words = 500
    elif question_lower.startswith('why'):
        # Explanation questions - should have reasoning
        min_words = 15
        max_words = 300
    else:
        min_words = 10
        max_words = 200

    word_count = len(re.findall(r'\w+', answer))

    if word_count < min_words:
        return word_count / min_words
    elif word_count > max_words:
        return max(0.5, 1 - (word_count - max_words) / max_words)
    else:
        return 1.0


def calculate_conciseness(answer: str, docs: List[str]) -> float:
    """Calculate if answer is appropriately concise."""
    answer_words = len(re.findall(r'\w+', answer))
    doc_words = sum(len(re.findall(r'\w+', d)) for d in docs)

    if doc_words == 0:
        return 0.5

    # Answer should be much shorter than combined docs
    ratio = answer_words / doc_words

    if ratio < 0.1:
        return 1.0
    elif ratio < 0.3:
        return 0.8
    elif ratio < 0.5:
        return 0.6
    else:
        return 0.4


def evaluate_rag(query: RAGQuery) -> RAGMetrics:
    """Evaluate RAG query."""
    retrieval = calculate_retrieval_relevance(query.question, query.retrieved_docs)
    relevance = calculate_answer_relevance(query.question, query.generated_answer)
    faithfulness = calculate_faithfulness(query.generated_answer, query.retrieved_docs)
    completeness = calculate_completeness(query.question, query.generated_answer)
    conciseness = calculate_conciseness(query.generated_answer, query.retrieved_docs)

    # Weighted average
    weights = {
        "retrieval": 0.2,
        "relevance": 0.25,
        "faithfulness": 0.3,
        "completeness": 0.15,
        "conciseness": 0.1,
    }

    overall = (
        retrieval * weights["retrieval"] +
        relevance * weights["relevance"] +
        faithfulness * weights["faithfulness"] +
        completeness * weights["completeness"] +
        conciseness * weights["conciseness"]
    )

    return RAGMetrics(
        retrieval_relevance=round(retrieval, 3),
        answer_relevance=round(relevance, 3),
        faithfulness=round(faithfulness, 3),
        completeness=round(completeness, 3),
        conciseness=round(conciseness, 3),
        overall_score=round(overall, 3),
    )


def run_benchmark() -> Dict:
    """Run benchmark with sample queries."""
    benchmark_queries = [
        RAGQuery(
            question="What is machine learning?",
            retrieved_docs=[
                "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "ML algorithms improve through experience without being explicitly programmed.",
            ],
            generated_answer="Machine learning is a type of AI that allows systems to learn from data and improve over time without explicit programming.",
        ),
        RAGQuery(
            question="How does photosynthesis work?",
            retrieved_docs=[
                "Photosynthesis converts light energy into chemical energy in plants.",
                "Chlorophyll absorbs sunlight, which drives the conversion of CO2 and water into glucose and oxygen.",
            ],
            generated_answer="Photosynthesis is the process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen. This occurs primarily in the chloroplasts where chlorophyll absorbs light energy.",
        ),
    ]

    results = {
        "timestamp": datetime.now().isoformat(),
        "queries": len(benchmark_queries),
        "evaluations": [],
        "average_scores": {},
    }

    metrics_sum = {
        "retrieval_relevance": 0,
        "answer_relevance": 0,
        "faithfulness": 0,
        "completeness": 0,
        "conciseness": 0,
        "overall_score": 0,
    }

    for query in benchmark_queries:
        metrics = evaluate_rag(query)
        results["evaluations"].append({
            "question": query.question[:50],
            "metrics": asdict(metrics),
        })

        for key in metrics_sum:
            metrics_sum[key] += getattr(metrics, key)

    for key in metrics_sum:
        results["average_scores"][key] = round(metrics_sum[key] / len(benchmark_queries), 3)

    return results


def save_result(result: Dict):
    """Save evaluation result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")


def print_metrics(metrics: RAGMetrics, query: RAGQuery = None):
    """Print evaluation metrics."""
    print("\n" + "="*60)
    print("RAG EVALUATION RESULTS")
    print("="*60)

    if query:
        print(f"\nQuestion: {query.question[:80]}")
        print(f"Docs: {len(query.retrieved_docs)}")
        print(f"Answer length: {len(query.generated_answer)} chars")

    print(f"\n--- Metrics ---")
    print(f"Retrieval Relevance: {metrics.retrieval_relevance:.1%}")
    print(f"Answer Relevance:    {metrics.answer_relevance:.1%}")
    print(f"Faithfulness:        {metrics.faithfulness:.1%}")
    print(f"Completeness:        {metrics.completeness:.1%}")
    print(f"Conciseness:         {metrics.conciseness:.1%}")
    print(f"\nOverall Score:       {metrics.overall_score:.1%}")

    # Rating
    if metrics.overall_score >= 0.8:
        print("\nRating: ⭐⭐⭐⭐⭐ Excellent")
    elif metrics.overall_score >= 0.6:
        print("\nRating: ⭐⭐⭐⭐ Good")
    elif metrics.overall_score >= 0.4:
        print("\nRating: ⭐⭐⭐ Fair")
    else:
        print("\nRating: ⭐⭐ Needs Improvement")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluator")
    parser.add_argument("--evaluate", "-e", help="Evaluate query from JSON file")
    parser.add_argument("--question", "-q", help="Question for inline evaluation")
    parser.add_argument("--docs", "-d", nargs="+", help="Retrieved documents")
    parser.add_argument("--answer", "-a", help="Generated answer")
    parser.add_argument("--benchmark", "-b", action="store_true", help="Run benchmark")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save result")

    args = parser.parse_args()

    if args.benchmark:
        results = run_benchmark()
        if args.save:
            save_result(results)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n" + "="*60)
            print("RAG BENCHMARK RESULTS")
            print("="*60)
            print(f"\nQueries evaluated: {results['queries']}")
            print(f"\nAverage Scores:")
            for key, value in results["average_scores"].items():
                print(f"  {key}: {value:.1%}")
        return 0

    if args.evaluate:
        data = json.loads(Path(args.evaluate).read_text())
        query = RAGQuery(**data)
    elif args.question and args.docs and args.answer:
        query = RAGQuery(
            question=args.question,
            retrieved_docs=args.docs,
            generated_answer=args.answer,
        )
    else:
        parser.print_help()
        return 0

    metrics = evaluate_rag(query)

    if args.save:
        save_result({"query": asdict(query), "metrics": asdict(metrics)})

    if args.json:
        print(json.dumps(asdict(metrics), indent=2))
    else:
        print_metrics(metrics, query)

    return 0 if metrics.overall_score >= 0.6 else 1


if __name__ == "__main__":
    sys.exit(main())
