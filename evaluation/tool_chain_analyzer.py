#!/usr/bin/env python3
"""
Tool Chain Effectiveness Analyzer
TIER 3 Phase 4 Task 26: GAP-EVAL-AG-003

Analyzes tool usage patterns to identify inefficiencies:
- Tool sequence analysis (order, dependencies)
- Redundancy detection (repeated calls with same args)
- Optimal path comparison (actual vs ideal)
- Efficiency scoring (0-100)

Target Metrics:
- Tool calls redundancy ratio: <10%
- Tool sequence efficiency: >80%

Usage:
    python3 tool_chain_analyzer.py --session SESSION.jsonl --report
    python3 tool_chain_analyzer.py --analyze-pattern "file search"
    python3 tool_chain_analyzer.py --report weekly

Version: 1.0.0
"""

import argparse
import json
import hashlib
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set


@dataclass
class ToolCall:
    """Represents a single tool call."""
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: str
    sequence_number: int
    duration_ms: Optional[float] = None
    success: bool = True
    result_hash: Optional[str] = None  # Hash of result for duplicate detection

    def args_hash(self) -> str:
        """Generate hash of arguments for comparison."""
        args_str = json.dumps(self.arguments, sort_keys=True)
        return hashlib.md5(args_str.encode()).hexdigest()[:16]


@dataclass
class ToolSequence:
    """Represents a sequence of tool calls for a task."""
    task_id: str
    session_id: str
    calls: List[ToolCall]
    start_time: str
    end_time: Optional[str] = None

    @property
    def total_calls(self) -> int:
        return len(self.calls)

    @property
    def unique_tools(self) -> Set[str]:
        return {c.tool_name for c in self.calls}

    def tool_pattern(self) -> str:
        """Generate tool call pattern signature."""
        return " -> ".join(c.tool_name for c in self.calls)


@dataclass
class RedundantCall:
    """Represents a detected redundant tool call."""
    tool_name: str
    first_occurrence: int  # Sequence number
    redundant_occurrence: int  # Sequence number
    arguments_hash: str
    reason: str  # "same_args" | "same_result" | "no_effect"


@dataclass
class ToolChainAnalysis:
    """Complete analysis of a tool sequence."""
    task_id: str
    session_id: str
    timestamp: str

    # Basic metrics
    total_calls: int
    unique_tools: int
    unique_patterns: int

    # Redundancy analysis
    redundant_calls: int
    redundancy_ratio: float  # redundant / total (target: <10%)
    redundant_details: List[RedundantCall]

    # Efficiency metrics
    efficiency_score: float  # 0-100 composite
    sequence_efficiency: float  # optimal_calls / actual_calls
    tool_diversity: float  # unique_tools / total_calls (higher = more diverse)

    # Pattern analysis
    tool_pattern: str
    common_pattern_match: Optional[str] = None  # If matches known optimal pattern
    suggested_improvements: List[str] = field(default_factory=list)


@dataclass
class ToolChainReport:
    """Aggregate report across multiple sessions."""
    period_start: str
    period_end: str
    total_sessions: int
    total_sequences: int
    total_tool_calls: int

    # Redundancy metrics
    avg_redundancy_ratio: float
    max_redundancy_ratio: float
    total_redundant_calls: int

    # Efficiency metrics
    avg_efficiency_score: float
    min_efficiency_score: float

    # Tool usage distribution
    tool_frequency: Dict[str, int]
    common_patterns: Dict[str, int]

    # Recommendations
    top_inefficiencies: List[str]
    improvement_opportunities: List[str]


