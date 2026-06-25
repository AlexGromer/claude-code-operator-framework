#!/usr/bin/env python3
"""
Cache Analytics Dashboard
Version: 1.0.0

Analyzes prompt caching metrics and generates cost optimization reports.
Reads cache metrics from metrics_tracker.py storage.

Usage:
    python cache_analytics.py --period week
    python cache_analytics.py --period month --output report.md
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any


class CacheAnalytics:
    """Analyze cache metrics from metrics_tracker."""

    def __init__(self, metrics_file: Path = None):
        """
        Initialize cache analytics.

        Args:
            metrics_file: Path to metrics.jsonl file
        """
        if metrics_file is None:
            metrics_file = Path.home() / ".claude" / "evaluation" / "data" / "metrics.jsonl"
        self.metrics_file = metrics_file

    def load_cache_metrics(self, period: str = "week") -> List[Dict]:
        """
        Load cache metrics from JSONL file.

        Args:
            period: Time period (day, week, month, all)

        Returns:
            List of cache metric entries
        """
        if not self.metrics_file.exists():
            return []

        # Calculate date range
        now = datetime.now(timezone.utc)
        if period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "week":
            cutoff = now - timedelta(weeks=1)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        else:  # all
            cutoff = datetime.min.replace(tzinfo=timezone.utc)

        # Load and filter
        cache_metrics = []
        with open(self.metrics_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('metric_type') == 'cache':
                        # Parse timestamp (handle with or without 'Z' suffix)
                        timestamp_str = entry['timestamp'].replace('Z', '+00:00')
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timestamp >= cutoff:
                            cache_metrics.append(entry)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        return cache_metrics

    def calculate_statistics(self, metrics: List[Dict]) -> Dict[str, Any]:
        """
        Calculate aggregate statistics.

        Args:
            metrics: List of cache metric entries

        Returns:
            Dictionary with calculated statistics
        """
        if not metrics:
            return {"error": "No cache metrics found for this period"}

        total_requests = len(metrics)

        # Extract values from metadata
        hit_rates = []
        savings = []
        latencies = []
        cached_tokens = 0
        fresh_tokens = 0

        for m in metrics:
            metadata = m.get('metadata', {})
            if 'hit_rate' in metadata:
                hit_rates.append(metadata['hit_rate'])
            if 'savings' in metadata:
                savings.append(metadata['savings'])
            if 'latency_ms' in metadata:
                latencies.append(metadata['latency_ms'])
            cached_tokens += metadata.get('cached_tokens', 0)
            fresh_tokens += metadata.get('fresh_tokens', 0)

        total_tokens = cached_tokens + fresh_tokens

        return {
            'total_requests': total_requests,
            'avg_hit_rate': sum(hit_rates) / len(hit_rates) if hit_rates else 0,
            'total_savings': sum(savings),
            'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
            'total_cached_tokens': cached_tokens,
            'total_fresh_tokens': fresh_tokens,
            'total_input_tokens': total_tokens
        }

    def generate_report(self, period: str = "week", format: str = "markdown") -> str:
        """
        Generate cache analytics report.

        Args:
            period: Time period (day, week, month, all)
            format: Output format (markdown, json)

        Returns:
            Formatted report as string
        """
        metrics = self.load_cache_metrics(period)
        stats = self.calculate_statistics(metrics)

        if "error" in stats:
            if format == "json":
                return json.dumps({"error": stats["error"]}, indent=2)
            return f"# Cache Analytics Report\n\n❌ {stats['error']}\n"

        if format == "json":
            return json.dumps(stats, indent=2)

        # Calculate projections
        if period == "week":
            multiplier = 52
            period_label = "Weekly"
        elif period == "month":
            multiplier = 12
            period_label = "Monthly"
        elif period == "day":
            multiplier = 365
            period_label = "Daily"
        else:
            multiplier = 1
            period_label = "All-Time"

        projected_annual = stats['total_savings'] * multiplier

        # Generate markdown report
        report = f"""# 💰 Cache Analytics Dashboard

