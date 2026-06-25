#!/usr/bin/env python3
"""
Auto Session Reopening Strategy — GAP-COST-SESSION-002

Features:
- Monitor context window usage indicators
- Recommend session reopen based on thresholds
- Generate continuity summary for new session
- Integration with session_health_check.py

Usage:
    python3 session_reopen_advisor.py --check
    python3 session_reopen_advisor.py --recommend
    python3 session_reopen_advisor.py --generate-summary
    python3 session_reopen_advisor.py --auto

Version: 1.0.0
"""

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Thresholds for session reopening
THRESHOLDS = {
    "token_count": 180000,  # 90% of 200k limit
    "cache_efficiency": 85.0,  # Below this % efficiency
    "response_latency": 5.0,  # Above this seconds
    "request_count": 100,  # After this many requests
    "history_accumulation": 20000,  # Tokens of history
}


@dataclass
class SessionHealth:
    """Session health status."""
    token_count: int
    cache_efficiency: float
    response_latency: float
    request_count: int
    history_tokens: int
    recommendation: str
    reasons: List[str]
    urgency: str  # low, medium, high, critical


def check_session_health(
    token_count: int,
    cache_efficiency: float,
    response_latency: float,
    request_count: int = 0,
    history_tokens: int = 0,
) -> Dict:
    """
    Check session health and recommend action.

    Args:
        token_count: Current token count
        cache_efficiency: Cache hit rate (0-100)
        response_latency: Average response time in seconds
        request_count: Number of requests in session
        history_tokens: Estimated history accumulation

    Returns:
        Dictionary with health status and recommendation
    """
    reasons = []
    urgency = "low"
    recommendation = "healthy"

    # Check token count
    if token_count >= THRESHOLDS["token_count"]:
        reasons.append(f"Token count high: {token_count:,} >= {THRESHOLDS['token_count']:,}")
        urgency = "critical"
        recommendation = "reopen"

    # Check cache efficiency
    if cache_efficiency < THRESHOLDS["cache_efficiency"]:
        reasons.append(f"Cache efficiency low: {cache_efficiency:.1f}% < {THRESHOLDS['cache_efficiency']:.1f}%")
        if urgency == "low":
            urgency = "medium"
        if recommendation == "healthy":
            recommendation = "reopen"

    # Check response latency
    if response_latency > THRESHOLDS["response_latency"]:
        reasons.append(f"High latency: {response_latency:.2f}s > {THRESHOLDS['response_latency']:.2f}s")
        if urgency == "low":
            urgency = "medium"
        if recommendation == "healthy":
            recommendation = "consider"

    # Check request count
    if request_count > THRESHOLDS["request_count"]:
        reasons.append(f"Many requests: {request_count} > {THRESHOLDS['request_count']}")
        if urgency == "low":
            urgency = "medium"

    # Check history accumulation
    if history_tokens > THRESHOLDS["history_accumulation"]:
        reasons.append(f"High history: {history_tokens:,} tokens")
        if urgency in ("low", "medium"):
            urgency = "high"
        if recommendation == "healthy":
            recommendation = "reopen"

    return {
        "token_count": token_count,
        "cache_efficiency": cache_efficiency,
        "response_latency": response_latency,
        "request_count": request_count,
        "history_tokens": history_tokens,
        "recommendation": recommendation,
        "reasons": reasons,
        "urgency": urgency,
    }


