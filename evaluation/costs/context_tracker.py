#!/usr/bin/env python3
"""
Context Budget Tracking Module
TIER 1 Tasks 4/5: GAP-COST-SESSION-004 + GAP-COST-IMPL-003

Real-time context window usage tracking with optimization suggestions.
Monitors token utilization, projects when context will be full, suggests session reopening.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ContextSnapshot:
    """Context budget snapshot at a point in time."""
    timestamp: str
    current_tokens: int
    max_tokens: int
    utilization: float
    cached_tokens: int
    fresh_tokens: int
    history_tokens: int
    efficiency: float  # Cache hit rate
    status: str  # healthy/warning/critical/exceeded
    message_count: int


class ContextBudgetTracker:
    """
    Tracks context window budget for Claude MAX usage optimization.

    TIER 1 Tasks 4/5 (GAP-COST-SESSION-004 + GAP-COST-IMPL-003):
    - Real-time context utilization tracking
    - Automatic triggers at 75%, 85%, 95% thresholds
    - Projection when context will be full
    - Session reopening suggestions
    - Dashboard display integration

    Target: Claude MAX subscribers (1M context window)
    Problem: Long sessions → context fills → degraded performance
    Solution: Proactive monitoring + timely session reopening
    """

    # Thresholds for alerts
    MAX_CONTEXT_TOKENS = 1_000_000  # Claude MAX context limit (1M)
    THRESHOLD_NORMAL = 0.75  # 750k tokens - show budget
    THRESHOLD_WARNING = 0.85  # 850k tokens - warn user
    THRESHOLD_CRITICAL = 0.95  # 950k tokens - critical alert

    def __init__(self, metrics_file: Optional[Path] = None, max_tokens: int = MAX_CONTEXT_TOKENS):
        """
        Initialize context budget tracker.

        Args:
            metrics_file: Path to metrics.jsonl (default: ~/.claude/evaluation/data/metrics.jsonl)
            max_tokens: Maximum context window size (default: 1M for Claude MAX)
        """
        if metrics_file is None:
            metrics_file = Path.home() / ".claude" / "evaluation" / "data" / "metrics.jsonl"

        self.metrics_file = metrics_file
        self.max_tokens = max_tokens

    def parse_session_for_context(self, session_file: Path) -> List[ContextSnapshot]:
        """
        Parse session JSONL file and extract context budget snapshots.

        Args:
            session_file: Path to session JSONL file

        Returns:
            List of ContextSnapshot instances
        """
        snapshots = []
        message_count = 0
        first_total_input = None

        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Process API response messages with usage data
                    if 'message' in entry and 'usage' in entry['message']:
                        usage = entry['message']['usage']
                        message_count += 1

                        # Extract token counts
                        input_fresh = usage.get('input_tokens', 0)
                        cache_creation = usage.get('cache_creation_input_tokens', 0)
                        cache_read = usage.get('cache_read_input_tokens', 0)
                        output = usage.get('output_tokens', 0)

                        # Total input = fresh + cache_creation + cache_read
                        total_input = input_fresh + cache_creation + cache_read
                        cached = cache_read
                        fresh = input_fresh + cache_creation

                        # Calculate history tokens (approximation)
                        if first_total_input is None:
                            first_total_input = total_input
                            history = 0
                        else:
                            history = max(0, total_input - first_total_input)

                        # Current tokens = total_input + output (approximation for context usage)
                        # Note: Actual context includes conversation history, which accumulates
                        current_tokens = total_input

                        # Calculate utilization
                        utilization = current_tokens / self.max_tokens

                        # Determine status
                        if utilization >= self.THRESHOLD_CRITICAL:
                            status = "critical"
                        elif utilization >= self.THRESHOLD_WARNING:
                            status = "warning"
                        elif utilization >= self.THRESHOLD_NORMAL:
                            status = "normal"
                        else:
                            status = "healthy"

                        # Calculate efficiency (cache hit rate)
                        usable_input = input_fresh + cache_read
                        efficiency = cache_read / usable_input if usable_input > 0 else 0

                        # Get timestamp
                        timestamp = entry.get('timestamp', datetime.now(timezone.utc).isoformat())

                        snapshots.append(ContextSnapshot(
                            timestamp=timestamp,
                            current_tokens=current_tokens,
                            max_tokens=self.max_tokens,
                            utilization=utilization,
                            cached_tokens=cached,
                            fresh_tokens=fresh,
                            history_tokens=history,
                            efficiency=efficiency,
                            status=status,
                            message_count=message_count
                        ))

                except (json.JSONDecodeError, KeyError):
                    continue

        return snapshots

    def calculate_context_stats(self, snapshots: List[ContextSnapshot]) -> Dict[str, Any]:
        """
        Calculate aggregate context budget statistics.

        Args:
            snapshots: List of ContextSnapshot instances

        Returns:
            Dictionary with context statistics:
            - current_tokens: Current total tokens
            - max_tokens: Maximum context window
            - utilization_pct: Current utilization percentage
            - cached_tokens: Cached tokens count
            - fresh_tokens: Fresh tokens count
            - history_tokens: Conversation history size
            - efficiency: Average cache hit rate
            - history_growth_rate: Tokens per request
            - projected_full_requests: Requests until context full
            - projected_full_minutes: Minutes until context full (estimate)
            - status: Current status (healthy/normal/warning/critical)
            - recommendation: Action recommendation
        """
        if not snapshots:
            return {"error": "No snapshots provided"}

        last = snapshots[-1]
        total_requests = len(snapshots)

        # Calculate average efficiency
        avg_efficiency = sum(s.efficiency for s in snapshots) / total_requests

        # History growth rate
        if total_requests > 1:
            history_growth_rate = last.history_tokens / total_requests
        else:
            history_growth_rate = 0

        # Project when context will be full
        remaining_tokens = self.max_tokens - last.current_tokens
        if history_growth_rate > 0:
            projected_full_requests = int(remaining_tokens / history_growth_rate)
            # Estimate 30 seconds per request (average)
            projected_full_minutes = (projected_full_requests * 30) / 60
        else:
            projected_full_requests = None
            projected_full_minutes = None

        # Determine recommendation based on status
        utilization_pct = last.utilization * 100

        if last.status == "critical":
            recommendation = "🔴 CRITICAL: Context nearly full. Reopen session NOW."
        elif last.status == "warning":
            recommendation = f"⚠️ High context usage ({utilization_pct:.1f}%). Session reopening recommended."
        elif last.status == "normal":
            if projected_full_requests and projected_full_requests < 50:
                recommendation = f"💡 Consider session reopening in ~{projected_full_requests} requests to maintain efficiency."
            else:
                recommendation = f"✅ Context usage normal ({utilization_pct:.1f}%). Monitor as session continues."
        else:
            recommendation = f"✅ Context healthy ({utilization_pct:.1f}%). Continue working."

        return {
            "current_tokens": last.current_tokens,
            "max_tokens": last.max_tokens,
            "utilization_pct": utilization_pct,
            "cached_tokens": last.cached_tokens,
            "fresh_tokens": last.fresh_tokens,
            "history_tokens": last.history_tokens,
            "efficiency": avg_efficiency,
            "history_growth_rate": history_growth_rate,
            "projected_full_requests": projected_full_requests,
            "projected_full_minutes": projected_full_minutes,
            "status": last.status,
            "recommendation": recommendation,
            "total_requests": total_requests
        }

    def should_summarize(self, current_tokens: int) -> bool:
        """
        Determine if session should be summarized based on context usage.

        Args:
            current_tokens: Current token count

        Returns:
            True if utilization exceeds warning threshold (85%)
        """
        return (current_tokens / self.max_tokens) > self.THRESHOLD_WARNING

    def selective_retain(self, messages: List[Dict[str, Any]], importance_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Retain important messages for selective history management.

        Priority: Code blocks > Decisions > Explanations

        Args:
            messages: List of message dictionaries
            importance_threshold: Minimum importance score to retain (0.0-1.0)

        Returns:
            Filtered list of messages
        """
        retained = []

        for msg in messages:
            content = msg.get('content', '')

            # Calculate importance score
            importance = 0.0

            # High priority: Code blocks
            if '```' in content:
                importance = 1.0
            # Medium priority: Decisions, errors, critical info
            elif any(keyword in content.lower() for keyword in ['error', 'critical', 'decision', 'implementation']):
                importance = 0.8
            # Low priority: Explanations, context
            elif any(keyword in content.lower() for keyword in ['explanation', 'background', 'context']):
                importance = 0.5
            else:
                importance = 0.3

            # Retain if importance exceeds threshold
            if importance >= importance_threshold:
                retained.append(msg)

        return retained

    def display_context_budget(self, session_file: Path) -> str:
        """
        Generate dashboard display for context budget.

        Args:
            session_file: Path to session JSONL file

        Returns:
            Formatted dashboard string
        """
        snapshots = self.parse_session_for_context(session_file)
        if not snapshots:
            return "❌ No context snapshots found in session file"

        stats = self.calculate_context_stats(snapshots)

        # Format numbers
        current = stats['current_tokens']
        max_tokens = stats['max_tokens']
        pct = stats['utilization_pct']
        cached = stats['cached_tokens']
        fresh = stats['fresh_tokens']
        history = stats['history_tokens']
        efficiency = stats['efficiency']
        growth_rate = stats['history_growth_rate']
        projected_req = stats['projected_full_requests']
        projected_min = stats['projected_full_minutes']

        # Build projection line
        if projected_req is not None:
            projection = f"│ Projected full: ~{projected_req} requests ({projected_min:.0f} minutes)\n"
        else:
            projection = "│ Projected full: N/A (no growth detected)\n"

        dashboard = f"""
┌─ CONTEXT BUDGET ─────────────────────────────────────────┐
│ Total: {current:,} / {max_tokens:,} tokens ({pct:.1f}%)
│ ├─ Cached: {cached:,} (core config, modules)
│ ├─ Fresh input: {fresh:,} (user query + cache creation)
│ └─ History: {history:,} (conversation accumulation)
│
│ Efficiency: {efficiency:.1%} (cache hit rate)
│ History growth: +{growth_rate:.1f} tokens/request avg
{projection}│
│ STATUS: {stats['status'].upper()}
│ {stats['recommendation']}
└──────────────────────────────────────────────────────────┘
"""
        return dashboard

    def collect_context_metric(self, snapshot: ContextSnapshot) -> None:
        """
        Collect context budget metric and store in metrics.jsonl.

        Args:
            snapshot: ContextSnapshot instance to store
        """
        metric_entry = {
            'timestamp': snapshot.timestamp,
            'metric_type': 'context_budget',
            'value': snapshot.utilization,
            'metadata': {
                'current_tokens': snapshot.current_tokens,
                'max_tokens': snapshot.max_tokens,
                'utilization': snapshot.utilization,
                'cached_tokens': snapshot.cached_tokens,
                'fresh_tokens': snapshot.fresh_tokens,
                'history_tokens': snapshot.history_tokens,
                'efficiency': snapshot.efficiency,
                'status': snapshot.status,
                'message_count': snapshot.message_count
            }
        }

        # Append to metrics file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metric_entry) + '\n')

    def track_context(self, session_file: Path, store_metrics: bool = True) -> Dict[str, Any]:
        """
        Track context budget and optionally store metrics.

        Args:
            session_file: Path to session JSONL file
            store_metrics: Whether to store metrics in metrics.jsonl

        Returns:
            Context statistics dictionary
        """
        snapshots = self.parse_session_for_context(session_file)

        if store_metrics:
            for snapshot in snapshots:
                self.collect_context_metric(snapshot)

        return self.calculate_context_stats(snapshots)