**Period:** {period_label}
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Total Requests** | {stats['total_requests']:,} |
| **Average Cache Hit Rate** | {stats['avg_hit_rate']*100:.1f}% |
| **Average Latency** | {stats['avg_latency_ms']:.0f}ms |
| **Total Savings (Period)** | ${stats['total_savings']:.2f} |
| **Projected Annual Savings** | ${projected_annual:.2f} |

---

## 🎯 Cache Performance

**Target Hit Rate:** 85-95%
**Current:** {stats['avg_hit_rate']*100:.1f}%
"""

        # Status indicator
        if 0.85 <= stats['avg_hit_rate'] <= 0.95:
            report += "**Status:** ✅ **ON TARGET**\n\n"
            status_emoji = "✅"
        elif stats['avg_hit_rate'] < 0.85:
            report += "**Status:** ⚠️ **BELOW TARGET**\n\n"
            status_emoji = "⚠️"
        else:
            report += "**Status:** ✅ **EXCELLENT** (Above 95%)\n\n"
            status_emoji = "⭐"

        # Token breakdown
        if stats['total_input_tokens'] > 0:
            cached_pct = stats['total_cached_tokens'] / stats['total_input_tokens'] * 100
            fresh_pct = stats['total_fresh_tokens'] / stats['total_input_tokens'] * 100
        else:
            cached_pct = fresh_pct = 0

        report += f"""---

## 💡 Token Breakdown

| Component | Tokens | Percentage |
|-----------|--------|------------|
| **Cached** | {stats['total_cached_tokens']:,} | {cached_pct:.1f}% |
| **Fresh** | {stats['total_fresh_tokens']:,} | {fresh_pct:.1f}% |
| **Total Input** | {stats['total_input_tokens']:,} | 100.0% |

---

## 📈 Recommendations

"""

        # Recommendations based on hit rate
        if stats['avg_hit_rate'] < 0.85:
            report += """- ⚠️ Cache hit rate below target (85%). Consider:
  - **Increasing cache TTL** (currently 5 min default)
  - **Restructuring prompts** for better reuse (more static content first)
  - **Adding more cacheable content** to system prompts
  - **Review CLAUDE.md sections** - move stable content to top
  - **Check Tier 4 caching** (few-shot examples should be cached)

"""
        elif stats['avg_hit_rate'] > 0.95:
            report += """- ⭐ **Excellent cache performance!** (>95% hit rate)
  - Continue current caching strategy
  - Monitor for regression weekly
  - Consider this a baseline for future optimizations

"""
        else:
            report += """- ✅ Cache hit rate within target range (85-95%)
  - Maintain current caching strategy
  - Monitor weekly for any degradation
  - Good balance of static vs dynamic content

"""

        # Cost optimization recommendations
        report += f"""## 💵 Cost Optimization Impact

Based on {period_label.lower()} data:
- **Current savings:** ${stats['total_savings']:.2f}
- **Projected annual:** ${projected_annual:.2f}
- **Effective discount:** {stats['avg_hit_rate']*0.9*100:.1f}% (cache hit rate × 90% discount)

**Next steps:**
1. Implement Model Router (Task 7) for additional -75% cost reduction
2. Add Context Budget Tracker (Task 8) for -30% on long sessions
3. Combined impact: -60-80% total cost reduction

---

*Generated by Cache Analytics Dashboard v1.0.0*
"""

        return report


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cache Analytics Dashboard - Analyze prompt caching metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --period week          # Weekly report (default)
  %(prog)s --period day           # Last 24 hours
  %(prog)s --period month         # Last 30 days
  %(prog)s --period all           # All-time statistics
  %(prog)s --output report.md     # Save to file
  %(prog)s --format json          # JSON output
        """
    )

    parser.add_argument(
        "--period",
        choices=["day", "week", "month", "all"],
        default="week",
        help="Report period (default: week)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--metrics-file",
        type=str,
        help="Path to metrics.jsonl file (default: ~/.claude/evaluation/data/metrics.jsonl)"
    )

    args = parser.parse_args()

    # Initialize analytics
    metrics_file = Path(args.metrics_file) if args.metrics_file else None
    analytics = CacheAnalytics(metrics_file=metrics_file)

    # Generate report
    try:
        report = analytics.generate_report(period=args.period, format=args.format)

        # Output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report)
            print(f"✅ Report saved to {args.output}")
        else:
            print(report)

    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
