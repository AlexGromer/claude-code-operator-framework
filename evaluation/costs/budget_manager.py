#!/usr/bin/env python3
"""
Budget Manager — Session, task, and daily cost budgets with alerts.

TIER 3 Phase 5 Task 29: GAP-COST-AG-003

Features:
- Per-session cost budgets
- Per-task cost limits
- Daily spending limits
- Multi-threshold alerts (50%, 75%, 90%)
- Soft/hard limit enforcement
- Budget history tracking

Usage:
    python3 budget_manager.py --status                    # Current budget status
    python3 budget_manager.py --set-session 5.0          # Set session budget to $5
    python3 budget_manager.py --set-daily 20.0           # Set daily budget to $20
    python3 budget_manager.py --check                    # Check all budgets
    python3 budget_manager.py --history --days 7         # Budget history

Version: 1.0.0
"""

import fcntl
import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BudgetLevel(Enum):
    """Budget alert levels."""
    HEALTHY = "healthy"      # <50%
    WARNING = "warning"      # 50-75%
    CRITICAL = "critical"    # 75-90%
    EXCEEDED = "exceeded"    # >90% (soft limit)
    BLOCKED = "blocked"      # >100% (hard limit)


class BudgetType(Enum):
    """Types of budgets."""
    SESSION = "session"
    TASK = "task"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class BudgetConfig:
    """Budget configuration."""
    budget_type: str
    limit: float  # USD
    soft_limit_pct: float = 90.0  # Percentage for soft limit (warning + confirm)
    hard_limit_pct: float = 100.0  # Percentage for hard limit (block)
    alert_thresholds: List[float] = field(default_factory=lambda: [50.0, 75.0, 90.0])
    enabled: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class BudgetStatus:
    """Current status of a budget."""
    budget_type: str
    limit: float
    spent: float
    remaining: float
    percentage: float
    level: str  # BudgetLevel value
    alerts_triggered: List[str]
    can_proceed: bool
    requires_confirmation: bool
    message: str


@dataclass
class BudgetAlert:
    """Budget alert record."""
    timestamp: str
    budget_type: str
    threshold: float
    current_pct: float
    spent: float
    limit: float
    message: str
    acknowledged: bool = False


@dataclass
class SpendingRecord:
    """Record of spending for budget tracking."""
    timestamp: str
    session_id: str
    task_id: Optional[str]
    amount: float  # USD
    category: str  # tokens, tools, etc.
    description: str


