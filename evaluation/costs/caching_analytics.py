#!/usr/bin/env python3
"""
Caching ROI Analysis Module
TIER 1 Task 2: GAP-COST-CACHING

Provides cache performance analysis, ROI calculation, and optimization recommendations.
Integrates with metrics_tracker.py for data collection.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json


class CacheAnalytics:
    """
    Analyzes prompt caching performance and calculates ROI.

    TIER 1 Task 2 (GAP-COST-CACHING): Prompt caching ROI analysis
    - Cache hit rate tracking (target: 80%+)
    - Cost savings calculation (-60-80% expected)
    - Annual ROI projection ($4,600-4,750/year medium usage)
    - Latency reduction analysis (API limitation: latency not available)
    """

    # Pricing (per 1M tokens) - Sonnet 4.5
    CACHE_PRICE_PER_1M = 3.0  # $3/1M cached tokens (90% discount)
    FRESH_PRICE_PER_1M = 30.0  # $30/1M fresh tokens (full price)

    # Target metrics
    TARGET_HIT_RATE = 0.85  # 85% cache hit rate minimum
    TARGET_COST_REDUCTION_MIN = 0.60  # 60% cost reduction minimum
    TARGET_COST_REDUCTION_MAX = 0.80  # 80% cost reduction target
    TARGET_ANNUAL_ROI_MIN = 4600  # $4,600/year minimum
    TARGET_ANNUAL_ROI_MAX = 4750  # $4,750/year target

    def __init__(self, metrics_file: Optional[Path] = None):
        """
        Initialize cache analytics.

        Args:
            metrics_file: Path to metrics.jsonl (default: ~/.claude/evaluation/data/metrics.jsonl)
        """
        if metrics_file is None:
            metrics_file = Path.home() / ".claude" / "evaluation" / "data" / "metrics.jsonl"

        self.metrics_file = metrics_file

    def calculate_roi(self, cached_tokens: int, fresh_tokens: int,
                     latency_cached: float = 0, latency_fresh: float = 0,
                     requests_per_year: int = 182500) -> Dict[str, Any]:
        """
        Calculate cache ROI: cost savings + latency reduction.

        Args:
            cached_tokens: Number of cached input tokens
            fresh_tokens: Number of fresh input tokens
            latency_cached: Request latency with cache (ms) - API doesn't provide, defaults to 0
            latency_fresh: Request latency without cache (ms) - API doesn't provide, defaults to 0
            requests_per_year: Projected annual request count (default: 500/day * 365)

        Returns:
            Dictionary with ROI metrics:
            - cost_savings: Cost saved per request ($)
            - cost_savings_pct: Cost reduction percentage
            - latency_reduction_pct: Latency reduction percentage (if available)
            - annual_savings: Projected annual cost savings ($)
            - hit_rate: Cache hit rate (0-1)
            - meets_target: Whether ROI meets target thresholds
        """
        total_input = cached_tokens + fresh_tokens
        if total_input == 0:
            return {
                "cost_savings": 0,
                "cost_savings_pct": 0,
                "latency_reduction_pct": None,
                "annual_savings": 0,
                "hit_rate": 0,
                "meets_target": False
            }

        # Calculate cache hit rate
        hit_rate = cached_tokens / total_input

        # Cost calculation
        cache_cost = cached_tokens * self.CACHE_PRICE_PER_1M / 1_000_000
        fresh_cost = fresh_tokens * self.FRESH_PRICE_PER_1M / 1_000_000
        total_cost_with_cache = cache_cost + fresh_cost
        total_cost_without_cache = total_input * self.FRESH_PRICE_PER_1M / 1_000_000

        cost_savings = total_cost_without_cache - total_cost_with_cache
        cost_savings_pct = cost_savings / total_cost_without_cache if total_cost_without_cache > 0 else 0

        # Latency reduction (if available)
        latency_reduction_pct = None
        if latency_fresh > 0 and latency_cached >= 0:
            latency_reduction_pct = (latency_fresh - latency_cached) / latency_fresh

        # Annual savings projection
        annual_savings = cost_savings * requests_per_year

        # Check if meets targets
        meets_target = (
            hit_rate >= self.TARGET_HIT_RATE and
            cost_savings_pct >= self.TARGET_COST_REDUCTION_MIN and
            annual_savings >= self.TARGET_ANNUAL_ROI_MIN
        )

        return {
            "cost_savings": cost_savings,
            "cost_savings_pct": cost_savings_pct,
            "latency_reduction_pct": latency_reduction_pct,
            "annual_savings": annual_savings,
            "hit_rate": hit_rate,
            "meets_target": meets_target,
            "total_cost_with_cache": total_cost_with_cache,
            "total_cost_without_cache": total_cost_without_cache
        }

    def analyze_cache_performance(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze cache performance over specified period.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Dictionary with performance analysis:
            - total_requests: Number of cache metric entries
            - avg_hit_rate: Average cache hit rate
            - total_savings: Total cost savings ($)
            - avg_cost_reduction: Average cost reduction percentage
            - performance_rating: Performance rating (excellent/good/needs_improvement)
            - recommendations: List of optimization recommendations
        """
        if not self.metrics_file.exists():
            return {
                "error": "Metrics file not found",
                "total_requests": 0
            }

        # Load cache metrics from last N days
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        cache_metrics = []
        with open(self.metrics_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('metric_type') == 'cache':
                        timestamp_str = entry['timestamp'].replace('Z', '+00:00')
                        timestamp = datetime.fromisoformat(timestamp_str)
                        # Ensure timezone-aware comparison
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        if start_date <= timestamp <= end_date:
                            cache_metrics.append(entry)
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue

        if not cache_metrics:
            return {
                "error": "No cache metrics found for period",
                "period_days": days,
                "total_requests": 0
            }

        # Calculate aggregates
        total_requests = len(cache_metrics)
        hit_rates = [m['metadata']['hit_rate'] for m in cache_metrics]
        savings = [m['metadata']['savings'] for m in cache_metrics]

        avg_hit_rate = sum(hit_rates) / len(hit_rates)
        total_savings = sum(savings)

        # Calculate average cost reduction
        cost_reductions = []
        for m in cache_metrics:
            with_cache = m['metadata']['cost_with_cache']
            without_cache = m['metadata']['cost_without_cache']
            if without_cache > 0:
                reduction = (without_cache - with_cache) / without_cache
                cost_reductions.append(reduction)

        avg_cost_reduction = sum(cost_reductions) / len(cost_reductions) if cost_reductions else 0

        # Performance rating
        if avg_hit_rate >= 0.90 and avg_cost_reduction >= 0.70:
            rating = "excellent"
        elif avg_hit_rate >= self.TARGET_HIT_RATE and avg_cost_reduction >= self.TARGET_COST_REDUCTION_MIN:
            rating = "good"
        else:
            rating = "needs_improvement"

        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_hit_rate, avg_cost_reduction, total_requests, days
        )

        return {
            "period_days": days,
            "total_requests": total_requests,
            "avg_hit_rate": avg_hit_rate,
            "total_savings": total_savings,
            "avg_cost_reduction": avg_cost_reduction,
            "performance_rating": rating,
            "recommendations": recommendations,
            "meets_target": avg_hit_rate >= self.TARGET_HIT_RATE and avg_cost_reduction >= self.TARGET_COST_REDUCTION_MIN
        }

    def _generate_recommendations(self, hit_rate: float, cost_reduction: float,
                                 total_requests: int, days: int) -> List[str]:
        """
        Generate optimization recommendations based on performance.

        Args:
            hit_rate: Average cache hit rate (0-1)
            cost_reduction: Average cost reduction percentage (0-1)
            total_requests: Total number of requests
            days: Period in days

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Hit rate recommendations
        if hit_rate < self.TARGET_HIT_RATE:
            recommendations.append(
                f"⚠️ Cache hit rate ({hit_rate:.1%}) below target ({self.TARGET_HIT_RATE:.0%}). "
                "Review caching strategy: ensure stable content (CLAUDE.md, modules) is cached."
            )
        elif hit_rate >= 0.95:
            recommendations.append(
                f"✅ Exceptional cache hit rate ({hit_rate:.1%})! Current strategy is highly effective."
            )
        else:
            recommendations.append(
                f"✅ Cache hit rate ({hit_rate:.1%}) meets target. Continue current strategy."
            )

        # Cost reduction recommendations
        if cost_reduction < self.TARGET_COST_REDUCTION_MIN:
            recommendations.append(
                f"⚠️ Cost reduction ({cost_reduction:.1%}) below target "
                f"({self.TARGET_COST_REDUCTION_MIN:.0%}-{self.TARGET_COST_REDUCTION_MAX:.0%}). "
                "Consider increasing cacheable content or reviewing cache boundaries."
            )
        elif cost_reduction > self.TARGET_COST_REDUCTION_MAX:
            recommendations.append(
                f"✅ Cost reduction ({cost_reduction:.1%}) exceeds target! "
                "Excellent optimization."
            )
        else:
            recommendations.append(
                f"✅ Cost reduction ({cost_reduction:.1%}) within target range. "
                "Performance optimal."
            )

        # Request volume recommendations
        requests_per_day = total_requests / days
        if requests_per_day < 50:
            recommendations.append(
                f"💡 Low request volume ({requests_per_day:.1f} req/day). "
                "Cache benefits increase with higher usage. "
                "Projected annual ROI is more reliable with 200+ req/day."
            )
        elif requests_per_day > 1000:
            recommendations.append(
                f"📈 High request volume ({requests_per_day:.1f} req/day). "
                "Cache optimization is critical. Monitor cache invalidation rates."
            )

        # Caching strategy recommendations
        if hit_rate >= 0.85:
            recommendations.append(
                "✅ Current 4-tier caching architecture is working well: "
                "Core Identity (Tier 1), Domain Modules (Tier 2), Few-Shot Examples (Tier 4)."
            )

        return recommendations

    def get_optimization_checklist(self) -> List[Dict[str, str]]:
        """
        Get optimization checklist for improving cache performance.

        Returns:
            List of optimization items with description and impact
        """
        return [
            {
                "item": "Review cache boundaries",
                "description": "Ensure CLAUDE.md and modules are in Tier 1-2 (always cached)",
                "impact": "HIGH - Increases hit rate by 10-15%"
            },
            {
                "item": "Minimize dynamic content in system prompt",
                "description": "Move timestamps, session IDs, user-specific data to user messages",
                "impact": "HIGH - Improves cache stability"
            },
            {
                "item": "Use cache_control blocks explicitly",
                "description": "Mark cacheable sections with cache_control: {type: 'ephemeral'}",
                "impact": "MEDIUM - Ensures intended content is cached"
            },
            {
                "item": "Monitor cache invalidation",
                "description": "Track how often cache needs to be rebuilt due to content changes",
                "impact": "MEDIUM - Identifies unstable cache sections"
            },
            {
                "item": "Optimize module loading",
                "description": "Load only necessary modules per domain to reduce fresh tokens",
                "impact": "MEDIUM - Reduces non-cacheable overhead"
            },
            {
                "item": "Separate static from dynamic few-shot examples",
                "description": "Cache generic examples (Tier 4), pass task-specific examples as fresh",
                "impact": "LOW - Minor hit rate improvement (2-3%)"
            }
        ]


def main():
    """CLI entry point for caching analytics."""
    import argparse

    parser = argparse.ArgumentParser(description="Caching ROI Analysis (TIER 1 Task 2)")
    parser.add_argument('--days', type=int, default=7, help="Analysis period in days (default: 7)")
    parser.add_argument('--metrics-file', type=Path, help="Path to metrics.jsonl file")
    parser.add_argument('--recommendations', action='store_true', help="Show optimization checklist")

    args = parser.parse_args()

    analytics = CacheAnalytics(metrics_file=args.metrics_file)

    if args.recommendations:
        print("\n📋 Cache Optimization Checklist\n")
        checklist = analytics.get_optimization_checklist()
        for i, item in enumerate(checklist, 1):
            print(f"{i}. **{item['item']}** ({item['impact']})")
            print(f"   {item['description']}\n")
    else:
        print(f"\n🔍 Analyzing cache performance (last {args.days} days)...\n")
        result = analytics.analyze_cache_performance(days=args.days)

        if "error" in result:
            print(f"❌ {result['error']}")
            return

        print(f"📊 Cache Performance Report\n")
        print(f"Period: {result['period_days']} days")
        print(f"Total Requests: {result['total_requests']}")
        print(f"Average Hit Rate: {result['avg_hit_rate']:.2%}")
        print(f"Total Savings: ${result['total_savings']:.2f}")
        print(f"Average Cost Reduction: {result['avg_cost_reduction']:.1%}")
        print(f"Performance Rating: {result['performance_rating'].upper()}")
        print(f"Meets Target: {'✅ YES' if result['meets_target'] else '⚠️ NO'}")

        print(f"\n💡 Recommendations:\n")
        for rec in result['recommendations']:
            print(f"  {rec}")


if __name__ == "__main__":
    main()