def main():
    """CLI entry point for context budget tracking."""
    import argparse

    parser = argparse.ArgumentParser(description="Context Budget Tracking (TIER 1 Tasks 4/5)")
    parser.add_argument('session_file', type=Path, help="Path to session JSONL file")
    parser.add_argument('--dashboard', action='store_true', help="Show dashboard display")
    parser.add_argument('--store', action='store_true', help="Store metrics in metrics.jsonl")
    parser.add_argument('--stats', action='store_true', help="Show detailed statistics")
    parser.add_argument('--max-tokens', type=int, default=1000000, help="Max context window size (default: 1M)")

    args = parser.parse_args()

    if not args.session_file.exists():
        print(f"❌ Session file not found: {args.session_file}")
        return

    tracker = ContextBudgetTracker(max_tokens=args.max_tokens)

    if args.dashboard:
        print(tracker.display_context_budget(args.session_file))

    if args.stats or not args.dashboard:
        stats = tracker.track_context(args.session_file, store_metrics=args.store)

        print(f"\n📊 Context Budget Statistics\n")
        print(f"Current Tokens: {stats['current_tokens']:,} / {stats['max_tokens']:,}")
        print(f"Utilization: {stats['utilization_pct']:.2f}%")
        print(f"Cached Tokens: {stats['cached_tokens']:,}")
        print(f"Fresh Tokens: {stats['fresh_tokens']:,}")
        print(f"History Tokens: {stats['history_tokens']:,}")
        print(f"Average Efficiency: {stats['efficiency']:.2%}")
        print(f"History Growth Rate: {stats['history_growth_rate']:.1f} tokens/request")

        if stats['projected_full_requests']:
            print(f"Projected Full: ~{stats['projected_full_requests']} requests ({stats['projected_full_minutes']:.0f} minutes)")
        else:
            print(f"Projected Full: N/A")

        print(f"Status: {stats['status'].upper()}")
        print(f"\n{stats['recommendation']}")

        if args.store:
            print(f"\n✅ Metrics stored to: {tracker.metrics_file}")


if __name__ == "__main__":
    main()
