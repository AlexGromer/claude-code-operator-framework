#!/usr/bin/env python3
"""
Automatic GAP Analysis Script

Analyzes metrics to detect regressions and creates GAPs automatically.
Called by systemd timer every Monday at 09:30 (after stats generation).

Detection criteria:
- Cache hit rate < 70% (target: 85-95%)
- Tool error rate > 5% (target: <5%)
- Latency increase > 20% week-over-week
- Routing confidence < 40% for any domain (target: >70%)
- Context budget exceeded (>95% utilization)

Usage:
    python analyze_gaps.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics_tracker import MetricsTracker


class GAPAnalyzer:
    """Analyzes metrics and creates GAPs for regressions."""

    def __init__(self):
        self.tracker = MetricsTracker()
        self.gaps_file = Path.home() / ".claude" / "GAPS.md"
        self.thresholds = {
            'cache_hit_rate_min': 0.70,
            'tool_error_rate_max': 0.05,
            'latency_increase_max': 0.20,
            'routing_confidence_min': 0.40,
            'context_utilization_max': 0.95
        }

    def analyze_cache_performance(self) -> List[Dict[str, Any]]:
        """Analyze cache hit rate."""
        gaps = []

        # Get cache metrics from last 7 days
        cache_metrics = self.tracker.get_metrics('cache', days=7)

        if not cache_metrics:
            return gaps

        avg_hit_rate = sum(m['value'] for m in cache_metrics) / len(cache_metrics)

        if avg_hit_rate < self.thresholds['cache_hit_rate_min']:
            gaps.append({
                'type': 'PERFORMANCE',
                'title': f'Low cache hit rate: {avg_hit_rate:.1%}',
                'description': f'Cache hit rate ({avg_hit_rate:.1%}) below threshold ({self.thresholds["cache_hit_rate_min"]:.0%})',
                'priority': 'P2',
                'module': 'CLAUDE.md (Prompt Caching)',
                'metric': avg_hit_rate
            })

        return gaps

    def analyze_tool_errors(self) -> List[Dict[str, Any]]:
        """Analyze tool error rate."""
        gaps = []

        # Get tool error metrics from last 7 days
        error_metrics = self.tracker.get_metrics('tool_error', days=7)

        if not error_metrics:
            return gaps

        # Calculate error rate (errors / total calls)
        total_calls = len(error_metrics)
        errors = sum(1 for m in error_metrics if m['value'] == 1)
        error_rate = errors / total_calls if total_calls > 0 else 0

        if error_rate > self.thresholds['tool_error_rate_max']:
            gaps.append({
                'type': 'RELIABILITY',
                'title': f'High tool error rate: {error_rate:.1%}',
                'description': f'Tool error rate ({error_rate:.1%}) exceeds threshold ({self.thresholds["tool_error_rate_max"]:.0%})',
                'priority': 'P1',
                'module': 'Unknown (analyze error patterns)',
                'metric': error_rate
            })

        return gaps

    def analyze_latency(self) -> List[Dict[str, Any]]:
        """Analyze latency trends."""
        gaps = []

        # Get latency metrics
        current_week = self.tracker.get_metrics('latency', days=7)
        previous_week = self.tracker.get_metrics('latency', days=14, offset=7)

        if not current_week or not previous_week:
            return gaps

        avg_current = sum(m['value'] for m in current_week) / len(current_week)
        avg_previous = sum(m['value'] for m in previous_week) / len(previous_week)

        if avg_previous > 0:
            increase = (avg_current - avg_previous) / avg_previous

            if increase > self.thresholds['latency_increase_max']:
                gaps.append({
                    'type': 'PERFORMANCE',
                    'title': f'Latency increased {increase:.1%} week-over-week',
                    'description': f'Average latency: {avg_current:.2f}s (was {avg_previous:.2f}s)',
                    'priority': 'P2',
                    'module': 'Unknown (investigate bottlenecks)',
                    'metric': increase
                })

        return gaps

    def analyze_routing_confidence(self) -> List[Dict[str, Any]]:
        """Analyze routing confidence by domain."""
        gaps = []

        # Get routing metrics
        routing_metrics = self.tracker.get_metrics('model_routing', days=7)

        if not routing_metrics:
            return gaps

        # Group by domain
        by_domain = {}
        for m in routing_metrics:
            domain = m.get('metadata', {}).get('domain', 'unknown')
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(m['value'])

        # Check each domain
        for domain, confidences in by_domain.items():
            avg_confidence = sum(confidences) / len(confidences)

            if avg_confidence < self.thresholds['routing_confidence_min']:
                gaps.append({
                    'type': 'ACCURACY',
                    'title': f'Low routing confidence in {domain}: {avg_confidence:.1%}',
                    'description': f'Average confidence ({avg_confidence:.1%}) below threshold ({self.thresholds["routing_confidence_min"]:.0%})',
                    'priority': 'P2',
                    'module': f'modules/00-role-routing.md ({domain})',
                    'metric': avg_confidence
                })

        return gaps

    def analyze_context_budget(self) -> List[Dict[str, Any]]:
        """Analyze context budget utilization."""
        gaps = []

        # Get context budget metrics
        budget_metrics = self.tracker.get_metrics('context_budget', days=7)

        if not budget_metrics:
            return gaps

        # Check for exceeded budget
        exceeded_count = sum(
            1 for m in budget_metrics
            if m.get('metadata', {}).get('status') == 'exceeded'
        )

        if exceeded_count > 0:
            gaps.append({
                'type': 'CAPACITY',
                'title': f'Context budget exceeded {exceeded_count} times in last 7 days',
                'description': 'Sessions running out of context window — need better summarization or session management',
                'priority': 'P1',
                'module': 'CLAUDE.md (Session Management)',
                'metric': exceeded_count
            })

        # Check for critical utilization
        critical_count = sum(
            1 for m in budget_metrics
            if m.get('metadata', {}).get('status') == 'critical'
        )

        if critical_count > len(budget_metrics) * 0.20:  # >20% of sessions critical
            gaps.append({
                'type': 'CAPACITY',
                'title': f'{critical_count} sessions in critical context range (80-95%)',
                'description': 'High number of sessions approaching context limit',
                'priority': 'P2',
                'module': 'CLAUDE.md (Session Management)',
                'metric': critical_count
            })

        return gaps

    def create_gap_entry(self, gap: Dict[str, Any]) -> str:
        """Format GAP entry for GAPS.md."""
        timestamp = datetime.now().strftime("%Y-%m-%d")

        return f"""
