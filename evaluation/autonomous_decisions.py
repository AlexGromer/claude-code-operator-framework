#!/usr/bin/env python3
"""
Autonomous Decision Quality Tracking

TIER 3 Task 19: GAP-EVAL-AG-008 (P1 Safety)

Tracks quality of autonomous decisions made by Claude without user confirmation:
- Tool selection decisions
- Approach choices (plan vs direct, sequential vs parallel)
- Error recovery strategies (retry, fallback, escalate)
- Model routing decisions (haiku/sonnet/opus)
- File operation decisions (which files to read/edit)

Measures:
- Decision correctness (led to right outcome)
- Decision appropriateness (was it the best choice)
- Efficiency (optimal cost/time)
- User override rate (how often user corrected)
- Decision regret (decisions later reversed)

Version: 1.0.0
"""

import json
import os
import re
import sys
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Data paths
DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
DECISIONS_LOG = DATA_DIR / "autonomous_decisions.jsonl"
DECISIONS_STATS = DATA_DIR / "decision_stats.json"


class DecisionType(Enum):
    """Types of autonomous decisions."""
    TOOL_SELECTION = "tool_selection"        # Which tool to use (Read/Grep/Bash/etc.)
    APPROACH_CHOICE = "approach_choice"      # Plan vs direct, sequential vs parallel
    ERROR_RECOVERY = "error_recovery"        # Retry, fallback, escalate, abort
    MODEL_ROUTING = "model_routing"          # haiku/sonnet/opus for subagents
    FILE_OPERATION = "file_operation"        # Which files to read/edit/write
    SCOPE_DECISION = "scope_decision"        # How much work to do (minimal vs comprehensive)


class DecisionOutcome(Enum):
    """Outcome of a decision."""
    SUCCESS = "success"           # Decision led to correct result
    PARTIAL = "partial"           # Partially correct
    FAILURE = "failure"           # Decision was wrong
    OVERRIDDEN = "overridden"     # User corrected the decision
    UNKNOWN = "unknown"           # Outcome not yet determined


class RecoveryStrategy(Enum):
    """Error recovery strategies."""
    RETRY = "retry"               # Retry same approach
    FALLBACK = "fallback"         # Try alternative approach
    ESCALATE = "escalate"         # Ask user for help
    ABORT = "abort"               # Give up
    WORKAROUND = "workaround"     # Find a workaround


@dataclass
class AutonomousDecision:
    """Represents a single autonomous decision."""
    decision_id: str
    timestamp: str
    session_id: str
    decision_type: str              # DecisionType value
    description: str                # What was decided
    context: str                    # Why (what triggered the decision)
    alternatives: List[str]         # What else could have been chosen
    chosen: str                     # What was actually chosen
    outcome: str = "unknown"        # DecisionOutcome value
    outcome_reason: str = ""        # Why this outcome
    user_override: bool = False     # Was user override applied?
    override_to: str = ""           # What user changed it to
    confidence: float = 0.5         # Decision confidence (0-1)
    cost_impact: float = 0.0        # Estimated cost impact (tokens/dollars)
    latency_impact_ms: float = 0.0  # Latency impact in ms
    correctness_score: float = 0.0  # Was it correct? (0-1)
    appropriateness_score: float = 0.0  # Was it the best choice? (0-1)
    efficiency_score: float = 0.0   # Was it efficient? (0-1)
    regret: bool = False            # Was decision later reversed?
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionQualityReport:
    """Aggregate decision quality report."""
    period_start: str
    period_end: str
    total_decisions: int
    by_type: Dict[str, int]
    by_outcome: Dict[str, int]

    # Quality scores (0-100)
    avg_correctness: float
    avg_appropriateness: float
    avg_efficiency: float
    composite_quality: float        # Weighted composite

    # Override metrics
    total_overrides: int
    override_rate: float            # overrides / total (0-1)
    regret_rate: float              # regrets / total (0-1)

    # Cost metrics
    total_cost_impact: float
    avg_cost_per_decision: float

    # Top issues
    top_override_types: List[Dict[str, Any]]
    top_failure_reasons: List[Dict[str, Any]]

    # Recommendations
    recommendations: List[str]


