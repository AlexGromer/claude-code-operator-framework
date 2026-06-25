#!/usr/bin/env python3
"""
Session-Level Evaluation Module
TIER 3 Phase 4 Task 27: GAP-EVAL-AG-004

Evaluates entire SESSIONS, not individual turns:
- Multi-turn coherence scoring
- Context retention tracking
- Goal persistence across turns
- Session completion rate

Metrics targets:
- Session completion rate >85%
- Context retention >90%
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import hashlib


@dataclass
class TurnAnalysis:
    """Analysis of a single conversation turn."""
    turn_number: int
    role: str  # "user" | "assistant"
    timestamp: Optional[str] = None
    token_count: int = 0
    tool_calls: int = 0
    references_previous: bool = False  # Does this turn reference earlier context?
    introduces_goal: bool = False  # Does this turn introduce a new goal?
    completes_goal: bool = False  # Does this turn complete a goal?
    coherence_score: float = 1.0  # 0-1, how coherent with previous turn


@dataclass
class GoalTracker:
    """Tracks goals throughout a session."""
    goal_id: str
    description: str
    introduced_at_turn: int
    completed_at_turn: Optional[int] = None
    status: str = "active"  # "active" | "completed" | "abandoned" | "superseded"
    sub_goals: List[str] = field(default_factory=list)


@dataclass
class SessionEvaluation:
    """Complete evaluation of a session."""
    session_id: str
    start_time: str
    end_time: Optional[str]

    # Turn metrics
    total_turns: int
    user_turns: int
    assistant_turns: int

    # Coherence metrics
    avg_coherence_score: float  # 0-1
    coherence_drops: int  # Number of significant coherence drops
    context_retention_score: float  # 0-1, how well context is maintained

    # Goal tracking
    goals_introduced: int
    goals_completed: int
    goals_abandoned: int
    goal_completion_rate: float  # 0-1

    # Session completion
    session_status: str  # "completed" | "partial" | "abandoned" | "interrupted"
    completion_score: float  # 0-1

    # Quality indicators
    tool_efficiency: float  # 0-1
    error_rate: float  # 0-1
    user_satisfaction_indicators: Dict[str, Any] = field(default_factory=dict)

    # Composite score
    session_quality_score: float = 0.0  # 0-100


@dataclass
class SessionReport:
    """Aggregate report over multiple sessions."""
    period_start: str
    period_end: str
    total_sessions: int

    # Completion metrics
    avg_session_completion_rate: float
    sessions_completed: int
    sessions_partial: int
    sessions_abandoned: int

    # Quality metrics
    avg_coherence_score: float
    avg_context_retention: float
    avg_goal_completion_rate: float
    avg_session_quality_score: float

    # Trends
    quality_trend: str  # "improving" | "stable" | "declining"
    coherence_trend: str

    # Top issues
    common_abandonment_reasons: List[str] = field(default_factory=list)
    coherence_drop_patterns: List[str] = field(default_factory=list)


class SessionEvaluator:
    """
    Evaluates session-level quality metrics.

    TIER 3 Phase 4 Task 27 (GAP-EVAL-AG-004): Session-level evaluation

    Key metrics:
    1. Multi-turn coherence: Does the conversation flow logically?
    2. Context retention: Is important context maintained?
    3. Goal tracking: Are goals introduced, tracked, and completed?
    4. Session completion: Was the session's purpose achieved?
    """

    # Coherence thresholds
    COHERENCE_DROP_THRESHOLD = 0.3  # Drop > 0.3 is significant

    # Context retention patterns (indicate good retention)
    CONTEXT_REFERENCE_PATTERNS = [
        r'\b(as (?:I |we |you )?mentioned|earlier|above|previously|before)\b',
        r'\b(continuing|following up|based on|given that|as discussed)\b',
        r'\b(the (?:same|previous|earlier|above))\b',
        r'\b(this|that|these|those) (?:error|issue|file|function|code|task)\b',
        r'\b(still|again|also|furthermore|additionally)\b',
    ]

    # Goal introduction patterns
    GOAL_PATTERNS = [
        r'\b((?:I )?(?:want|need|would like|trying) to)\b',
        r'\b((?:can you|could you|please) (?:help|create|fix|update|add|remove))\b',
        r'\b(the (?:goal|objective|task|requirement) is)\b',
        r'\b(implement|develop|build|design|refactor|debug)\b',
    ]

    # Goal completion patterns
    COMPLETION_PATTERNS = [
        r'\b(done|completed|finished|fixed|resolved|implemented)\b',
        r'\b(successfully|works|working|passes|passing)\b',
        r'\b(that\'s (?:it|all|everything))\b',
        r'\b(thanks|thank you|perfect|great|excellent)\b',
    ]

    # Abandonment indicators
    ABANDONMENT_PATTERNS = [
        r'\b(never ?mind|forget (?:it|about)|let\'s (?:stop|skip|move on))\b',
        r'\b(too (?:complicated|difficult|complex)|doesn\'t (?:work|matter))\b',
        r'\b(I\'ll (?:do it|handle it) (?:myself|manually|later))\b',
    ]

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize session evaluator."""
        self.data_dir = data_dir or Path.home() / ".claude" / "evaluation" / "data"
        self.sessions_file = self.data_dir / "session_evaluations.jsonl"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_session(self, session_file: Path) -> SessionEvaluation:
        """
        Evaluate a complete session from its JSONL file.

        Args:
            session_file: Path to session JSONL file

        Returns:
            SessionEvaluation with all metrics
        """
        messages = self._load_session(session_file)
        if not messages:
            return self._empty_evaluation(session_file.stem)

        # Extract session metadata
        session_id = session_file.stem
        start_time = self._get_timestamp(messages[0]) or datetime.now().isoformat()
        end_time = self._get_timestamp(messages[-1]) if len(messages) > 1 else None

        # Analyze turns
        turns = self._analyze_turns(messages)

        # Calculate coherence
        coherence_score, coherence_drops = self._calculate_coherence(turns)

        # Track context retention
        context_retention = self._calculate_context_retention(messages, turns)

        # Track goals
        goals = self._track_goals(messages, turns)
        goals_completed = len([g for g in goals if g.status == "completed"])
        goals_abandoned = len([g for g in goals if g.status == "abandoned"])
        goal_completion_rate = goals_completed / len(goals) if goals else 1.0

        # Determine session status
        session_status, completion_score = self._evaluate_session_completion(
            messages, turns, goals
        )

        # Calculate tool efficiency and error rate
        tool_stats = self._analyze_tool_usage(messages)

        # User satisfaction indicators
        satisfaction = self._analyze_user_satisfaction(messages)

        # Calculate composite score
        quality_score = self._calculate_quality_score(
            coherence_score=coherence_score,
            context_retention=context_retention,
            goal_completion_rate=goal_completion_rate,
            completion_score=completion_score,
            tool_efficiency=tool_stats["efficiency"],
            error_rate=tool_stats["error_rate"],
        )

        evaluation = SessionEvaluation(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            total_turns=len(turns),
            user_turns=len([t for t in turns if t.role == "user"]),
            assistant_turns=len([t for t in turns if t.role == "assistant"]),
            avg_coherence_score=coherence_score,
            coherence_drops=coherence_drops,
            context_retention_score=context_retention,
            goals_introduced=len(goals),
            goals_completed=goals_completed,
            goals_abandoned=goals_abandoned,
            goal_completion_rate=goal_completion_rate,
            session_status=session_status,
            completion_score=completion_score,
            tool_efficiency=tool_stats["efficiency"],
            error_rate=tool_stats["error_rate"],
            user_satisfaction_indicators=satisfaction,
            session_quality_score=quality_score,
        )

        # Persist evaluation
        self._save_evaluation(evaluation)

        return evaluation

    def _load_session(self, session_file: Path) -> List[Dict[str, Any]]:
        """Load messages from session JSONL file."""
        messages = []
        try:
            with open(session_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            if msg.get("type") in ("user", "assistant"):
                                messages.append(msg)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"Error loading session: {e}")
        return messages

    def _get_timestamp(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract timestamp from message."""
        return message.get("timestamp") or message.get("created_at")

    def _analyze_turns(self, messages: List[Dict[str, Any]]) -> List[TurnAnalysis]:
        """Analyze each turn in the conversation."""
        turns = []

        for i, msg in enumerate(messages):
            role = msg.get("type", "unknown")
            content = self._extract_content(msg)

            turn = TurnAnalysis(
                turn_number=i + 1,
                role=role,
                timestamp=self._get_timestamp(msg),
                token_count=len(content.split()) * 1.3,  # Rough token estimate
                tool_calls=len(msg.get("tool_calls", [])),
                references_previous=self._check_references_previous(content),
                introduces_goal=self._check_introduces_goal(content, role),
                completes_goal=self._check_completes_goal(content),
            )

            # Calculate coherence with previous turn
            if i > 0 and turns:
                prev_content = self._extract_content(messages[i - 1])
                turn.coherence_score = self._calculate_turn_coherence(
                    prev_content, content
                )

            turns.append(turn)

        return turns

    def _extract_content(self, message: Dict[str, Any]) -> str:
        """Extract text content from message."""
        content = message.get("message", {})
        if isinstance(content, dict):
            content = content.get("content", "")
        if isinstance(content, list):
            # Handle content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = " ".join(text_parts)
        return str(content)

    def _check_references_previous(self, content: str) -> bool:
        """Check if content references previous context."""
        content_lower = content.lower()
        for pattern in self.CONTEXT_REFERENCE_PATTERNS:
            if re.search(pattern, content_lower):
                return True
        return False

    def _check_introduces_goal(self, content: str, role: str) -> bool:
        """Check if turn introduces a goal (user turns only)."""
        if role != "user":
            return False
        content_lower = content.lower()
        for pattern in self.GOAL_PATTERNS:
            if re.search(pattern, content_lower):
                return True
        return False

    def _check_completes_goal(self, content: str) -> bool:
        """Check if turn indicates goal completion."""
        content_lower = content.lower()
        for pattern in self.COMPLETION_PATTERNS:
            if re.search(pattern, content_lower):
                return True
        return False

    def _calculate_turn_coherence(self, prev_content: str, curr_content: str) -> float:
        """Calculate coherence between two turns using simple heuristics."""
        if not prev_content or not curr_content:
            return 1.0

        prev_words = set(prev_content.lower().split())
        curr_words = set(curr_content.lower().split())

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of',
                      'and', 'or', 'in', 'on', 'at', 'for', 'with', 'as', 'by'}
        prev_words -= stop_words
        curr_words -= stop_words

        if not prev_words or not curr_words:
            return 0.8  # Default for very short turns

        # Calculate Jaccard similarity
        intersection = len(prev_words & curr_words)
        union = len(prev_words | curr_words)

        base_coherence = intersection / union if union > 0 else 0.5

        # Boost for explicit references
        if self._check_references_previous(curr_content):
            base_coherence = min(1.0, base_coherence + 0.2)

        return min(1.0, base_coherence + 0.3)  # Add base coherence floor

    def _calculate_coherence(
        self, turns: List[TurnAnalysis]
    ) -> Tuple[float, int]:
        """Calculate overall coherence and count significant drops."""
        if len(turns) < 2:
            return 1.0, 0

        scores = [t.coherence_score for t in turns[1:]]
        avg_coherence = sum(scores) / len(scores) if scores else 1.0

        # Count significant drops
        drops = 0
        for i in range(1, len(scores)):
            if scores[i - 1] - scores[i] > self.COHERENCE_DROP_THRESHOLD:
                drops += 1

        return avg_coherence, drops

    def _calculate_context_retention(
        self,
        messages: List[Dict[str, Any]],
        turns: List[TurnAnalysis]
    ) -> float:
        """Calculate context retention score."""
        if len(turns) < 3:
            return 1.0  # Too short to evaluate

        # Count turns that reference previous context
        reference_count = sum(1 for t in turns if t.references_previous)

        # Expected references: roughly half of assistant turns should reference context
        assistant_turns = len([t for t in turns if t.role == "assistant"])
        expected_references = assistant_turns * 0.5

        if expected_references == 0:
            return 1.0

        retention = min(1.0, reference_count / expected_references)

        return retention

    def _track_goals(
        self,
        messages: List[Dict[str, Any]],
        turns: List[TurnAnalysis]
    ) -> List[GoalTracker]:
        """Track goals throughout the session."""
        goals = []
        active_goal: Optional[GoalTracker] = None

        for i, turn in enumerate(turns):
            content = self._extract_content(messages[i])

            if turn.introduces_goal and turn.role == "user":
                # Close previous goal if any
                if active_goal and active_goal.status == "active":
                    active_goal.status = "superseded"

                # Create new goal
                goal_id = hashlib.md5(content[:100].encode()).hexdigest()[:8]
                active_goal = GoalTracker(
                    goal_id=goal_id,
                    description=content[:200],
                    introduced_at_turn=turn.turn_number,
                )
                goals.append(active_goal)

            elif turn.completes_goal and active_goal:
                active_goal.status = "completed"
                active_goal.completed_at_turn = turn.turn_number
                active_goal = None

            elif self._check_abandonment(content) and active_goal:
                active_goal.status = "abandoned"
                active_goal = None

        # Mark remaining active goal based on session end
        if active_goal and active_goal.status == "active":
            # Check if last turn was positive
            if turns and turns[-1].completes_goal:
                active_goal.status = "completed"
                active_goal.completed_at_turn = turns[-1].turn_number
            else:
                active_goal.status = "abandoned"

        return goals

    def _check_abandonment(self, content: str) -> bool:
        """Check if content indicates goal abandonment."""
        content_lower = content.lower()
        for pattern in self.ABANDONMENT_PATTERNS:
            if re.search(pattern, content_lower):
                return True
        return False

    def _evaluate_session_completion(
        self,
        messages: List[Dict[str, Any]],
        turns: List[TurnAnalysis],
        goals: List[GoalTracker],
    ) -> Tuple[str, float]:
        """Evaluate session completion status and score."""
        if not turns:
            return "abandoned", 0.0

        # Check last few turns for completion indicators
        last_turns = turns[-3:] if len(turns) >= 3 else turns
        completion_indicators = sum(1 for t in last_turns if t.completes_goal)

        # Calculate completion score based on goals
        if goals:
            completed = len([g for g in goals if g.status == "completed"])
            completion_ratio = completed / len(goals)
        else:
            # No explicit goals, use completion indicators
            completion_ratio = min(1.0, completion_indicators / 2)

        # Determine status
        if completion_ratio >= 0.8:
            status = "completed"
        elif completion_ratio >= 0.5:
            status = "partial"
        elif len(turns) < 4:
            status = "interrupted"
        else:
            status = "abandoned"

        return status, completion_ratio

    def _analyze_tool_usage(self, messages: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze tool usage for efficiency and error rate."""
        total_calls = 0
        successful_calls = 0
        error_calls = 0

        for msg in messages:
            if msg.get("type") == "assistant":
                tool_calls = msg.get("tool_calls", [])
                total_calls += len(tool_calls)

                # Check for tool results in subsequent messages
                for tc in tool_calls:
                    # Simplified: assume success unless error pattern found
                    successful_calls += 1

            # Check for error indicators
            content = self._extract_content(msg)
            if re.search(r'\b(error|failed|exception|traceback)\b', content.lower()):
                error_calls += 1

        efficiency = successful_calls / total_calls if total_calls > 0 else 1.0
        error_rate = error_calls / max(1, len(messages))

        return {
            "efficiency": efficiency,
            "error_rate": min(1.0, error_rate),
            "total_calls": total_calls,
        }

    def _analyze_user_satisfaction(
        self, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze indicators of user satisfaction."""
        indicators = {
            "positive_feedback": 0,
            "negative_feedback": 0,
            "corrections": 0,
            "thanks": 0,
        }

        positive_patterns = [
            r'\b(thanks|thank you|great|perfect|excellent|awesome|good job)\b',
        ]
        negative_patterns = [
            r'\b(wrong|incorrect|not what I|doesn\'t work|broken|bad)\b',
        ]
        correction_patterns = [
            r'\b(no,|actually|I meant|not that|instead)\b',
        ]

        for msg in messages:
            if msg.get("type") != "user":
                continue

            content = self._extract_content(msg).lower()

            for pattern in positive_patterns:
                if re.search(pattern, content):
                    indicators["positive_feedback"] += 1
                    if "thank" in content:
                        indicators["thanks"] += 1

            for pattern in negative_patterns:
                if re.search(pattern, content):
                    indicators["negative_feedback"] += 1

            for pattern in correction_patterns:
                if re.search(pattern, content):
                    indicators["corrections"] += 1

        return indicators

    def _calculate_quality_score(
        self,
        coherence_score: float,
        context_retention: float,
        goal_completion_rate: float,
        completion_score: float,
        tool_efficiency: float,
        error_rate: float,
    ) -> float:
        """
        Calculate composite session quality score (0-100).

        Weights:
        - Goal completion: 30%
        - Coherence: 25%
        - Context retention: 20%
        - Session completion: 15%
        - Tool efficiency: 10% (reduced by error rate)
        """
        tool_score = tool_efficiency * (1 - error_rate)

        score = (
            goal_completion_rate * 30 +
            coherence_score * 25 +
            context_retention * 20 +
            completion_score * 15 +
            tool_score * 10
        )

        return round(score, 1)

    def _save_evaluation(self, evaluation: SessionEvaluation) -> None:
        """Persist evaluation to JSONL file."""
        with open(self.sessions_file, 'a') as f:
            f.write(json.dumps(asdict(evaluation)) + "\n")

    def _empty_evaluation(self, session_id: str) -> SessionEvaluation:
        """Return empty evaluation for failed loads."""
        now = datetime.now().isoformat()
        return SessionEvaluation(
            session_id=session_id,
            start_time=now,
            end_time=now,
            total_turns=0,
            user_turns=0,
            assistant_turns=0,
            avg_coherence_score=0.0,
            coherence_drops=0,
            context_retention_score=0.0,
            goals_introduced=0,
            goals_completed=0,
            goals_abandoned=0,
            goal_completion_rate=0.0,
            session_status="abandoned",
            completion_score=0.0,
            tool_efficiency=0.0,
            error_rate=1.0,
            user_satisfaction_indicators={},
            session_quality_score=0.0,
        )

    def generate_report(
        self,
        days: int = 7,
        session_dir: Optional[Path] = None,
    ) -> SessionReport:
        """
        Generate aggregate report over multiple sessions.

        Args:
            days: Number of days to include
            session_dir: Directory containing session files

        Returns:
            SessionReport with aggregate metrics
        """
        evaluations = self._load_evaluations(days)

        if not evaluations:
            now = datetime.now().isoformat()
            return SessionReport(
                period_start=now,
                period_end=now,
                total_sessions=0,
                avg_session_completion_rate=0.0,
                sessions_completed=0,
                sessions_partial=0,
                sessions_abandoned=0,
                avg_coherence_score=0.0,
                avg_context_retention=0.0,
                avg_goal_completion_rate=0.0,
                avg_session_quality_score=0.0,
                quality_trend="stable",
                coherence_trend="stable",
            )

        # Calculate aggregates
        total = len(evaluations)
        completed = len([e for e in evaluations if e["session_status"] == "completed"])
        partial = len([e for e in evaluations if e["session_status"] == "partial"])
        abandoned = len([e for e in evaluations
                        if e["session_status"] in ("abandoned", "interrupted")])

        avg_coherence = sum(e["avg_coherence_score"] for e in evaluations) / total
        avg_retention = sum(e["context_retention_score"] for e in evaluations) / total
        avg_goal_rate = sum(e["goal_completion_rate"] for e in evaluations) / total
        avg_quality = sum(e["session_quality_score"] for e in evaluations) / total

        # Calculate trends (compare first half to second half)
        mid = len(evaluations) // 2
        if mid > 0:
            first_half = evaluations[:mid]
            second_half = evaluations[mid:]

            first_quality = sum(e["session_quality_score"] for e in first_half) / len(first_half)
            second_quality = sum(e["session_quality_score"] for e in second_half) / len(second_half)

            first_coherence = sum(e["avg_coherence_score"] for e in first_half) / len(first_half)
            second_coherence = sum(e["avg_coherence_score"] for e in second_half) / len(second_half)

            quality_trend = "improving" if second_quality > first_quality + 2 else \
                           "declining" if second_quality < first_quality - 2 else "stable"
            coherence_trend = "improving" if second_coherence > first_coherence + 0.05 else \
                             "declining" if second_coherence < first_coherence - 0.05 else "stable"
        else:
            quality_trend = "stable"
            coherence_trend = "stable"

        return SessionReport(
            period_start=evaluations[0]["start_time"],
            period_end=evaluations[-1]["start_time"],
            total_sessions=total,
            avg_session_completion_rate=completed / total if total > 0 else 0.0,
            sessions_completed=completed,
            sessions_partial=partial,
            sessions_abandoned=abandoned,
            avg_coherence_score=avg_coherence,
            avg_context_retention=avg_retention,
            avg_goal_completion_rate=avg_goal_rate,
            avg_session_quality_score=avg_quality,
            quality_trend=quality_trend,
            coherence_trend=coherence_trend,
        )

    def _load_evaluations(self, days: int) -> List[Dict[str, Any]]:
        """Load evaluations from the last N days."""
        evaluations = []

        if not self.sessions_file.exists():
            return evaluations

        cutoff = datetime.now().timestamp() - (days * 24 * 3600)

        with open(self.sessions_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        eval_data = json.loads(line)
                        # Parse timestamp
                        start_time = eval_data.get("start_time", "")
                        try:
                            ts = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            if ts.timestamp() >= cutoff:
                                evaluations.append(eval_data)
                        except (ValueError, AttributeError):
                            evaluations.append(eval_data)  # Include if can't parse
                    except json.JSONDecodeError:
                        continue

        return evaluations

    def display_dashboard(self, report: SessionReport) -> str:
        """Generate dashboard display for session evaluation report."""
        lines = [
            "",
            "=" * 70,
            "SESSION EVALUATION DASHBOARD",
            "=" * 70,
            "",
            f"Period: {report.period_start[:10]} to {report.period_end[:10]}",
            f"Total Sessions: {report.total_sessions}",
            "",
            "─" * 70,
            "COMPLETION METRICS",
            "─" * 70,
            "",
            f"  Session Completion Rate: {report.avg_session_completion_rate * 100:.1f}%",
            f"    ├─ Completed:  {report.sessions_completed}",
            f"    ├─ Partial:    {report.sessions_partial}",
            f"    └─ Abandoned:  {report.sessions_abandoned}",
            "",
            "─" * 70,
            "QUALITY METRICS",
            "─" * 70,
            "",
            f"  Average Session Quality Score: {report.avg_session_quality_score:.1f}/100",
            f"  Average Coherence Score:       {report.avg_coherence_score * 100:.1f}%",
            f"  Average Context Retention:     {report.avg_context_retention * 100:.1f}%",
            f"  Average Goal Completion:       {report.avg_goal_completion_rate * 100:.1f}%",
            "",
            "─" * 70,
            "TRENDS",
            "─" * 70,
            "",
            f"  Quality Trend:   {self._trend_indicator(report.quality_trend)}",
            f"  Coherence Trend: {self._trend_indicator(report.coherence_trend)}",
            "",
            "─" * 70,
            "TARGETS",
            "─" * 70,
            "",
            f"  Session Completion Rate: {report.avg_session_completion_rate * 100:.1f}% (target: >85%)",
            f"  Context Retention:       {report.avg_context_retention * 100:.1f}% (target: >90%)",
            "",
            "=" * 70,
        ]

        return "\n".join(lines)

    def _trend_indicator(self, trend: str) -> str:
        """Convert trend to visual indicator."""
        indicators = {
            "improving": "📈 Improving",
            "stable": "➡️  Stable",
            "declining": "📉 Declining",
        }
        return indicators.get(trend, trend)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Session-Level Evaluation")
    parser.add_argument(
        "--session",
        type=Path,
        help="Evaluate a specific session file"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate aggregate report"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days to include in report (default: 7)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    evaluator = SessionEvaluator()

    if args.session:
        evaluation = evaluator.evaluate_session(args.session)
        if args.json:
            print(json.dumps(asdict(evaluation), indent=2))
        else:
            print(f"\nSession: {evaluation.session_id}")
            print(f"Status: {evaluation.session_status}")
            print(f"Quality Score: {evaluation.session_quality_score}/100")
            print(f"Coherence: {evaluation.avg_coherence_score * 100:.1f}%")
            print(f"Context Retention: {evaluation.context_retention_score * 100:.1f}%")
            print(f"Goal Completion: {evaluation.goal_completion_rate * 100:.1f}%")

    elif args.report:
        report = evaluator.generate_report(days=args.days)
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print(evaluator.display_dashboard(report))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
