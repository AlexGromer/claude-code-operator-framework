#!/usr/bin/env python3
"""
Tool Call Latency Optimizer

Analyzes tool call patterns, identifies bottlenecks, and suggests optimizations.
Implements GAP-PERF-AGENT-001: Tool Call Latency Optimization.

Usage:
    python latency_optimizer.py --analyze
    python latency_optimizer.py --suggest
    python latency_optimizer.py --report
    python latency_optimizer.py --benchmark <tool>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime
import statistics


class LatencyAnalyzer:
    """Analyzes tool call latency patterns."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize analyzer."""
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".claude" / "evaluation" / "data"
        self.latency_file = self.data_dir / "latency_data.jsonl"
        self.tool_chain_file = self.data_dir / "tool_chain.jsonl"

    def analyze_tool_latency(self) -> Dict[str, Any]:
        """Analyze latency by tool."""
        tool_latencies = defaultdict(list)

        # Read from latency data
        if self.latency_file.exists():
            try:
                with open(self.latency_file) as f:
                    for line in f:
                        data = json.loads(line.strip())
                        tool = data.get("tool", "unknown")
                        latency = data.get("latency_ms", 0)
                        if latency > 0:
                            tool_latencies[tool].append(latency)
            except Exception as e:
                print(f"Error reading latency data: {e}", file=sys.stderr)

        # Calculate statistics per tool
        stats = {}
        for tool, latencies in tool_latencies.items():
            if latencies:
                latencies_sorted = sorted(latencies)
                stats[tool] = {
                    "count": len(latencies),
                    "avg": round(statistics.mean(latencies), 2),
                    "p50": round(statistics.median(latencies), 2),
                    "p95": round(latencies[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies), 2),
                    "min": round(min(latencies), 2),
                    "max": round(max(latencies), 2),
                    "total_time_ms": round(sum(latencies), 2)
                }

        return stats

    def identify_bottlenecks(self, threshold_ms: int = 1000) -> List[Dict[str, Any]]:
        """Identify slow tools (bottlenecks)."""
        tool_stats = self.analyze_tool_latency()

        bottlenecks = []
        for tool, stats in tool_stats.items():
            # A tool is a bottleneck if:
            # 1. P95 > threshold
            # 2. Multiple calls (>5)
            if stats["p95"] > threshold_ms and stats["count"] > 5:
                bottlenecks.append({
                    "tool": tool,
                    "avg_latency": stats["avg"],
                    "p95_latency": stats["p95"],
                    "count": stats["count"],
                    "total_time_ms": stats["total_time_ms"],
                    "severity": "high" if stats["p95"] > 5000 else "medium"
                })

        # Sort by total time impact
        bottlenecks.sort(key=lambda x: x["total_time_ms"], reverse=True)
        return bottlenecks

    def analyze_parallelization_opportunities(self) -> List[Dict[str, Any]]:
        """Identify opportunities for parallel tool execution."""
        opportunities = []

        # Read tool chain to find sequential independent calls
        if not self.tool_chain_file.exists():
            return opportunities

        try:
            with open(self.tool_chain_file) as f:
                calls = [json.loads(line.strip()) for line in f]

            # Simple heuristic: consecutive Read/Grep/Glob calls can be parallelized
            parallelizable_tools = {"Read", "Grep", "Glob", "WebSearch"}

            i = 0
            while i < len(calls) - 1:
                current = calls[i]
                next_call = calls[i + 1]

                current_tool = current.get("tool", "")
                next_tool = next_call.get("tool", "")

                if (current_tool in parallelizable_tools and
                    next_tool in parallelizable_tools):
                    opportunities.append({
                        "type": "sequential_reads",
                        "tools": [current_tool, next_tool],
                        "suggestion": "These calls can run in parallel",
                        "potential_savings_ms": min(
                            current.get("latency_ms", 0),
                            next_call.get("latency_ms", 0)
                        )
                    })
                i += 1

        except Exception as e:
            print(f"Error analyzing tool chain: {e}", file=sys.stderr)

        return opportunities

    def analyze_cache_efficiency(self) -> Dict[str, Any]:
        """Analyze cache hit rates."""
        # Placeholder - would analyze repeated identical calls
        return {
            "cache_available": False,
            "suggestion": "Implement caching for repeated Read/Grep operations"
        }


def analyze_tool_latency() -> Dict[str, Any]:
    """Analyze tool latency (public API)."""
    analyzer = LatencyAnalyzer()
    return analyzer.analyze_tool_latency()