class BudgetManager:
    """
    Manages cost budgets for Claude Code sessions.

    TIER 3 Phase 5 Task 29 (GAP-COST-AG-003)

    Features:
    - Session, task, daily, weekly, monthly budgets
    - Multi-threshold alerts
    - Soft limits (warning + confirmation)
    - Hard limits (blocking)
    - Budget history and analytics
    """

    # Default budgets (USD)
    DEFAULT_BUDGETS = {
        BudgetType.SESSION.value: 5.0,    # $5 per session
        BudgetType.TASK.value: 1.0,       # $1 per task
        BudgetType.DAILY.value: 20.0,     # $20 per day
        BudgetType.WEEKLY.value: 100.0,   # $100 per week
        BudgetType.MONTHLY.value: 300.0,  # $300 per month
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize budget manager."""
        self.data_dir = data_dir or Path.home() / ".claude" / "evaluation" / "data"
        self.config_file = self.data_dir / "budget_config.json"
        self.spending_file = self.data_dir / "budget_spending.jsonl"
        self.alerts_file = self.data_dir / "budget_alerts.jsonl"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.config = self._load_config()
        self._triggered_alerts: Dict[str, set] = {}  # budget_type -> set of triggered thresholds

    def _load_config(self) -> Dict[str, BudgetConfig]:
        """Load budget configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return {
                        k: BudgetConfig(**v) for k, v in data.items()
                    }
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error loading config, using defaults: {e}")

        # Create default config
        config = {}
        for budget_type, limit in self.DEFAULT_BUDGETS.items():
            config[budget_type] = BudgetConfig(
                budget_type=budget_type,
                limit=limit,
            )
        self._save_config(config)
        return config

    def _save_config(self, config: Dict[str, BudgetConfig]) -> None:
        """Save budget configuration."""
        with open(self.config_file, 'w') as f:
            json.dump({k: asdict(v) for k, v in config.items()}, f, indent=2)

    def set_budget(
        self,
        budget_type: BudgetType,
        limit: float,
        soft_limit_pct: float = 90.0,
        hard_limit_pct: float = 100.0,
        alert_thresholds: Optional[List[float]] = None,
    ) -> BudgetConfig:
        """
        Set a budget limit.

        Args:
            budget_type: Type of budget
            limit: Limit in USD
            soft_limit_pct: Percentage for soft limit (default 90%)
            hard_limit_pct: Percentage for hard limit (default 100%)
            alert_thresholds: Custom alert thresholds

        Returns:
            Updated budget configuration
        """
        config = BudgetConfig(
            budget_type=budget_type.value,
            limit=limit,
            soft_limit_pct=soft_limit_pct,
            hard_limit_pct=hard_limit_pct,
            alert_thresholds=alert_thresholds or [50.0, 75.0, 90.0],
        )
        self.config[budget_type.value] = config
        self._save_config(self.config)

        logger.info(f"Budget set: {budget_type.value} = ${limit:.2f}")
        return config

    def get_budget(self, budget_type: BudgetType) -> Optional[BudgetConfig]:
        """Get budget configuration."""
        return self.config.get(budget_type.value)

    def record_spending(
        self,
        amount: float,
        session_id: str,
        category: str,
        description: str = "",
        task_id: Optional[str] = None,
    ) -> None:
        """
        Record a spending event.

        Args:
            amount: Amount spent in USD
            session_id: Current session ID
            category: Cost category (tokens, tools, etc.)
            description: Optional description
            task_id: Optional task ID
        """
        record = SpendingRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            task_id=task_id,
            amount=amount,
            category=category,
            description=description,
        )

        with open(self.spending_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(asdict(record)) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_spending(
        self,
        budget_type: BudgetType,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> float:
        """
        Get total spending for a budget period.

        Args:
            budget_type: Type of budget to check
            session_id: Session ID (for session budget)
            task_id: Task ID (for task budget)

        Returns:
            Total spending in USD
        """
        if not self.spending_file.exists():
            return 0.0

        now = datetime.now(timezone.utc)

        # Determine time window
        if budget_type == BudgetType.SESSION:
            # All spending in current session
            filter_func = lambda r: r.get("session_id") == session_id
        elif budget_type == BudgetType.TASK:
            # All spending in current task
            filter_func = lambda r: r.get("task_id") == task_id
        elif budget_type == BudgetType.DAILY:
            # Last 24 hours
            cutoff = now - timedelta(days=1)
            filter_func = lambda r: self._parse_timestamp(r.get("timestamp", "")) >= cutoff
        elif budget_type == BudgetType.WEEKLY:
            # Last 7 days
            cutoff = now - timedelta(days=7)
            filter_func = lambda r: self._parse_timestamp(r.get("timestamp", "")) >= cutoff
        elif budget_type == BudgetType.MONTHLY:
            # Last 30 days
            cutoff = now - timedelta(days=30)
            filter_func = lambda r: self._parse_timestamp(r.get("timestamp", "")) >= cutoff
        else:
            return 0.0

        total = 0.0
        with open(self.spending_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        if filter_func(record):
                            total += record.get("amount", 0.0)
                    except json.JSONDecodeError:
                        logger.warning(f"Corrupted spending record skipped: {line[:80]}")
                        continue

        return total

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO timestamp."""
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def check_budget(
        self,
        budget_type: BudgetType,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        proposed_spend: float = 0.0,
    ) -> BudgetStatus:
        """
        Check budget status and generate alerts.

        Args:
            budget_type: Type of budget to check
            session_id: Session ID (for session budget)
            task_id: Task ID (for task budget)
            proposed_spend: Amount about to be spent (for pre-check)

        Returns:
            BudgetStatus with current state
        """
        config = self.config.get(budget_type.value)
        if not config or not config.enabled:
            return BudgetStatus(
                budget_type=budget_type.value,
                limit=0.0,
                spent=0.0,
                remaining=float('inf'),
                percentage=0.0,
                level=BudgetLevel.HEALTHY.value,
                alerts_triggered=[],
                can_proceed=True,
                requires_confirmation=False,
                message="Budget not configured or disabled",
            )

        spent = self.get_spending(budget_type, session_id, task_id)
        total_after = spent + proposed_spend
        percentage = (total_after / config.limit * 100) if config.limit > 0 else 0
        remaining = max(0, config.limit - spent)

        # Determine level
        if percentage >= config.hard_limit_pct:
            level = BudgetLevel.BLOCKED
        elif percentage >= config.soft_limit_pct:
            level = BudgetLevel.EXCEEDED
        elif percentage >= 75:
            level = BudgetLevel.CRITICAL
        elif percentage >= 50:
            level = BudgetLevel.WARNING
        else:
            level = BudgetLevel.HEALTHY

        # Check for new alerts
        alerts_triggered = []
        budget_key = f"{budget_type.value}_{session_id or 'global'}"
        if budget_key not in self._triggered_alerts:
            self._triggered_alerts[budget_key] = set()

        for threshold in config.alert_thresholds:
            if percentage >= threshold and threshold not in self._triggered_alerts[budget_key]:
                self._triggered_alerts[budget_key].add(threshold)
                alert_msg = f"{budget_type.value} budget at {percentage:.1f}% (threshold: {threshold}%)"
                alerts_triggered.append(alert_msg)
                self._record_alert(budget_type, threshold, percentage, spent, config.limit)

        # Determine actions
        can_proceed = level not in (BudgetLevel.BLOCKED,)
        requires_confirmation = level == BudgetLevel.EXCEEDED

        # Generate message
        if level == BudgetLevel.BLOCKED:
            message = f"❌ BLOCKED: {budget_type.value} budget exceeded (${spent:.2f}/${config.limit:.2f})"
        elif level == BudgetLevel.EXCEEDED:
            message = f"⚠️ SOFT LIMIT: {budget_type.value} at {percentage:.1f}% - requires confirmation"
        elif level == BudgetLevel.CRITICAL:
            message = f"🔴 CRITICAL: {budget_type.value} at {percentage:.1f}%"
        elif level == BudgetLevel.WARNING:
            message = f"🟡 WARNING: {budget_type.value} at {percentage:.1f}%"
        else:
            message = f"✅ HEALTHY: {budget_type.value} at {percentage:.1f}%"

        return BudgetStatus(
            budget_type=budget_type.value,
            limit=config.limit,
            spent=spent,
            remaining=remaining,
            percentage=percentage,
            level=level.value,
            alerts_triggered=alerts_triggered,
            can_proceed=can_proceed,
            requires_confirmation=requires_confirmation,
            message=message,
        )

    def _record_alert(
        self,
        budget_type: BudgetType,
        threshold: float,
        current_pct: float,
        spent: float,
        limit: float,
    ) -> None:
        """Record a budget alert."""
        alert = BudgetAlert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            budget_type=budget_type.value,
            threshold=threshold,
            current_pct=current_pct,
            spent=spent,
            limit=limit,
            message=f"{budget_type.value} budget reached {threshold}% threshold",
        )

        with open(self.alerts_file, 'a') as f:
            f.write(json.dumps(asdict(alert)) + "\n")

    def check_all_budgets(
        self,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, BudgetStatus]:
        """
        Check all configured budgets.

        Returns:
            Dictionary of budget type -> status
        """
        statuses = {}
        for budget_type in BudgetType:
            statuses[budget_type.value] = self.check_budget(
                budget_type, session_id, task_id
            )
        return statuses

    def can_spend(
        self,
        amount: float,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Check if spending amount is allowed.

        Args:
            amount: Proposed spending amount
            session_id: Current session ID
            task_id: Current task ID

        Returns:
            Tuple of (can_proceed, list of blocking reasons)
        """
        blocking_reasons = []

        for budget_type in BudgetType:
            status = self.check_budget(
                budget_type, session_id, task_id, proposed_spend=amount
            )
            if not status.can_proceed:
                blocking_reasons.append(status.message)

        return len(blocking_reasons) == 0, blocking_reasons

    def get_budget_history(self, days: int = 7) -> List[Dict]:
        """Get spending history by day."""
        if not self.spending_file.exists():
            return []

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        # Aggregate by day
        daily_spending = {}

        with open(self.spending_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        ts = self._parse_timestamp(record.get("timestamp", ""))
                        if ts >= cutoff:
                            day = ts.strftime("%Y-%m-%d")
                            if day not in daily_spending:
                                daily_spending[day] = {
                                    "date": day,
                                    "total": 0.0,
                                    "by_category": {},
                                    "count": 0,
                                }
                            daily_spending[day]["total"] += record.get("amount", 0.0)
                            daily_spending[day]["count"] += 1

                            category = record.get("category", "unknown")
                            if category not in daily_spending[day]["by_category"]:
                                daily_spending[day]["by_category"][category] = 0.0
                            daily_spending[day]["by_category"][category] += record.get("amount", 0.0)
                    except json.JSONDecodeError:
                        continue

        return sorted(daily_spending.values(), key=lambda x: x["date"])

    def get_alerts_history(self, days: int = 7) -> List[BudgetAlert]:
        """Get alert history."""
        if not self.alerts_file.exists():
            return []

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        alerts = []
        with open(self.alerts_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        ts = self._parse_timestamp(data.get("timestamp", ""))
                        if ts >= cutoff:
                            alerts.append(BudgetAlert(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue

        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def reset_session_budget(self, session_id: str) -> None:
        """Reset triggered alerts for a new session."""
        keys_to_remove = [k for k in self._triggered_alerts if session_id in k]
        for key in keys_to_remove:
            del self._triggered_alerts[key]

    def generate_dashboard(
        self,
        session_id: Optional[str] = None,
    ) -> str:
        """Generate budget status dashboard."""
        lines = [
            "",
            "=" * 70,
            "BUDGET STATUS DASHBOARD",
            "=" * 70,
            "",
        ]

        # Current budgets
        lines.append("─" * 70)
        lines.append("CURRENT BUDGETS")
        lines.append("─" * 70)
        lines.append("")

        statuses = self.check_all_budgets(session_id)

        for budget_type, status in statuses.items():
            if status.limit > 0:
                bar_width = 40
                filled = int(min(100, status.percentage) / 100 * bar_width)
                bar = "█" * filled + "░" * (bar_width - filled)

                level_icon = {
                    "healthy": "✅",
                    "warning": "🟡",
                    "critical": "🔴",
                    "exceeded": "⚠️",
                    "blocked": "❌",
                }.get(status.level, "?")

                lines.append(f"  {budget_type.upper():12} {level_icon}")
                lines.append(f"    [{bar}] {status.percentage:.1f}%")
                lines.append(f"    ${status.spent:.2f} / ${status.limit:.2f} (${status.remaining:.2f} remaining)")
                lines.append("")

        # Recent alerts
        alerts = self.get_alerts_history(days=1)
        if alerts:
            lines.append("─" * 70)
            lines.append("RECENT ALERTS (24h)")
            lines.append("─" * 70)
            lines.append("")

            for alert in alerts[:5]:
                lines.append(f"  [{alert.timestamp[:16]}] {alert.message}")
            lines.append("")

        # Spending history (last 7 days)
        history = self.get_budget_history(days=7)
        if history:
            lines.append("─" * 70)
            lines.append("DAILY SPENDING (Last 7 days)")
            lines.append("─" * 70)
            lines.append("")

            for day in history[-7:]:
                lines.append(f"  {day['date']}: ${day['total']:.2f} ({day['count']} operations)")

            total_week = sum(d["total"] for d in history)
            lines.append(f"\n  Weekly Total: ${total_week:.2f}")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Budget Manager")
    parser.add_argument("--status", action="store_true", help="Show budget status dashboard")
    parser.add_argument("--set-session", type=float, help="Set session budget (USD)")
    parser.add_argument("--set-task", type=float, help="Set task budget (USD)")
    parser.add_argument("--set-daily", type=float, help="Set daily budget (USD)")
    parser.add_argument("--set-weekly", type=float, help="Set weekly budget (USD)")
    parser.add_argument("--set-monthly", type=float, help="Set monthly budget (USD)")
    parser.add_argument("--check", action="store_true", help="Check all budgets")
    parser.add_argument("--history", action="store_true", help="Show spending history")
    parser.add_argument("--alerts", action="store_true", help="Show alert history")
    parser.add_argument("--days", type=int, default=7, help="Days for history (default: 7)")
    parser.add_argument("--session-id", help="Session ID for session-specific checks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    manager = BudgetManager()

    # Set budgets
    if args.set_session:
        manager.set_budget(BudgetType.SESSION, args.set_session)
        print(f"✅ Session budget set to ${args.set_session:.2f}")

    if args.set_task:
        manager.set_budget(BudgetType.TASK, args.set_task)
        print(f"✅ Task budget set to ${args.set_task:.2f}")

    if args.set_daily:
        manager.set_budget(BudgetType.DAILY, args.set_daily)
        print(f"✅ Daily budget set to ${args.set_daily:.2f}")

    if args.set_weekly:
        manager.set_budget(BudgetType.WEEKLY, args.set_weekly)
        print(f"✅ Weekly budget set to ${args.set_weekly:.2f}")

    if args.set_monthly:
        manager.set_budget(BudgetType.MONTHLY, args.set_monthly)
        print(f"✅ Monthly budget set to ${args.set_monthly:.2f}")

    # Check budgets
    if args.check:
        statuses = manager.check_all_budgets(args.session_id)
        if args.json:
            print(json.dumps({k: asdict(v) if hasattr(v, '__dict__') else v
                            for k, v in statuses.items()}, indent=2))
        else:
            for budget_type, status in statuses.items():
                print(status.message)

    # Show status
    if args.status:
        print(manager.generate_dashboard(args.session_id))

    # Show history
    if args.history:
        history = manager.get_budget_history(args.days)
        if args.json:
            print(json.dumps(history, indent=2))
        else:
            print(f"\nSpending History (Last {args.days} days):")
            for day in history:
                print(f"  {day['date']}: ${day['total']:.2f}")

    # Show alerts
    if args.alerts:
        alerts = manager.get_alerts_history(args.days)
        if args.json:
            print(json.dumps([asdict(a) for a in alerts], indent=2))
        else:
            print(f"\nAlert History (Last {args.days} days):")
            for alert in alerts:
                print(f"  [{alert.timestamp[:16]}] {alert.message}")

    # Default: show status if no other action
    if not any([args.set_session, args.set_task, args.set_daily, args.set_weekly,
                args.set_monthly, args.check, args.status, args.history, args.alerts]):
        print(manager.generate_dashboard(args.session_id))


if __name__ == "__main__":
    main()
