#!/usr/bin/env python3
"""
Latency and Performance Tracking
TIER 2C Task 19: GAP-EVAL-LATENCY

Tracks response latency metrics for Claude Code sessions:
- TTFT (time to first token)
- Total response time
- Throughput (tokens/sec)
- Percentile analysis (p50/p90/p99)

Target: Performance baseline + degradation detection
"""

import json
import statistics
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict


@dataclass
class LatencyMetric:
    """Represents a single latency measurement."""
    timestamp: str
    session_id: str
    request_number: int
    ttft_ms: Optional[float] = None  # Time to first token (milliseconds)
    total_time_ms: Optional[float] = None  # Total response time
    input_tokens: int = 0
    output_tokens: int = 0
    throughput_tok_per_sec: Optional[float] = None  # Output tokens / total_time
    model: str = "unknown"
    cached_tokens: int = 0  # Cache contribution
    tool_calls: int = 0  # Number of tool calls in response


@dataclass
class PercentileStats:
    """Percentile statistics for a metric."""
    p50: float  # Median
    p90: float
    p95: float
    p99: float
    mean: float
    min: float
    max: float
    stddev: float
    count: int


@dataclass
class LatencyReport:
    """Comprehensive latency report."""
    period_start: str
    period_end: str
    total_requests: int

    # TTFT statistics
    ttft: Optional[PercentileStats]

    # Total response time statistics
    total_time: Optional[PercentileStats]

    # Throughput statistics
    throughput: Optional[PercentileStats]

    # Breakdown by model
    by_model: Dict[str, Dict[str, Any]]

    # Breakdown by cache status
    cached_vs_fresh: Dict[str, Dict[str, float]]

    # Performance trends
    degradation_detected: bool
    trend: str  # "improving" | "stable" | "degrading"