def identify_bottlenecks(data: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Identify bottlenecks (public API)."""
    if data:
        # Use provided data
        tool_latencies = defaultdict(list)
        for entry in data:
            tool = entry.get("tool", "unknown")
            latency = entry.get("latency_ms", 0)
            tool_latencies[tool].append(latency)

        # Calculate stats and find bottlenecks
        bottlenecks = []
        for tool, latencies in tool_latencies.items():
            if latencies:
                avg = statistics.mean(latencies)
                if avg > 1000:  # Threshold
                    bottlenecks.append({
                        "tool": tool,
                        "avg_latency": round(avg, 2),
                        "count": len(latencies)
                    })
        return bottlenecks
    else:
        analyzer = LatencyAnalyzer()
        return analyzer.identify_bottlenecks()


def suggest_optimizations(bottlenecks: List[Dict[str, Any]]) -> List[str]:
    """Generate optimization suggestions."""
    suggestions = []

    for bottleneck in bottlenecks:
        tool = bottleneck.get("tool", "")
        avg_latency = bottleneck.get("avg_latency", 0)

        if tool == "Bash":
            suggestions.append(
                f"Tool '{tool}' (avg: {avg_latency}ms): Consider breaking into smaller commands or using Python scripts"
            )
        elif tool == "Read":
            suggestions.append(
                f"Tool '{tool}' (avg: {avg_latency}ms): Use offset/limit for large files, or cache frequently read files"
            )
        elif tool == "Grep":
            suggestions.append(
                f"Tool '{tool}' (avg: {avg_latency}ms): Narrow search patterns, use type filters, or pre-index codebase"
            )
        elif tool == "WebSearch":
            suggestions.append(
                f"Tool '{tool}' (avg: {avg_latency}ms): Use WebFetch cache or reduce number of searches"
            )
        else:
            suggestions.append(
                f"Tool '{tool}' (avg: {avg_latency}ms): Investigate slow operations"
            )

    return suggestions


def generate_report() -> None:
    """Generate latency optimization report."""
    analyzer = LatencyAnalyzer()

    print("=" * 80)
    print("LATENCY OPTIMIZATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Tool latency analysis
    print("[1] TOOL LATENCY ANALYSIS:")
    tool_stats = analyzer.analyze_tool_latency()

    if not tool_stats:
        print("  No latency data available")
    else:
        # Sort by avg latency
        sorted_tools = sorted(
            tool_stats.items(),
            key=lambda x: x[1]["avg"],
            reverse=True
        )

        for tool, stats in sorted_tools[:10]:  # Top 10 slowest
            print(f"\n  Tool: {tool}")
            print(f"    Calls: {stats['count']}")
            print(f"    Avg: {stats['avg']:.2f} ms")
            print(f"    P95: {stats['p95']:.2f} ms")
            print(f"    Total time: {stats['total_time_ms']:.2f} ms")

    # Bottlenecks
    print("\n[2] BOTTLENECKS:")
    bottlenecks = analyzer.identify_bottlenecks()

    if not bottlenecks:
        print("  No significant bottlenecks detected")
    else:
        for i, bottleneck in enumerate(bottlenecks, 1):
            print(f"\n  {i}. {bottleneck['tool']} ({bottleneck['severity'].upper()})")
            print(f"     P95: {bottleneck['p95_latency']:.2f} ms")
            print(f"     Calls: {bottleneck['count']}")
            print(f"     Total impact: {bottleneck['total_time_ms']:.2f} ms")

    # Optimization suggestions
    print("\n[3] OPTIMIZATION SUGGESTIONS:")
    suggestions = suggest_optimizations(bottlenecks)

    if not suggestions:
        print("  No specific suggestions at this time")
    else:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")

    # Parallelization opportunities
    print("\n[4] PARALLELIZATION OPPORTUNITIES:")
    opportunities = analyzer.analyze_parallelization_opportunities()

    if not opportunities:
        print("  No parallelization opportunities detected")
    else:
        for i, opp in enumerate(opportunities[:5], 1):  # Top 5
            print(f"  {i}. {opp['suggestion']}")
            print(f"     Tools: {', '.join(opp['tools'])}")
            print(f"     Potential savings: {opp['potential_savings_ms']:.2f} ms")

    print("\n" + "=" * 80)


def benchmark_tool(tool_name: str) -> None:
    """Benchmark a specific tool."""
    analyzer = LatencyAnalyzer()
    stats = analyzer.analyze_tool_latency()

    if tool_name not in stats:
        print(f"No data available for tool: {tool_name}")
        return

    tool_stats = stats[tool_name]

    print("=" * 80)
    print(f"BENCHMARK: {tool_name}")
    print("=" * 80)
    print(f"Total calls: {tool_stats['count']}")
    print(f"Avg latency: {tool_stats['avg']:.2f} ms")
    print(f"P50: {tool_stats['p50']:.2f} ms")
    print(f"P95: {tool_stats['p95']:.2f} ms")
    print(f"Min: {tool_stats['min']:.2f} ms")
    print(f"Max: {tool_stats['max']:.2f} ms")
    print(f"Total time: {tool_stats['total_time_ms']:.2f} ms")
    print("=" * 80)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tool Call Latency Optimizer"
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze tool latency patterns"
    )

    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Generate optimization suggestions"
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate comprehensive latency report"
    )

    parser.add_argument(
        "--benchmark",
        metavar="TOOL",
        help="Benchmark a specific tool"
    )

    args = parser.parse_args()

    if args.analyze:
        stats = analyze_tool_latency()
        print(json.dumps(stats, indent=2))

    elif args.suggest:
        analyzer = LatencyAnalyzer()
        bottlenecks = analyzer.identify_bottlenecks()
        suggestions = suggest_optimizations(bottlenecks)
        for suggestion in suggestions:
            print(f"• {suggestion}")

    elif args.report:
        generate_report()

    elif args.benchmark:
        benchmark_tool(args.benchmark)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
