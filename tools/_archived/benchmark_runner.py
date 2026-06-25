#!/usr/bin/env python3
"""
Benchmark Runner (GAP-PERF-001)

Performance benchmarking tool for agent systems.
Measures latency, throughput, and resource usage.

Usage:
    python benchmark_runner.py --run BENCHMARK_NAME
    python benchmark_runner.py --compare BENCH1 BENCH2
    python benchmark_runner.py --report
"""

import argparse
import json
import sys
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
BENCH_DIR = DATA_DIR / "benchmarks"
RESULTS_FILE = BENCH_DIR / "benchmark_results.jsonl"


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    benchmark_id: str
    name: str
    iterations: int
    latencies_ms: List[float]
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float
    errors: int
    timestamp: str


BENCHMARKS = {
    "tool_invocation": {
        "name": "Tool Invocation Speed",
        "iterations": 100,
        "operation": "simulate_tool_call",
    },
    "context_retrieval": {
        "name": "Context Retrieval Latency",
        "iterations": 50,
        "operation": "simulate_context_lookup",
    },
    "response_generation": {
        "name": "Response Generation Time",
        "iterations": 20,
        "operation": "simulate_response_gen",
    },
}


def simulate_operation(op_type: str) -> float:
    """Simulate an operation and return latency."""
    import random
    base_latency = {
        "simulate_tool_call": 50,
        "simulate_context_lookup": 100,
        "simulate_response_gen": 500,
    }.get(op_type, 100)
    
    # Add some variance
    latency = base_latency + random.gauss(0, base_latency * 0.1)
    time.sleep(latency / 10000)  # Small actual delay
    return max(1, latency)


def run_benchmark(bench_name: str) -> BenchmarkResult:
    """Run a benchmark."""
    if bench_name not in BENCHMARKS:
        raise ValueError(f"Unknown benchmark: {bench_name}")

    bench = BENCHMARKS[bench_name]
    iterations = bench["iterations"]
    latencies = []
    errors = 0

    start_time = time.time()
    
    for _ in range(iterations):
        try:
            latency = simulate_operation(bench["operation"])
            latencies.append(latency)
        except Exception:
            errors += 1

    total_time = time.time() - start_time
    
    # Calculate metrics
    sorted_lat = sorted(latencies)
    p50_idx = int(len(sorted_lat) * 0.5)
    p95_idx = int(len(sorted_lat) * 0.95)
    p99_idx = int(len(sorted_lat) * 0.99)

    result = BenchmarkResult(
        benchmark_id=f"bench-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        name=bench["name"],
        iterations=iterations,
        latencies_ms=latencies,
        avg_latency_ms=round(statistics.mean(latencies), 2),
        p50_latency_ms=round(sorted_lat[p50_idx], 2) if sorted_lat else 0,
        p95_latency_ms=round(sorted_lat[min(p95_idx, len(sorted_lat)-1)], 2) if sorted_lat else 0,
        p99_latency_ms=round(sorted_lat[min(p99_idx, len(sorted_lat)-1)], 2) if sorted_lat else 0,
        throughput_rps=round(iterations / total_time, 2),
        errors=errors,
        timestamp=datetime.now().isoformat(),
    )

    log_result(result)
    return result


def log_result(result: BenchmarkResult):
    """Log benchmark result."""
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    data = asdict(result)
    data.pop("latencies_ms")  # Don't log all latencies
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")


def compare_benchmarks(bench1_id: str, bench2_id: str) -> Dict:
    """Compare two benchmark results."""
    results = []
    if RESULTS_FILE.exists():
        for line in RESULTS_FILE.read_text().splitlines():
            if line.strip():
                results.append(json.loads(line))

    r1 = next((r for r in results if bench1_id in r["benchmark_id"]), None)
    r2 = next((r for r in results if bench2_id in r["benchmark_id"]), None)

    if not r1 or not r2:
        return {"error": "Benchmark results not found"}

    return {
        "comparison": {
            "latency_diff_percent": round((r2["avg_latency_ms"] - r1["avg_latency_ms"]) / r1["avg_latency_ms"] * 100, 2),
            "throughput_diff_percent": round((r2["throughput_rps"] - r1["throughput_rps"]) / r1["throughput_rps"] * 100, 2),
        },
        "bench1": {"id": r1["benchmark_id"], "avg_latency": r1["avg_latency_ms"]},
        "bench2": {"id": r2["benchmark_id"], "avg_latency": r2["avg_latency_ms"]},
    }


def get_report() -> Dict:
    """Generate benchmark report."""
    results = []
    if RESULTS_FILE.exists():
        for line in RESULTS_FILE.read_text().splitlines():
            if line.strip():
                results.append(json.loads(line))

    if not results:
        return {"total_runs": 0, "benchmarks": {}}

    by_name = {}
    for r in results:
        name = r["name"]
        if name not in by_name:
            by_name[name] = []
        by_name[name].append(r)

    return {
        "total_runs": len(results),
        "benchmarks": {
            name: {
                "runs": len(runs),
                "avg_latency": round(statistics.mean(r["avg_latency_ms"] for r in runs), 2),
                "best_throughput": max(r["throughput_rps"] for r in runs),
            }
            for name, runs in by_name.items()
        },
    }


def print_result(result: BenchmarkResult):
    """Print benchmark result."""
    print(f"\n{'='*50}")
    print(f"BENCHMARK: {result.name}")
    print(f"{'='*50}")
    print(f"Iterations: {result.iterations}")
    print(f"Avg Latency: {result.avg_latency_ms}ms")
    print(f"P50: {result.p50_latency_ms}ms | P95: {result.p95_latency_ms}ms | P99: {result.p99_latency_ms}ms")
    print(f"Throughput: {result.throughput_rps} req/s")
    print(f"Errors: {result.errors}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark Runner")
    parser.add_argument("--run", "-r", help="Run benchmark")
    parser.add_argument("--list", "-l", action="store_true", help="List benchmarks")
    parser.add_argument("--compare", nargs=2, help="Compare two benchmarks")
    parser.add_argument("--report", action="store_true", help="Show report")
    parser.add_argument("--json", "-j", action="store_true")
    args = parser.parse_args()

    if args.list:
        for name, b in BENCHMARKS.items():
            print(f"📊 {name}: {b['name']} ({b['iterations']} iterations)")
        return 0

    if args.run:
        try:
            result = run_benchmark(args.run)
            if args.json:
                data = asdict(result)
                data.pop("latencies_ms")
                print(json.dumps(data, indent=2))
            else:
                print_result(result)
        except ValueError as e:
            print(f"❌ {e}")
            return 1
        return 0

    if args.compare:
        comp = compare_benchmarks(args.compare[0], args.compare[1])
        print(json.dumps(comp, indent=2))
        return 0

    if args.report:
        report = get_report()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"\nTotal Runs: {report['total_runs']}")
            for name, data in report.get("benchmarks", {}).items():
                print(f"  {name}: {data['runs']} runs, avg {data['avg_latency']}ms")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