class SessionReopenAdvisor:
    """
    Advisor for session reopening strategy.

    Features:
    - Health monitoring
    - Continuity summary generation
    - Automatic recommendations
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize advisor."""
        self.data_dir = data_dir or Path.home() / ".claude" / "evaluation" / "data"
        self.summaries_dir = self.data_dir / "summaries" / "session"

        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def generate_summary(
        self,
        active_tasks: List[str],
        modified_files: List[str],
        pending_decisions: List[str],
        key_context: str,
        session_id: str = "",
    ) -> str:
        """
        Generate continuity summary for session transition.

        Args:
            active_tasks: List of active tasks
            modified_files: List of files modified
            pending_decisions: Pending decisions
            key_context: Key context to preserve
            session_id: Session ID

        Returns:
            Markdown summary
        """
        lines = [
            "# Session Continuity Summary",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Session ID:** {session_id or 'unknown'}",
            "",
            "## Active Tasks",
            "",
        ]

        if active_tasks:
            for i, task in enumerate(active_tasks, 1):
                lines.append(f"{i}. {task}")
        else:
            lines.append("*No active tasks*")

        lines.extend([
            "",
            "## Modified Files",
            "",
        ])

        if modified_files:
            for file in modified_files:
                lines.append(f"- `{file}`")
        else:
            lines.append("*No files modified*")

        lines.extend([
            "",
            "## Pending Decisions",
            "",
        ])

        if pending_decisions:
            for decision in pending_decisions:
                lines.append(f"- {decision}")
        else:
            lines.append("*No pending decisions*")

        lines.extend([
            "",
            "## Key Context",
            "",
            key_context or "*No additional context*",
            "",
            "---",
            "",
            "## Recovery Instructions",
            "",
            "To continue work in a new session:",
            "",
            "1. Start new Claude session",
            "2. In first message, paste: \"Continue from this summary: <paste above>\"",
            "3. Claude will restore context and continue work",
            "",
        ])

        return "\n".join(lines)

    def save_summary(
        self,
        summary: str,
        session_id: str,
        project_name: str = "",
    ) -> Path:
        """
        Save continuity summary to file.

        Args:
            summary: Summary markdown
            session_id: Session ID
            project_name: Optional project name

        Returns:
            Path to saved file
        """
        # Create project directory
        if project_name:
            summary_dir = self.summaries_dir / project_name
        else:
            summary_dir = self.summaries_dir

        summary_dir.mkdir(parents=True, exist_ok=True)

        # Save with timestamp and session ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{session_id[:8]}.md"
        summary_file = summary_dir / filename

        with open(summary_file, 'w') as f:
            f.write(summary)

        logger.info(f"Summary saved: {summary_file}")
        return summary_file

    def get_latest_summary(self, project_name: str = "") -> Optional[Path]:
        """
        Get latest continuity summary.

        Args:
            project_name: Optional project name

        Returns:
            Path to latest summary or None
        """
        if project_name:
            summary_dir = self.summaries_dir / project_name
        else:
            summary_dir = self.summaries_dir

        if not summary_dir.exists():
            return None

        summaries = list(summary_dir.glob("*.md"))
        if not summaries:
            return None

        return max(summaries, key=lambda p: p.stat().st_mtime)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Session Reopen Advisor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current session health",
    )
    parser.add_argument(
        "--recommend",
        action="store_true",
        help="Get reopening recommendation",
    )
    parser.add_argument(
        "--generate-summary",
        action="store_true",
        help="Generate continuity summary",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatic check and generate summary if needed",
    )

    # Health check parameters
    parser.add_argument(
        "--token-count",
        type=int,
        default=0,
        help="Current token count",
    )
    parser.add_argument(
        "--cache-efficiency",
        type=float,
        default=100.0,
        help="Cache efficiency percentage",
    )
    parser.add_argument(
        "--response-latency",
        type=float,
        default=1.0,
        help="Average response latency in seconds",
    )
    parser.add_argument(
        "--request-count",
        type=int,
        default=0,
        help="Number of requests in session",
    )
    parser.add_argument(
        "--history-tokens",
        type=int,
        default=0,
        help="Estimated history tokens",
    )

    # Summary parameters
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=[],
        help="Active tasks",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=[],
        help="Modified files",
    )
    parser.add_argument(
        "--decisions",
        nargs="+",
        default=[],
        help="Pending decisions",
    )
    parser.add_argument(
        "--context",
        default="",
        help="Key context to preserve",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Session ID",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    advisor = SessionReopenAdvisor()

    # Check health
    if args.check or args.recommend or args.auto:
        health = check_session_health(
            token_count=args.token_count,
            cache_efficiency=args.cache_efficiency,
            response_latency=args.response_latency,
            request_count=args.request_count,
            history_tokens=args.history_tokens,
        )

        if args.json:
            print(json.dumps(health, indent=2))
        else:
            print("\n📊 Session Health Check\n")
            print(f"  Token Count:       {health['token_count']:,}")
            print(f"  Cache Efficiency:  {health['cache_efficiency']:.1f}%")
            print(f"  Response Latency:  {health['response_latency']:.2f}s")
            print(f"  Request Count:     {health['request_count']}")
            print(f"  History Tokens:    {health['history_tokens']:,}")
            print()

            # Show recommendation
            urgency_icon = {
                "low": "✅",
                "medium": "🟡",
                "high": "🟠",
                "critical": "🔴",
            }.get(health['urgency'], "?")

            recommendation_text = {
                "healthy": "Session is healthy",
                "consider": "Consider reopening",
                "reopen": "Reopen recommended",
            }.get(health['recommendation'], "Unknown")

            print(f"  {urgency_icon} {recommendation_text.upper()}")

            if health['reasons']:
                print()
                print("  Reasons:")
                for reason in health['reasons']:
                    print(f"    - {reason}")

            print()

        # Auto-generate summary if needed
        if args.auto and health['recommendation'] == 'reopen':
            print("🔄 Generating continuity summary...\n")
            summary = advisor.generate_summary(
                active_tasks=args.tasks or ["Continue current work"],
                modified_files=args.files,
                pending_decisions=args.decisions,
                key_context=args.context or "Session context from previous work",
                session_id=args.session_id,
            )

            summary_file = advisor.save_summary(
                summary,
                args.session_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
            )

            print(f"📄 Summary saved: {summary_file}")
            print()
            print("Preview:")
            print("─" * 70)
            print(summary[:500])
            if len(summary) > 500:
                print("...")
            print()

    # Generate summary
    if args.generate_summary and not args.auto:
        summary = advisor.generate_summary(
            active_tasks=args.tasks or [],
            modified_files=args.files or [],
            pending_decisions=args.decisions or [],
            key_context=args.context or "",
            session_id=args.session_id,
        )

        if args.json:
            print(json.dumps({"summary": summary}, indent=2))
        else:
            print(summary)

    # Default: show check
    if not any([args.check, args.recommend, args.generate_summary, args.auto]):
        health = check_session_health(
            token_count=args.token_count,
            cache_efficiency=args.cache_efficiency,
            response_latency=args.response_latency,
            request_count=args.request_count,
            history_tokens=args.history_tokens,
        )
        print(json.dumps(health, indent=2))


if __name__ == "__main__":
    main()
