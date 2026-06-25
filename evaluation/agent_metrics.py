#!/usr/bin/env python3
"""
Agent-Level Quality Metrics
TIER 2C Task 20: GAP-EVAL-AG-001

Measures WHOLE AGENT performance, not just LLM accuracy:
- Task completion rate
- Tool efficiency
- Error recovery quality
- Agent effectiveness score (0-100)

Distinction: LLM accuracy ≠ agent effectiveness.
Agent can use LLM perfectly but still fail tasks due to tool errors,
planning mistakes, or context mismanagement.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict


@dataclass
class TaskOutcome:
    """Represents outcome of a single task."""
    task_id: str
    timestamp: str
    session_id: str
    status: str  # "completed" | "partial" | "failed" | "abandoned"
    quality_score: Optional[float] = None  # 1-5 scale
    completion_pct: float = 0.0  # 0-100%
    tool_calls_total: int = 0
    tool_calls_successful: int = 0
    tool_calls_redundant: int = 0
    errors_total: int = 0
    errors_recovered: int = 0
    user_corrections: int = 0  # Number of times user corrected agent
    duration_seconds: Optional[float] = None


@dataclass
class SessionQuality:
    """Aggregate quality metrics for a session."""
    session_id: str
    timestamp: str
    tasks_attempted: int
    tasks_completed: int
    tasks_partial: int
    tasks_failed: int
    avg_quality_score: float  # Average of task quality scores
    avg_completion_pct: float  # Average completion percentage
    tool_efficiency: float  # 1 - (redundant_calls / total_calls)
    error_recovery_rate: float  # recovered / total
    agent_effectiveness_score: float  # Composite score (0-100)


@dataclass
class AgentReport:
    """Comprehensive agent quality report."""
    period_start: str
    period_end: str
    total_sessions: int
    total_tasks: int

    # Task completion metrics
    task_completion_rate: float  # completed / attempted
    task_partial_rate: float  # partial / attempted
    task_failure_rate: float  # failed / attempted

    # Quality metrics
    avg_quality_score: float  # 1-5 scale
    avg_completion_pct: float  # 0-100%

    # Tool efficiency metrics
    avg_tool_efficiency: float  # 0-100%
    avg_redundant_ratio: float  # redundant / total

    # Error handling metrics
    avg_error_recovery_rate: float  # 0-100%
    total_errors: int
    total_recoveries: int

    # User intervention
    avg_user_corrections_per_task: float
    user_override_rate: float  # tasks with corrections / total

    # Agent effectiveness
    agent_effectiveness_score: float  # Composite (0-100)

    # Breakdown by status
    by_status: Dict[str, int]


class AgentMetrics:
    """
    Tracks and analyzes agent-level quality metrics.

    TIER 2C Task 20 (GAP-EVAL-AG-001): Agent-level quality metrics
    - Measures WHOLE AGENT performance (not just LLM)
    - Tracks task completion, tool efficiency, error recovery
    - Provides composite effectiveness score
    """

    def __init__(self, metrics_file: Optional[Path] = None):
        """
        Initialize agent metrics tracker.

        Args:
            metrics_file: Path to agent metrics JSONL file
        """
        if metrics_file is None:
            metrics_file = Path.home() / ".claude" / "evaluation" / "data" / "agent_metrics.jsonl"

        self.metrics_file = metrics_file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def track_task(
        self,
        task_id: str,
        session_id: str,
        status: str,
        quality_score: Optional[float] = None,
        completion_pct: float = 0.0,
        tool_calls_total: int = 0,
        tool_calls_successful: int = 0,
        tool_calls_redundant: int = 0,
        errors_total: int = 0,
        errors_recovered: int = 0,
        user_corrections: int = 0,
        duration_seconds: Optional[float] = None
    ) -> TaskOutcome:
        """
        Track outcome of a single task.

        Args:
            task_id: Task identifier
            session_id: Session UUID
            status: "completed" | "partial" | "failed" | "abandoned"
            quality_score: Quality rating (1-5)
            completion_pct: Percentage completed (0-100)
            tool_calls_total: Total tool calls made
            tool_calls_successful: Successful tool calls
            tool_calls_redundant: Redundant tool calls
            errors_total: Total errors encountered
            errors_recovered: Errors successfully recovered from
            user_corrections: Number of user corrections
            duration_seconds: Task duration in seconds

        Returns:
            TaskOutcome object
        """
        outcome = TaskOutcome(
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            status=status,
            quality_score=quality_score,
            completion_pct=completion_pct,
            tool_calls_total=tool_calls_total,
            tool_calls_successful=tool_calls_successful,
            tool_calls_redundant=tool_calls_redundant,
            errors_total=errors_total,
            errors_recovered=errors_recovered,
            user_corrections=user_corrections,
            duration_seconds=duration_seconds
        )

        # Append to metrics file
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(asdict(outcome)) + '\n')

        return outcome

    def track_subagent(
        self,
        agent_type: str,
        model: str,
        description: str,
        success: bool,
        session_id: str = "unknown",
        complexity_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track a subagent (Task tool) execution.

        Simplified method for hook integration - records subagent calls.

        Args:
            agent_type: Type of subagent (Explore, Plan, Bash, general-purpose)
            model: Model used (haiku, sonnet, opus)
            description: Task description
            success: Whether task succeeded
            session_id: Session UUID
            complexity_score: Estimated complexity (0-10)
            metadata: Optional additional metadata

        Returns:
            Dict with recorded data
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "subagent",
            "agent_type": agent_type,
            "model": model,
            "description": description[:100],
            "success": success,
            "session_id": session_id,
            "complexity_score": complexity_score,
            "metadata": metadata or {}
        }

        # Write to dedicated subagent file
        subagent_file = self.metrics_file.parent / "agent_task_metrics.jsonl"
        with open(subagent_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        return entry

    def load_outcomes(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[TaskOutcome]:
        """
        Load task outcomes from file.

        Args:
            session_id: Filter by session ID (optional)
            limit: Maximum number of outcomes to load (optional)

        Returns:
            List of TaskOutcome objects
        """
        if not self.metrics_file.exists():
            return []

        outcomes = []
        with open(self.metrics_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)

                    # Filter by session if specified
                    if session_id and data.get('session_id') != session_id:
                        continue

                    outcomes.append(TaskOutcome(**data))

                    if limit and len(outcomes) >= limit:
                        break

                except (json.JSONDecodeError, TypeError):
                    continue

        return outcomes

    def calculate_agent_effectiveness(
        self,
        task_completion_rate: float,
        tool_efficiency: float,
        error_recovery_rate: float,
        avg_quality_score: float
    ) -> float:
        """
        Calculate composite agent effectiveness score.

        Formula:
        - 40% task completion rate
        - 25% tool efficiency
        - 20% error recovery rate
        - 15% quality score (normalized to 0-100)

        Args:
            task_completion_rate: Percentage (0-100)
            tool_efficiency: Percentage (0-100)
            error_recovery_rate: Percentage (0-100)
            avg_quality_score: Average quality (1-5 scale)

        Returns:
            Effectiveness score (0-100)
        """
        # Normalize quality score to 0-100
        quality_normalized = ((avg_quality_score - 1) / 4) * 100 if avg_quality_score > 0 else 0

        effectiveness = (
            0.40 * task_completion_rate +
            0.25 * tool_efficiency +
            0.20 * error_recovery_rate +
            0.15 * quality_normalized
        )

        return round(effectiveness, 2)

    def generate_session_quality(
        self,
        session_id: str
    ) -> Optional[SessionQuality]:
        """
        Generate quality metrics for a single session.

        Args:
            session_id: Session UUID

        Returns:
            SessionQuality object (None if no data)
        """
        outcomes = self.load_outcomes(session_id=session_id)

        if not outcomes:
            return None

        # Count by status
        tasks_completed = sum(1 for o in outcomes if o.status == "completed")
        tasks_partial = sum(1 for o in outcomes if o.status == "partial")
        tasks_failed = sum(1 for o in outcomes if o.status in ["failed", "abandoned"])
        tasks_attempted = len(outcomes)

        # Calculate averages
        quality_scores = [o.quality_score for o in outcomes if o.quality_score is not None]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        completion_pcts = [o.completion_pct for o in outcomes]
        avg_completion_pct = sum(completion_pcts) / len(completion_pcts) if completion_pcts else 0.0

        # Tool efficiency
        total_tool_calls = sum(o.tool_calls_total for o in outcomes)
        redundant_tool_calls = sum(o.tool_calls_redundant for o in outcomes)
        tool_efficiency = (1 - (redundant_tool_calls / total_tool_calls)) * 100 if total_tool_calls > 0 else 100.0

        # Error recovery
        total_errors = sum(o.errors_total for o in outcomes)
        total_recoveries = sum(o.errors_recovered for o in outcomes)
        error_recovery_rate = (total_recoveries / total_errors) * 100 if total_errors > 0 else 100.0

        # Agent effectiveness
        task_completion_rate = (tasks_completed / tasks_attempted) * 100 if tasks_attempted > 0 else 0.0

        agent_effectiveness_score = self.calculate_agent_effectiveness(
            task_completion_rate=task_completion_rate,
            tool_efficiency=tool_efficiency,
            error_recovery_rate=error_recovery_rate,
            avg_quality_score=avg_quality_score
        )

        return SessionQuality(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tasks_attempted=tasks_attempted,
            tasks_completed=tasks_completed,
            tasks_partial=tasks_partial,
            tasks_failed=tasks_failed,
            avg_quality_score=avg_quality_score,
            avg_completion_pct=avg_completion_pct,
            tool_efficiency=tool_efficiency,
            error_recovery_rate=error_recovery_rate,
            agent_effectiveness_score=agent_effectiveness_score
        )

    def generate_report(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> AgentReport:
        """
        Generate comprehensive agent quality report.

        Args:
            session_id: Filter by session ID (optional)
            limit: Maximum number of outcomes to analyze (optional)

        Returns:
            AgentReport object
        """
        outcomes = self.load_outcomes(session_id=session_id, limit=limit)

        if not outcomes:
            # Empty report
            return AgentReport(
                period_start="N/A",
                period_end="N/A",
                total_sessions=0,
                total_tasks=0,
                task_completion_rate=0.0,
                task_partial_rate=0.0,
                task_failure_rate=0.0,
                avg_quality_score=0.0,
                avg_completion_pct=0.0,
                avg_tool_efficiency=0.0,
                avg_redundant_ratio=0.0,
                avg_error_recovery_rate=0.0,
                total_errors=0,
                total_recoveries=0,
                avg_user_corrections_per_task=0.0,
                user_override_rate=0.0,
                agent_effectiveness_score=0.0,
                by_status={}
            )

        # Extract timestamps
        period_start = outcomes[0].timestamp
        period_end = outcomes[-1].timestamp

        # Count sessions
        unique_sessions = len(set(o.session_id for o in outcomes))
        total_tasks = len(outcomes)

        # Count by status
        by_status = defaultdict(int)
        for outcome in outcomes:
            by_status[outcome.status] += 1

        tasks_completed = by_status.get("completed", 0)
        tasks_partial = by_status.get("partial", 0)
        tasks_failed = by_status.get("failed", 0) + by_status.get("abandoned", 0)

        # Task completion rates
        task_completion_rate = (tasks_completed / total_tasks) * 100 if total_tasks > 0 else 0.0
        task_partial_rate = (tasks_partial / total_tasks) * 100 if total_tasks > 0 else 0.0
        task_failure_rate = (tasks_failed / total_tasks) * 100 if total_tasks > 0 else 0.0

        # Quality metrics
        quality_scores = [o.quality_score for o in outcomes if o.quality_score is not None]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        completion_pcts = [o.completion_pct for o in outcomes]
        avg_completion_pct = sum(completion_pcts) / len(completion_pcts) if completion_pcts else 0.0

        # Tool efficiency
        total_tool_calls = sum(o.tool_calls_total for o in outcomes)
        redundant_tool_calls = sum(o.tool_calls_redundant for o in outcomes)
        avg_redundant_ratio = (redundant_tool_calls / total_tool_calls) if total_tool_calls > 0 else 0.0
        avg_tool_efficiency = (1 - avg_redundant_ratio) * 100

        # Error handling
        total_errors = sum(o.errors_total for o in outcomes)
        total_recoveries = sum(o.errors_recovered for o in outcomes)
        avg_error_recovery_rate = (total_recoveries / total_errors) * 100 if total_errors > 0 else 100.0

        # User intervention
        total_user_corrections = sum(o.user_corrections for o in outcomes)
        avg_user_corrections_per_task = total_user_corrections / total_tasks if total_tasks > 0 else 0.0
        tasks_with_corrections = sum(1 for o in outcomes if o.user_corrections > 0)
        user_override_rate = (tasks_with_corrections / total_tasks) * 100 if total_tasks > 0 else 0.0

        # Agent effectiveness
        agent_effectiveness_score = self.calculate_agent_effectiveness(
            task_completion_rate=task_completion_rate,
            tool_efficiency=avg_tool_efficiency,
            error_recovery_rate=avg_error_recovery_rate,
            avg_quality_score=avg_quality_score
        )

        return AgentReport(
            period_start=period_start,
            period_end=period_end,
            total_sessions=unique_sessions,
            total_tasks=total_tasks,
            task_completion_rate=task_completion_rate,
            task_partial_rate=task_partial_rate,
            task_failure_rate=task_failure_rate,
            avg_quality_score=avg_quality_score,
            avg_completion_pct=avg_completion_pct,
            avg_tool_efficiency=avg_tool_efficiency,
            avg_redundant_ratio=avg_redundant_ratio * 100,
            avg_error_recovery_rate=avg_error_recovery_rate,
            total_errors=total_errors,
            total_recoveries=total_recoveries,
            avg_user_corrections_per_task=avg_user_corrections_per_task,
            user_override_rate=user_override_rate,
            agent_effectiveness_score=agent_effectiveness_score,
            by_status=dict(by_status)
        )

    def format_report(self, report: AgentReport) -> str:
        """
        Format agent quality report for display.

        Args:
            report: AgentReport object

        Returns:
            Formatted string
        """
        lines = []

        lines.append("=" * 70)
        lines.append("AGENT QUALITY REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Period info
        lines.append(f"Period: {report.period_start[:19]} → {report.period_end[:19]}")
        lines.append(f"Sessions: {report.total_sessions}")
        lines.append(f"Tasks: {report.total_tasks}")
        lines.append("")

        # Task completion
        lines.append("📊 Task Completion:")
        lines.append(f"  • Completed: {report.task_completion_rate:.1f}% ({report.by_status.get('completed', 0)} tasks)")
        lines.append(f"  • Partial: {report.task_partial_rate:.1f}% ({report.by_status.get('partial', 0)} tasks)")
        lines.append(f"  • Failed: {report.task_failure_rate:.1f}% ({report.by_status.get('failed', 0) + report.by_status.get('abandoned', 0)} tasks)")
        lines.append("")

        # Quality
        lines.append("⭐ Quality Metrics:")
        lines.append(f"  • Avg Quality Score: {report.avg_quality_score:.2f}/5.0")
        lines.append(f"  • Avg Completion: {report.avg_completion_pct:.1f}%")
        lines.append("")

        # Tool efficiency
        lines.append("🔧 Tool Efficiency:")
        lines.append(f"  • Tool Efficiency: {report.avg_tool_efficiency:.1f}%")
        lines.append(f"  • Redundant Calls: {report.avg_redundant_ratio:.1f}%")
        lines.append("")

        # Error handling
        lines.append("🛡️  Error Recovery:")
        lines.append(f"  • Recovery Rate: {report.avg_error_recovery_rate:.1f}%")
        lines.append(f"  • Total Errors: {report.total_errors}")
        lines.append(f"  • Recovered: {report.total_recoveries}")
        lines.append("")

        # User intervention
        lines.append("👤 User Intervention:")
        lines.append(f"  • Avg Corrections per Task: {report.avg_user_corrections_per_task:.2f}")
        lines.append(f"  • Override Rate: {report.user_override_rate:.1f}%")
        lines.append("")

        # Agent effectiveness
        lines.append(f"🎯 AGENT EFFECTIVENESS SCORE: {report.agent_effectiveness_score:.1f}/100")
        lines.append("")
        lines.append("  Formula: 40% completion + 25% tool efficiency +")
        lines.append("           20% error recovery + 15% quality")
        lines.append("")

        # Grade
        if report.agent_effectiveness_score >= 90:
            grade = "🏆 EXCELLENT"
        elif report.agent_effectiveness_score >= 80:
            grade = "✅ GOOD"
        elif report.agent_effectiveness_score >= 70:
            grade = "⚠️  ACCEPTABLE"
        elif report.agent_effectiveness_score >= 60:
            grade = "🔴 NEEDS IMPROVEMENT"
        else:
            grade = "❌ POOR"

        lines.append(f"  Grade: {grade}")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Quality Metrics")
    parser.add_argument('--session-id', type=str, help="Filter by session ID")
    parser.add_argument('--limit', type=int, help="Limit number of outcomes to analyze")
    parser.add_argument('--report', action='store_true', help="Generate agent quality report")
    parser.add_argument('--test', action='store_true', help="Run test suite")

    args = parser.parse_args()

    metrics = AgentMetrics()

    if args.test:
        # Test suite
        print("=" * 70)
        print("AGENT METRICS TEST SUITE")
        print("=" * 70)
        print()

        # Test 1: Track sample tasks
        print("Test 1: Track sample tasks")

        test_session = "test-session-agent-001"

        # Simulate 10 tasks with varying outcomes
        tasks = [
            # Completed tasks
            ("task-1", "completed", 4.5, 100, 10, 10, 0, 0, 0, 0),
            ("task-2", "completed", 4.0, 100, 8, 8, 0, 1, 1, 0),
            ("task-3", "completed", 5.0, 100, 12, 12, 0, 0, 0, 0),
            ("task-4", "completed", 4.2, 100, 15, 14, 1, 2, 2, 0),
            ("task-5", "completed", 4.8, 100, 6, 6, 0, 0, 0, 0),

            # Partial tasks
            ("task-6", "partial", 3.5, 70, 20, 18, 2, 3, 2, 1),
            ("task-7", "partial", 3.0, 60, 25, 20, 5, 4, 3, 2),

            # Failed tasks
            ("task-8", "failed", 2.0, 30, 15, 10, 3, 5, 2, 1),
            ("task-9", "abandoned", 1.5, 20, 8, 5, 1, 3, 0, 0),
            ("task-10", "completed", 4.5, 100, 10, 10, 0, 1, 1, 0),
        ]

        for task_data in tasks:
            metrics.track_task(
                task_id=task_data[0],
                session_id=test_session,
                status=task_data[1],
                quality_score=task_data[2],
                completion_pct=task_data[3],
                tool_calls_total=task_data[4],
                tool_calls_successful=task_data[5],
                tool_calls_redundant=task_data[6],
                errors_total=task_data[7],
                errors_recovered=task_data[8],
                user_corrections=task_data[9]
            )

        print(f"✅ Tracked 10 sample tasks for session {test_session}")
        print()

        # Test 2: Generate session quality
        print("Test 2: Generate session quality")
        session_quality = metrics.generate_session_quality(test_session)
        if session_quality:
            print(f"  Tasks Attempted: {session_quality.tasks_attempted}")
            print(f"  Tasks Completed: {session_quality.tasks_completed}")
            print(f"  Agent Effectiveness: {session_quality.agent_effectiveness_score:.1f}/100")
            print("✅ PASS")
        else:
            print("❌ FAIL: No session quality data")
        print()

        # Test 3: Generate report
        print("Test 3: Generate full report")
        report = metrics.generate_report(session_id=test_session)
        print(metrics.format_report(report))

        # Test 4: Verify calculations
        print("Test 4: Verify calculations")
        assert report.total_tasks == 10, "Should have 10 tasks"
        assert report.task_completion_rate == 60.0, "Should have 60% completion rate (6/10)"
        assert report.agent_effectiveness_score > 0, "Effectiveness score should be > 0"
        print("✅ PASS")
        print()

        print("=" * 70)
        print("All tests passed!")

    elif args.report:
        # Generate report
        report = metrics.generate_report(
            session_id=args.session_id,
            limit=args.limit
        )
        print(metrics.format_report(report))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
