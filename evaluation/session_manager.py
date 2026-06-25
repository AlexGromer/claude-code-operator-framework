#!/usr/bin/env python3
"""
Session Manager - Auto Reopening Strategy
TIER 2B Task 17: GAP-COST-SESSION-002

Automatically suggests/triggers session reopening when context grows too large.
Implements three phases: Manual warnings, Semi-auto prompts, Full auto-reopen.

Target: Claude MAX users with usage limits
ROI: -7.9% token usage via strategic session reopening
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from session_token_tracker import SessionTokenTracker, SessionMetrics
except ImportError:
    SessionTokenTracker = None
    SessionMetrics = None


@dataclass
class ReopeningTrigger:
    """Represents a condition that triggered reopening recommendation."""
    condition: str
    current_value: Any
    threshold: Any
    severity: str  # warning, critical
    message: str


class SessionManager:
    """
    Manages session lifecycle and reopening strategy.

    TIER 2B Task 17 (GAP-COST-SESSION-002): Auto session reopening strategy
    - Phase 1 (Manual): Dashboard warning + user decision
    - Phase 2 (Semi-auto): Prompt user when threshold reached
    - Phase 3 (Full auto): Auto-reopen with context preservation

    Trigger conditions (any of):
    - Every 50 requests
    - History size > 20k tokens
    - Input tokens > 850k (85% of 1M context window)
    - Session duration > 8 hours
    """

    # Thresholds for reopening triggers
    REQUESTS_THRESHOLD = 50  # Every N requests
    HISTORY_THRESHOLD = 20000  # 20k tokens conversation history
    CONTEXT_UTILIZATION_THRESHOLD = 0.85  # 85% of 1M context window
    SESSION_DURATION_HOURS = 8  # 8 hours

    # Context window size (Claude)
    MAX_CONTEXT_TOKENS = 1_000_000  # 1M tokens

    def __init__(self,
                 session_file: Optional[Path] = None,
                 metrics_file: Optional[Path] = None,
                 auto_mode: bool = False):
        """
        Initialize session manager.

        Args:
            session_file: Path to current session JSONL
            metrics_file: Path to metrics.jsonl
            auto_mode: If True, enable full auto-reopening (Phase 3)
        """
        self.session_file = session_file
        self.metrics_file = metrics_file
        self.auto_mode = auto_mode

        # Initialize token tracker
        if SessionTokenTracker:
            self.tracker = SessionTokenTracker(metrics_file=metrics_file)
        else:
            self.tracker = None

    def get_current_session_file(self) -> Optional[Path]:
        """
        Find current session JSONL file if not specified.

        Returns:
            Path to session file or None if not found
        """
        if self.session_file:
            return self.session_file

        # Try to detect current session from working directory
        cwd = Path.cwd()

        # Encode project path (same way Claude Code does)
        encoded = str(cwd).replace('/', '-').replace('_', '-')

        # Find project directory
        projects_dir = Path.home() / ".claude" / "projects"

        if not projects_dir.exists():
            return None

        project_dirs = [d for d in projects_dir.iterdir() if d.is_dir() and encoded in d.name]

        if not project_dirs:
            return None

        project_dir = project_dirs[0]

        # Find most recent session file
        session_files = sorted(project_dir.glob('*.jsonl'),
                              key=lambda f: f.stat().st_mtime,
                              reverse=True)

        return session_files[0] if session_files else None

    def check_reopening_triggers(self, session_file: Optional[Path] = None) -> List[ReopeningTrigger]:
        """
        Check if any reopening conditions are met.

        Args:
            session_file: Path to session JSONL (optional, auto-detected if None)

        Returns:
            List of triggered conditions (empty if no triggers)
        """
        triggers = []

        # Auto-detect session file if not provided
        if session_file is None:
            session_file = self.get_current_session_file()

        if not session_file or not session_file.exists():
            return triggers

        # Parse session for metrics
        if not self.tracker:
            return triggers

        try:
            metrics = self.tracker.parse_session_file(session_file)
        except Exception as e:
            print(f"Error parsing session: {e}", file=sys.stderr)
            return triggers

        if not metrics:
            return triggers

        last_metric = metrics[-1]
        total_requests = len(metrics)

        # Get session metadata
        session_start, session_duration_hours = self._get_session_duration(session_file)

        # Trigger 1: Request count threshold
        if total_requests >= self.REQUESTS_THRESHOLD:
            if total_requests % self.REQUESTS_THRESHOLD == 0:  # Every N requests
                triggers.append(ReopeningTrigger(
                    condition="request_count",
                    current_value=total_requests,
                    threshold=self.REQUESTS_THRESHOLD,
                    severity="warning",
                    message=f"Session has {total_requests} requests (threshold: {self.REQUESTS_THRESHOLD})"
                ))

        # Trigger 2: History size threshold
        if last_metric.history_tokens >= self.HISTORY_THRESHOLD:
            severity = "critical" if last_metric.history_tokens >= 40000 else "warning"
            triggers.append(ReopeningTrigger(
                condition="history_size",
                current_value=last_metric.history_tokens,
                threshold=self.HISTORY_THRESHOLD,
                severity=severity,
                message=f"Conversation history: {last_metric.history_tokens:,} tokens (threshold: {self.HISTORY_THRESHOLD:,})"
            ))

        # Trigger 3: Context utilization threshold
        context_utilization = last_metric.input_tokens_total / self.MAX_CONTEXT_TOKENS
        if context_utilization >= self.CONTEXT_UTILIZATION_THRESHOLD:
            triggers.append(ReopeningTrigger(
                condition="context_utilization",
                current_value=context_utilization,
                threshold=self.CONTEXT_UTILIZATION_THRESHOLD,
                severity="critical",
                message=f"Context utilization: {context_utilization:.1%} (threshold: {self.CONTEXT_UTILIZATION_THRESHOLD:.0%})"
            ))

        # Trigger 4: Session duration threshold
        if session_duration_hours >= self.SESSION_DURATION_HOURS:
            triggers.append(ReopeningTrigger(
                condition="session_duration",
                current_value=session_duration_hours,
                threshold=self.SESSION_DURATION_HOURS,
                severity="warning",
                message=f"Session duration: {session_duration_hours:.1f} hours (threshold: {self.SESSION_DURATION_HOURS}h)"
            ))

        return triggers

    def _get_session_duration(self, session_file: Path) -> Tuple[Optional[datetime], float]:
        """
        Calculate session duration from first to last message.

        Args:
            session_file: Path to session JSONL

        Returns:
            Tuple of (session_start_time, duration_in_hours)
        """
        try:
            with open(session_file, 'r') as f:
                lines = f.readlines()

            if not lines:
                return None, 0.0

            # Parse first and last timestamps
            first_entry = json.loads(lines[0])
            last_entry = json.loads(lines[-1])

            first_ts = first_entry.get('timestamp')
            last_ts = last_entry.get('timestamp')

            if not first_ts or not last_ts:
                return None, 0.0

            # Parse timestamps (ISO 8601 format)
            first_dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
            last_dt = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))

            duration = (last_dt - first_dt).total_seconds() / 3600  # hours

            return first_dt, duration

        except Exception as e:
            print(f"Error calculating session duration: {e}", file=sys.stderr)
            return None, 0.0

    def generate_reopening_recommendation(self,
                                          triggers: List[ReopeningTrigger],
                                          session_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Generate reopening recommendation based on triggers.

        Args:
            triggers: List of triggered conditions
            session_file: Path to session JSONL

        Returns:
            Dictionary with recommendation details:
            - should_reopen: bool
            - severity: warning/critical
            - triggers: list of trigger details
            - recommendation_text: formatted message
            - context_summary: what to preserve
        """
        if not triggers:
            return {
                "should_reopen": False,
                "severity": "healthy",
                "triggers": [],
                "recommendation_text": "✅ Session healthy - Continue working",
                "context_summary": None
            }

        # Determine severity (critical if any trigger is critical)
        severity = "critical" if any(t.severity == "critical" for t in triggers) else "warning"

        # Generate recommendation text
        if severity == "critical":
            icon = "🔴"
            action = "REOPEN SESSION NOW"
        else:
            icon = "⚠️"
            action = "Consider reopening session"

        recommendation_lines = [
            f"{icon} {action}",
            "",
            "Triggered conditions:"
        ]

        for trigger in triggers:
            recommendation_lines.append(f"  • {trigger.message}")

        recommendation_lines.extend([
            "",
            "Benefits of reopening:",
            "  • Reset conversation history (reduce token usage)",
            "  • Improve response latency",
            "  • Optimize cache utilization",
            "",
            "To reopen:",
            "  1. Type 'exit' to close current session",
            "  2. Start new session (wrapper auto-generates continuity summary)",
            "  3. Paste summary if needed for context"
        ])

        recommendation_text = "\n".join(recommendation_lines)

        # Generate context summary (what to preserve)
        context_summary = self._generate_context_summary(session_file) if session_file else None

        return {
            "should_reopen": True,
            "severity": severity,
            "triggers": [asdict(t) for t in triggers],
            "recommendation_text": recommendation_text,
            "context_summary": context_summary
        }

    def _generate_context_summary(self, session_file: Path) -> Optional[str]:
        """
        Generate context preservation summary (what to keep from current session).

        Args:
            session_file: Path to session JSONL

        Returns:
            Formatted summary text or None
        """
        try:
            with open(session_file, 'r') as f:
                lines = f.readlines()

            # Analyze last N messages for context
            recent_messages = lines[-20:] if len(lines) > 20 else lines

            # Extract key context (simplified - can be enhanced)
            summary_lines = [
                "# Session Continuity Summary",
                "",
                f"**Session:** {session_file.stem}",
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"**Messages:** {len(lines)}",
                "",
                "## Active Context",
                "",
                "Recent work:",
                "- Last 20 messages contain current task context",
                "- Review conversation for critical decisions",
                "- Code changes and file references preserved in new session",
                "",
                "## Recommendation",
                "",
                "Copy this summary to new session if you need context continuity.",
                "Otherwise, start fresh for optimal performance."
            ]

            return "\n".join(summary_lines)

        except Exception as e:
            print(f"Error generating context summary: {e}", file=sys.stderr)
            return None

    def display_dashboard(self, session_file: Optional[Path] = None) -> str:
        """
        Generate and return formatted dashboard.

        Args:
            session_file: Path to session JSONL (optional, auto-detected)

        Returns:
            Formatted dashboard string
        """
        # Auto-detect session file
        if session_file is None:
            session_file = self.get_current_session_file()

        if not session_file or not session_file.exists():
            return "❌ Session file not found"

        # Check triggers
        triggers = self.check_reopening_triggers(session_file)

        # Generate recommendation
        recommendation = self.generate_reopening_recommendation(triggers, session_file)

        # Get session stats
        if self.tracker:
            try:
                metrics = self.tracker.parse_session_file(session_file)
                stats = self.tracker.calculate_session_stats(metrics)

                # Check if stats has error
                if "error" in stats:
                    return f"❌ {stats['error']}"

            except Exception as e:
                return f"❌ Error calculating stats: {e}"
        else:
            return "❌ SessionTokenTracker not available"

        # Format dashboard
        dashboard_lines = [
            "=" * 70,
            "SESSION REOPENING DASHBOARD",
            "=" * 70,
            "",
            f"Session ID: {stats['session_id']}",
            f"Total Requests: {stats['total_requests']}",
            f"History Size: {stats['current_history']:,} tokens",
            f"Cache Efficiency: {stats['avg_efficiency']:.1%}",
            f"History Growth Rate: {stats['history_growth_rate']:.1f} tokens/request",
            "",
            "─" * 70,
            recommendation['recommendation_text'],
            "─" * 70,
        ]

        # Add context summary if critical
        if recommendation['severity'] == 'critical' and recommendation['context_summary']:
            dashboard_lines.extend([
                "",
                "CONTEXT PRESERVATION SUMMARY:",
                "",
                recommendation['context_summary']
            ])

        dashboard_lines.append("=" * 70)

        return "\n".join(dashboard_lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Session Manager - Auto Reopening Strategy")
    parser.add_argument('--session-file', type=Path, help="Path to session JSONL file")
    parser.add_argument('--check', action='store_true', help="Check reopening triggers")
    parser.add_argument('--dashboard', action='store_true', help="Display reopening dashboard")
    parser.add_argument('--auto', action='store_true', help="Enable auto-reopening mode (Phase 3)")

    args = parser.parse_args()

    # Initialize manager
    manager = SessionManager(
        session_file=args.session_file,
        auto_mode=args.auto
    )

    if args.check:
        # Check triggers
        triggers = manager.check_reopening_triggers(args.session_file)

        if not triggers:
            print("✅ No reopening triggers detected")
            sys.exit(0)

        print(f"⚠️ {len(triggers)} reopening trigger(s) detected:")
        for trigger in triggers:
            print(f"  • [{trigger.severity.upper()}] {trigger.message}")

        sys.exit(1 if any(t.severity == 'critical' for t in triggers) else 0)

    elif args.dashboard:
        # Display dashboard
        dashboard = manager.display_dashboard(args.session_file)
        print(dashboard)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