### GAP-AUTO-{gap['type']}-{timestamp.replace('-', '')}

**Title:** {gap['title']}
**Priority:** {gap['priority']}
**Module:** {gap['module']}
**Status:** 🔴 DETECTED (auto-generated)
**Detected:** {timestamp}
**Metric:** {gap['metric']}

**Description:**
{gap['description']}

**Recommended Actions:**
- Analyze root cause in affected module
- Review recent changes to configuration
- Check for external factors (API changes, load increase)
- Implement fixes and monitor metric improvement

**Detection Method:** Automatic via `analyze_gaps.py`

---
"""

    def write_gaps_to_file(self, gaps: List[Dict[str, Any]]) -> None:
        """Append detected gaps to GAPS.md."""
        if not gaps:
            print("✅ No regressions detected — all metrics healthy")
            return

        # Read current GAPS.md
        if self.gaps_file.exists():
            with open(self.gaps_file, 'r') as f:
                current_content = f.read()
        else:
            current_content = "# GAPS.md - Tracked Gaps and Resolutions\n\n"

        # Find insertion point (after header, before first GAP)
        lines = current_content.split('\n')
        insertion_index = 0

        for i, line in enumerate(lines):
            if line.startswith('### GAP-'):
                insertion_index = i
                break

        if insertion_index == 0:
            # No existing gaps, append to end
            insertion_index = len(lines)

        # Insert new gaps
        new_entries = []
        for gap in gaps:
            new_entries.append(self.create_gap_entry(gap))

        # Combine
        new_content = '\n'.join(lines[:insertion_index]) + '\n'.join(new_entries) + '\n'.join(lines[insertion_index:])

        # Write back
        with open(self.gaps_file, 'w') as f:
            f.write(new_content)

        print(f"⚠️  Detected {len(gaps)} regression(s) — logged to {self.gaps_file}")
        for gap in gaps:
            print(f"   - {gap['priority']} {gap['title']}")

    def run_analysis(self) -> None:
        """Run full GAP analysis."""
        print("🔍 Running automatic GAP analysis...")

        all_gaps = []

        # Run all analyzers
        all_gaps.extend(self.analyze_cache_performance())
        all_gaps.extend(self.analyze_tool_errors())
        all_gaps.extend(self.analyze_latency())
        all_gaps.extend(self.analyze_routing_confidence())
        all_gaps.extend(self.analyze_context_budget())

        # Write to GAPS.md
        self.write_gaps_to_file(all_gaps)


def main():
    """Main entry point."""
    try:
        analyzer = GAPAnalyzer()
        analyzer.run_analysis()
    except Exception as e:
        print(f"❌ Error during GAP analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
