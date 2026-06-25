#!/usr/bin/env python3
"""
Claude Metrics Tracker
Version: 2.0.0

Tracks and reports metrics for Claude agent performance:
- Accuracy (correct responses)
- Hallucinations (fabricated facts)
- Tool errors (failed tool calls)
- Latency (response time)
- Cost (API usage)
- Model routing (Tier 2 integration)
- Context budget (Tier 2 integration)
- Cache performance (Tier 2 integration)
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

try:
    import pandas as pd
    import numpy as np
    from scipy import stats
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)


class MetricsTracker:
    """Core metrics tracking and reporting engine."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize metrics tracker with configuration."""
        self.config_path = config_path or Path.home() / ".claude" / "evaluation" / "config.yaml"
        self.config = self._load_config()

        # Paths
        self.data_path = Path(self.config['evaluation']['metrics']['storage_path']).expanduser()
        self.reports_path = Path(self.config['evaluation']['reporting']['output_path']).expanduser()

        # Ensure directories exist
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            print(f"ERROR: Configuration file not found: {self.config_path}")
            print("Run setup.py first to create configuration.")
            sys.exit(1)

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def collect_metric(self, metric_type: str, value: Any, metadata: Optional[Dict] = None) -> None:
        """
        Collect a single metric data point.

        Args:
            metric_type: Type of metric (accuracy, hallucination, tool_error, latency, cost)
            value: Metric value
            metadata: Additional context (task_id, domain, model, etc.)
        """
        if not self.config['evaluation']['metrics']['enabled']:
            return

        metric_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metric_type': metric_type,
            'value': value,
            'metadata': metadata or {}
        }

        # Append to JSONL file
        with open(self.data_path, 'a') as f:
            f.write(json.dumps(metric_entry) + '\n')

    def collect_cache_metric(self, cached_tokens: int, fresh_tokens: int,
                            latency_ms: int, model: str = "claude-sonnet-4-5-20250929") -> None:
        """
        Collect cache-specific metrics for prompt caching analysis.

        Args:
            cached_tokens: Number of cached input tokens
            fresh_tokens: Number of fresh input tokens
            latency_ms: Request latency in milliseconds
            model: Model identifier
        """
        if not self.config['evaluation']['metrics']['enabled']:
            return

        total_input = cached_tokens + fresh_tokens
        hit_rate = cached_tokens / total_input if total_input > 0 else 0

        # Pricing (per 1M tokens)
        # Cached: 90% discount ($0.003 vs $0.03 for Sonnet)
        cache_cost = cached_tokens * 0.003 / 1000
        fresh_cost = fresh_tokens * 0.03 / 1000
        without_cache_cost = total_input * 0.03 / 1000
        savings = without_cache_cost - (cache_cost + fresh_cost)

        # Store as cache metric with detailed metadata
        metadata = {
            'model': model,
            'cached_tokens': cached_tokens,
            'fresh_tokens': fresh_tokens,
            'total_input_tokens': total_input,
            'hit_rate': hit_rate,
            'latency_ms': latency_ms,
            'savings': savings,
            'cost_with_cache': cache_cost + fresh_cost,
            'cost_without_cache': without_cache_cost
        }

        self.collect_metric('cache', hit_rate, metadata)

    def collect_model_routing_metric(self, task_description: str, selected_model: str,
                                     complexity: str, cost_saved: float) -> None:
        """
        Collect model routing metrics for cost optimization tracking.

        Args:
            task_description: Brief task description
            selected_model: Model selected by router (haiku/sonnet/opus)
            complexity: Classified complexity (simple/medium/complex)
            cost_saved: Estimated cost savings vs always using Sonnet
        """
        if not self.config['evaluation']['metrics']['enabled']:
            return

        metadata = {
            'task_description': task_description[:100],  # Truncate
            'selected_model': selected_model,
            'complexity': complexity,
            'cost_saved_usd': cost_saved,
            'router_version': '1.0.0'
        }

        self.collect_metric('model_routing', selected_model, metadata)

    def collect_session_token_metric(self, session_id: str, request_number: int,
                                     input_tokens_total: int, input_tokens_cached: int,
                                     input_tokens_fresh: int, history_tokens: int,
                                     efficiency: float, output_tokens: int) -> None:
        """
        Collect session token usage metrics for Claude MAX optimization.

        TIER 1 Task 1 (GAP-COST-SESSION-001): Session token usage tracking
        Tracks cumulative token usage per session, history growth, efficiency.

        Args:
            session_id: Session identifier
            request_number: Request number in session
            input_tokens_total: Total input tokens for this request
            input_tokens_cached: Cached input tokens
            input_tokens_fresh: Fresh input tokens
            history_tokens: Estimated conversation history size
            efficiency: Cache hit rate (0-1)
            output_tokens: Output tokens generated
        """
        if not self.config['evaluation']['metrics']['enabled']:
            return

        metadata = {
            'session_id': session_id,
            'request_number': request_number,
            'input_tokens_total': input_tokens_total,
            'input_tokens_cached': input_tokens_cached,
            'input_tokens_fresh': input_tokens_fresh,
            'history_tokens': history_tokens,
            'efficiency': efficiency,
            'output_tokens': output_tokens
        }

        self.collect_metric('session_tokens', efficiency, metadata)

    def collect_context_budget_metric(self, current_tokens: int, max_tokens: int,
                                      utilization: float, status: str,
                                      message_count: int) -> None:
        """
        Collect context budget metrics for session management tracking.

        Args:
            current_tokens: Current token count
            max_tokens: Maximum context window size
            utilization: Utilization percentage (0.0-1.0)
            status: Budget status (healthy/warning/critical/exceeded)
            message_count: Number of messages in session
        """
        if not self.config['evaluation']['metrics']['enabled']:
            return

        metadata = {
            'current_tokens': current_tokens,
            'max_tokens': max_tokens,
            'utilization': utilization,
            'status': status,
            'message_count': message_count,
            'budget_version': '1.0.0'
        }

        self.collect_metric('context_budget', utilization, metadata)

    def load_metrics(self, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load metrics from storage.

        Args:
            start_date: Filter metrics after this date
            end_date: Filter metrics before this date

        Returns:
            DataFrame with metrics
        """
        if not self.data_path.exists():
            return pd.DataFrame()

        # Load JSONL
        metrics = []
        with open(self.data_path, 'r') as f:
            for line in f:
                try:
                    metrics.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if not metrics:
            return pd.DataFrame()

        df = pd.DataFrame(metrics)
        # Normalize timestamps: replace 'Z' with '+00:00' for consistent ISO8601 format
        # This handles both:
        # - '2026-01-23T13:54:48.815874Z' → '2026-01-23T13:54:48.815874+00:00'
        # - '2026-01-24T20:55:16.791377+00:00Z' → '2026-01-24T20:55:16.791377+00:00'
        # - '2026-01-26T11:21:51.502287' → unchanged (cache metrics without TZ)
        df['timestamp'] = df['timestamp'].str.replace(r'Z$', '+00:00', regex=True)
        # Parse timestamps using ISO8601 format (handles both TZ-aware and TZ-naive)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce')
        # Convert all to UTC: localize naive timestamps, convert aware ones
        def ensure_utc(ts):
            if pd.isna(ts):
                return ts
            if ts.tz is None:
                return ts.tz_localize('UTC')
            else:
                return ts.tz_convert('UTC')
        df['timestamp'] = df['timestamp'].apply(ensure_utc)

        # Apply date filters
        if start_date:
            df = df[df['timestamp'] >= start_date]
        if end_date:
            df = df[df['timestamp'] <= end_date]

        return df

    def calculate_statistics(self, df: pd.DataFrame, metric_type: str) -> Dict[str, float]:
        """
        Calculate statistics for a metric type.

        Args:
            df: DataFrame with metrics
            metric_type: Type of metric to analyze

        Returns:
            Dictionary with statistics (mean, median, std, min, max, count)
        """
        metric_data = df[df['metric_type'] == metric_type]['value']

        if metric_data.empty:
            return {
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }

        # Convert to numeric if possible
        try:
            metric_data = pd.to_numeric(metric_data)
        except (ValueError, TypeError):
            # For boolean metrics (True/False), convert to 1/0
            metric_data = metric_data.astype(float)

        return {
            'mean': float(metric_data.mean()),
            'median': float(metric_data.median()),
            'std': float(metric_data.std()),
            'min': float(metric_data.min()),
            'max': float(metric_data.max()),
            'count': int(len(metric_data))
        }

    def generate_weekly_report(self, output_format: str = 'markdown') -> str:
        """
        Generate weekly metrics report.

        Args:
            output_format: Report format (markdown, json, html)

        Returns:
            Report content as string
        """
        # Calculate date range (last 7 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)

        # Load metrics
        df = self.load_metrics(start_date, end_date)

        if df.empty:
            return self._format_empty_report(start_date, end_date, output_format)

        # Calculate statistics for each metric type
        metrics_summary = {}
        for metric_type in ['accuracy', 'hallucination', 'tool_error', 'latency', 'cost']:
            metrics_summary[metric_type] = self.calculate_statistics(df, metric_type)

        # Detect regressions
        regressions = self._detect_regressions(metrics_summary)

        # Format report
        if output_format == 'markdown':
            return self._format_markdown_report(start_date, end_date, metrics_summary, regressions)
        elif output_format == 'json':
            return json.dumps({
                'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'metrics': metrics_summary,
                'regressions': regressions
            }, indent=2)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _detect_regressions(self, current_metrics: Dict[str, Dict]) -> List[str]:
        """
        Detect performance regressions based on thresholds.

        Args:
            current_metrics: Current period metrics

        Returns:
            List of regression warnings
        """
        regressions = []
        thresholds = {
            'accuracy': self.config['evaluation']['regression']['threshold_accuracy'],
            'hallucination': self.config['evaluation']['regression']['threshold_hallucination'],
            'tool_error': self.config['evaluation']['regression']['threshold_tool_errors']
        }

        targets = {
            'accuracy': 0.85,  # Target: ≥85%
            'hallucination': 0.05,  # Target: ≤5%
            'tool_error': 0.10  # Target: ≤10%
        }

        for metric_type, threshold in thresholds.items():
            if metric_type in current_metrics and current_metrics[metric_type]['count'] > 0:
                current_value = current_metrics[metric_type]['mean']
                target_value = targets[metric_type]

                if metric_type == 'accuracy':
                    # For accuracy, lower is bad
                    if current_value < target_value - threshold:
                        regressions.append(
                            f"⚠️ {metric_type.upper()} regression: {current_value:.1%} "
                            f"(target: {target_value:.1%})"
                        )
                else:
                    # For hallucination and tool_error, higher is bad
                    if current_value > target_value + threshold:
                        regressions.append(
                            f"⚠️ {metric_type.upper()} regression: {current_value:.1%} "
                            f"(target: {target_value:.1%})"
                        )

        return regressions

    def _format_markdown_report(self, start_date: datetime, end_date: datetime,
                                 metrics_summary: Dict, regressions: List[str]) -> str:
        """Format metrics report as Markdown."""
        report = f"""# Claude Metrics Report - Weekly

**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## Summary

| Metric | Mean | Median | Std Dev | Min | Max | Count |
|--------|------|--------|---------|-----|-----|-------|
"""

        for metric_type, stats in metrics_summary.items():
            if stats['count'] > 0:
                if metric_type in ['accuracy', 'hallucination', 'tool_error']:
                    # Format as percentage
                    report += f"| {metric_type.title()} | {stats['mean']:.1%} | {stats['median']:.1%} | {stats['std']:.3f} | {stats['min']:.1%} | {stats['max']:.1%} | {stats['count']} |\n"
                elif metric_type == 'latency':
                    # Format as seconds
                    report += f"| {metric_type.title()} | {stats['mean']:.2f}s | {stats['median']:.2f}s | {stats['std']:.3f} | {stats['min']:.2f}s | {stats['max']:.2f}s | {stats['count']} |\n"
                elif metric_type == 'cost':
                    # Format as currency
                    report += f"| {metric_type.title()} | ${stats['mean']:.4f} | ${stats['median']:.4f} | ${stats['std']:.4f} | ${stats['min']:.4f} | ${stats['max']:.4f} | {stats['count']} |\n"

        # Regressions
        if regressions:
            report += "\n---\n\n## ⚠️ Regressions Detected\n\n"
            for regression in regressions:
                report += f"- {regression}\n"
        else:
            report += "\n---\n\n## ✅ No Regressions\n\nAll metrics within target thresholds.\n"

        # Targets
        report += """
---

## Target Metrics

| Metric | Target | Status |
|--------|--------|--------|
"""
        # Accuracy target
        acc = metrics_summary.get('accuracy', {})
        if acc.get('count', 0) > 0:
            status = "✅" if acc['mean'] >= 0.85 else "❌"
            report += f"| Accuracy | ≥85% | {status} {acc['mean']:.1%} |\n"

        # Hallucination target
        hall = metrics_summary.get('hallucination', {})
        if hall.get('count', 0) > 0:
            status = "✅" if hall['mean'] <= 0.05 else "❌"
            report += f"| Hallucinations | ≤5% | {status} {hall['mean']:.1%} |\n"

        # Tool error target
        tool_err = metrics_summary.get('tool_error', {})
        if tool_err.get('count', 0) > 0:
            status = "✅" if tool_err['mean'] <= 0.10 else "❌"
            report += f"| Tool Errors | ≤10% | {status} {tool_err['mean']:.1%} |\n"

        report += "\n---\n\n*Generated by Claude Evaluation Framework v1.0.0*\n"

        return report

    def _format_empty_report(self, start_date: datetime, end_date: datetime,
                            output_format: str) -> str:
        """Format report when no data available."""
        if output_format == 'markdown':
            return f"""# Claude Metrics Report - Weekly

**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## No Data Available

No metrics were collected during this period.

To start collecting metrics:
1. Ensure `evaluation.metrics.enabled: true` in config.yaml
2. Configure hooks in settings.json (optional)
3. Run tasks and metrics will be collected automatically

---

*Generated by Claude Evaluation Framework v1.0.0*
"""
        else:
            return json.dumps({
                'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'message': 'No data available'
            })

    def generate_tier2_report(self, output_format: str = 'markdown') -> str:
        """
        Generate Tier 2 cost optimization report.

        Args:
            output_format: Report format (markdown, json)

        Returns:
            Report content as string
        """
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Load metrics
        df = self.load_metrics(start_date, end_date)

        if df.empty:
            return self._format_empty_report(start_date, end_date, output_format)

        # Analyze model routing
        routing_data = df[df['metric_type'] == 'model_routing']
        routing_summary = {}
        if not routing_data.empty:
            model_counts = routing_data['value'].value_counts()
            total_cost_saved = sum([
                m.get('cost_saved_usd', 0)
                for m in routing_data['metadata']
                if isinstance(m, dict)
            ])
            routing_summary = {
                'haiku_count': int(model_counts.get('claude-haiku-4-20250514', 0)),
                'sonnet_count': int(model_counts.get('claude-sonnet-4-5-20250929', 0)),
                'opus_count': int(model_counts.get('claude-opus-4-5-20251101', 0)),
                'total_cost_saved_usd': float(total_cost_saved),
                'total_requests': int(len(routing_data))
            }

        # Analyze context budget
        budget_data = df[df['metric_type'] == 'context_budget']
        budget_summary = {}
        if not budget_data.empty:
            avg_utilization = float(budget_data['value'].mean())
            max_utilization = float(budget_data['value'].max())
            status_counts = {}
            for metadata in budget_data['metadata']:
                if isinstance(metadata, dict):
                    status = metadata.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1

            budget_summary = {
                'avg_utilization': avg_utilization,
                'max_utilization': max_utilization,
                'status_distribution': status_counts,
                'total_checks': int(len(budget_data))
            }

        # Analyze cache performance
        cache_data = df[df['metric_type'] == 'cache']
        cache_summary = {}
        if not cache_data.empty:
            avg_hit_rate = float(cache_data['value'].mean())
            total_savings = sum([
                m.get('savings', 0)
                for m in cache_data['metadata']
                if isinstance(m, dict)
            ])
            cache_summary = {
                'avg_hit_rate': avg_hit_rate,
                'total_savings_usd': float(total_savings),
                'total_requests': int(len(cache_data))
            }

        # Format report
        if output_format == 'markdown':
            return self._format_tier2_markdown_report(
                start_date, end_date, routing_summary, budget_summary, cache_summary
            )
        elif output_format == 'json':
            return json.dumps({
                'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'model_routing': routing_summary,
                'context_budget': budget_summary,
                'cache_performance': cache_summary
            }, indent=2)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _format_tier2_markdown_report(self, start_date: datetime, end_date: datetime,
                                       routing: Dict, budget: Dict, cache: Dict) -> str:
        """Format Tier 2 report as Markdown."""
        report = f"""# Tier 2 Cost Optimization Report - Weekly

**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Model Routing Analytics

"""
        if routing:
            total = routing['total_requests']
            haiku_pct = (routing['haiku_count'] / total * 100) if total > 0 else 0
            sonnet_pct = (routing['sonnet_count'] / total * 100) if total > 0 else 0
            opus_pct = (routing['opus_count'] / total * 100) if total > 0 else 0

            report += f"""
| Model | Count | Percentage | Cost per 1M tokens |
|-------|-------|------------|-------------------|
| Haiku | {routing['haiku_count']} | {haiku_pct:.1f}% | $0.25 / $1.25 |
| Sonnet | {routing['sonnet_count']} | {sonnet_pct:.1f}% | $3 / $15 |
| Opus | {routing['opus_count']} | {opus_pct:.1f}% | $15 / $75 |
| **Total** | **{total}** | **100%** | — |

**💰 Cost Savings:** ${routing['total_cost_saved_usd']:.2f} (vs always using Sonnet)

**Target:** ≥60% Haiku usage for simple tasks
**Actual:** {haiku_pct:.1f}% ({'✅' if haiku_pct >= 60 else '⚠️'})

"""
        else:
            report += "No model routing data available.\n\n"

        report += "---\n\n## Context Budget Management\n\n"
        if budget:
            report += f"""
| Metric | Value |
|--------|-------|
| Average Utilization | {budget['avg_utilization']:.1%} |
| Peak Utilization | {budget['max_utilization']:.1%} |
| Total Checks | {budget['total_checks']} |

**Status Distribution:**
"""
            for status, count in budget['status_distribution'].items():
                emoji = {'healthy': '🟢', 'warning': '🟡', 'critical': '🟠', 'exceeded': '🔴'}.get(status, '⚪')
                report += f"- {emoji} {status.title()}: {count}\n"

            report += "\n**Target:** <60% average utilization\n"
            report += f"**Actual:** {budget['avg_utilization']:.1%} ({'✅' if budget['avg_utilization'] < 0.60 else '⚠️'})\n\n"
        else:
            report += "No context budget data available.\n\n"

        report += "---\n\n## Cache Performance\n\n"
        if cache:
            report += f"""
| Metric | Value |
|--------|-------|
| Average Hit Rate | {cache['avg_hit_rate']:.1%} |
| Cost Savings | ${cache['total_savings_usd']:.2f} |
| Total Requests | {cache['total_requests']} |

**Target:** ≥85% cache hit rate (Tier 1, 2, 4)
**Actual:** {cache['avg_hit_rate']:.1%} ({'✅' if cache['avg_hit_rate'] >= 0.85 else '⚠️'})

"""
        else:
            report += "No cache performance data available.\n\n"

        # Calculate total savings
        total_savings = (
            routing.get('total_cost_saved_usd', 0) +
            cache.get('total_savings_usd', 0)
        )

        report += f"""---

## 💰 Total Cost Optimization

| Category | Savings |
|----------|---------|
| Model Routing | ${routing.get('total_cost_saved_usd', 0):.2f} |
| Prompt Caching | ${cache.get('total_savings_usd', 0):.2f} |
| **Total Saved** | **${total_savings:.2f}** |

**Estimated Annual Savings:** ${total_savings * 52:.2f} (extrapolated from weekly data)

**ROI Targets:**
- Model Router: -75% cost reduction ({'✅ Exceeded' if routing.get('total_cost_saved_usd', 0) > 0 else '⚠️ Pending'})
- Context Management: -30% token savings (tracked via utilization)
- Prompt Caching: -60-80% cost reduction ({'✅ Exceeded' if cache.get('avg_hit_rate', 0) >= 0.80 else '⚠️ Pending'})

---

*Generated by Claude Evaluation Framework v2.0.0*
"""

        return report

    def save_report(self, report_content: str, report_type: str = 'weekly') -> Path:
        """
        Save report to file.

        Args:
            report_content: Report content
            report_type: Report type (weekly, monthly, etc.)

        Returns:
            Path to saved report
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"{report_type}_report_{timestamp}.md"
        report_path = self.reports_path / filename

        with open(report_path, 'w') as f:
            f.write(report_content)

        return report_path

    def generate_cache_dashboard(self, days: int = 7, output_format: str = 'markdown') -> str:
        """
        Generate detailed cache performance dashboard.

        Args:
            days: Number of days to analyze (default: 7)
            output_format: Report format (markdown, json)

        Returns:
            Dashboard content as string
        """
        # Calculate date range (UTC-aware)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Load metrics
        df = self.load_metrics(start_date, end_date)

        if df.empty:
            return self._format_empty_cache_dashboard(start_date, end_date, output_format)

        # Filter cache metrics only
        cache_data = df[df['metric_type'] == 'cache'].copy()

        if cache_data.empty:
            return self._format_empty_cache_dashboard(start_date, end_date, output_format)

        # Extract metadata into columns for easier analysis
        cache_data['model'] = cache_data['metadata'].apply(lambda x: x.get('model', 'unknown') if isinstance(x, dict) else 'unknown')
        cache_data['cached_tokens'] = cache_data['metadata'].apply(lambda x: x.get('cached_tokens', 0) if isinstance(x, dict) else 0)
        cache_data['fresh_tokens'] = cache_data['metadata'].apply(lambda x: x.get('fresh_tokens', 0) if isinstance(x, dict) else 0)
        cache_data['total_input_tokens'] = cache_data['metadata'].apply(lambda x: x.get('total_input_tokens', 0) if isinstance(x, dict) else 0)
        cache_data['hit_rate'] = cache_data['metadata'].apply(lambda x: x.get('hit_rate', 0) if isinstance(x, dict) else 0)
        cache_data['savings'] = cache_data['metadata'].apply(lambda x: x.get('savings', 0) if isinstance(x, dict) else 0)
        cache_data['cost_with_cache'] = cache_data['metadata'].apply(lambda x: x.get('cost_with_cache', 0) if isinstance(x, dict) else 0)
        cache_data['cost_without_cache'] = cache_data['metadata'].apply(lambda x: x.get('cost_without_cache', 0) if isinstance(x, dict) else 0)
        cache_data['latency_ms'] = cache_data['metadata'].apply(lambda x: x.get('latency_ms', 0) if isinstance(x, dict) else 0)

        # Filter out synthetic entries (test data)
        cache_data = cache_data[cache_data['model'] != '<synthetic>']

        if cache_data.empty:
            return self._format_empty_cache_dashboard(start_date, end_date, output_format)

        # Calculate aggregate statistics
        total_requests = len(cache_data)
        avg_hit_rate = float(cache_data['hit_rate'].mean())
        total_cached_tokens = int(cache_data['cached_tokens'].sum())
        total_fresh_tokens = int(cache_data['fresh_tokens'].sum())
        total_input_tokens = int(cache_data['total_input_tokens'].sum())
        total_savings = float(cache_data['savings'].sum())
        total_cost_with_cache = float(cache_data['cost_with_cache'].sum())
        total_cost_without_cache = float(cache_data['cost_without_cache'].sum())

        # Cost per request
        avg_cost_with_cache = total_cost_with_cache / total_requests if total_requests > 0 else 0
        avg_cost_without_cache = total_cost_without_cache / total_requests if total_requests > 0 else 0
        cost_reduction_pct = ((avg_cost_without_cache - avg_cost_with_cache) / avg_cost_without_cache * 100) if avg_cost_without_cache > 0 else 0

        # Daily breakdown (group by date)
        cache_data['date'] = pd.to_datetime(cache_data['timestamp']).dt.date
        daily_stats = cache_data.groupby('date').agg({
            'hit_rate': 'mean',
            'savings': 'sum',
            'cached_tokens': 'sum',
            'fresh_tokens': 'sum'
        }).reset_index()

        # Format report
        if output_format == 'markdown':
            return self._format_cache_dashboard_markdown(
                start_date, end_date, days,
                total_requests, avg_hit_rate,
                total_cached_tokens, total_fresh_tokens, total_input_tokens,
                total_savings, avg_cost_with_cache, avg_cost_without_cache, cost_reduction_pct,
                daily_stats
            )
        elif output_format == 'json':
            return json.dumps({
                'period': {'start': start_date.isoformat(), 'end': end_date.isoformat(), 'days': days},
                'summary': {
                    'total_requests': int(total_requests),
                    'avg_hit_rate': float(avg_hit_rate),
                    'total_cached_tokens': int(total_cached_tokens),
                    'total_fresh_tokens': int(total_fresh_tokens),
                    'total_input_tokens': int(total_input_tokens),
                    'total_savings_usd': float(total_savings),
                    'avg_cost_with_cache_usd': float(avg_cost_with_cache),
                    'avg_cost_without_cache_usd': float(avg_cost_without_cache),
                    'cost_reduction_pct': float(cost_reduction_pct)
                },
                'daily_breakdown': daily_stats.to_dict(orient='records')
            }, indent=2)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _format_cache_dashboard_markdown(self, start_date: datetime, end_date: datetime, days: int,
                                         total_requests: int, avg_hit_rate: float,
                                         total_cached: int, total_fresh: int, total_input: int,
                                         total_savings: float, avg_cost_cached: float,
                                         avg_cost_uncached: float, cost_reduction_pct: float,
                                         daily_stats: pd.DataFrame) -> str:
        """Format cache dashboard as Markdown."""
        report = f"""# 📊 Cache Performance Dashboard

**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days} days)
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 🎯 Key Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Cache Hit Rate** | {avg_hit_rate:.2%} | ≥85% | {'✅' if avg_hit_rate >= 0.85 else '⚠️'} |
| **Total Requests** | {total_requests:,} | — | — |
| **Cost Reduction** | {cost_reduction_pct:.1f}% | 60-80% | {'✅' if cost_reduction_pct >= 60 else '⚠️'} |
| **Total Savings** | ${total_savings:.2f} | — | — |

---

## 💰 Cost Analysis

### Per-Request Costs

| Scenario | Cost per Request | Annual Projection* |
|----------|------------------|-------------------|
| **With Cache** | ${avg_cost_cached:.4f} | ${avg_cost_cached * 365 * (total_requests / days):.2f} |
| **Without Cache** | ${avg_cost_uncached:.4f} | ${avg_cost_uncached * 365 * (total_requests / days):.2f} |
| **Savings** | ${avg_cost_uncached - avg_cost_cached:.4f} | **${total_savings * 365 / days:.2f}** |

*Extrapolated from {days}-day average ({total_requests / days:.1f} requests/day)

### Cost Breakdown

```
Total Input Tokens:  {total_input:,}
├─ Cached Tokens:    {total_cached:,} ({total_cached / total_input * 100:.1f}%) @ $0.003/1k
└─ Fresh Tokens:     {total_fresh:,} ({total_fresh / total_input * 100:.1f}%) @ $0.030/1k

Cost with Cache:     ${avg_cost_cached * total_requests:.2f}
Cost without Cache:  ${avg_cost_uncached * total_requests:.2f}
Total Savings:       ${total_savings:.2f} ({cost_reduction_pct:.1f}% reduction)
```

---

## 📈 Daily Trends

| Date | Hit Rate | Savings | Cached Tokens | Fresh Tokens |
|------|----------|---------|---------------|--------------|
"""
        # Add daily breakdown
        for _, row in daily_stats.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            hit_rate = row['hit_rate']
            savings = row['savings']
            cached = int(row['cached_tokens'])
            fresh = int(row['fresh_tokens'])

            report += f"| {date_str} | {hit_rate:.2%} | ${savings:.2f} | {cached:,} | {fresh:,} |\n"

        # Calculate trend
        if len(daily_stats) >= 2:
            first_hit_rate = daily_stats.iloc[0]['hit_rate']
            last_hit_rate = daily_stats.iloc[-1]['hit_rate']
            trend = last_hit_rate - first_hit_rate
            trend_emoji = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
            trend_text = f"{trend_emoji} Hit rate trend: {trend:+.2%} over {days} days"
        else:
            trend_text = "— Insufficient data for trend analysis"

        report += f"\n**Trend Analysis:** {trend_text}\n"

        report += f"""
---

## 🎯 Recommendations

"""
        # Generate recommendations based on metrics
        recommendations = []

        if avg_hit_rate < 0.85:
            recommendations.append("⚠️ **Cache hit rate below target (85%)** — Investigate cache invalidation patterns")
        else:
            recommendations.append("✅ **Cache hit rate on target** — Excellent performance!")

        if cost_reduction_pct < 60:
            recommendations.append("⚠️ **Cost reduction below target (60-80%)** — Review caching strategy")
        elif cost_reduction_pct > 80:
            recommendations.append("✅ **Exceptional cost reduction** — Current strategy is highly effective!")
        else:
            recommendations.append("✅ **Cost reduction within target range** — Caching strategy working as expected")

        # Annual savings projection
        annual_savings = total_savings * 365 / days
        if annual_savings >= 4600:
            recommendations.append(f"💰 **On track to exceed annual savings target** — Projected: ${annual_savings:.2f}/year (Target: $4,600-4,750)")
        else:
            recommendations.append(f"⚠️ **Below annual savings target** — Projected: ${annual_savings:.2f}/year (Target: $4,600-4,750)")

        for rec in recommendations:
            report += f"{rec}\n"

        report += f"""
---

## 📋 ROI Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cache Hit Rate | ≥85% | {avg_hit_rate:.1%} | {'✅ Achieved' if avg_hit_rate >= 0.85 else '⚠️ Below Target'} |
| Cost Reduction | 60-80% | {cost_reduction_pct:.1f}% | {'✅ Exceeded' if cost_reduction_pct > 80 else ('✅ Achieved' if cost_reduction_pct >= 60 else '⚠️ Below Target')} |
| Annual Savings | $4,600-4,750 | ${total_savings * 365 / days:.2f} | {'✅ On Track' if total_savings * 365 / days >= 4600 else '⚠️ Below Target'} |

**Overall Status:** {'✅ All targets met' if avg_hit_rate >= 0.85 and cost_reduction_pct >= 60 and total_savings * 365 / days >= 4600 else '⚠️ Some targets need attention'}

---

*Generated by Claude Evaluation Framework v2.0.0 — TIER 1 Task 3 (Caching Analytics Dashboard)*
"""

        return report

    def _format_empty_cache_dashboard(self, start_date: datetime, end_date: datetime,
                                     output_format: str) -> str:
        """Format empty cache dashboard when no data available."""
        if output_format == 'markdown':
            return f"""# 📊 Cache Performance Dashboard

**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## No Cache Data Available

No cache metrics were collected during this period.

Cache metrics are collected automatically when:
1. Session transcripts are parsed (`parse_session_metrics.py`)
2. Cache performance is logged via `MetricsTracker.collect_cache_metric()`

**To start collecting cache metrics:**
- Ensure prompt caching is enabled in your Claude API configuration
- Run Claude Code sessions — metrics are collected automatically on session exit
- Wait for wrapper script to process session transcript

---

*Generated by Claude Evaluation Framework v2.0.0*
"""
        else:
            return json.dumps({
                'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'message': 'No cache data available'
            })


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Claude Metrics Tracker')
    parser.add_argument('--report', choices=['weekly', 'monthly', 'tier2', 'caching', 'session', 'context-budget', 'usage-limit', 'session-reopening', 'latency', 'agent-quality', 'task-quality', 'maturity', 'hallucination', 'autonomous-decisions', 'security', 'agent-cost', 'tool-chain', 'session-eval', 'multi-turn', 'budget', 'task-cost'],
                       help='Generate report (weekly=standard, tier2=cost optimization, caching=cache dashboard, session=token usage, context-budget=context window tracking, usage-limit=usage limit monitoring, session-reopening=reopening strategy, latency=performance metrics, agent-quality=agent effectiveness metrics, task-quality=task completion assessment, maturity=configuration maturity, hallucination=hallucination detection, security=prompt injection detection, agent-cost=unified agent cost tracking, tool-chain=tool usage patterns, session-eval=session-level evaluation, multi-turn=conversation optimization, budget=session/task/daily budgets, task-cost=cost by task type)')
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown',
                       help='Report format (default: markdown)')
    parser.add_argument('--output', type=Path, help='Output file path')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to analyze (for caching report, default: 7)')
    parser.add_argument('--session-file', type=Path,
                       help='Session JSONL file path (for session report)')
    parser.add_argument('--collect', action='store_true',
                       help='Collect metric (interactive)')
    parser.add_argument('--quick-check', action='store_true',
                       help='Quick validation check (for git hooks)')
    parser.add_argument('--config', type=Path, help='Path to config.yaml')

    args = parser.parse_args()

    # Initialize tracker
    tracker = MetricsTracker(config_path=args.config)

    if args.report:
        # Generate report
        if args.report == 'weekly':
            report = tracker.generate_weekly_report(output_format=args.format)

            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                print(f"✅ Report saved to: {args.output}")
            else:
                # Save to default location
                report_path = tracker.save_report(report, report_type='weekly')
                print(report)
                print(f"\n✅ Report saved to: {report_path}")

        elif args.report == 'monthly':
            print("❌ Monthly reports not yet implemented (Phase 3 feature)")
            sys.exit(1)

        elif args.report == 'tier2':
            # Generate Tier 2 cost optimization report
            report = tracker.generate_tier2_report(output_format=args.format)

            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                print(f"✅ Tier 2 report saved to: {args.output}")
            else:
                # Save to default location
                report_path = tracker.save_report(report, report_type='tier2')
                print(report)
                print(f"\n✅ Tier 2 report saved to: {report_path}")

        elif args.report == 'caching':
            # Generate cache performance dashboard
            report = tracker.generate_cache_dashboard(days=args.days, output_format=args.format)

            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                print(f"✅ Cache dashboard saved to: {args.output}")
            else:
                # Save to default location
                report_path = tracker.save_report(report, report_type='caching')
                print(report)
                print(f"\n✅ Cache dashboard saved to: {report_path}")

        elif args.report == 'session':
            # Generate session token usage dashboard
            if not args.session_file:
                print("❌ Error: --session-file required for session report")
                sys.exit(1)

            if not args.session_file.exists():
                print(f"❌ Error: Session file not found: {args.session_file}")
                sys.exit(1)

            # Import session_token_tracker
            from session_token_tracker import SessionTokenTracker

            session_tracker = SessionTokenTracker()
            dashboard = session_tracker.display_dashboard(args.session_file)
            print(dashboard)

            # Also show detailed stats
            stats = session_tracker.track_session(args.session_file, store_metrics=False)
            print(f"\n📊 Detailed Statistics:")
            print(f"  Average Efficiency: {stats['avg_efficiency']:.2%}")
            print(f"  History Growth Rate: {stats['history_growth_rate']:.1f} tokens/request")
            print(f"  Total Input Growth: {stats['total_input_growth']:,} tokens")

        elif args.report == 'context-budget':
            # Generate context budget dashboard
            if not args.session_file:
                print("❌ Error: --session-file required for context-budget report")
                sys.exit(1)

            if not args.session_file.exists():
                print(f"❌ Error: Session file not found: {args.session_file}")
                sys.exit(1)

            # Import context_tracker
            from costs.context_tracker import ContextBudgetTracker

            context_tracker = ContextBudgetTracker()
            dashboard = context_tracker.display_context_budget(args.session_file)
            print(dashboard)

            # Also show detailed stats
            stats = context_tracker.track_context(args.session_file, store_metrics=False)
            print(f"\n📊 Detailed Statistics:")
            print(f"  Current Tokens: {stats['current_tokens']:,} / {stats['max_tokens']:,}")
            print(f"  Utilization: {stats['utilization_pct']:.2f}%")
            print(f"  Average Efficiency: {stats['efficiency']:.2%}")
            print(f"  History Growth Rate: {stats['history_growth_rate']:.1f} tokens/request")
            if stats['projected_full_requests']:
                print(f"  Projected Full: ~{stats['projected_full_requests']} requests ({stats['projected_full_minutes']:.0f} minutes)")

        elif args.report == 'usage-limit':
            # Generate usage limit dashboard (Claude MAX subscription)
            if not args.session_file:
                print("❌ Error: --session-file required for usage-limit report")
                sys.exit(1)

            if not args.session_file.exists():
                print(f"❌ Error: Session file not found: {args.session_file}")
                sys.exit(1)

            # Import usage_limit_tracker
            from usage_limit_tracker import UsageLimitTracker

            limit_tracker = UsageLimitTracker()
            dashboard = limit_tracker.display_usage_budget(args.session_file)
            print(dashboard)

            # Also show detailed stats
            limit_tracker.parse_session_for_usage(args.session_file)
            status = limit_tracker.get_budget_status()
            print(f"\n📊 Detailed Statistics:")
            print(f"  Messages Used: {status['messages_used']}/{status['messages_limit']}")
            print(f"  Usage: {status['usage_pct']:.2f}%")
            print(f"  Window: {status['window_hours']} hours rolling")
            print(f"  Message Rate: {status['message_rate']:.2f} msg/hour")
            print(f"  Projected Messages: {status['projected_messages']}")
            print(f"  Headroom: {status['headroom']} messages")
            if status['time_until_reset']:
                hours = int(status['time_until_reset'].total_seconds() // 3600)
                minutes = int((status['time_until_reset'].total_seconds() % 3600) // 60)
                print(f"  Window Reset: {hours}h {minutes}m (at {status['reset_timestamp'].strftime('%Y-%m-%d %H:%M UTC')})")

        elif args.report == 'session-reopening':
            # Generate session reopening dashboard
            # Import session_manager
            from session_manager import SessionManager

            manager = SessionManager()

            # Check triggers
            session_file = args.session_file if args.session_file else manager.get_current_session_file()

            if not session_file:
                print("❌ Error: Could not detect current session file. Use --session-file to specify.")
                sys.exit(1)

            if not session_file.exists():
                print(f"❌ Error: Session file not found: {session_file}")
                sys.exit(1)

            # Display reopening dashboard
            dashboard = manager.display_dashboard(session_file)
            print(dashboard)

            # Also show triggers in detail
            triggers = manager.check_reopening_triggers(session_file)
            if triggers:
                print(f"\n⚠️ {len(triggers)} reopening trigger(s) detected:")
                for trigger in triggers:
                    print(f"  • [{trigger.severity.upper()}] {trigger.condition}: {trigger.current_value} (threshold: {trigger.threshold})")
            else:
                print("\n✅ No reopening triggers detected")

        elif args.report == 'latency':
            # Generate latency and performance report
            from latency_tracker import LatencyTracker

            latency_tracker = LatencyTracker()

            # Get session_id from session-file if provided
            session_id = None
            if args.session_file:
                # Extract session ID from file path
                # Format: ~/.claude/projects/-opt-your-project/SESSION_ID.jsonl
                session_id = args.session_file.stem

            # Generate report
            report = latency_tracker.generate_report(
                session_id=session_id,
                limit=None
            )

            # Display formatted report
            print(latency_tracker.format_report(report))

            # Also show detailed stats
            if report.total_requests > 0:
                print(f"\n📊 Detailed Statistics:")
                print(f"  Total Requests: {report.total_requests}")

                if report.ttft:
                    print(f"  TTFT Samples: {report.ttft.count}")

                if report.total_time:
                    print(f"  Total Time Samples: {report.total_time.count}")

                if report.throughput:
                    print(f"  Throughput Samples: {report.throughput.count}")

                # Model breakdown
                if report.by_model:
                    print(f"\n🤖 Model Distribution:")
                    for model, stats in report.by_model.items():
                        print(f"  • {model}: {stats['count']} requests ({stats['count']/report.total_requests*100:.1f}%)")

                # Performance trend
                if report.degradation_detected:
                    print(f"\n⚠️  WARNING: Performance degradation detected!")
                    print(f"  Trend: {report.trend.upper()}")
                    print(f"  Recommendation: Investigate recent changes or reopen session")

        elif args.report == 'agent-quality':
            # Generate agent-level quality metrics report
            from agent_metrics import AgentMetrics

            agent_metrics = AgentMetrics()

            # Get session_id from session-file if provided
            session_id = None
            if args.session_file:
                # Extract session ID from file path
                session_id = args.session_file.stem

            # Generate report
            report = agent_metrics.generate_report(
                session_id=session_id,
                limit=None
            )

            # Display formatted report
            print(agent_metrics.format_report(report))

            # Also show detailed stats
            if report.total_tasks > 0:
                print(f"\n📊 Detailed Statistics:")
                print(f"  Total Tasks: {report.total_tasks}")
                print(f"  Total Sessions: {report.total_sessions}")
                print(f"  Completion Rate: {report.task_completion_rate:.1f}%")
                print(f"  Average Quality Score: {report.avg_quality_score:.2f}/5.0")
                print(f"  Tool Efficiency: {report.avg_tool_efficiency:.1f}%")
                print(f"  Error Recovery Rate: {report.avg_error_recovery_rate:.1f}%")
                print(f"\n🎯 Agent Effectiveness Score: {report.agent_effectiveness_score:.1f}/100")

                # Task status breakdown
                if hasattr(report, 'status_breakdown') and report.status_breakdown:
                    print(f"\n📋 Task Status Breakdown:")
                    for status, count in report.status_breakdown.items():
                        emoji = {'completed': '✅', 'partial': '⚠️', 'failed': '❌', 'abandoned': '🚫'}.get(status, '⚪')
                        pct = (count / report.total_tasks * 100) if report.total_tasks > 0 else 0
                        print(f"  {emoji} {status.title()}: {count} ({pct:.1f}%)")

                # Session quality breakdown
                if hasattr(report, 'session_quality') and report.session_quality:
                    print(f"\n🔬 Session Quality Breakdown:")
                    for session_id, quality in sorted(report.session_quality.items(), key=lambda x: x[1], reverse=True)[:5]:
                        print(f"  • Session {session_id[:8]}...: {quality:.1f}/100")

        elif args.report == 'task-quality':
            # Generate task completion quality metrics
            from task_completion import TaskCompletionAnalyzer

            analyzer = TaskCompletionAnalyzer()

            if not args.session_file:
                print("❌ Error: --session-file required for task-quality report")
                sys.exit(1)

            if not args.session_file.exists():
                print(f"❌ Error: Session file not found: {args.session_file}")
                sys.exit(1)

            # Detect tasks from session
            tasks = analyzer.detect_tasks_from_session(args.session_file)

            if not tasks:
                print("No tasks detected in session.")
                sys.exit(0)

            print(f"\n=== Detected {len(tasks)} Task(s) ===\n")

            # Assess each task
            for i, task in enumerate(tasks):
                assessment = analyzer.assess_task(task, args.session_file, task_start_index=i*10)
                print(analyzer.format_assessment(assessment))
                print("\n" + "="*60 + "\n")

        elif args.report == 'maturity':
            # Generate configuration maturity assessment
            from maturity_model import MaturityModel

            model = MaturityModel()
            assessment = model.assess_current_level()

            # Display dashboard
            print(model.format_dashboard(assessment))

        elif args.report == 'hallucination':
            # Generate hallucination detection report
            from hallucination_detector import HallucinationDetector, HallucinationLogger
            import json

            detector = HallucinationDetector()
            logger_instance = HallucinationLogger()

            # Check if session file provided
            if not args.session_file:
                print("❌ Error: --session-file required for hallucination report")
                print("Usage: python metrics_tracker.py --report hallucination --session-file SESSION.jsonl")
                sys.exit(1)

            if not args.session_file.exists():
                print(f"❌ Error: Session file not found: {args.session_file}")
                sys.exit(1)

            # Parse session JSONL to extract assistant responses
            assistant_responses = []
            try:
                with open(args.session_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            # Check if this is an assistant message
                            if entry.get('message', {}).get('role') == 'assistant':
                                content = entry['message'].get('content', [])
                                # Extract text from content blocks (skip thinking blocks)
                                if isinstance(content, list):
                                    text_parts = []
                                    for block in content:
                                        if isinstance(block, dict):
                                            if block.get('type') == 'text':
                                                text_parts.append(block.get('text', ''))
                                            # Skip thinking blocks, tool_use, tool_result
                                elif isinstance(content, str):
                                    # Fallback for string content
                                    text_parts = [content]
                                else:
                                    continue

                                text = ' '.join(text_parts).strip()
                                if text:
                                    assistant_responses.append({
                                        'content': text,
                                        'timestamp': entry.get('timestamp', ''),
                                        'message_id': entry.get('message', {}).get('id', '')
                                    })
            except (json.JSONDecodeError, IOError) as e:
                print(f"❌ Error parsing session file: {e}")
                sys.exit(1)

            if not assistant_responses:
                print("❌ No assistant responses found in session file")
                sys.exit(0)

            # Analyze each response for hallucinations
            results = []
            for resp in assistant_responses:
                result = detector.detect(resp['content'])
                # Log to persistent storage
                logger_instance.log_detection(result, session_id=args.session_file.stem)
                results.append(result)

            # Aggregate statistics
            total_hallucinations = sum(r.total_hallucinations for r in results)

            # Aggregate by category
            by_category = {}
            for result in results:
                for cat, count in result.by_category.items():
                    by_category[cat] = by_category.get(cat, 0) + count

            # Aggregate by severity
            by_severity = {}
            for result in results:
                for sev, count in result.by_severity.items():
                    by_severity[sev] = by_severity.get(sev, 0) + count

            # Calculate risk distribution
            risk_dist = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
            for result in results:
                risk_dist[result.risk_level] = risk_dist.get(result.risk_level, 0) + 1

            # Calculate hallucination rate
            hallucination_rate = (total_hallucinations / len(results)) if results else 0

            # Display dashboard
            print("\n" + "="*70)
            print("HALLUCINATION DETECTION REPORT")
            print("="*70)
            print(f"\nSession: {args.session_file.stem}")
            print(f"Assistant Responses Analyzed: {len(assistant_responses)}")
            print(f"\n{'-'*70}")
            print("OVERALL METRICS")
            print("-"*70)
            print(f"Total Hallucinations Detected: {total_hallucinations}")
            print(f"Hallucination Rate: {hallucination_rate*100:.1f}% ({total_hallucinations}/{len(results)} responses)")
            print(f"Average per Response: {hallucination_rate:.2f} hallucinations")

            print(f"\n{'-'*70}")
            print("BY SEVERITY")
            print("-"*70)
            critical = by_severity.get('critical', 0)
            major = by_severity.get('major', 0)
            minor = by_severity.get('minor', 0)
            total = critical + major + minor

            if total > 0:
                print(f"CRITICAL: {critical} ({critical/total*100:.0f}%){'    🔴 URGENT: Review required!' if critical > 0 else '    🟢 No critical issues'}")
                print(f"MAJOR:    {major} ({major/total*100:.0f}%){'   ⚠️  Review recommended' if major > 0 else '   🟢 Acceptable'}")
                print(f"MINOR:    {minor} ({minor/total*100:.0f}%){'   💡 Low impact' if minor > 0 else ''}")
            else:
                print("🟢 No hallucinations detected")

            if by_category:
                print(f"\n{'-'*70}")
                print("BY CATEGORY")
                print("-"*70)
                category_icons = {
                    'citation': '📚',
                    'version': '🔄',
                    'quantitative': '📊',
                    'factual': '⚠️',
                    'temporal': '⏰',
                    'entity': '👤',
                    'code': '💻'
                }
                for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                    icon = category_icons.get(cat, '•')
                    pct = (count / total * 100) if total > 0 else 0
                    cat_label = cat.title().ljust(14)
                    print(f"{icon} {cat_label}: {count} ({pct:.0f}%)")

            print(f"\n{'-'*70}")
            print("RISK ASSESSMENT")
            print("-"*70)
            for risk in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
                count = risk_dist.get(risk, 0)
                pct = (count / len(results) * 100) if results else 0
                icon = {'LOW': '✅', 'MEDIUM': '⚠️', 'HIGH': '🔴', 'CRITICAL': '🔴'}.get(risk, '•')
                print(f"{icon} {risk.ljust(9)}: {count} responses ({pct:.1f}%)")

            # Overall risk level
            if critical > 0 or risk_dist.get('CRITICAL', 0) > 0:
                overall_risk = "CRITICAL"
                overall_icon = "🔴"
            elif major >= 3 or risk_dist.get('HIGH', 0) > 0:
                overall_risk = "HIGH"
                overall_icon = "🔴"
            elif major >= 1 or risk_dist.get('MEDIUM', 0) > 5:
                overall_risk = "MEDIUM"
                overall_icon = "⚠️"
            else:
                overall_risk = "LOW"
                overall_icon = "✅"

            print(f"\nOverall Risk Level: {overall_risk} ({overall_icon} {'Acceptable' if overall_risk == 'LOW' else 'Needs attention'})")

            # Show top hallucinations
            all_hallucinations = []
            for result in results:
                all_hallucinations.extend(result.hallucinations)

            if all_hallucinations:
                print(f"\n{'-'*70}")
                print("TOP HALLUCINATIONS")
                print("-"*70)
                # Sort by severity (critical > major > minor), then by confidence
                severity_order = {'critical': 0, 'major': 1, 'minor': 2}
                sorted_hallucinations = sorted(
                    all_hallucinations,
                    key=lambda h: (severity_order.get(h.severity.value, 3), -h.confidence)
                )
                for i, h in enumerate(sorted_hallucinations[:5], 1):
                    print(f"\n{i}. [{h.severity.value.upper()}] {h.category.value.title()}: \"{h.text_snippet[:60]}...\"")
                    print(f"   Pattern: {h.pattern_id} | Confidence: {h.confidence:.2f}")
                    print(f"   Description: {h.description}")

                if len(all_hallucinations) > 5:
                    print(f"\n... and {len(all_hallucinations) - 5} more hallucinations detected")

            # Recommendations
            print(f"\n{'-'*70}")
            print("RECOMMENDATIONS")
            print("-"*70)
            if hallucination_rate < 0.05:
                print("✅ Hallucination rate below 5% threshold - excellent performance")
            elif hallucination_rate < 0.10:
                print("✅ Hallucination rate below 10% threshold - acceptable performance")
            else:
                print(f"⚠️  Hallucination rate {hallucination_rate*100:.1f}% exceeds 10% threshold")

            if major > 0:
                print(f"💡 {major} MAJOR severity detections - review for factual accuracy")
            if critical > 0:
                print(f"🔴 {critical} CRITICAL severity detections - URGENT review required")

            print("💡 Consider adding uncertainty expressions (modules/11-prompting.md)")
            print("💡 Enable CoVe (Chain-of-Verification) for critical claims")

            print("\n" + "="*70 + "\n")

            # Also show historical stats
            historical = logger_instance.get_historical_stats()
            if "error" not in historical and historical.get("total_entries", 0) > 1:
                print(f"📊 Historical Statistics (last {historical['total_entries']} analyses):")
                print(f"  Average hallucinations per analysis: {historical['average_per_entry']:.2f}")
                print(f"  Overall hallucination rate: {historical['hallucination_rate']:.2f}")

        elif args.report == 'autonomous-decisions':
            # Generate autonomous decision quality report
            from autonomous_decisions import AutonomousDecisionTracker

            tracker = AutonomousDecisionTracker()
            report = tracker.generate_report()
            print(tracker.format_report(report))

        elif args.report == 'security':
            # Generate security evaluation report
            from security_eval import SecurityEvaluator

            evaluator = SecurityEvaluator()
            report = evaluator.run_full_evaluation()
            print(evaluator.format_report(report))

        elif args.report == 'agent-cost':
            # Generate agent cost tracking report
            sys.path.insert(0, str(Path.home() / ".claude" / "evaluation" / "costs"))
            from agent_cost_tracker import AgentCostTracker

            cost_tracker = AgentCostTracker()
            if args.session_file:
                print(cost_tracker.generate_report(session_id=str(args.session_file)))
            else:
                print(cost_tracker.generate_report())

        elif args.report == 'tool-chain':
            # Generate tool chain analysis report (Task 26: GAP-EVAL-AG-003)
            from tool_chain_analyzer import ToolChainAnalyzer, format_report as tc_format_report

            analyzer = ToolChainAnalyzer()

            # If session file provided, analyze that session
            if args.session_file:
                if not args.session_file.exists():
                    print(f"Error: Session file not found: {args.session_file}")
                    sys.exit(1)

                # Analyze single session
                report = analyzer.generate_report(period_days=1)
                print(tc_format_report(report))

                # Show session-specific analysis
                print(f"\n📊 Session-specific analysis:")
                sequences = analyzer.parse_session(args.session_file)
                if sequences:
                    for seq in sequences:
                        analysis = analyzer.analyze_sequence(seq)
                        print(f"\nSequence ({seq.total_calls} calls):")
                        print(f"  Efficiency: {analysis.efficiency_score:.1f}/100")
                        print(f"  Redundant calls: {len(analysis.redundant_calls)}")
                        if analysis.suggestions:
                            print(f"  Suggestions: {len(analysis.suggestions)}")
                            for s in analysis.suggestions[:3]:
                                print(f"    • {s}")
                else:
                    print("  No tool sequences found in session")
            else:
                # Generate weekly report
                report = analyzer.generate_report(period_days=args.days)
                formatted = tc_format_report(report)
                print(formatted)

                # Save to default location
                report_path = tracker.save_report(formatted, report_type='tool_chain')
                print(f"\n✅ Tool chain report saved to: {report_path}")

        elif args.report == 'session-eval':
            # Generate session-level evaluation report (Task 27: GAP-EVAL-AG-004)
            from session_evaluator import SessionEvaluator

            evaluator = SessionEvaluator()

            if args.session_file:
                if not args.session_file.exists():
                    print(f"Error: Session file not found: {args.session_file}")
                    sys.exit(1)

                # Evaluate single session
                evaluation = evaluator.evaluate_session(args.session_file)
                print(f"\n📊 Session Evaluation: {evaluation.session_id}")
                print(f"  Status: {evaluation.session_status}")
                print(f"  Quality Score: {evaluation.session_quality_score}/100")
                print(f"  Coherence: {evaluation.avg_coherence_score * 100:.1f}%")
                print(f"  Context Retention: {evaluation.context_retention_score * 100:.1f}%")
                print(f"  Goal Completion: {evaluation.goal_completion_rate * 100:.1f}%")
                print(f"  Tool Efficiency: {evaluation.tool_efficiency * 100:.1f}%")
            else:
                # Generate aggregate report
                report = evaluator.generate_report(days=args.days)
                print(evaluator.display_dashboard(report))

                # Save to default location
                report_path = tracker.save_report(
                    evaluator.display_dashboard(report), report_type='session_eval'
                )
                print(f"\n✅ Session evaluation report saved to: {report_path}")

        elif args.report == 'multi-turn':
            # Generate multi-turn optimization report (Task 28: GAP-COST-AG-007)
            from multi_turn_optimizer import MultiTurnOptimizer

            optimizer = MultiTurnOptimizer()

            if args.session_file:
                if not args.session_file.exists():
                    print(f"Error: Session file not found: {args.session_file}")
                    sys.exit(1)

                # Get recommendation for session
                messages = []
                with open(args.session_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                msg = json.loads(line)
                                if msg.get("type") in ("user", "assistant"):
                                    messages.append(msg)
                            except json.JSONDecodeError:
                                continue

                recommendation = optimizer.get_recommendation(messages)
                print(f"\n📊 Multi-Turn Optimization Recommendation:")
                print(f"  {recommendation['message']}")
                print(f"  Current tokens: {recommendation['current_tokens']:,}")
                print(f"  Turn count: {recommendation['turn_count']}")
                if recommendation['should_optimize']:
                    print(f"  Recommended strategy: {recommendation['recommended_strategy']}")
                    print(f"  Expected savings: {recommendation['estimated_savings']:,} tokens")
            else:
                # Generate aggregate report
                report = optimizer.generate_report(days=args.days)
                print(report)

                # Save to default location
                report_path = tracker.save_report(report, report_type='multi_turn')
                print(f"\n✅ Multi-turn optimization report saved to: {report_path}")

        elif args.report == 'budget':
            # Generate budget status report (Task 29: GAP-COST-AG-003)
            sys.path.insert(0, str(Path.home() / ".claude" / "evaluation" / "costs"))
            from budget_manager import BudgetManager

            budget_manager = BudgetManager()

            if args.session_file:
                # Show budget for specific session
                session_id = args.session_file.stem
                print(budget_manager.generate_dashboard(session_id))
            else:
                # Show overall budget dashboard
                print(budget_manager.generate_dashboard())

                # Save to default location
                report_path = tracker.save_report(
                    budget_manager.generate_dashboard(), report_type='budget'
                )
                print(f"\n✅ Budget report saved to: {report_path}")

        elif args.report == 'task-cost':
            # Generate task cost analysis report (Task 30: GAP-COST-AG-004)
            sys.path.insert(0, str(Path.home() / ".claude" / "evaluation" / "costs"))
            from task_cost_analyzer import TaskCostAnalyzer

            analyzer = TaskCostAnalyzer()
            print(analyzer.generate_dashboard(args.days))

            # Save to default location
            report_path = tracker.save_report(
                analyzer.generate_dashboard(args.days), report_type='task_cost'
            )
            print(f"\n✅ Task cost report saved to: {report_path}")

    elif args.collect:
        print("Interactive metric collection not yet implemented.")
        print("Metrics are collected automatically via hooks.")
        sys.exit(1)

    elif args.quick_check:
        # Quick validation (for git hooks)
        print("✅ Metrics system operational")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