class AutonomousDecisionTracker:
    """
    Tracks and analyzes autonomous decisions.

    Integration points:
    - PostToolUse hook → log_tool_decision()
    - session_end_hook → aggregate_session()
    - metrics_tracker → --report autonomous-decisions
    - agent_metrics → decision quality in effectiveness score
    """

    # Decision quality weights for composite score
    QUALITY_WEIGHTS = {
        "correctness": 0.45,      # Most important: was it right?
        "appropriateness": 0.30,  # Was it the best choice?
        "efficiency": 0.25        # Was it cost/time efficient?
    }

    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize decision tracker.

        Args:
            log_file: Path to decisions JSONL file
        """
        self.log_file = log_file or DECISIONS_LOG
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._decision_counter = 0

    def _generate_id(self) -> str:
        """Generate unique decision ID."""
        self._decision_counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"DEC-{ts}-{self._decision_counter:04d}"

    def log_decision(
        self,
        session_id: str,
        decision_type: DecisionType,
        description: str,
        context: str,
        chosen: str,
        alternatives: Optional[List[str]] = None,
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AutonomousDecision:
        """
        Log an autonomous decision.

        Args:
            session_id: Current session UUID
            decision_type: Type of decision
            description: What was decided
            context: Why/what triggered it
            chosen: What was actually chosen
            alternatives: What else could have been chosen
            confidence: Decision confidence (0-1)
            metadata: Additional metadata

        Returns:
            AutonomousDecision object
        """
        decision = AutonomousDecision(
            decision_id=self._generate_id(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            decision_type=decision_type.value,
            description=description,
            context=context,
            alternatives=alternatives or [],
            chosen=chosen,
            confidence=confidence,
            metadata=metadata or {}
        )

        # Append to log file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(asdict(decision)) + '\n')

        logger.info(f"Decision logged: {decision.decision_id} [{decision_type.value}] {chosen}")
        return decision

    def log_tool_decision(
        self,
        session_id: str,
        tool_name: str,
        tool_args: str = "",
        alternatives: Optional[List[str]] = None,
        context: str = "",
        confidence: float = 0.5
    ) -> AutonomousDecision:
        """
        Log a tool selection decision.

        Convenience method for the most common decision type.

        Args:
            session_id: Session UUID
            tool_name: Name of tool chosen (Read, Grep, Bash, etc.)
            tool_args: Tool arguments/parameters
            alternatives: Other tools that could have been used
            context: Why this tool was chosen
            confidence: Decision confidence

        Returns:
            AutonomousDecision object
        """
        return self.log_decision(
            session_id=session_id,
            decision_type=DecisionType.TOOL_SELECTION,
            description=f"Selected tool: {tool_name}",
            context=context or f"Tool call with args: {tool_args[:200]}",
            chosen=tool_name,
            alternatives=alternatives or self._infer_tool_alternatives(tool_name),
            confidence=confidence,
            metadata={"tool_args": tool_args[:500]}
        )

    def log_model_routing(
        self,
        session_id: str,
        chosen_model: str,
        task_description: str,
        alternatives: Optional[List[str]] = None,
        confidence: float = 0.7
    ) -> AutonomousDecision:
        """
        Log a model routing decision.

        Args:
            session_id: Session UUID
            chosen_model: Model chosen (haiku/sonnet/opus)
            task_description: What the subagent will do
            alternatives: Other models considered
            confidence: Routing confidence

        Returns:
            AutonomousDecision object
        """
        return self.log_decision(
            session_id=session_id,
            decision_type=DecisionType.MODEL_ROUTING,
            description=f"Routed to {chosen_model} for: {task_description[:100]}",
            context=f"Subagent task: {task_description[:200]}",
            chosen=chosen_model,
            alternatives=alternatives or ["haiku", "sonnet", "opus"],
            confidence=confidence,
            metadata={"task": task_description[:500]}
        )

    def log_error_recovery(
        self,
        session_id: str,
        error_type: str,
        strategy: RecoveryStrategy,
        context: str,
        alternatives: Optional[List[str]] = None,
        confidence: float = 0.5
    ) -> AutonomousDecision:
        """
        Log an error recovery decision.

        Args:
            session_id: Session UUID
            error_type: Type of error encountered
            strategy: Recovery strategy chosen
            context: Error context
            alternatives: Other strategies considered
            confidence: Strategy confidence

        Returns:
            AutonomousDecision object
        """
        return self.log_decision(
            session_id=session_id,
            decision_type=DecisionType.ERROR_RECOVERY,
            description=f"Error recovery: {strategy.value} for {error_type}",
            context=context,
            chosen=strategy.value,
            alternatives=alternatives or [s.value for s in RecoveryStrategy],
            confidence=confidence,
            metadata={"error_type": error_type}
        )

    def update_outcome(
        self,
        decision_id: str,
        outcome: DecisionOutcome,
        outcome_reason: str = "",
        correctness_score: float = 0.0,
        appropriateness_score: float = 0.0,
        efficiency_score: float = 0.0,
        user_override: bool = False,
        override_to: str = "",
        regret: bool = False,
        cost_impact: float = 0.0,
        latency_impact_ms: float = 0.0
    ) -> bool:
        """
        Update the outcome of a previously logged decision.

        Args:
            decision_id: Decision ID to update
            outcome: Decision outcome
            outcome_reason: Reason for this outcome
            correctness_score: Was it correct? (0-1)
            appropriateness_score: Was it the best choice? (0-1)
            efficiency_score: Was it efficient? (0-1)
            user_override: Was the decision overridden?
            override_to: What user changed it to
            regret: Was the decision later reversed?
            cost_impact: Cost impact (tokens or dollars)
            latency_impact_ms: Latency impact in milliseconds

        Returns:
            True if updated, False if decision not found
        """
        if not self.log_file.exists():
            return False

        lines = self.log_file.read_text().strip().split('\n')
        updated = False

        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                if data.get("decision_id") == decision_id:
                    data["outcome"] = outcome.value
                    data["outcome_reason"] = outcome_reason
                    data["correctness_score"] = correctness_score
                    data["appropriateness_score"] = appropriateness_score
                    data["efficiency_score"] = efficiency_score
                    data["user_override"] = user_override
                    data["override_to"] = override_to
                    data["regret"] = regret
                    data["cost_impact"] = cost_impact
                    data["latency_impact_ms"] = latency_impact_ms
                    lines[i] = json.dumps(data)
                    updated = True
                    break
            except json.JSONDecodeError:
                continue

        if updated:
            self.log_file.write_text('\n'.join(lines) + '\n')
            logger.info(f"Decision {decision_id} updated: {outcome.value}")

        return updated

    def load_decisions(
        self,
        session_id: Optional[str] = None,
        decision_type: Optional[DecisionType] = None,
        limit: Optional[int] = None
    ) -> List[AutonomousDecision]:
        """
        Load decisions from log file.

        Args:
            session_id: Filter by session ID
            decision_type: Filter by decision type
            limit: Maximum number of decisions to load

        Returns:
            List of AutonomousDecision objects
        """
        if not self.log_file.exists():
            return []

        decisions = []
        for line in self.log_file.read_text().strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)

                if session_id and data.get("session_id") != session_id:
                    continue
                if decision_type and data.get("decision_type") != decision_type.value:
                    continue

                decisions.append(AutonomousDecision(**data))

                if limit and len(decisions) >= limit:
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        return decisions

    def generate_report(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> DecisionQualityReport:
        """
        Generate comprehensive decision quality report.

        Args:
            session_id: Filter by session ID
            limit: Max decisions to analyze

        Returns:
            DecisionQualityReport object
        """
        decisions = self.load_decisions(session_id=session_id, limit=limit)

        if not decisions:
            return DecisionQualityReport(
                period_start="N/A",
                period_end="N/A",
                total_decisions=0,
                by_type={},
                by_outcome={},
                avg_correctness=0.0,
                avg_appropriateness=0.0,
                avg_efficiency=0.0,
                composite_quality=0.0,
                total_overrides=0,
                override_rate=0.0,
                regret_rate=0.0,
                total_cost_impact=0.0,
                avg_cost_per_decision=0.0,
                top_override_types=[],
                top_failure_reasons=[],
                recommendations=["No decisions recorded yet."]
            )

        # Time range
        timestamps = [d.timestamp for d in decisions]
        period_start = min(timestamps)
        period_end = max(timestamps)

        # Count by type
        by_type = defaultdict(int)
        for d in decisions:
            by_type[d.decision_type] += 1

        # Count by outcome
        by_outcome = defaultdict(int)
        for d in decisions:
            by_outcome[d.outcome] += 1

        # Quality scores (only for decisions with scores > 0)
        scored = [d for d in decisions if d.correctness_score > 0 or d.appropriateness_score > 0]

        if scored:
            avg_correctness = sum(d.correctness_score for d in scored) / len(scored) * 100
            avg_appropriateness = sum(d.appropriateness_score for d in scored) / len(scored) * 100
            avg_efficiency = sum(d.efficiency_score for d in scored) / len(scored) * 100
        else:
            avg_correctness = 0.0
            avg_appropriateness = 0.0
            avg_efficiency = 0.0

        # Composite quality score
        composite_quality = (
            self.QUALITY_WEIGHTS["correctness"] * avg_correctness +
            self.QUALITY_WEIGHTS["appropriateness"] * avg_appropriateness +
            self.QUALITY_WEIGHTS["efficiency"] * avg_efficiency
        )

        # Override metrics
        overrides = [d for d in decisions if d.user_override]
        total_overrides = len(overrides)
        override_rate = total_overrides / len(decisions) if decisions else 0.0

        # Regret metrics
        regrets = [d for d in decisions if d.regret]
        regret_rate = len(regrets) / len(decisions) if decisions else 0.0

        # Cost metrics
        total_cost_impact = sum(d.cost_impact for d in decisions)
        avg_cost_per_decision = total_cost_impact / len(decisions) if decisions else 0.0

        # Top override types
        override_by_type = defaultdict(int)
        for d in overrides:
            override_by_type[d.decision_type] += 1
        top_override_types = [
            {"type": k, "count": v, "rate": v / by_type.get(k, 1)}
            for k, v in sorted(override_by_type.items(), key=lambda x: -x[1])[:5]
        ]

        # Top failure reasons
        failure_reasons = defaultdict(int)
        for d in decisions:
            if d.outcome in ("failure", "overridden") and d.outcome_reason:
                failure_reasons[d.outcome_reason] += 1
        top_failure_reasons = [
            {"reason": k, "count": v}
            for k, v in sorted(failure_reasons.items(), key=lambda x: -x[1])[:5]
        ]

        # Recommendations
        recommendations = self._generate_recommendations(
            decisions, override_rate, regret_rate, avg_correctness,
            avg_appropriateness, avg_efficiency, by_type, by_outcome
        )

        return DecisionQualityReport(
            period_start=period_start,
            period_end=period_end,
            total_decisions=len(decisions),
            by_type=dict(by_type),
            by_outcome=dict(by_outcome),
            avg_correctness=round(avg_correctness, 2),
            avg_appropriateness=round(avg_appropriateness, 2),
            avg_efficiency=round(avg_efficiency, 2),
            composite_quality=round(composite_quality, 2),
            total_overrides=total_overrides,
            override_rate=round(override_rate, 4),
            regret_rate=round(regret_rate, 4),
            total_cost_impact=round(total_cost_impact, 4),
            avg_cost_per_decision=round(avg_cost_per_decision, 6),
            top_override_types=top_override_types,
            top_failure_reasons=top_failure_reasons,
            recommendations=recommendations
        )

    def _generate_recommendations(
        self,
        decisions: List[AutonomousDecision],
        override_rate: float,
        regret_rate: float,
        avg_correctness: float,
        avg_appropriateness: float,
        avg_efficiency: float,
        by_type: Dict[str, int],
        by_outcome: Dict[str, int]
    ) -> List[str]:
        """Generate actionable recommendations based on decision quality."""
        recommendations = []

        # Override rate
        if override_rate > 0.2:
            recommendations.append(
                f"HIGH override rate ({override_rate:.0%}). "
                "Consider asking user before making autonomous decisions."
            )
        elif override_rate > 0.1:
            recommendations.append(
                f"Moderate override rate ({override_rate:.0%}). "
                "Review most-overridden decision types for improvement."
            )

        # Regret rate
        if regret_rate > 0.1:
            recommendations.append(
                f"Regret rate ({regret_rate:.0%}) suggests decisions being reversed. "
                "Consider more cautious initial approach."
            )

        # Quality scores
        if avg_correctness > 0 and avg_correctness < 60:
            recommendations.append(
                f"Low correctness score ({avg_correctness:.0f}/100). "
                "Improve decision accuracy - verify assumptions before acting."
            )

        if avg_appropriateness > 0 and avg_appropriateness < 60:
            recommendations.append(
                f"Low appropriateness score ({avg_appropriateness:.0f}/100). "
                "Consider more alternatives before choosing approach."
            )

        if avg_efficiency > 0 and avg_efficiency < 60:
            recommendations.append(
                f"Low efficiency score ({avg_efficiency:.0f}/100). "
                "Optimize tool selection and minimize redundant operations."
            )

        # Decision type distribution
        total = sum(by_type.values())
        if total > 0:
            tool_pct = by_type.get("tool_selection", 0) / total
            if tool_pct > 0.8:
                recommendations.append(
                    "Most decisions are tool selections. "
                    "Track higher-level decisions (approach, scope) for better insights."
                )

        # Failure rate
        failures = by_outcome.get("failure", 0)
        if total > 0 and failures / total > 0.15:
            recommendations.append(
                f"High failure rate ({failures}/{total}). "
                "Analyze failure patterns and add fallback strategies."
            )

        if not recommendations:
            recommendations.append("Decision quality is within acceptable range.")

        return recommendations

    def _infer_tool_alternatives(self, tool_name: str) -> List[str]:
        """Infer alternative tools based on the chosen tool."""
        alternatives_map = {
            "Read": ["Grep", "Bash(cat)", "Glob"],
            "Grep": ["Read", "Bash(grep)", "Glob"],
            "Glob": ["Bash(find)", "Bash(ls)"],
            "Edit": ["Write", "Bash(sed)"],
            "Write": ["Edit", "Bash(cat)"],
            "Bash": ["Read", "Grep", "Glob", "Edit", "Write"],
            "Task": ["Bash", "Read", "Grep"],
            "WebSearch": ["WebFetch", "Bash(curl)"],
            "WebFetch": ["WebSearch", "Bash(curl)"],
        }
        return alternatives_map.get(tool_name, [])

    def analyze_session_decisions(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Analyze all decisions in a session.

        Returns structured analysis for session_end_hook integration.
        """
        decisions = self.load_decisions(session_id=session_id)

        if not decisions:
            return {
                "session_id": session_id,
                "total_decisions": 0,
                "analysis": "No decisions recorded for this session."
            }

        # Analyze patterns
        tool_choices = defaultdict(int)
        for d in decisions:
            if d.decision_type == "tool_selection":
                tool_choices[d.chosen] += 1

        overrides = [d for d in decisions if d.user_override]
        failures = [d for d in decisions if d.outcome == "failure"]

        # Calculate session quality
        scored = [d for d in decisions if d.correctness_score > 0]
        avg_quality = 0.0
        if scored:
            avg_quality = sum(
                d.correctness_score * 0.45 +
                d.appropriateness_score * 0.30 +
                d.efficiency_score * 0.25
                for d in scored
            ) / len(scored) * 100

        return {
            "session_id": session_id,
            "total_decisions": len(decisions),
            "by_type": dict(defaultdict(int, {
                d.decision_type: sum(1 for x in decisions if x.decision_type == d.decision_type)
                for d in decisions
            })),
            "tool_distribution": dict(tool_choices),
            "overrides": len(overrides),
            "override_rate": len(overrides) / len(decisions) if decisions else 0.0,
            "failures": len(failures),
            "failure_rate": len(failures) / len(decisions) if decisions else 0.0,
            "avg_decision_quality": round(avg_quality, 2),
            "top_tools": sorted(tool_choices.items(), key=lambda x: -x[1])[:5],
            "override_details": [
                {"type": o.decision_type, "chosen": o.chosen, "override_to": o.override_to}
                for o in overrides[:5]
            ]
        }

    def format_report(self, report: DecisionQualityReport) -> str:
        """Format report as human-readable text."""
        lines = []
        lines.append("=" * 70)
        lines.append("AUTONOMOUS DECISION QUALITY REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Period: {report.period_start[:10]} to {report.period_end[:10]}")
        lines.append(f"Total Decisions: {report.total_decisions}")
        lines.append("")

        # By Type
        lines.append("-" * 70)
        lines.append("BY DECISION TYPE")
        lines.append("-" * 70)
        for dtype, count in sorted(report.by_type.items(), key=lambda x: -x[1]):
            pct = count / report.total_decisions * 100 if report.total_decisions else 0
            lines.append(f"  {dtype:<25} {count:>5} ({pct:.1f}%)")
        lines.append("")

        # By Outcome
        lines.append("-" * 70)
        lines.append("BY OUTCOME")
        lines.append("-" * 70)
        outcome_icons = {
            "success": "OK", "partial": "~~", "failure": "XX",
            "overridden": "!!", "unknown": "??"
        }
        for outcome, count in sorted(report.by_outcome.items(), key=lambda x: -x[1]):
            icon = outcome_icons.get(outcome, "  ")
            pct = count / report.total_decisions * 100 if report.total_decisions else 0
            lines.append(f"  [{icon}] {outcome:<20} {count:>5} ({pct:.1f}%)")
        lines.append("")

        # Quality Scores
        lines.append("-" * 70)
        lines.append("QUALITY SCORES")
        lines.append("-" * 70)
        lines.append(f"  Correctness:      {report.avg_correctness:>6.1f}/100")
        lines.append(f"  Appropriateness:  {report.avg_appropriateness:>6.1f}/100")
        lines.append(f"  Efficiency:       {report.avg_efficiency:>6.1f}/100")
        lines.append(f"  Composite:        {report.composite_quality:>6.1f}/100")
        lines.append("")

        # Override Metrics
        lines.append("-" * 70)
        lines.append("OVERRIDE & REGRET")
        lines.append("-" * 70)
        lines.append(f"  Total Overrides:  {report.total_overrides}")
        lines.append(f"  Override Rate:    {report.override_rate:.1%}")
        lines.append(f"  Regret Rate:      {report.regret_rate:.1%}")
        lines.append("")

        if report.top_override_types:
            lines.append("  Most Overridden Types:")
            for item in report.top_override_types:
                lines.append(f"    - {item['type']}: {item['count']} ({item.get('rate', 0):.0%})")
            lines.append("")

        # Cost
        if report.total_cost_impact > 0:
            lines.append("-" * 70)
            lines.append("COST IMPACT")
            lines.append("-" * 70)
            lines.append(f"  Total Cost Impact:   ${report.total_cost_impact:.4f}")
            lines.append(f"  Avg per Decision:    ${report.avg_cost_per_decision:.6f}")
            lines.append("")

        # Top Failures
        if report.top_failure_reasons:
            lines.append("-" * 70)
            lines.append("TOP FAILURE REASONS")
            lines.append("-" * 70)
            for item in report.top_failure_reasons:
                lines.append(f"  - {item['reason']}: {item['count']}")
            lines.append("")

        # Recommendations
        lines.append("-" * 70)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 70)
        for rec in report.recommendations:
            lines.append(f"  - {rec}")
        lines.append("")
        lines.append("=" * 70)

        return '\n'.join(lines)


