#!/usr/bin/env python3
"""
Agent Cost Tracker — Unified cost tracking across all agent operations.

Tracks costs for:
- Tokens (input/output/cached) across all models
- Tool executions (Bash, Read, Write, WebFetch, etc.)
- Subagent spawns (Task tool)
- External API calls
- Compute resources (execution time)
- Storage operations (file writes)

Usage:
    python3 agent_cost_tracker.py --report                    # Current day summary
    python3 agent_cost_tracker.py --report --session SESSION  # Session summary
    python3 agent_cost_tracker.py --test                      # Run self-tests
    python3 agent_cost_tracker.py --stats                     # Historical stats

Version: 1.0.0
Task: TIER 2B Task 19 - Agent Cost Tracking (GAP-COST-IMPL-003)
Author: Claude Code
Date: 2026-01-29
"""

import argparse
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Individual cost record for a single operation."""
    timestamp: str  # ISO format
    session_id: str
    category: str  # tokens, tools, subagents, external_apis, compute, storage
    amount: float  # USD
    details: dict  # category-specific metadata

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CostRecord':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class CostSummary:
    """Aggregated cost summary for a period."""
    session_id: str
    period_start: str
    period_end: str
    total_cost: float
    by_category: Dict[str, float]  # category -> total
    by_model: Dict[str, float]  # model -> total (for tokens)
    by_tool: Dict[str, float]  # tool -> total (for tools)
    request_count: int
    cost_per_request: float
    hourly_rate: float
    daily_projection: float
    budget_status: str  # healthy/warning/critical

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class AgentCostTracker:
    """Unified agent cost tracking across all cost sources."""

    # Default storage location
    STORAGE_FILE = Path.home() / ".claude" / "evaluation" / "data" / "agent_costs.jsonl"

    # Token pricing per 1M tokens (USD)
    TOKEN_PRICING = {
        "haiku": {"input": 1.0, "output": 5.0, "cached_input": 0.1},
        "sonnet": {"input": 3.0, "output": 15.0, "cached_input": 0.3},
        "opus": {"input": 15.0, "output": 75.0, "cached_input": 1.5},
    }

    # Tool execution costs (estimated USD per call)
    TOOL_COSTS = {
        # Core tools
        "Bash": 0.001,
        "Read": 0.0001,
        "Write": 0.0001,
        "Edit": 0.0001,
        "Glob": 0.0001,
        "Grep": 0.0002,
        "Task": 0.05,  # Subagent spawn overhead
        "WebFetch": 0.005,
        "WebSearch": 0.01,
        "NotebookEdit": 0.0002,
        # MCP GitHub tools
        "mcp__github__search_code": 0.002,
        "mcp__github__search_repositories": 0.002,
        "mcp__github__search_issues": 0.002,
        "mcp__github__get_file_contents": 0.001,
        "mcp__github__list_commits": 0.001,
        "mcp__github__list_issues": 0.001,
        "mcp__github__list_pull_requests": 0.001,
        "mcp__github__get_issue": 0.0005,
        "mcp__github__get_pull_request": 0.0005,
        "mcp__github__create_issue": 0.003,
        "mcp__github__create_pull_request": 0.005,
        "mcp__github__push_files": 0.005,
        "mcp__github__create_or_update_file": 0.003,
    }

    # Tool alert thresholds (USD per session) — alert if exceeded
    TOOL_THRESHOLDS = {
        "Task": 0.50,          # Subagent spawns can add up
        "WebSearch": 0.25,     # Web searches can be expensive
        "WebFetch": 0.15,      # External fetches
        "mcp__github__create_pull_request": 0.10,
        "default": 0.10,       # Default threshold per tool
    }

    # Budget thresholds (USD)
    DAILY_BUDGET = 50.0
    SESSION_BUDGET = 10.0

    def __init__(self, storage_file: Optional[Path] = None):
        """
        Initialize agent cost tracker.

        Args:
            storage_file: Path to JSONL storage file (default: STORAGE_FILE)
        """
        self.storage_file = storage_file or self.STORAGE_FILE
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"AgentCostTracker initialized (storage: {self.storage_file})")

    def log_token_cost(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0
    ) -> float:
        """
        Log token usage cost.

        Args:
            session_id: Session identifier
            model: Model name (haiku/sonnet/opus)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached input tokens (90% discount)

        Returns:
            Total cost in USD
        """
        model_lower = model.lower()
        if model_lower not in self.TOKEN_PRICING:
            logger.warning(f"Unknown model '{model}', defaulting to sonnet pricing")
            model_lower = "sonnet"

        pricing = self.TOKEN_PRICING[model_lower]

        # Calculate costs (per million tokens)
        fresh_input_tokens = input_tokens - cached_tokens
        input_cost = (fresh_input_tokens / 1_000_000) * pricing["input"]
        cached_cost = (cached_tokens / 1_000_000) * pricing["cached_input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        total_cost = input_cost + cached_cost + output_cost

        record = CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            category="tokens",
            amount=total_cost,
            details={
                "model": model_lower,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_tokens": cached_tokens,
                "input_cost": input_cost,
                "cached_cost": cached_cost,
                "output_cost": output_cost,
            }
        )

        self._write_record(record)
        logger.debug(f"Logged token cost: ${total_cost:.6f} ({model_lower})")

        return total_cost

    def log_tool_cost(
        self,
        session_id: str,
        tool_name: str,
        execution_time_ms: int = 0,
        external_api: bool = False
    ) -> float:
        """
        Log tool execution cost.

        Args:
            session_id: Session identifier
            tool_name: Name of tool executed
            execution_time_ms: Execution time in milliseconds
            external_api: Whether tool made external API calls

        Returns:
            Total cost in USD
        """
        base_cost = self.TOOL_COSTS.get(tool_name, 0.0001)  # Default minimal cost

        # Add execution time cost if significant
        execution_cost = 0.0
        if execution_time_ms > 1000:  # >1 second
            execution_cost = (execution_time_ms / 1000) * 0.001

        total_cost = base_cost + execution_cost

        category = "external_apis" if external_api else "tools"

        record = CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            category=category,
            amount=total_cost,
            details={
                "tool_name": tool_name,
                "execution_time_ms": execution_time_ms,
                "external_api": external_api,
                "base_cost": base_cost,
                "execution_cost": execution_cost,
            }
        )

        self._write_record(record)
        logger.debug(f"Logged tool cost: ${total_cost:.6f} ({tool_name})")

        return total_cost

    def log_subagent_cost(
        self,
        session_id: str,
        subagent_id: str,
        subagent_model: str,
        tokens_used: Dict[str, int]
    ) -> float:
        """
        Log subagent spawn and execution cost.

        Args:
            session_id: Parent session identifier
            subagent_id: Subagent session identifier
            subagent_model: Model used by subagent
            tokens_used: Dict with input_tokens, output_tokens, cached_tokens

        Returns:
            Total cost in USD
        """
        # Spawn overhead
        spawn_cost = 0.01

        # Token costs
        token_cost = self.log_token_cost(
            session_id=subagent_id,  # Track under subagent session
            model=subagent_model,
            input_tokens=tokens_used.get("input_tokens", 0),
            output_tokens=tokens_used.get("output_tokens", 0),
            cached_tokens=tokens_used.get("cached_tokens", 0)
        )

        total_cost = spawn_cost + token_cost

        record = CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,  # Attribute to parent session
            category="subagents",
            amount=spawn_cost,  # Only spawn overhead here (tokens logged separately)
            details={
                "subagent_id": subagent_id,
                "subagent_model": subagent_model,
                "spawn_cost": spawn_cost,
                "token_cost": token_cost,
                "total_cost": total_cost,
            }
        )

        self._write_record(record)
        logger.debug(f"Logged subagent cost: ${total_cost:.6f} ({subagent_id})")

        return total_cost

    def log_compute_cost(
        self,
        session_id: str,
        execution_time_seconds: float
    ) -> float:
        """
        Log compute resource cost.

        Args:
            session_id: Session identifier
            execution_time_seconds: Execution time in seconds

        Returns:
            Total cost in USD
        """
        cost = execution_time_seconds * 0.001  # $0.001 per second

        record = CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            category="compute",
            amount=cost,
            details={
                "execution_time_seconds": execution_time_seconds,
            }
        )

        self._write_record(record)
        logger.debug(f"Logged compute cost: ${cost:.6f}")

        return cost

    def log_storage_cost(
        self,
        session_id: str,
        bytes_written: int
    ) -> float:
        """
        Log storage operation cost.

        Args:
            session_id: Session identifier
            bytes_written: Number of bytes written

        Returns:
            Total cost in USD
        """
        kb_written = bytes_written / 1024
        cost = kb_written * 0.0001  # $0.0001 per KB

        record = CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            category="storage",
            amount=cost,
            details={
                "bytes_written": bytes_written,
                "kb_written": kb_written,
            }
        )

        self._write_record(record)
        logger.debug(f"Logged storage cost: ${cost:.6f}")

        return cost

    def _write_record(self, record: CostRecord) -> None:
        """
        Write cost record to JSONL storage.

        Args:
            record: Cost record to write
        """
        try:
            with open(self.storage_file, 'a') as f:
                f.write(json.dumps(record.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to write cost record: {e}")

    def _read_records(
        self,
        session_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[CostRecord]:
        """
        Read cost records from storage.

        Args:
            session_id: Filter by session ID (optional)
            since: Filter by timestamp (optional)

        Returns:
            List of cost records
        """
        if not self.storage_file.exists():
            return []

        records = []

        try:
            with open(self.storage_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        record = CostRecord.from_dict(data)

                        # Apply filters
                        if session_id and record.session_id != session_id:
                            continue

                        if since:
                            record_time = datetime.fromisoformat(record.timestamp)
                            if record_time < since:
                                continue

                        records.append(record)

                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Skipping invalid record: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to read cost records: {e}")

        return records

    def get_session_summary(self, session_id: str) -> CostSummary:
        """
        Get cost summary for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            Cost summary
        """
        records = self._read_records(session_id=session_id)

        if not records:
            # Return empty summary
            return CostSummary(
                session_id=session_id,
                period_start=datetime.now(timezone.utc).isoformat(),
                period_end=datetime.now(timezone.utc).isoformat(),
                total_cost=0.0,
                by_category={},
                by_model={},
                by_tool={},
                request_count=0,
                cost_per_request=0.0,
                hourly_rate=0.0,
                daily_projection=0.0,
                budget_status="healthy"
            )

        # Calculate aggregates
        total_cost = sum(r.amount for r in records)

        by_category = defaultdict(float)
        by_model = defaultdict(float)
        by_tool = defaultdict(float)

        for record in records:
            by_category[record.category] += record.amount

            if record.category == "tokens":
                model = record.details.get("model", "unknown")
                by_model[model] += record.amount

            if record.category in ("tools", "external_apis"):
                tool = record.details.get("tool_name", "unknown")
                by_tool[tool] += record.amount

        # Time span
        timestamps = [datetime.fromisoformat(r.timestamp) for r in records]
        period_start = min(timestamps)
        period_end = max(timestamps)
        duration_hours = (period_end - period_start).total_seconds() / 3600

        # Derived metrics
        request_count = len(records)
        cost_per_request = total_cost / request_count if request_count > 0 else 0.0
        hourly_rate = total_cost / duration_hours if duration_hours > 0 else 0.0
        daily_projection = hourly_rate * 24

        # Budget status
        budget_pct = (total_cost / self.SESSION_BUDGET) * 100
        if budget_pct >= 100:
            budget_status = "critical"
        elif budget_pct >= 80:
            budget_status = "warning"
        else:
            budget_status = "healthy"

        return CostSummary(
            session_id=session_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            total_cost=total_cost,
            by_category=dict(by_category),
            by_model=dict(by_model),
            by_tool=dict(by_tool),
            request_count=request_count,
            cost_per_request=cost_per_request,
            hourly_rate=hourly_rate,
            daily_projection=daily_projection,
            budget_status=budget_status
        )

    def get_daily_summary(self, date: Optional[datetime] = None) -> CostSummary:
        """
        Get cost summary for a specific day.

        Args:
            date: Date to summarize (default: today)

        Returns:
            Cost summary
        """
        if date is None:
            date = datetime.now(timezone.utc)

        # Start and end of day (UTC)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        records = self._read_records(since=day_start)
        records = [r for r in records if datetime.fromisoformat(r.timestamp) < day_end]

        if not records:
            # Return empty summary
            return CostSummary(
                session_id="daily",
                period_start=day_start.isoformat(),
                period_end=day_end.isoformat(),
                total_cost=0.0,
                by_category={},
                by_model={},
                by_tool={},
                request_count=0,
                cost_per_request=0.0,
                hourly_rate=0.0,
                daily_projection=0.0,
                budget_status="healthy"
            )

        # Calculate aggregates
        total_cost = sum(r.amount for r in records)

        by_category = defaultdict(float)
        by_model = defaultdict(float)
        by_tool = defaultdict(float)

        for record in records:
            by_category[record.category] += record.amount

            if record.category == "tokens":
                model = record.details.get("model", "unknown")
                by_model[model] += record.amount

            if record.category in ("tools", "external_apis"):
                tool = record.details.get("tool_name", "unknown")
                by_tool[tool] += record.amount

        # Derived metrics
        request_count = len(records)
        cost_per_request = total_cost / request_count if request_count > 0 else 0.0
        duration_hours = (day_end - day_start).total_seconds() / 3600
        hourly_rate = total_cost / duration_hours if duration_hours > 0 else 0.0
        daily_projection = total_cost  # Already daily

        # Budget status
        budget_pct = (total_cost / self.DAILY_BUDGET) * 100
        if budget_pct >= 100:
            budget_status = "critical"
        elif budget_pct >= 80:
            budget_status = "warning"
        else:
            budget_status = "healthy"

        return CostSummary(
            session_id="daily",
            period_start=day_start.isoformat(),
            period_end=day_end.isoformat(),
            total_cost=total_cost,
            by_category=dict(by_category),
            by_model=dict(by_model),
            by_tool=dict(by_tool),
            request_count=request_count,
            cost_per_request=cost_per_request,
            hourly_rate=hourly_rate,
            daily_projection=daily_projection,
            budget_status=budget_status
        )

    def generate_report(self, session_id: Optional[str] = None) -> str:
        """
        Generate formatted cost report.

        Args:
            session_id: Session ID (default: daily summary)

        Returns:
            Formatted report text
        """
        if session_id:
            summary = self.get_session_summary(session_id)
            period_elapsed = self._format_duration(summary.period_start, summary.period_end)
            title = f"Session: {session_id[:8]}... ({period_elapsed})"
        else:
            summary = self.get_daily_summary()
            date_str = datetime.fromisoformat(summary.period_start).strftime("%Y-%m-%d")
            title = f"Daily Summary: {date_str}"

        # Status emoji
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "🔴"
        }.get(summary.budget_status, "❓")

        # Calculate percentages
        total = summary.total_cost
        if total > 0:
            pcts = {cat: (amt / total) * 100 for cat, amt in summary.by_category.items()}
        else:
            pcts = {}

        # Budget calculations
        budget = self.SESSION_BUDGET if session_id else self.DAILY_BUDGET
        budget_used_pct = (total / budget * 100) if budget > 0 else 0
        budget_remaining = max(0, budget - total)

        # Build report
        lines = [
            "═" * 62,
            f"  AGENT COST TRACKING — {title}",
            "═" * 62,
            "",
            "COST BREAKDOWN:",
        ]

        # Categories
        categories = [
            "tokens", "tools", "subagents",
            "external_apis", "compute", "storage"
        ]

        for cat in categories:
            amt = summary.by_category.get(cat, 0.0)
            pct = pcts.get(cat, 0.0)
            lines.append(f"  {cat.replace('_', ' ').title():<16}${amt:>7.3f}  ({pct:>5.1f}%)")

        lines.extend([
            "  " + "─" * 58,
            f"  {'TOTAL':<16}${total:>7.3f}  (100%)",
            "",
        ])

        # Top models (if any)
        if summary.by_model:
            lines.append("TOP MODELS:")
            sorted_models = sorted(summary.by_model.items(), key=lambda x: x[1], reverse=True)
            for model, cost in sorted_models[:3]:
                lines.append(f"  {model:<16}${cost:>7.3f}")
            lines.append("")

        # Top tools (if any)
        if summary.by_tool:
            lines.append("TOP TOOLS:")
            sorted_tools = sorted(summary.by_tool.items(), key=lambda x: x[1], reverse=True)
            for tool, cost in sorted_tools[:3]:
                lines.append(f"  {tool:<16}${cost:>7.3f}")
            lines.append("")

        # Projections
        lines.extend([
            "PROJECTIONS:",
            f"  Hourly Rate:      ${summary.hourly_rate:>6.2f}/hour",
            f"  Daily Projection: ${summary.daily_projection:>6.2f}",
            f"  Daily Budget:     ${budget:>6.2f} (remaining: ${budget_remaining:>6.2f})",
            "",
        ])

        # Status
        status_text = summary.budget_status.upper()
        lines.extend([
            f"STATUS: {status_emoji} {status_text} ({budget_used_pct:.0f}% of budget used)",
            "",
            "═" * 62,
        ])

        return "\n".join(lines)

    def get_budget_status(self, session_id: Optional[str] = None) -> dict:
        """
        Get current budget status.

        Args:
            session_id: Session ID (default: daily)

        Returns:
            Budget status dictionary
        """
        if session_id:
            summary = self.get_session_summary(session_id)
            budget = self.SESSION_BUDGET
            scope = "session"
        else:
            summary = self.get_daily_summary()
            budget = self.DAILY_BUDGET
            scope = "daily"

        spent = summary.total_cost
        remaining = max(0, budget - spent)
        used_pct = (spent / budget * 100) if budget > 0 else 0

        return {
            "scope": scope,
            "budget": budget,
            "spent": spent,
            "remaining": remaining,
            "used_pct": used_pct,
            "status": summary.budget_status,
            "request_count": summary.request_count,
            "cost_per_request": summary.cost_per_request,
        }

    @staticmethod
    def _format_duration(start_iso: str, end_iso: str) -> str:
        """Format duration between two ISO timestamps."""
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        delta = end - start

        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    # === Task 22: Tool Execution Cost Tracking (GAP-COST-AG-002) ===

    def get_expensive_tools(
        self,
        session_id: Optional[str] = None,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Get the most expensive tools by cost.

        Args:
            session_id: Session ID (default: daily)
            top_n: Number of top tools to return

        Returns:
            List of dicts with tool name, total cost, call count, avg cost
        """
        if session_id:
            summary = self.get_session_summary(session_id)
        else:
            summary = self.get_daily_summary()

        if not summary.by_tool:
            return []

        # Get detailed tool stats
        records = self._read_records(session_id=session_id) if session_id else self._read_records()

        tool_stats = defaultdict(lambda: {"cost": 0.0, "count": 0})
        for record in records:
            if record.category in ("tools", "external_apis"):
                tool_name = record.details.get("tool_name", "unknown")
                tool_stats[tool_name]["cost"] += record.amount
                tool_stats[tool_name]["count"] += 1

        # Calculate averages and format
        result = []
        for tool_name, stats in tool_stats.items():
            avg_cost = stats["cost"] / stats["count"] if stats["count"] > 0 else 0
            result.append({
                "tool": tool_name,
                "total_cost": stats["cost"],
                "call_count": stats["count"],
                "avg_cost": avg_cost,
                "base_cost": self.TOOL_COSTS.get(tool_name, 0.0001),
            })

        # Sort by total cost descending
        result.sort(key=lambda x: x["total_cost"], reverse=True)

        return result[:top_n]

    def get_tool_alerts(self, session_id: Optional[str] = None) -> List[Dict]:
        """
        Check if any tools exceeded their cost thresholds.

        Args:
            session_id: Session ID (default: daily)

        Returns:
            List of alert dicts with tool name, cost, threshold, percent over
        """
        if session_id:
            summary = self.get_session_summary(session_id)
        else:
            summary = self.get_daily_summary()

        alerts = []
        for tool_name, total_cost in summary.by_tool.items():
            threshold = self.TOOL_THRESHOLDS.get(
                tool_name,
                self.TOOL_THRESHOLDS.get("default", 0.10)
            )

            if total_cost > threshold:
                pct_over = ((total_cost - threshold) / threshold) * 100
                alerts.append({
                    "tool": tool_name,
                    "total_cost": total_cost,
                    "threshold": threshold,
                    "pct_over": pct_over,
                    "severity": "critical" if pct_over > 100 else "warning",
                })

        # Sort by percent over threshold descending
        alerts.sort(key=lambda x: x["pct_over"], reverse=True)

        return alerts

    def generate_tool_report(self, session_id: Optional[str] = None) -> str:
        """
        Generate detailed tool cost report.

        Args:
            session_id: Session ID (default: daily)

        Returns:
            Formatted tool cost report
        """
        expensive_tools = self.get_expensive_tools(session_id, top_n=10)
        alerts = self.get_tool_alerts(session_id)

        lines = [
            "═" * 62,
            "  TOOL COST ANALYSIS REPORT",
            "═" * 62,
            "",
        ]

        # Expensive tools section
        if expensive_tools:
            lines.append("TOP EXPENSIVE TOOLS:")
            lines.append(f"  {'Tool':<24}{'Cost':>10}{'Calls':>8}{'Avg':>10}")
            lines.append("  " + "─" * 52)

            for tool in expensive_tools:
                lines.append(
                    f"  {tool['tool']:<24}"
                    f"${tool['total_cost']:>8.4f}"
                    f"{tool['call_count']:>8}"
                    f"${tool['avg_cost']:>8.4f}"
                )
            lines.append("")

        # Alerts section
        if alerts:
            lines.append("⚠️ TOOL COST ALERTS:")
            for alert in alerts:
                severity_icon = "🔴" if alert["severity"] == "critical" else "⚠️"
                lines.append(
                    f"  {severity_icon} {alert['tool']}: "
                    f"${alert['total_cost']:.4f} "
                    f"(threshold: ${alert['threshold']:.2f}, "
                    f"+{alert['pct_over']:.0f}% over)"
                )
            lines.append("")
        else:
            lines.append("✅ No tool cost alerts")
            lines.append("")

        lines.append("═" * 62)

        return "\n".join(lines)


