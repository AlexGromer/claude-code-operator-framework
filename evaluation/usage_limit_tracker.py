#!/usr/bin/env python3
"""
Usage Limit Budget Management Module
TIER 1 Task 6: GAP-COST-SESSION-003

Tracks usage against Claude MAX subscription limits (messages per 5-hour rolling window).
Provides budget status, warnings, and projections to avoid hitting usage limits.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque


@dataclass
class MessageRecord:
    """Record of a single message in the rolling window."""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    message_number: int


class UsageLimitTracker:
    """
    Tracks usage limits for Claude MAX subscription.

    TIER 1 Task 6 (GAP-COST-SESSION-003):
    - Rolling window tracking (100 messages / 5 hours)
    - Budget status calculation
    - Warning thresholds (70%, 90%)
    - Projection at current rate
    - Time until window reset

    Target: Claude MAX subscribers (usage limits, not pay-per-token)
    Problem: Hitting message limits → blocked usage → workflow disruption
    Solution: Proactive monitoring + rate awareness + timing suggestions
    """

    # Claude MAX limits (as of 2026)
    MAX_MESSAGES_PER_WINDOW = 100  # Messages per window
    WINDOW_HOURS = 5  # Rolling window duration

    # Warning thresholds
    THRESHOLD_YELLOW = 0.70  # 70% - yellow warning
    THRESHOLD_RED = 0.90     # 90% - red warning

    # Estimated token limits (not officially documented, based on observation)
    ESTIMATED_INPUT_TOKEN_LIMIT = 10_000_000  # ~10M input tokens per window
    ESTIMATED_OUTPUT_TOKEN_LIMIT = 2_000_000  # ~2M output tokens per window

    def __init__(self, max_messages: int = MAX_MESSAGES_PER_WINDOW,
                 window_hours: int = WINDOW_HOURS,
                 metrics_file: Optional[Path] = None):
        """
        Initialize usage limit tracker.

        Args:
            max_messages: Maximum messages per window (default: 100 for Claude MAX)
            window_hours: Rolling window duration in hours (default: 5)
            metrics_file: Path to metrics.jsonl (default: ~/.claude/evaluation/data/metrics.jsonl)
        """
        if metrics_file is None:
            metrics_file = Path.home() / ".claude" / "evaluation" / "data" / "metrics.jsonl"

        self.max_messages = max_messages
        self.window_duration = timedelta(hours=window_hours)
        self.metrics_file = metrics_file

        # Rolling window storage (deque for efficient removal from both ends)
        self.messages: deque[MessageRecord] = deque()

    def parse_session_for_usage(self, session_file: Path) -> List[MessageRecord]:
        """
        Parse session JSONL file and extract message records for usage tracking.

        Args:
            session_file: Path to session JSONL file

        Returns:
            List of MessageRecord instances within rolling window
        """
        records = []
        message_number = 0

        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Process API response messages with usage data
                    if 'message' in entry and 'usage' in entry['message']:
                        usage = entry['message']['usage']
                        message_number += 1

                        # Extract token counts
                        input_fresh = usage.get('input_tokens', 0)
                        cache_creation = usage.get('cache_creation_input_tokens', 0)
                        cache_read = usage.get('cache_read_input_tokens', 0)
                        output = usage.get('output_tokens', 0)

                        # Total input = fresh + cache_creation (cache_read doesn't count toward limits)
                        total_input = input_fresh + cache_creation
                        cached = cache_read

                        # Parse timestamp
                        timestamp_str = entry.get('timestamp', datetime.now(timezone.utc).isoformat())
                        # Handle both 'Z' and '+00:00' suffixes
                        timestamp_str = timestamp_str.replace('Z', '+00:00')
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)

                        records.append(MessageRecord(
                            timestamp=timestamp,
                            input_tokens=total_input,
                            output_tokens=output,
                            cached_tokens=cached,
                            message_number=message_number
                        ))

                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # Filter to rolling window (last 5 hours from most recent message)
        if records:
            latest_time = records[-1].timestamp
            window_start = latest_time - self.window_duration
            records = [r for r in records if r.timestamp >= window_start]

        return records

    def cleanup_old_messages(self, current_time: datetime) -> None:
        """
        Remove messages outside the rolling window.

        Args:
            current_time: Current timestamp for window calculation
        """
        window_start = current_time - self.window_duration

        # Remove messages older than window start
        while self.messages and self.messages[0].timestamp < window_start:
            self.messages.popleft()

    def track_message(self, timestamp: datetime, input_tokens: int,
                     output_tokens: int, cached_tokens: int) -> None:
        """
        Add message to rolling window tracker.

        Args:
            timestamp: Message timestamp
            input_tokens: Input tokens (fresh + cache_creation)
            output_tokens: Output tokens
            cached_tokens: Cached tokens (cache_read)
        """
        # Cleanup old messages first
        self.cleanup_old_messages(timestamp)

        # Add new message
        message_number = len(self.messages) + 1
        self.messages.append(MessageRecord(
            timestamp=timestamp,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            message_number=message_number
        ))

    def calculate_reset_time(self, current_time: datetime) -> Tuple[timedelta, datetime]:
        """
        Calculate time until oldest message exits the window (window resets).

        Args:
            current_time: Current timestamp

        Returns:
            Tuple of (time_until_reset, reset_timestamp)
        """
        if not self.messages:
            return timedelta(0), current_time

        # Window resets when oldest message is 5 hours old
        oldest = self.messages[0]
        reset_time = oldest.timestamp + self.window_duration
        time_until_reset = reset_time - current_time

        if time_until_reset < timedelta(0):
            time_until_reset = timedelta(0)

        return time_until_reset, reset_time

    def calculate_message_rate(self) -> float:
        """
        Calculate current message rate (messages per hour).

        Returns:
            Messages per hour based on current window
        """
        if len(self.messages) < 2:
            return 0.0

        # Calculate time span of messages in window
        time_span = self.messages[-1].timestamp - self.messages[0].timestamp
        hours = time_span.total_seconds() / 3600

        if hours == 0:
            return 0.0

        return len(self.messages) / hours

    def project_usage(self, current_time: datetime) -> Dict[str, Any]:
        """
        Project usage at current rate until window reset.

        Args:
            current_time: Current timestamp

        Returns:
            Dictionary with projection:
            - projected_messages: Total messages by window end
            - will_exceed: Whether projected to exceed limit
            - headroom: Messages remaining before limit
        """
        time_until_reset, _ = self.calculate_reset_time(current_time)
        hours_remaining = time_until_reset.total_seconds() / 3600

        if hours_remaining <= 0:
            # Window is resetting, no projection needed
            return {
                "projected_messages": len(self.messages),
                "will_exceed": False,
                "headroom": self.max_messages - len(self.messages)
            }

        message_rate = self.calculate_message_rate()
        projected_additional = int(message_rate * hours_remaining)
        projected_total = len(self.messages) + projected_additional

        return {
            "projected_messages": projected_total,
            "will_exceed": projected_total > self.max_messages,
            "headroom": self.max_messages - projected_total,
            "message_rate": message_rate
        }

    def get_budget_status(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get current budget status with warnings and projections.

        Args:
            current_time: Current timestamp (default: now)

        Returns:
            Dictionary with budget status:
            - messages_used: Current messages in window
            - messages_limit: Maximum messages allowed
            - usage_pct: Usage percentage (0-1)
            - time_until_reset: Time until window resets
            - reset_timestamp: When window resets
            - message_rate: Current messages per hour
            - projected_messages: Projected total by window end
            - status: Budget status (healthy/warning/critical/exceeded)
            - warning_message: Warning message for user
            - total_input_tokens: Total input tokens in window
            - total_output_tokens: Total output tokens in window
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        self.cleanup_old_messages(current_time)

        messages_used = len(self.messages)
        usage_pct = messages_used / self.max_messages

        time_until_reset, reset_timestamp = self.calculate_reset_time(current_time)
        projection = self.project_usage(current_time)

        # Calculate token totals
        total_input = sum(m.input_tokens for m in self.messages)
        total_output = sum(m.output_tokens for m in self.messages)

        # Determine status and warning
        if messages_used >= self.max_messages:
            status = "exceeded"
            warning = "🔴 LIMIT REACHED: You've hit the 100 message limit. Wait for window reset."
        elif usage_pct >= self.THRESHOLD_RED:
            status = "critical"
            hours = int(time_until_reset.total_seconds() // 3600)
            minutes = int((time_until_reset.total_seconds() % 3600) // 60)
            warning = f"🔴 CRITICAL: {messages_used}/{self.max_messages} messages used (90%+). Window resets in {hours}h {minutes}m."
        elif usage_pct >= self.THRESHOLD_YELLOW:
            status = "warning"
            warning = f"⚠️ WARNING: {messages_used}/{self.max_messages} messages used (70%+). Monitor usage rate."
        elif projection["will_exceed"]:
            status = "warning"
            warning = f"⚠️ Projected to exceed limit ({projection['projected_messages']} messages). Reduce rate or wait for reset."
        else:
            status = "healthy"
            warning = f"✅ Usage healthy: {messages_used}/{self.max_messages} messages ({usage_pct:.1%}). Projected: {projection['projected_messages']} (under limit)."

        return {
            "messages_used": messages_used,
            "messages_limit": self.max_messages,
            "usage_pct": usage_pct,
            "time_until_reset": time_until_reset,
            "reset_timestamp": reset_timestamp,
            "message_rate": projection.get("message_rate", 0.0),
            "projected_messages": projection["projected_messages"],
            "headroom": projection["headroom"],
            "status": status,
            "warning_message": warning,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "window_hours": self.window_duration.total_seconds() / 3600
        }

    def display_usage_budget(self, session_file: Path) -> str:
        """
        Generate dashboard display for usage limit budget.

        Args:
            session_file: Path to session JSONL file

        Returns:
            Formatted dashboard string
        """
        # Parse session and load messages
        records = self.parse_session_for_usage(session_file)

        if not records:
            return "❌ No message records found in session file"

        # Load messages into tracker
        self.messages.clear()
        for record in records:
            self.messages.append(record)

        # Get budget status (use latest message time as current)
        current_time = records[-1].timestamp if records else datetime.now(timezone.utc)
        status = self.get_budget_status(current_time)

        # Format reset time
        hours = int(status['time_until_reset'].total_seconds() // 3600)
        minutes = int((status['time_until_reset'].total_seconds() % 3600) // 60)

        # Format reset timestamp
        reset_time_str = status['reset_timestamp'].strftime('%Y-%m-%d %H:%M UTC')

        # Token estimates
        input_pct = (status['total_input_tokens'] / self.ESTIMATED_INPUT_TOKEN_LIMIT) * 100
        output_pct = (status['total_output_tokens'] / self.ESTIMATED_OUTPUT_TOKEN_LIMIT) * 100

        dashboard = f"""