class LatencyTracker:
    """
    Tracks and analyzes latency metrics for Claude Code sessions.

    TIER 2C Task 19 (GAP-EVAL-LATENCY): Latency and Performance Evaluation
    - Tracks TTFT, total response time, throughput
    - Calculates percentiles (p50/p90/p95/p99)
    - Detects performance degradation
    - Provides dashboard visualization
    """

    def __init__(self, metrics_file: Optional[Path] = None):
        """
        Initialize latency tracker.

        Args:
            metrics_file: Path to latency metrics JSONL file
        """
        if metrics_file is None:
            metrics_file = Path.home() / ".claude" / "evaluation" / "data" / "latency_metrics.jsonl"

        self.metrics_file = metrics_file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def track_response(
        self,
        session_id: str,
        request_number: int,
        ttft_ms: Optional[float] = None,
        total_time_ms: Optional[float] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = "unknown",
        cached_tokens: int = 0,
        tool_calls: int = 0
    ) -> LatencyMetric:
        """
        Track latency for a single response.

        Args:
            session_id: Session UUID
            request_number: Sequential request number
            ttft_ms: Time to first token (milliseconds)
            total_time_ms: Total response time (milliseconds)
            input_tokens: Total input tokens
            output_tokens: Total output tokens
            model: Model name (haiku/sonnet/opus)
            cached_tokens: Number of cached tokens
            tool_calls: Number of tool calls

        Returns:
            LatencyMetric object
        """
        # Calculate throughput if we have data
        throughput = None
        if total_time_ms and total_time_ms > 0 and output_tokens > 0:
            # tokens/sec = (output_tokens / total_time_ms) * 1000
            throughput = (output_tokens / total_time_ms) * 1000

        metric = LatencyMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            request_number=request_number,
            ttft_ms=ttft_ms,
            total_time_ms=total_time_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            throughput_tok_per_sec=throughput,
            model=model,
            cached_tokens=cached_tokens,
            tool_calls=tool_calls
        )

        # Append to metrics file
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(asdict(metric)) + '\n')

        return metric

    def track_tool_latency(
        self,
        tool_name: str,
        latency_ms: float,
        session_id: str = "unknown",
        response_size: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track latency for a single tool execution.

        Simplified method for hook integration - records tool-level latency.

        Args:
            tool_name: Name of the tool (Read, Write, Bash, etc.)
            latency_ms: Estimated latency in milliseconds
            session_id: Session UUID
            response_size: Size of tool response in characters
            metadata: Optional additional metadata

        Returns:
            Dict with recorded data
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "tool_latency",
            "tool_name": tool_name,
            "latency_ms": latency_ms,
            "session_id": session_id,
            "response_size": response_size,
            "metadata": metadata or {}
        }

        # Write to dedicated tool latency file
        tool_latency_file = self.metrics_file.parent / "tool_latency.jsonl"
        with open(tool_latency_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        return entry

    def load_metrics(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[LatencyMetric]:
        """
        Load latency metrics from file.

        Args:
            session_id: Filter by session ID (optional)
            limit: Maximum number of metrics to load (optional)

        Returns:
            List of LatencyMetric objects
        """
        if not self.metrics_file.exists():
            return []

        metrics = []
        with open(self.metrics_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)

                    # Filter by session if specified
                    if session_id and data.get('session_id') != session_id:
                        continue

                    metrics.append(LatencyMetric(**data))

                    if limit and len(metrics) >= limit:
                        break

                except (json.JSONDecodeError, TypeError):
                    continue

        return metrics

    def calculate_percentiles(self, values: List[float]) -> PercentileStats:
        """
        Calculate percentile statistics for a list of values.

        Args:
            values: List of numeric values

        Returns:
            PercentileStats object
        """
        if not values:
            return PercentileStats(
                p50=0, p90=0, p95=0, p99=0,
                mean=0, min=0, max=0, stddev=0, count=0
            )

        sorted_values = sorted(values)
        count = len(sorted_values)

        return PercentileStats(
            p50=statistics.median(sorted_values),
            p90=sorted_values[int(count * 0.90)] if count > 10 else sorted_values[-1],
            p95=sorted_values[int(count * 0.95)] if count > 20 else sorted_values[-1],
            p99=sorted_values[int(count * 0.99)] if count > 100 else sorted_values[-1],
            mean=statistics.mean(sorted_values),
            min=min(sorted_values),
            max=max(sorted_values),
            stddev=statistics.stdev(sorted_values) if count > 1 else 0,
            count=count
        )

    def generate_report(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> LatencyReport:
        """
        Generate comprehensive latency report.

        Args:
            session_id: Filter by session ID (optional)
            limit: Maximum number of metrics to analyze (optional)

        Returns:
            LatencyReport object
        """
        metrics = self.load_metrics(session_id=session_id, limit=limit)

        if not metrics:
            # Empty report
            return LatencyReport(
                period_start="N/A",
                period_end="N/A",
                total_requests=0,
                ttft=None,
                total_time=None,
                throughput=None,
                by_model={},
                cached_vs_fresh={},
                degradation_detected=False,
                trend="stable"
            )

        # Extract timestamps
        period_start = metrics[0].timestamp
        period_end = metrics[-1].timestamp
        total_requests = len(metrics)

        # Extract metrics for percentile analysis
        ttft_values = [m.ttft_ms for m in metrics if m.ttft_ms is not None]
        total_time_values = [m.total_time_ms for m in metrics if m.total_time_ms is not None]
        throughput_values = [m.throughput_tok_per_sec for m in metrics if m.throughput_tok_per_sec is not None]

        # Calculate percentiles
        ttft_stats = self.calculate_percentiles(ttft_values) if ttft_values else None
        total_time_stats = self.calculate_percentiles(total_time_values) if total_time_values else None
        throughput_stats = self.calculate_percentiles(throughput_values) if throughput_values else None

        # Breakdown by model
        by_model = self._breakdown_by_model(metrics)

        # Breakdown by cache status
        cached_vs_fresh = self._breakdown_by_cache(metrics)

        # Detect performance degradation
        degradation_detected, trend = self._detect_degradation(metrics)

        return LatencyReport(
            period_start=period_start,
            period_end=period_end,
            total_requests=total_requests,
            ttft=ttft_stats,
            total_time=total_time_stats,
            throughput=throughput_stats,
            by_model=by_model,
            cached_vs_fresh=cached_vs_fresh,
            degradation_detected=degradation_detected,
            trend=trend
        )

    def _breakdown_by_model(self, metrics: List[LatencyMetric]) -> Dict[str, Dict[str, Any]]:
        """
        Break down metrics by model type.

        Args:
            metrics: List of LatencyMetric objects

        Returns:
            Dictionary of model → stats
        """
        by_model = defaultdict(lambda: {
            'ttft': [],
            'total_time': [],
            'throughput': [],
            'count': 0
        })

        for metric in metrics:
            model = metric.model
            by_model[model]['count'] += 1

            if metric.ttft_ms is not None:
                by_model[model]['ttft'].append(metric.ttft_ms)
            if metric.total_time_ms is not None:
                by_model[model]['total_time'].append(metric.total_time_ms)
            if metric.throughput_tok_per_sec is not None:
                by_model[model]['throughput'].append(metric.throughput_tok_per_sec)

        # Calculate averages
        result = {}
        for model, data in by_model.items():
            result[model] = {
                'count': data['count'],
                'avg_ttft': statistics.mean(data['ttft']) if data['ttft'] else 0,
                'avg_total_time': statistics.mean(data['total_time']) if data['total_time'] else 0,
                'avg_throughput': statistics.mean(data['throughput']) if data['throughput'] else 0
            }

        return result

    def _breakdown_by_cache(self, metrics: List[LatencyMetric]) -> Dict[str, Dict[str, float]]:
        """
        Break down metrics by cache status (cached vs fresh).

        Args:
            metrics: List of LatencyMetric objects

        Returns:
            Dictionary of cache status → stats
        """
        cached = []
        fresh = []

        for metric in metrics:
            if metric.cached_tokens > 0:
                cached.append(metric)
            else:
                fresh.append(metric)

        result = {}

        if cached:
            cached_ttft = [m.ttft_ms for m in cached if m.ttft_ms is not None]
            cached_total = [m.total_time_ms for m in cached if m.total_time_ms is not None]

            result['cached'] = {
                'count': len(cached),
                'avg_ttft': statistics.mean(cached_ttft) if cached_ttft else 0,
                'avg_total_time': statistics.mean(cached_total) if cached_total else 0
            }

        if fresh:
            fresh_ttft = [m.ttft_ms for m in fresh if m.ttft_ms is not None]
            fresh_total = [m.total_time_ms for m in fresh if m.total_time_ms is not None]

            result['fresh'] = {
                'count': len(fresh),
                'avg_ttft': statistics.mean(fresh_ttft) if fresh_ttft else 0,
                'avg_total_time': statistics.mean(fresh_total) if fresh_total else 0
            }

        return result

    def _detect_degradation(self, metrics: List[LatencyMetric]) -> Tuple[bool, str]:
        """
        Detect performance degradation by comparing recent vs historical metrics.

        Args:
            metrics: List of LatencyMetric objects (chronological)

        Returns:
            Tuple of (degradation_detected: bool, trend: str)
        """
        if len(metrics) < 20:
            # Not enough data for trend analysis
            return False, "stable"

        # Split into historical (first 50%) and recent (last 50%)
        split_point = len(metrics) // 2
        historical = metrics[:split_point]
        recent = metrics[split_point:]

        # Calculate average total_time for each period
        historical_times = [m.total_time_ms for m in historical if m.total_time_ms is not None]
        recent_times = [m.total_time_ms for m in recent if m.total_time_ms is not None]

        if not historical_times or not recent_times:
            return False, "stable"

        avg_historical = statistics.mean(historical_times)
        avg_recent = statistics.mean(recent_times)

        # Calculate percentage change
        pct_change = ((avg_recent - avg_historical) / avg_historical) * 100

        # Threshold for degradation: >15% slower
        if pct_change > 15:
            return True, "degrading"
        elif pct_change < -15:
            return False, "improving"
        else:
            return False, "stable"

    def format_report(self, report: LatencyReport) -> str:
        """
        Format latency report for display.

        Args:
            report: LatencyReport object

        Returns:
            Formatted string
        """
        lines = []

        lines.append("=" * 70)
        lines.append("LATENCY & PERFORMANCE REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Period info
        lines.append(f"Period: {report.period_start[:19]} → {report.period_end[:19]}")
        lines.append(f"Total Requests: {report.total_requests}")
        lines.append("")

        # TTFT statistics
        if report.ttft:
            lines.append("📊 TTFT (Time to First Token):")
            lines.append(f"  • p50 (median): {report.ttft.p50:.0f} ms")
            lines.append(f"  • p90: {report.ttft.p90:.0f} ms")
            lines.append(f"  • p99: {report.ttft.p99:.0f} ms")
            lines.append(f"  • mean: {report.ttft.mean:.0f} ms")
            lines.append(f"  • range: {report.ttft.min:.0f} - {report.ttft.max:.0f} ms")
            lines.append("")

        # Total response time statistics
        if report.total_time:
            lines.append("⏱️  Total Response Time:")
            lines.append(f"  • p50 (median): {report.total_time.p50:.0f} ms")
            lines.append(f"  • p90: {report.total_time.p90:.0f} ms")
            lines.append(f"  • p99: {report.total_time.p99:.0f} ms")
            lines.append(f"  • mean: {report.total_time.mean:.0f} ms")
            lines.append(f"  • range: {report.total_time.min:.0f} - {report.total_time.max:.0f} ms")
            lines.append("")

        # Throughput statistics
        if report.throughput:
            lines.append("🚀 Throughput (tokens/sec):")
            lines.append(f"  • p50 (median): {report.throughput.p50:.1f} tok/s")
            lines.append(f"  • p90: {report.throughput.p90:.1f} tok/s")
            lines.append(f"  • mean: {report.throughput.mean:.1f} tok/s")
            lines.append(f"  • range: {report.throughput.min:.1f} - {report.throughput.max:.1f} tok/s")
            lines.append("")

        # Breakdown by model
        if report.by_model:
            lines.append("🤖 Breakdown by Model:")
            for model, stats in sorted(report.by_model.items()):
                lines.append(f"  • {model}: {stats['count']} requests")
                lines.append(f"    - Avg TTFT: {stats['avg_ttft']:.0f} ms")
                lines.append(f"    - Avg Total: {stats['avg_total_time']:.0f} ms")
                lines.append(f"    - Avg Throughput: {stats['avg_throughput']:.1f} tok/s")
            lines.append("")

        # Cache impact
        if report.cached_vs_fresh:
            lines.append("💾 Cache Impact:")
            if 'cached' in report.cached_vs_fresh:
                cached = report.cached_vs_fresh['cached']
                lines.append(f"  • Cached: {cached['count']} requests")
                lines.append(f"    - Avg TTFT: {cached['avg_ttft']:.0f} ms")
                lines.append(f"    - Avg Total: {cached['avg_total_time']:.0f} ms")

            if 'fresh' in report.cached_vs_fresh:
                fresh = report.cached_vs_fresh['fresh']
                lines.append(f"  • Fresh (no cache): {fresh['count']} requests")
                lines.append(f"    - Avg TTFT: {fresh['avg_ttft']:.0f} ms")
                lines.append(f"    - Avg Total: {fresh['avg_total_time']:.0f} ms")

            # Calculate speedup
            if 'cached' in report.cached_vs_fresh and 'fresh' in report.cached_vs_fresh:
                cached_time = report.cached_vs_fresh['cached']['avg_total_time']
                fresh_time = report.cached_vs_fresh['fresh']['avg_total_time']

                if fresh_time > 0:
                    speedup = ((fresh_time - cached_time) / fresh_time) * 100
                    lines.append(f"  • Cache speedup: {speedup:.1f}% faster")

            lines.append("")

        # Performance trend
        lines.append(f"📈 Performance Trend: {report.trend.upper()}")
        if report.degradation_detected:
            lines.append("  ⚠️  Degradation detected! Recent responses 15%+ slower.")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Latency and Performance Tracker")
    parser.add_argument('--session-id', type=str, help="Filter by session ID")
    parser.add_argument('--limit', type=int, help="Limit number of metrics to analyze")
    parser.add_argument('--report', action='store_true', help="Generate latency report")
    parser.add_argument('--test', action='store_true', help="Run test suite")

    args = parser.parse_args()

    tracker = LatencyTracker()

    if args.test:
        # Test suite
        print("=" * 70)
        print("LATENCY TRACKER TEST SUITE")
        print("=" * 70)
        print()

        # Test 1: Track sample metrics
        print("Test 1: Track sample metrics")

        test_session = "test-session-12345"

        # Simulate 10 requests with varying latency
        for i in range(1, 11):
            tracker.track_response(
                session_id=test_session,
                request_number=i,
                ttft_ms=500 + (i * 50),  # Increasing TTFT
                total_time_ms=2000 + (i * 200),  # Increasing total time
                input_tokens=1500,
                output_tokens=800,
                model="sonnet",
                cached_tokens=1200 if i % 2 == 0 else 0,  # Alternating cache
                tool_calls=i % 3  # 0, 1, or 2 tool calls
            )

        print(f"✅ Tracked 10 sample metrics for session {test_session}")
        print()

        # Test 2: Generate report
        print("Test 2: Generate report")
        report = tracker.generate_report(session_id=test_session)
        print(tracker.format_report(report))

        # Test 3: Verify percentiles
        print("Test 3: Verify percentiles")
        assert report.total_requests == 10, "Should have 10 requests"
        assert report.ttft is not None, "Should have TTFT stats"
        assert report.ttft.p50 > 0, "P50 should be > 0"
        print("✅ PASS")
        print()

        print("=" * 70)
        print("All tests passed!")

    elif args.report:
        # Generate report
        report = tracker.generate_report(
            session_id=args.session_id,
            limit=args.limit
        )
        print(tracker.format_report(report))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