def run_self_test() -> None:
    """Run self-tests for AgentCostTracker."""
    print("Running AgentCostTracker self-tests...\n")

    # Use temporary storage
    import tempfile
    temp_file = Path(tempfile.mktemp(suffix=".jsonl"))
    tracker = AgentCostTracker(storage_file=temp_file)

    test_session = "test-session-001"
    passed = 0
    failed = 0

    # Test 1: Token cost calculation (haiku)
    print("Test 1: Token cost calculation (haiku)...")
    cost = tracker.log_token_cost(test_session, "haiku", 10000, 5000, 2000)
    expected = (8000/1_000_000)*1.0 + (2000/1_000_000)*0.1 + (5000/1_000_000)*5.0
    assert abs(cost - expected) < 0.0001, f"Expected {expected}, got {cost}"
    print(f"  ✅ PASS: ${cost:.6f}\n")
    passed += 1

    # Test 2: Token cost calculation (sonnet)
    print("Test 2: Token cost calculation (sonnet)...")
    cost = tracker.log_token_cost(test_session, "sonnet", 15000, 8000, 5000)
    expected = (10000/1_000_000)*3.0 + (5000/1_000_000)*0.3 + (8000/1_000_000)*15.0
    assert abs(cost - expected) < 0.0001, f"Expected {expected}, got {cost}"
    print(f"  ✅ PASS: ${cost:.6f}\n")
    passed += 1

    # Test 3: Tool cost logging
    print("Test 3: Tool cost logging...")
    cost = tracker.log_tool_cost(test_session, "Bash", execution_time_ms=1500)
    assert cost > 0, "Cost should be positive"
    print(f"  ✅ PASS: ${cost:.6f}\n")
    passed += 1

    # Test 4: Subagent cost logging
    print("Test 4: Subagent cost logging...")
    cost = tracker.log_subagent_cost(
        test_session,
        "subagent-001",
        "haiku",
        {"input_tokens": 5000, "output_tokens": 2000, "cached_tokens": 1000}
    )
    assert cost > 0, "Cost should be positive"
    print(f"  ✅ PASS: ${cost:.6f}\n")
    passed += 1

    # Test 5: Session summary aggregation
    print("Test 5: Session summary aggregation...")
    summary = tracker.get_session_summary(test_session)
    assert summary.total_cost > 0, "Total cost should be positive"
    assert summary.request_count > 0, "Request count should be positive"
    assert "tokens" in summary.by_category, "Should have tokens category"
    print(f"  ✅ PASS: Total ${summary.total_cost:.3f}, {summary.request_count} requests\n")
    passed += 1

    # Test 6: Daily summary
    print("Test 6: Daily summary...")
    daily = tracker.get_daily_summary()
    assert daily.total_cost >= 0, "Daily cost should be non-negative"
    print(f"  ✅ PASS: Daily total ${daily.total_cost:.3f}\n")
    passed += 1

    # Test 7: Budget status
    print("Test 7: Budget status...")
    status = tracker.get_budget_status(test_session)
    assert "budget" in status, "Should have budget field"
    assert "spent" in status, "Should have spent field"
    assert "status" in status, "Should have status field"
    assert status["status"] in ["healthy", "warning", "critical"], "Status should be valid"
    print(f"  ✅ PASS: Status={status['status']}, Spent=${status['spent']:.3f}\n")
    passed += 1

    # Test 8: Report generation
    print("Test 8: Report generation...")
    report = tracker.generate_report(test_session)
    assert len(report) > 0, "Report should not be empty"
    assert "AGENT COST TRACKING" in report, "Report should have title"
    assert "COST BREAKDOWN" in report, "Report should have breakdown section"
    print(f"  ✅ PASS: Generated report ({len(report)} chars)\n")
    passed += 1

    # Test 9: Storage file creation
    print("Test 9: Storage file creation...")
    assert temp_file.exists(), "Storage file should exist"
    lines = temp_file.read_text().strip().split('\n')
    assert len(lines) > 0, "Storage file should have records"
    print(f"  ✅ PASS: {len(lines)} records written\n")
    passed += 1

    # Clean up
    temp_file.unlink()

    print("=" * 62)
    print(f"Self-test complete: {passed} passed, {failed} failed")
    print("=" * 62)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Cost Tracker - Unified cost tracking"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate cost report"
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for report (default: daily summary)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run self-tests"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show historical statistics"
    )

    args = parser.parse_args()

    if args.test:
        run_self_test()
        return

    tracker = AgentCostTracker()

    if args.report:
        report = tracker.generate_report(session_id=args.session)
        print(report)

    elif args.stats:
        # Show historical stats
        print("Historical statistics not yet implemented")
        print("Use --report for current/session reports")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
