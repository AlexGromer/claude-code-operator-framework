#!/usr/bin/env python3
"""
Subagent Spawn Cost Tracking — GAP-COST-AG-008

Features:
- Track cost per subagent spawn (model type, duration, tokens)
- Cost estimation before spawn (haiku/sonnet/opus pricing)
- Budget enforcement for subagent orchestration
- Integration with budget_manager.py

Usage:
    python3 subagent_cost_tracker.py --estimate "task description" --model sonnet
    python3 subagent_cost_tracker.py --report
    python3 subagent_cost_tracker.py --history --days 7
    python3 subagent_cost_tracker.py --set-budget 10.0

Version: 1.0.0
"""

import argparse
import fcntl
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Claude pricing (as of Jan 2025)
MODEL_PRICING = {
    "haiku": {
        "input": 0.00025,  # $0.25 per 1M tokens
        "output": 0.00125,  # $1.25 per 1M tokens
        "cache_write": 0.0003,
        "cache_read": 0.000025,
    },
    "sonnet": {
        "input": 0.003,  # $3 per 1M tokens
        "output": 0.015,  # $15 per 1M tokens
        "cache_write": 0.00375,
        "cache_read": 0.0003,
    },
    "opus": {
        "input": 0.015,  # $15 per 1M tokens
        "output": 0.075,  # $75 per 1M tokens
        "cache_write": 0.01875,
        "cache_read": 0.0015,
    },
}


@dataclass
class SubagentSpawn:
    """Record of a subagent spawn."""
    timestamp: str
    subagent_id: str
    model: str
    description: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    duration_ms: int = 0
    cost: float = 0.0
    session_id: str = ""


@dataclass
class BudgetConfig:
    """Budget configuration for subagents."""
    limit: float  # USD
    spent: float = 0.0
    enabled: bool = True
    alert_threshold: float = 0.8  # 80%


def estimate_subagent_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """
    Estimate cost for a subagent spawn.

    Args:
        model: Model name (haiku, sonnet, opus)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_read_tokens: Cached tokens read
        cache_write_tokens: Tokens written to cache

    Returns:
        Estimated cost in USD
    """
    # Normalize model name
    model_key = model.lower()
    if "haiku" in model_key:
        model_key = "haiku"
    elif "sonnet" in model_key:
        model_key = "sonnet"
    elif "opus" in model_key:
        model_key = "opus"
    else:
        logger.warning(f"Unknown model {model}, using sonnet pricing")
        model_key = "sonnet"

    pricing = MODEL_PRICING[model_key]

    # Calculate cost
    cost = (
        (input_tokens * pricing["input"] / 1000) +
        (output_tokens * pricing["output"] / 1000) +
        (cache_read_tokens * pricing["cache_read"] / 1000) +
        (cache_write_tokens * pricing["cache_write"] / 1000)
    )

    return cost