class ToolChainAnalyzer:
    """
    Analyzes tool chain effectiveness for Claude Code sessions.

    TIER 3 Phase 4 Task 26 (GAP-EVAL-AG-003):
    - Tool sequence analysis
    - Redundancy detection
    - Optimal path comparison
    - Efficiency scoring

    Target: <10% redundancy ratio, >80% efficiency score
    """

    # Known optimal patterns for common tasks
    OPTIMAL_PATTERNS = {
        "file_read": ["Read"],
        "file_search": ["Glob", "Read"],
        "content_search": ["Grep", "Read"],
        "file_edit": ["Read", "Edit"],
        "file_create": ["Write"],
        "code_search": ["Glob", "Grep", "Read"],
        "git_status": ["Bash"],
        "git_commit": ["Bash", "Bash"],  # status + commit
        "explore_codebase": ["Task"],  # Use Explore subagent
    }

    # Tools that are commonly used redundantly
    REDUNDANCY_PRONE_TOOLS = {
        "Read": "Reading same file multiple times",
        "Glob": "Searching for same pattern repeatedly",
        "Grep": "Searching same content repeatedly",
        "Bash": "Running same command multiple times",
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize tool chain analyzer.

        Args:
            data_dir: Directory for storing analysis data
        """
        if data_dir is None:
            data_dir = Path.home() / ".claude" / "evaluation" / "data"

        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.analysis_file = self.data_dir / "tool_chain_analysis.jsonl"

    def parse_session(self, session_file: Path) -> List[ToolSequence]:
        """
        Parse tool calls from session JSONL file.

        Args:
            session_file: Path to session transcript

        Returns:
            List of tool sequences (one per detected task)
        """
        if not session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")

        sequences = []
        current_calls = []
        session_id = session_file.stem
        sequence_number = 0
        task_id = "task_0"
        task_counter = 0

        with open(session_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Detect task boundaries (user messages)
                    if entry.get('type') == 'input':
                        # Save previous sequence if exists
                        if current_calls:
                            sequences.append(ToolSequence(
                                task_id=task_id,
                                session_id=session_id,
                                calls=current_calls,
                                start_time=current_calls[0].timestamp if current_calls else "",
                                end_time=current_calls[-1].timestamp if current_calls else None
                            ))

                        # Start new task
                        task_counter += 1
                        task_id = f"task_{task_counter}"
                        current_calls = []
                        sequence_number = 0

                    # Extract tool calls
                    if entry.get('type') == 'tool_use':
                        tool_name = entry.get('tool_name', entry.get('name', 'Unknown'))
                        arguments = entry.get('arguments', entry.get('input', {}))
                        timestamp = entry.get('timestamp', datetime.now(timezone.utc).isoformat())

                        # Create ToolCall
                        call = ToolCall(
                            tool_name=tool_name,
                            arguments=arguments if isinstance(arguments, dict) else {},
                            timestamp=timestamp,
                            sequence_number=sequence_number,
                            success=True  # Default, updated by result
                        )

                        current_calls.append(call)
                        sequence_number += 1

                    # Check for tool results
                    if entry.get('type') == 'tool_result':
                        if current_calls:
                            # Hash result for duplicate detection
                            result_text = str(entry.get('result', ''))[:1000]
                            current_calls[-1].result_hash = hashlib.md5(
                                result_text.encode()
                            ).hexdigest()[:16]

                            # Check for errors
                            if entry.get('error') or 'error' in result_text.lower()[:100]:
                                current_calls[-1].success = False

                except json.JSONDecodeError:
                    continue

        # Save final sequence
        if current_calls:
            sequences.append(ToolSequence(
                task_id=task_id,
                session_id=session_id,
                calls=current_calls,
                start_time=current_calls[0].timestamp if current_calls else "",
                end_time=current_calls[-1].timestamp if current_calls else None
            ))

        return sequences

    def detect_redundancy(self, sequence: ToolSequence) -> List[RedundantCall]:
        """
        Detect redundant tool calls in a sequence.

        Redundancy types:
        - same_args: Same tool with identical arguments
        - same_result: Same tool producing identical result
        - no_effect: Tool call that doesn't change state

        Args:
            sequence: Tool sequence to analyze

        Returns:
            List of detected redundant calls
        """
        redundant = []

        # Track calls by tool + args hash
        seen_calls: Dict[str, int] = {}  # key: "tool:args_hash", value: first seq num

        # Track results for same_result detection
        seen_results: Dict[str, int] = {}  # key: "tool:result_hash", value: first seq num

        for call in sequence.calls:
            # Check for same_args redundancy
            call_key = f"{call.tool_name}:{call.args_hash()}"

            if call_key in seen_calls:
                redundant.append(RedundantCall(
                    tool_name=call.tool_name,
                    first_occurrence=seen_calls[call_key],
                    redundant_occurrence=call.sequence_number,
                    arguments_hash=call.args_hash(),
                    reason="same_args"
                ))
            else:
                seen_calls[call_key] = call.sequence_number

            # Check for same_result redundancy (if result available)
            if call.result_hash:
                result_key = f"{call.tool_name}:{call.result_hash}"

                if result_key in seen_results and call_key not in seen_calls:
                    # Same result but different args - potentially redundant
                    redundant.append(RedundantCall(
                        tool_name=call.tool_name,
                        first_occurrence=seen_results[result_key],
                        redundant_occurrence=call.sequence_number,
                        arguments_hash=call.args_hash(),
                        reason="same_result"
                    ))
                else:
                    seen_results[result_key] = call.sequence_number

            # Check for no_effect patterns
            if self._is_no_effect_call(call, sequence.calls):
                # Already counted in same_args check
                pass

        return redundant

    def _is_no_effect_call(self, call: ToolCall, all_calls: List[ToolCall]) -> bool:
        """
        Check if call has no effect (e.g., reading unchanged file).

        Args:
            call: Tool call to check
            all_calls: All calls in sequence

        Returns:
            True if call has no effect
        """
        # Read after Read (no Write/Edit in between)
        if call.tool_name == "Read":
            file_path = call.arguments.get("file_path", "")

            # Find previous Read of same file
            for prev_call in all_calls:
                if prev_call.sequence_number >= call.sequence_number:
                    break

                if (prev_call.tool_name == "Read" and
                    prev_call.arguments.get("file_path") == file_path):

                    # Check if file was modified in between
                    modified = False
                    for between in all_calls:
                        if between.sequence_number <= prev_call.sequence_number:
                            continue
                        if between.sequence_number >= call.sequence_number:
                            break

                        if between.tool_name in ("Edit", "Write"):
                            if between.arguments.get("file_path") == file_path:
                                modified = True
                                break

                    if not modified:
                        return True

        return False

    def calculate_efficiency(
        self,
        sequence: ToolSequence,
        redundant_calls: List[RedundantCall]
    ) -> Tuple[float, float, float]:
        """
        Calculate efficiency metrics for a tool sequence.

        Returns:
            Tuple of (efficiency_score, sequence_efficiency, tool_diversity)
        """
        if not sequence.calls:
            return 100.0, 1.0, 1.0

        total = sequence.total_calls
        redundant_count = len(redundant_calls)
        unique_count = len(sequence.unique_tools)

        # Sequence efficiency: (total - redundant) / total
        sequence_efficiency = (total - redundant_count) / total if total > 0 else 1.0

        # Tool diversity: unique tools / total calls (normalized)
        # Perfect is ~0.3-0.7 (some reuse is expected)
        raw_diversity = unique_count / total if total > 0 else 1.0
        tool_diversity = min(raw_diversity * 2, 1.0)  # Normalize

        # Composite efficiency score (0-100)
        # Weights: 60% redundancy, 30% diversity, 10% pattern match
        redundancy_score = (1 - (redundant_count / total)) * 100 if total > 0 else 100
        diversity_score = tool_diversity * 100

        efficiency_score = (
            redundancy_score * 0.6 +
            diversity_score * 0.3 +
            10  # Base score for completing task
        )

        return min(efficiency_score, 100.0), sequence_efficiency, tool_diversity

    def suggest_improvements(
        self,
        sequence: ToolSequence,
        redundant_calls: List[RedundantCall]
    ) -> List[str]:
        """
        Generate improvement suggestions for tool usage.

        Args:
            sequence: Tool sequence analyzed
            redundant_calls: Detected redundant calls

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Redundancy-based suggestions
        redundant_by_tool = defaultdict(list)
        for r in redundant_calls:
            redundant_by_tool[r.tool_name].append(r)

        for tool, calls in redundant_by_tool.items():
            if len(calls) >= 2:
                if tool == "Read":
                    suggestions.append(
                        f"Consider caching file contents: '{tool}' called {len(calls)+1} times "
                        f"with same arguments"
                    )
                elif tool == "Glob" or tool == "Grep":
                    suggestions.append(
                        f"Consider combining searches: '{tool}' repeated {len(calls)+1} times"
                    )
                elif tool == "Bash":
                    suggestions.append(
                        f"Consider batching commands: '{tool}' repeated {len(calls)+1} times"
                    )
                else:
                    suggestions.append(
                        f"Redundant '{tool}' calls detected: {len(calls)} unnecessary calls"
                    )

        # Pattern-based suggestions
        pattern = sequence.tool_pattern()

        # Detect suboptimal patterns
        if "Glob -> Glob" in pattern:
            suggestions.append("Multiple Glob calls - consider using more specific patterns")

        if "Read -> Read -> Read" in pattern:
            suggestions.append("Sequential file reads - consider batch reading or caching")

        if "Bash -> Bash -> Bash -> Bash" in pattern:
            suggestions.append("Many Bash calls - consider chaining commands with &&")

        # Tool-specific suggestions
        if sequence.total_calls > 20 and "Task" not in sequence.unique_tools:
            suggestions.append(
                "Complex operation (>20 tool calls) - consider using Task tool "
                "with Explore subagent for codebase searches"
            )

        return suggestions

    def analyze_sequence(self, sequence: ToolSequence) -> ToolChainAnalysis:
        """
        Perform complete analysis of a tool sequence.

        Args:
            sequence: Tool sequence to analyze

        Returns:
            Complete analysis with metrics and suggestions
        """
        # Detect redundancy
        redundant_calls = self.detect_redundancy(sequence)

        # Calculate efficiency
        efficiency_score, sequence_efficiency, tool_diversity = self.calculate_efficiency(
            sequence, redundant_calls
        )

        # Generate suggestions
        suggestions = self.suggest_improvements(sequence, redundant_calls)

        # Check for pattern match
        pattern = sequence.tool_pattern()
        pattern_match = None
        for name, optimal in self.OPTIMAL_PATTERNS.items():
            if pattern.replace(" -> ", ",").split(",") == optimal:
                pattern_match = name
                break

        analysis = ToolChainAnalysis(
            task_id=sequence.task_id,
            session_id=sequence.session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_calls=sequence.total_calls,
            unique_tools=len(sequence.unique_tools),
            unique_patterns=1,  # Single sequence
            redundant_calls=len(redundant_calls),
            redundancy_ratio=len(redundant_calls) / sequence.total_calls if sequence.total_calls > 0 else 0,
            redundant_details=redundant_calls,
            efficiency_score=efficiency_score,
            sequence_efficiency=sequence_efficiency,
            tool_diversity=tool_diversity,
            tool_pattern=pattern,
            common_pattern_match=pattern_match,
            suggested_improvements=suggestions
        )

        # Persist analysis
        self._save_analysis(analysis)

        return analysis

    def _save_analysis(self, analysis: ToolChainAnalysis):
        """Save analysis to JSONL file."""
        with open(self.analysis_file, 'a') as f:
            # Convert dataclass to dict, handling nested dataclasses
            data = asdict(analysis)
            f.write(json.dumps(data) + "\n")

    def generate_report(
        self,
        period_days: int = 7,
        session_files: Optional[List[Path]] = None
    ) -> ToolChainReport:
        """
        Generate aggregate report across sessions.

        Args:
            period_days: Number of days to include
            session_files: Specific files to analyze (optional)

        Returns:
            Aggregate report
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)

        # Collect all analyses
        analyses = []

        if self.analysis_file.exists():
            with open(self.analysis_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        timestamp = datetime.fromisoformat(
                            data.get('timestamp', '').replace('Z', '+00:00')
                        )
                        if timestamp >= period_start:
                            analyses.append(data)
                    except (json.JSONDecodeError, ValueError):
                        continue

        if not analyses:
            return ToolChainReport(
                period_start=period_start.isoformat(),
                period_end=now.isoformat(),
                total_sessions=0,
                total_sequences=0,
                total_tool_calls=0,
                avg_redundancy_ratio=0.0,
                max_redundancy_ratio=0.0,
                total_redundant_calls=0,
                avg_efficiency_score=100.0,
                min_efficiency_score=100.0,
                tool_frequency={},
                common_patterns={},
                top_inefficiencies=[],
                improvement_opportunities=[]
            )

        # Aggregate metrics
        session_ids = set(a['session_id'] for a in analyses)
        total_calls = sum(a['total_calls'] for a in analyses)
        redundancy_ratios = [a['redundancy_ratio'] for a in analyses]
        efficiency_scores = [a['efficiency_score'] for a in analyses]
        total_redundant = sum(a['redundant_calls'] for a in analyses)

        # Tool frequency
        tool_freq = defaultdict(int)
        for a in analyses:
            pattern = a.get('tool_pattern', '')
            for tool in pattern.split(' -> '):
                tool_freq[tool.strip()] += 1

        # Pattern frequency
        pattern_freq = defaultdict(int)
        for a in analyses:
            pattern = a.get('tool_pattern', '')
            # Simplify pattern for aggregation
            simplified = ' -> '.join(pattern.split(' -> ')[:5])  # First 5 tools
            pattern_freq[simplified] += 1

        # Top inefficiencies
        inefficiencies = []
        for a in analyses:
            if a['redundancy_ratio'] > 0.1:  # >10% redundancy
                inefficiencies.append(
                    f"Task {a['task_id']}: {a['redundancy_ratio']*100:.1f}% redundancy "
                    f"({a['redundant_calls']} calls)"
                )

        # Improvement opportunities
        all_suggestions = []
        for a in analyses:
            all_suggestions.extend(a.get('suggested_improvements', []))

        # Count suggestion frequency
        suggestion_freq = defaultdict(int)
        for s in all_suggestions:
            suggestion_freq[s] += 1

        top_suggestions = sorted(
            suggestion_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return ToolChainReport(
            period_start=period_start.isoformat(),
            period_end=now.isoformat(),
            total_sessions=len(session_ids),
            total_sequences=len(analyses),
            total_tool_calls=total_calls,
            avg_redundancy_ratio=sum(redundancy_ratios) / len(redundancy_ratios) if redundancy_ratios else 0,
            max_redundancy_ratio=max(redundancy_ratios) if redundancy_ratios else 0,
            total_redundant_calls=total_redundant,
            avg_efficiency_score=sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 100,
            min_efficiency_score=min(efficiency_scores) if efficiency_scores else 100,
            tool_frequency=dict(sorted(tool_freq.items(), key=lambda x: x[1], reverse=True)),
            common_patterns=dict(sorted(pattern_freq.items(), key=lambda x: x[1], reverse=True)[:10]),
            top_inefficiencies=inefficiencies[:10],
            improvement_opportunities=[s[0] for s in top_suggestions]
        )

    def analyze_session(self, session_file: Path) -> List[ToolChainAnalysis]:
        """
        Analyze all tool sequences in a session.

        Args:
            session_file: Path to session JSONL file

        Returns:
            List of analyses for each task in session
        """
        sequences = self.parse_session(session_file)

        analyses = []
        for sequence in sequences:
            if sequence.calls:  # Skip empty sequences
                analysis = self.analyze_sequence(sequence)
                analyses.append(analysis)

        return analyses


def format_report(report: ToolChainReport) -> str:
    """Format report for display."""
    lines = [
        "=" * 70,
        "TOOL CHAIN EFFECTIVENESS REPORT",
        "=" * 70,
        "",
        f"Period: {report.period_start[:10]} to {report.period_end[:10]}",
        f"Sessions: {report.total_sessions} | Sequences: {report.total_sequences} | Tool Calls: {report.total_tool_calls}",
        "",
        "─" * 70,
        "REDUNDANCY METRICS",
        "─" * 70,
        f"Average Redundancy Ratio: {report.avg_redundancy_ratio*100:.1f}% (target: <10%)",
        f"Max Redundancy Ratio: {report.max_redundancy_ratio*100:.1f}%",
        f"Total Redundant Calls: {report.total_redundant_calls}",
        f"Status: {'✅ GOOD' if report.avg_redundancy_ratio < 0.1 else '⚠️ NEEDS IMPROVEMENT'}",
        "",
        "─" * 70,
        "EFFICIENCY METRICS",
        "─" * 70,
        f"Average Efficiency Score: {report.avg_efficiency_score:.1f}/100 (target: >80)",
        f"Min Efficiency Score: {report.min_efficiency_score:.1f}/100",
        f"Status: {'✅ GOOD' if report.avg_efficiency_score >= 80 else '⚠️ NEEDS IMPROVEMENT'}",
        "",
    ]

    if report.tool_frequency:
        lines.extend([
            "─" * 70,
            "TOOL USAGE DISTRIBUTION",
            "─" * 70,
        ])
        for tool, count in list(report.tool_frequency.items())[:10]:
            lines.append(f"  {tool}: {count}")

    if report.top_inefficiencies:
        lines.extend([
            "",
            "─" * 70,
            "TOP INEFFICIENCIES",
            "─" * 70,
        ])
        for item in report.top_inefficiencies[:5]:
            lines.append(f"  • {item}")

    if report.improvement_opportunities:
        lines.extend([
            "",
            "─" * 70,
            "IMPROVEMENT OPPORTUNITIES",
            "─" * 70,
        ])
        for item in report.improvement_opportunities:
            lines.append(f"  💡 {item}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_analysis(analysis: ToolChainAnalysis) -> str:
    """Format single analysis for display."""
    lines = [
        f"Task: {analysis.task_id} | Session: {analysis.session_id}",
        "─" * 50,
        f"Tool Calls: {analysis.total_calls} | Unique Tools: {analysis.unique_tools}",
        f"Redundant: {analysis.redundant_calls} ({analysis.redundancy_ratio*100:.1f}%)",
        f"Efficiency Score: {analysis.efficiency_score:.1f}/100",
        f"Pattern: {analysis.tool_pattern[:60]}{'...' if len(analysis.tool_pattern) > 60 else ''}",
    ]

    if analysis.common_pattern_match:
        lines.append(f"Matched Pattern: {analysis.common_pattern_match}")

    if analysis.suggested_improvements:
        lines.append("")
        lines.append("Suggestions:")
        for s in analysis.suggested_improvements[:3]:
            lines.append(f"  💡 {s}")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tool Chain Effectiveness Analyzer"
    )
    parser.add_argument(
        "--session", "-s",
        type=Path,
        help="Session JSONL file to analyze"
    )
    parser.add_argument(
        "--report", "-r",
        nargs="?",
        const="weekly",
        choices=["daily", "weekly", "monthly"],
        help="Generate aggregate report (default: weekly)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()
    analyzer = ToolChainAnalyzer()

    if args.session:
        # Analyze specific session
        try:
            analyses = analyzer.analyze_session(args.session)

            if args.json:
                print(json.dumps([asdict(a) for a in analyses], indent=2))
            else:
                for analysis in analyses:
                    print(format_analysis(analysis))
                    print()

                # Summary
                if analyses:
                    avg_redundancy = sum(a.redundancy_ratio for a in analyses) / len(analyses)
                    avg_efficiency = sum(a.efficiency_score for a in analyses) / len(analyses)
                    print("=" * 50)
                    print(f"SESSION SUMMARY: {len(analyses)} tasks analyzed")
                    print(f"Avg Redundancy: {avg_redundancy*100:.1f}% | Avg Efficiency: {avg_efficiency:.1f}/100")

        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.report:
        # Generate aggregate report
        period_days = {"daily": 1, "weekly": 7, "monthly": 30}[args.report]
        report = analyzer.generate_report(period_days=period_days)

        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print(format_report(report))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