┌─ USAGE LIMITS (Claude MAX) ──────────────────────────────┐
│ Messages: {status['messages_used']}/{status['messages_limit']} ({status['usage_pct']:.1%}) in current window
│ Window resets: {hours}h {minutes}m ({reset_time_str})
│ Current rate: {status['message_rate']:.1f} msg/hour
│ Projected: {status['projected_messages']} messages {'(OVER LIMIT ⚠️)' if status['projected_messages'] > self.max_messages else '(under limit ✅)'}
│
│ TOKEN BUDGET (Estimated Limits):
│ ├─ Input tokens:  {status['total_input_tokens']:,} / ~{self.ESTIMATED_INPUT_TOKEN_LIMIT:,} ({input_pct:.1f}%)
│ ├─ Output tokens: {status['total_output_tokens']:,} / ~{self.ESTIMATED_OUTPUT_TOKEN_LIMIT:,} ({output_pct:.1f}%)
│ └─ Window: {status['window_hours']:.0f} hours rolling
│
│ STATUS: {status['status'].upper()}
│ {status['warning_message']}
└───────────────────────────────────────────────────────────┘
"""
        return dashboard

    def collect_usage_metric(self, status: Dict[str, Any]) -> None:
        """
        Collect usage limit metric and store in metrics.jsonl.

        Args:
            status: Budget status dictionary from get_budget_status()
        """
        metric_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metric_type': 'usage_limit',
            'value': status['usage_pct'],
            'metadata': {
                'messages_used': status['messages_used'],
                'messages_limit': status['messages_limit'],
                'usage_pct': status['usage_pct'],
                'message_rate': status['message_rate'],
                'projected_messages': status['projected_messages'],
                'headroom': status['headroom'],
                'status': status['status'],
                'total_input_tokens': status['total_input_tokens'],
                'total_output_tokens': status['total_output_tokens'],
                'window_hours': status['window_hours']
            }
        }

        # Append to metrics file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metric_entry) + '\n')

    def track_session(self, session_file: Path, store_metrics: bool = True) -> Dict[str, Any]:
        """
        Track usage limits and optionally store metrics.

        Args:
            session_file: Path to session JSONL file
            store_metrics: Whether to store metrics in metrics.jsonl

        Returns:
            Budget status dictionary
        """
        records = self.parse_session_for_usage(session_file)

        # Load messages into tracker
        self.messages.clear()
        for record in records:
            self.messages.append(record)

        # Get status
        current_time = records[-1].timestamp if records else datetime.now(timezone.utc)
        status = self.get_budget_status(current_time)

        if store_metrics:
            self.collect_usage_metric(status)

        return status


def main():
    """CLI entry point for usage limit tracking."""
    import argparse

    parser = argparse.ArgumentParser(description="Usage Limit Budget Management (TIER 1 Task 6)")
    parser.add_argument('session_file', type=Path, help="Path to session JSONL file")
    parser.add_argument('--dashboard', action='store_true', help="Show dashboard display")
    parser.add_argument('--store', action='store_true', help="Store metrics in metrics.jsonl")
    parser.add_argument('--stats', action='store_true', help="Show detailed statistics")
    parser.add_argument('--max-messages', type=int, default=100, help="Max messages per window (default: 100)")
    parser.add_argument('--window-hours', type=int, default=5, help="Window duration in hours (default: 5)")

    args = parser.parse_args()

    if not args.session_file.exists():
        print(f"❌ Session file not found: {args.session_file}")
        return

    tracker = UsageLimitTracker(
        max_messages=args.max_messages,
        window_hours=args.window_hours
    )

    if args.dashboard:
        print(tracker.display_usage_budget(args.session_file))

    if args.stats or not args.dashboard:
        status = tracker.track_session(args.session_file, store_metrics=args.store)

        print(f"\n📊 Usage Limit Statistics\n")
        print(f"Messages Used: {status['messages_used']} / {status['messages_limit']} ({status['usage_pct']:.2%})")
        print(f"Message Rate: {status['message_rate']:.1f} msg/hour")
        print(f"Projected Messages: {status['projected_messages']}")
        print(f"Headroom: {status['headroom']} messages")

        hours = int(status['time_until_reset'].total_seconds() // 3600)
        minutes = int((status['time_until_reset'].total_seconds() % 3600) // 60)
        print(f"Time Until Reset: {hours}h {minutes}m")

        print(f"Total Input Tokens: {status['total_input_tokens']:,}")
        print(f"Total Output Tokens: {status['total_output_tokens']:,}")
        print(f"Status: {status['status'].upper()}")
        print(f"\n{status['warning_message']}")

        if args.store:
            print(f"\n✅ Metrics stored to: {tracker.metrics_file}")


if __name__ == "__main__":
    main()