class SubagentCostTracker:
    """
    Track costs for subagent spawning.

    Features:
    - Record spawn events with token counts
    - Estimate costs before spawning
    - Budget enforcement
    - Cost analytics and reporting
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize tracker."""
        self.data_dir = data_dir or Path.home() / ".claude" / "evaluation" / "data"
        self.spawns_file = self.data_dir / "subagent_spawns.jsonl"
        self.budget_file = self.data_dir / "subagent_budget.json"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.budget = self._load_budget()

    def _load_budget(self) -> BudgetConfig:
        """Load budget configuration."""
        if self.budget_file.exists():
            try:
                with open(self.budget_file, 'r') as f:
                    data = json.load(f)
                    return BudgetConfig(**data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error loading budget: {e}")

        # Default budget: $10 per session
        return BudgetConfig(limit=10.0)

    def _save_budget(self):
        """Save budget configuration."""
        with open(self.budget_file, 'w') as f:
            json.dump(asdict(self.budget), f, indent=2)

    def set_budget(self, limit: float, alert_threshold: float = 0.8):
        """
        Set subagent budget limit.

        Args:
            limit: Budget limit in USD
            alert_threshold: Alert when spent reaches this % (default 80%)
        """
        self.budget.limit = limit
        self.budget.alert_threshold = alert_threshold
        self._save_budget()
        logger.info(f"Subagent budget set to ${limit:.2f}")

    def record_spawn(
        self,
        subagent_id: str,
        model: str,
        description: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        duration_ms: int = 0,
        session_id: str = "",
    ) -> SubagentSpawn:
        """
        Record a subagent spawn event.

        Args:
            subagent_id: Unique ID for this subagent
            model: Model used (haiku/sonnet/opus)
            description: Description of task
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            cache_read_tokens: Cached tokens read
            cache_write_tokens: Tokens written to cache
            duration_ms: Execution duration in milliseconds
            session_id: Session ID

        Returns:
            SubagentSpawn record
        """
        # Calculate cost
        cost = estimate_subagent_cost(
            model, input_tokens, output_tokens,
            cache_read_tokens, cache_write_tokens
        )

        # Create record
        spawn = SubagentSpawn(
            timestamp=datetime.now(timezone.utc).isoformat(),
            subagent_id=subagent_id,
            model=model,
            description=description,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            duration_ms=duration_ms,
            cost=cost,
            session_id=session_id,
        )

        # Write to file
        with open(self.spawns_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(asdict(spawn)) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Update budget
        self.budget.spent += cost
        self._save_budget()

        # Check for budget alerts
        if self.budget.enabled:
            pct = (self.budget.spent / self.budget.limit) if self.budget.limit > 0 else 0
            if pct >= self.budget.alert_threshold:
                logger.warning(
                    f"⚠️ Subagent budget at {pct*100:.1f}% "
                    f"(${self.budget.spent:.2f}/${self.budget.limit:.2f})"
                )

        return spawn

    def can_spawn(self, estimated_cost: float) -> Tuple[bool, str]:
        """
        Check if a subagent can be spawned within budget.

        Args:
            estimated_cost: Estimated cost for the spawn

        Returns:
            Tuple of (can_spawn, reason)
        """
        if not self.budget.enabled:
            return True, "Budget enforcement disabled"

        total_after = self.budget.spent + estimated_cost
        if total_after > self.budget.limit:
            return False, (
                f"Budget exceeded: ${total_after:.2f} > ${self.budget.limit:.2f}"
            )

        return True, "Within budget"

    def get_history(self, days: int = 7) -> List[Dict]:
        """
        Get spawn history.

        Args:
            days: Number of days to retrieve

        Returns:
            List of spawn records
        """
        if not self.spawns_file.exists():
            return []

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        spawns = []
        with open(self.spawns_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        ts = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
                        if ts >= cutoff:
                            spawns.append(record)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        return spawns

    def get_statistics(self, days: int = 7) -> Dict:
        """
        Get statistics for subagent spawns.

        Args:
            days: Number of days for statistics

        Returns:
            Dictionary with statistics
        """
        history = self.get_history(days)

        if not history:
            return {
                "total_spawns": 0,
                "total_cost": 0.0,
                "by_model": {},
                "avg_cost": 0.0,
            }

        # Aggregate by model
        by_model = {}
        total_cost = 0.0

        for spawn in history:
            model = spawn["model"]
            if model not in by_model:
                by_model[model] = {
                    "count": 0,
                    "cost": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }

            by_model[model]["count"] += 1
            by_model[model]["cost"] += spawn.get("cost", 0.0)
            by_model[model]["input_tokens"] += spawn.get("input_tokens", 0)
            by_model[model]["output_tokens"] += spawn.get("output_tokens", 0)
            total_cost += spawn.get("cost", 0.0)

        return {
            "total_spawns": len(history),
            "total_cost": total_cost,
            "by_model": by_model,
            "avg_cost": total_cost / len(history) if history else 0.0,
            "budget_limit": self.budget.limit,
            "budget_spent": self.budget.spent,
            "budget_remaining": max(0, self.budget.limit - self.budget.spent),
        }

    def generate_report(self) -> str:
        """Generate cost report."""
        stats = self.get_statistics(days=7)

        lines = [
            "",
            "=" * 70,
            "SUBAGENT COST REPORT (Last 7 days)",
            "=" * 70,
            "",
            f"Total Spawns:       {stats['total_spawns']}",
            f"Total Cost:         ${stats['total_cost']:.4f}",
            f"Average Cost:       ${stats['avg_cost']:.4f} per spawn",
            "",
            "Budget Status:",
            f"  Limit:            ${stats['budget_limit']:.2f}",
            f"  Spent:            ${stats['budget_spent']:.2f}",
            f"  Remaining:        ${stats['budget_remaining']:.2f}",
            "",
        ]

        if stats['by_model']:
            lines.append("─" * 70)
            lines.append("BY MODEL")
            lines.append("─" * 70)
            lines.append("")

            for model, data in stats['by_model'].items():
                lines.append(f"  {model.upper()}:")
                lines.append(f"    Spawns:         {data['count']}")
                lines.append(f"    Cost:           ${data['cost']:.4f}")
                lines.append(f"    Input Tokens:   {data['input_tokens']:,}")
                lines.append(f"    Output Tokens:  {data['output_tokens']:,}")
                lines.append(f"    Avg Cost:       ${data['cost']/data['count']:.4f}")
                lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Subagent Cost Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--estimate",
        metavar="DESC",
        help="Estimate cost for a task description",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        choices=["haiku", "sonnet", "opus"],
        help="Model to use for estimation (default: sonnet)",
    )
    parser.add_argument(
        "--input-tokens",
        type=int,
        default=5000,
        help="Estimated input tokens (default: 5000)",
    )
    parser.add_argument(
        "--output-tokens",
        type=int,
        default=2000,
        help="Estimated output tokens (default: 2000)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show cost report",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show spawn history",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days of history to show (default: 7)",
    )
    parser.add_argument(
        "--set-budget",
        type=float,
        metavar="USD",
        help="Set budget limit in USD",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    tracker = SubagentCostTracker()

    # Set budget
    if args.set_budget is not None:
        tracker.set_budget(args.set_budget)
        print(f"✅ Subagent budget set to ${args.set_budget:.2f}")
        return

    # Estimate cost
    if args.estimate:
        cost = estimate_subagent_cost(
            args.model,
            args.input_tokens,
            args.output_tokens,
        )

        if args.json:
            print(json.dumps({
                "task": args.estimate,
                "model": args.model,
                "input_tokens": args.input_tokens,
                "output_tokens": args.output_tokens,
                "estimated_cost": cost,
            }, indent=2))
        else:
            print(f"\n📊 Cost Estimation")
            print(f"  Task:          {args.estimate}")
            print(f"  Model:         {args.model}")
            print(f"  Input Tokens:  {args.input_tokens:,}")
            print(f"  Output Tokens: {args.output_tokens:,}")
            print(f"  Estimated:     ${cost:.4f}\n")

            # Check budget
            can_spawn, reason = tracker.can_spawn(cost)
            if can_spawn:
                print(f"✅ {reason}")
            else:
                print(f"❌ {reason}")

    # Show report
    if args.report:
        print(tracker.generate_report())

    # Show history
    if args.history:
        history = tracker.get_history(args.days)

        if args.json:
            print(json.dumps(history, indent=2))
        else:
            print(f"\n📜 Spawn History (Last {args.days} days)\n")
            if not history:
                print("  No spawns recorded.")
            else:
                for spawn in history:
                    print(f"  [{spawn['timestamp'][:19]}] {spawn['model']:8} ${spawn['cost']:.4f} - {spawn['description'][:50]}")

    # Default: show report if no action
    if not any([args.estimate, args.report, args.history, args.set_budget]):
        print(tracker.generate_report())


if __name__ == "__main__":
    main()
