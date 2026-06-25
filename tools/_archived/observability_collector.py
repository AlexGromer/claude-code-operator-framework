#!/usr/bin/env python3
"""
LLM Observability Collector

Collects and aggregates metrics for agent performance monitoring.
Implements GAP-OBS-001: LLM Observability Framework.

Usage:
    python observability_collector.py --collect
    python observability_collector.py --report [daily|weekly]
    python observability_collector.py --export [json|csv] --output <file>
    python observability_collector.py --dashboard
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class MetricsCollector:
    """Collects observability metrics from logs."""

    def __init__(self, logs_dir: Optional[str] = None):
        """Initialize metrics collector."""
        self.logs_dir = Path(logs_dir) if logs_dir else Path.home() / ".claude" / "logs"
        self.data_dir = Path.home() / ".claude" / "evaluation" / "data"

    def collect_latency_metrics(self) -> Dict[str, Any]:
        """Collect latency metrics from latency logs."""
        latency_file = self.data_dir / "latency_data.jsonl"
        if not latency_file.exists():
            return {
                "total_calls": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "avg": 0
            }

        latencies = []
        try:
            with open(latency_file) as f:
                for line in f:
                    data = json.loads(line.strip())
                    if "latency_ms" in data:
                        latencies.append(data["latency_ms"])
        except Exception as e:
            print(f"Error reading latency data: {e}", file=sys.stderr)

        if not latencies:
            return {"total_calls": 0, "p50": 0, "p95": 0, "p99": 0, "avg": 0}

        latencies.sort()
        return {
            "total_calls": len(latencies),
            "p50": statistics.median(latencies),
            "p95": latencies[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies),
            "p99": latencies[int(len(latencies) * 0.99)] if len(latencies) > 100 else max(latencies),
            "avg": statistics.mean(latencies),
            "min": min(latencies),
            "max": max(latencies)
        }

    def collect_token_counts(self) -> Dict[str, Any]:
        """Collect token usage metrics."""
        cost_file = self.data_dir / "cost_data.jsonl"
        if not cost_file.exists():
            return {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0
            }

        input_tokens = 0
        output_tokens = 0
        total_cost = 0

        try:
            with open(cost_file) as f:
                for line in f:
                    data = json.loads(line.strip())
                    input_tokens += data.get("input_tokens", 0)
                    output_tokens += data.get("output_tokens", 0)
                    total_cost += data.get("cost_usd", 0)
        except Exception as e:
            print(f"Error reading cost data: {e}", file=sys.stderr)

        return {
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "total_cost_usd": round(total_cost, 4)
        }

    def collect_error_rates(self) -> Dict[str, Any]:
        """Collect error rate metrics."""
        tool_chain_file = self.data_dir / "tool_chain.jsonl"
        if not tool_chain_file.exists():
            return {
                "total_calls": 0,
                "errors": 0,
                "error_rate": 0
            }

        total_calls = 0
        errors = 0

        try:
            with open(tool_chain_file) as f:
                for line in f:
                    data = json.loads(line.strip())
                    total_calls += 1
                    if data.get("error") or data.get("status") == "error":
                        errors += 1
        except Exception as e:
            print(f"Error reading tool chain data: {e}", file=sys.stderr)

        error_rate = (errors / total_calls * 100) if total_calls > 0 else 0

        return {
            "total_calls": total_calls,
            "errors": errors,
            "error_rate": round(error_rate, 2)
        }

    def collect_tool_usage(self) -> Dict[str, Any]:
        """Collect tool usage statistics."""
        tool_chain_file = self.data_dir / "tool_chain.jsonl"
        if not tool_chain_file.exists():
            return {"tool_counts": {}, "total_calls": 0}

        tool_counts = defaultdict(int)

        try:
            with open(tool_chain_file) as f:
                for line in f:
                    data = json.loads(line.strip())
                    tool = data.get("tool", "unknown")
                    tool_counts[tool] += 1
        except Exception as e:
            print(f"Error reading tool chain data: {e}", file=sys.stderr)

        total_calls = sum(tool_counts.values())

        # Calculate percentages
        tool_stats = {}
        for tool, count in tool_counts.items():
            percentage = (count / total_calls * 100) if total_calls > 0 else 0
            tool_stats[tool] = {
                "count": count,
                "percentage": round(percentage, 2)
            }

        return {
            "tool_counts": tool_stats,
            "total_calls": total_calls,
            "unique_tools": len(tool_counts)
        }

    def collect_hallucination_rate(self) -> Dict[str, Any]:
        """Collect hallucination detection metrics."""
        hallucination_file = self.data_dir / "hallucination_checks.jsonl"
        if not hallucination_file.exists():
            return {
                "total_checks": 0,
                "hallucinations_detected": 0,
                "hallucination_rate": 0
            }

        total_checks = 0
        hallucinations = 0

        try:
            with open(hallucination_file) as f:
                for line in f:
                    data = json.loads(line.strip())
                    total_checks += 1
                    if data.get("is_hallucination"):
                        hallucinations += 1
        except Exception as e:
            print(f"Error reading hallucination data: {e}", file=sys.stderr)

        rate = (hallucinations / total_checks * 100) if total_checks > 0 else 0

        return {
            "total_checks": total_checks,
            "hallucinations_detected": hallucinations,
            "hallucination_rate": round(rate, 2)
        }


def collect_metrics() -> Dict[str, Any]:
    """Collect all metrics."""
    collector = MetricsCollector()

    return {
        "latency": collector.collect_latency_metrics(),
        "token_counts": collector.collect_token_counts(),
        "error_rates": collector.collect_error_rates(),
        "tool_usage": collector.collect_tool_usage(),
        "hallucination": collector.collect_hallucination_rate(),
        "timestamp": datetime.now().isoformat()
    }


def aggregate_metrics(data: List[Dict[str, Any]], period: str = "session") -> Dict[str, Any]:
    """Aggregate metrics over a time period."""
    if not data:
        return {}

    # Simple aggregation - sum counts, average rates
    aggregated = {
        "period": period,
        "total_records": len(data),
        "summary": {}
    }

    # Aggregate latencies
    latencies = [d.get("latency_ms", 0) for d in data if "latency_ms" in d]
    if latencies:
        aggregated["summary"]["latency"] = {
            "avg": round(statistics.mean(latencies), 2),
            "p50": round(statistics.median(latencies), 2),
            "min": min(latencies),
            "max": max(latencies)
        }

    # Aggregate tokens
    total_tokens = sum(d.get("tokens", 0) for d in data)
    if total_tokens > 0:
        aggregated["summary"]["tokens"] = {
            "total": total_tokens,
            "avg_per_call": round(total_tokens / len(data), 2)
        }

    return aggregated


def export_metrics(metrics: Any, output_file: str, format: str = "json") -> None:
    """Export metrics to file."""
    output_path = Path(output_file)

    if format == "json":
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"Metrics exported to {output_path} (JSON)")

    elif format == "csv":
        # Flatten metrics for CSV
        if isinstance(metrics, dict):
            # Convert single dict to list
            data = [metrics]
        elif isinstance(metrics, list):
            data = metrics
        else:
            print("Error: Cannot export this data format to CSV", file=sys.stderr)
            return

        if not data:
            print("No data to export", file=sys.stderr)
            return

        # Write CSV
        with open(output_path, 'w', newline='') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        print(f"Metrics exported to {output_path} (CSV)")


def generate_report(period: str = "daily") -> None:
    """Generate metrics report."""
    metrics = collect_metrics()

    print("=" * 80)
    print(f"OBSERVABILITY REPORT ({period.upper()})")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Latency
    print("[1] LATENCY METRICS:")
    latency = metrics.get("latency", {})
    print(f"  Total calls: {latency.get('total_calls', 0)}")
    print(f"  P50: {latency.get('p50', 0):.2f} ms")
    print(f"  P95: {latency.get('p95', 0):.2f} ms")
    print(f"  P99: {latency.get('p99', 0):.2f} ms")
    print(f"  Avg: {latency.get('avg', 0):.2f} ms")
    print()

    # Token counts
    print("[2] TOKEN USAGE:")
    tokens = metrics.get("token_counts", {})
    print(f"  Total input: {tokens.get('total_input_tokens', 0):,}")
    print(f"  Total output: {tokens.get('total_output_tokens', 0):,}")
    print(f"  Total cost: ${tokens.get('total_cost_usd', 0):.4f}")
    print()

    # Error rates
    print("[3] ERROR RATES:")
    errors = metrics.get("error_rates", {})
    print(f"  Total calls: {errors.get('total_calls', 0)}")
    print(f"  Errors: {errors.get('errors', 0)}")
    print(f"  Error rate: {errors.get('error_rate', 0):.2f}%")
    print()

    # Tool usage
    print("[4] TOOL USAGE:")
    tools = metrics.get("tool_usage", {})
    print(f"  Total calls: {tools.get('total_calls', 0)}")
    print(f"  Unique tools: {tools.get('unique_tools', 0)}")
    tool_counts = tools.get("tool_counts", {})
    if tool_counts:
        print("  Top tools:")
        sorted_tools = sorted(
            tool_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:5]
        for tool, stats in sorted_tools:
            print(f"    - {tool}: {stats['count']} ({stats['percentage']:.1f}%)")
    print()

    # Hallucination
    print("[5] HALLUCINATION DETECTION:")
    halluc = metrics.get("hallucination", {})
    print(f"  Total checks: {halluc.get('total_checks', 0)}")
    print(f"  Detected: {halluc.get('hallucinations_detected', 0)}")
    print(f"  Rate: {halluc.get('hallucination_rate', 0):.2f}%")

    print("\n" + "=" * 80)


def generate_dashboard() -> None:
    """Generate dashboard view of key metrics."""
    metrics = collect_metrics()

    latency = metrics.get("latency", {})
    tokens = metrics.get("token_counts", {})
    errors = metrics.get("error_rates", {})
    tools = metrics.get("tool_usage", {})

    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║                        OBSERVABILITY DASHBOARD                           ║")
    print("╠══════════════════════════════════════════════════════════════════════════╣")
    print("║                                                                          ║")
    print(f"║  🕐 Latency (P95): {latency.get('p95', 0):>8.2f} ms                                     ║")
    print(f"║  💰 Cost:          ${tokens.get('total_cost_usd', 0):>8.4f}                                  ║")
    print(f"║  🔧 Tool Calls:    {tools.get('total_calls', 0):>8,}                                        ║")
    print(f"║  ❌ Error Rate:    {errors.get('error_rate', 0):>8.2f}%                                      ║")
    print("║                                                                          ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LLM Observability Collector"
    )

    parser.add_argument(
        "--collect",
        action="store_true",
        help="Collect current metrics"
    )

    parser.add_argument(
        "--report",
        choices=["daily", "weekly"],
        help="Generate metrics report"
    )

    parser.add_argument(
        "--export",
        choices=["json", "csv"],
        help="Export metrics format"
    )

    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Output file for export"
    )

    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Display dashboard view"
    )

    args = parser.parse_args()

    if args.collect:
        metrics = collect_metrics()
        print(json.dumps(metrics, indent=2))

    elif args.report:
        generate_report(args.report)

    elif args.export and args.output:
        metrics = collect_metrics()
        export_metrics(metrics, args.output, args.export)

    elif args.dashboard:
        generate_dashboard()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