def run_self_test() -> bool:
    """Run self-test to verify module functionality."""
    import tempfile

    print("[SELF-TEST] Autonomous Decision Quality Tracker")
    print("-" * 50)

    tests_passed = 0
    tests_total = 0

    with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False, mode='w') as f:
        temp_path = Path(f.name)

    try:
        tracker = AutonomousDecisionTracker(log_file=temp_path)

        # Test 1: Log decision
        tests_total += 1
        d1 = tracker.log_decision(
            session_id="test-session-001",
            decision_type=DecisionType.TOOL_SELECTION,
            description="Selected Read tool",
            context="User asked to view file",
            chosen="Read",
            alternatives=["Grep", "Bash(cat)"],
            confidence=0.8
        )
        assert d1.decision_id.startswith("DEC-"), f"Bad ID: {d1.decision_id}"
        tests_passed += 1
        print(f"  [PASS] Test 1: Log decision ({d1.decision_id})")

        # Test 2: Log tool decision
        tests_total += 1
        d2 = tracker.log_tool_decision(
            session_id="test-session-001",
            tool_name="Grep",
            tool_args="pattern='def main' path=src/",
            context="Searching for function definition"
        )
        assert d2.decision_type == "tool_selection"
        tests_passed += 1
        print(f"  [PASS] Test 2: Log tool decision")

        # Test 3: Log model routing
        tests_total += 1
        d3 = tracker.log_model_routing(
            session_id="test-session-001",
            chosen_model="haiku",
            task_description="Simple file listing"
        )
        assert d3.decision_type == "model_routing"
        tests_passed += 1
        print(f"  [PASS] Test 3: Log model routing")

        # Test 4: Log error recovery
        tests_total += 1
        d4 = tracker.log_error_recovery(
            session_id="test-session-001",
            error_type="FileNotFoundError",
            strategy=RecoveryStrategy.FALLBACK,
            context="File not found, trying alternative path"
        )
        assert d4.decision_type == "error_recovery"
        tests_passed += 1
        print(f"  [PASS] Test 4: Log error recovery")

        # Test 5: Update outcome
        tests_total += 1
        result = tracker.update_outcome(
            decision_id=d1.decision_id,
            outcome=DecisionOutcome.SUCCESS,
            outcome_reason="File read successfully",
            correctness_score=0.9,
            appropriateness_score=0.8,
            efficiency_score=0.7
        )
        assert result is True
        tests_passed += 1
        print(f"  [PASS] Test 5: Update outcome")

        # Test 6: Update with override
        tests_total += 1
        tracker.update_outcome(
            decision_id=d2.decision_id,
            outcome=DecisionOutcome.OVERRIDDEN,
            outcome_reason="User preferred Read instead",
            user_override=True,
            override_to="Read",
            correctness_score=0.4,
            appropriateness_score=0.3,
            efficiency_score=0.5
        )
        tests_passed += 1
        print(f"  [PASS] Test 6: Update with override")

        # Test 7: Load decisions
        tests_total += 1
        loaded = tracker.load_decisions(session_id="test-session-001")
        assert len(loaded) == 4, f"Expected 4, got {len(loaded)}"
        tests_passed += 1
        print(f"  [PASS] Test 7: Load decisions (found {len(loaded)})")

        # Test 8: Load by type
        tests_total += 1
        tool_decisions = tracker.load_decisions(
            session_id="test-session-001",
            decision_type=DecisionType.TOOL_SELECTION
        )
        assert len(tool_decisions) == 2
        tests_passed += 1
        print(f"  [PASS] Test 8: Load by type (found {len(tool_decisions)})")

        # Test 9: Generate report
        tests_total += 1
        report = tracker.generate_report(session_id="test-session-001")
        assert report.total_decisions == 4
        assert report.total_overrides == 1
        assert report.override_rate > 0
        tests_passed += 1
        print(f"  [PASS] Test 9: Generate report (quality: {report.composite_quality:.1f}/100)")

        # Test 10: Format report
        tests_total += 1
        formatted = tracker.format_report(report)
        assert "AUTONOMOUS DECISION QUALITY REPORT" in formatted
        assert "RECOMMENDATIONS" in formatted
        tests_passed += 1
        print(f"  [PASS] Test 10: Format report ({len(formatted)} chars)")

        # Test 11: Session analysis
        tests_total += 1
        analysis = tracker.analyze_session_decisions("test-session-001")
        assert analysis["total_decisions"] == 4
        assert analysis["overrides"] == 1
        tests_passed += 1
        print(f"  [PASS] Test 11: Session analysis")

        # Test 12: Empty session
        tests_total += 1
        empty = tracker.analyze_session_decisions("nonexistent")
        assert empty["total_decisions"] == 0
        tests_passed += 1
        print(f"  [PASS] Test 12: Empty session handling")

    finally:
        temp_path.unlink(missing_ok=True)

    print("-" * 50)
    print(f"Results: {tests_passed}/{tests_total} tests passed")
    return tests_passed == tests_total


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Decision Quality Tracking"
    )
    parser.add_argument("--test", action="store_true", help="Run self-test")
    parser.add_argument("--report", action="store_true", help="Generate decision quality report")
    parser.add_argument("--session", type=str, help="Filter by session ID")
    parser.add_argument("--stats", action="store_true", help="Show decision statistics")
    parser.add_argument("--output", choices=["text", "json"], default="text")

    args = parser.parse_args()

    if args.test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    tracker = AutonomousDecisionTracker()

    if args.report or args.stats:
        report = tracker.generate_report(session_id=args.session)

        if args.output == "json":
            print(json.dumps(asdict(report), indent=2, default=str))
        else:
            print(tracker.format_report(report))

    elif args.session:
        analysis = tracker.analyze_session_decisions(args.session)
        if args.output == "json":
            print(json.dumps(analysis, indent=2, default=str))
        else:
            print(f"\nSession: {analysis['session_id']}")
            print(f"Total Decisions: {analysis['total_decisions']}")
            if analysis['total_decisions'] > 0:
                print(f"Overrides: {analysis['overrides']} ({analysis['override_rate']:.1%})")
                print(f"Failures: {analysis['failures']} ({analysis['failure_rate']:.1%})")
                print(f"Decision Quality: {analysis['avg_decision_quality']:.1f}/100")
                if analysis.get('top_tools'):
                    print(f"Top Tools: {', '.join(f'{t}({c})' for t, c in analysis['top_tools'])}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
