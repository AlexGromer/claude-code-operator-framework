#!/usr/bin/env python3
"""
Task Cost Analyzer — Cost analysis by task type, domain, and complexity.

TIER 3 Phase 5 Task 30: GAP-COST-AG-004

Features:
- Task type classification (by domain, complexity)
- Cost aggregation by category
- Pattern analysis (expensive vs cheap tasks)
- Cost breakdown reports
- Optimization recommendations

Usage:
    python3 task_cost_analyzer.py --report                  # Full cost breakdown
    python3 task_cost_analyzer.py --by-domain              # Costs by domain
    python3 task_cost_analyzer.py --by-complexity          # Costs by complexity
    python3 task_cost_analyzer.py --expensive              # Most expensive patterns
    python3 task_cost_analyzer.py --recommendations        # Optimization tips

Version: 1.0.0
"""

import json
import re
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskDomain(Enum):
    """Task domain categories."""
    SECURITY = "security"
    DEVOPS = "devops"
    DEVELOPMENT = "development"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TESTING = "testing"
    PLANNING = "planning"
    GENERAL = "general"


class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"      # <5 min, single tool
    SIMPLE = "simple"        # 5-15 min, 2-5 tools
    MODERATE = "moderate"    # 15-30 min, 5-15 tools
    COMPLEX = "complex"      # 30-60 min, 15-30 tools
    EPIC = "epic"            # >60 min, 30+ tools


@dataclass
class TaskCostRecord:
    """Cost record for a single task."""
    timestamp: str
    session_id: str
    task_id: str
    domain: str
    complexity: str
    description: str
    total_cost: float
    token_cost: float
    tool_cost: float
    duration_seconds: int
    tool_calls: int
    tokens_used: int
    success: bool


@dataclass
class DomainCostSummary:
    """Cost summary for a domain."""
    domain: str
    total_cost: float
    task_count: int
    avg_cost_per_task: float
    total_tokens: int
    total_tool_calls: int
    avg_duration: float
    success_rate: float
    most_expensive_task: Optional[str] = None
    cost_trend: str = "stable"  # increasing/decreasing/stable


@dataclass
class ComplexityCostSummary:
    """Cost summary by complexity level."""
    complexity: str
    total_cost: float
    task_count: int
    avg_cost_per_task: float
    avg_duration: float
    avg_tool_calls: float


@dataclass
class CostPattern:
    """Identified cost pattern."""
    pattern_name: str
    description: str
    avg_cost: float
    frequency: int
    example_tasks: List[str]
    optimization_tip: str


@dataclass
class TaskCostReport:
    """Complete task cost analysis report."""
    period_start: str
    period_end: str
    total_tasks: int
    total_cost: float
    by_domain: Dict[str, DomainCostSummary]
    by_complexity: Dict[str, ComplexityCostSummary]
    expensive_patterns: List[CostPattern]
    recommendations: List[str]


class TaskCostAnalyzer:
    """
    Analyzes costs by task type, domain, and complexity.

    TIER 3 Phase 5 Task 30 (GAP-COST-AG-004)

    Classification:
    - Domain: security, devops, development, documentation, etc.
    - Complexity: trivial, simple, moderate, complex, epic

    Analysis:
    - Cost aggregation by category
    - Pattern identification
    - Optimization recommendations
    """

    # Domain classification patterns
    DOMAIN_PATTERNS = {
        TaskDomain.SECURITY: [
            r'\b(security|pentest|audit|vulnerability|CVE|nmap|nuclei|exploit)\b',
            r'\b(OWASP|MITRE|injection|XSS|CSRF|authentication)\b',
        ],
        TaskDomain.DEVOPS: [
            r'\b(deploy|kubernetes|k8s|docker|terraform|ansible|CI/CD|pipeline)\b',
            r'\b(helm|argocd|jenkins|github actions|infrastructure)\b',
        ],
        TaskDomain.DEVELOPMENT: [
            r'\b(implement|develop|code|function|class|module|feature)\b',
            r'\b(API|endpoint|database|schema|model)\b',
        ],
        TaskDomain.DOCUMENTATION: [
            r'\b(document|readme|guide|tutorial|comment|docstring)\b',
            r'\b(wiki|specification|manual)\b',
        ],
        TaskDomain.RESEARCH: [
            r'\b(research|investigate|analyze|study|explore|search)\b',
            r'\b(comparison|benchmark|evaluation)\b',
        ],
        TaskDomain.DEBUGGING: [
            r'\b(debug|fix|bug|error|issue|problem|broken)\b',
            r'\b(traceback|exception|crash|failure)\b',
        ],
        TaskDomain.REFACTORING: [
            r'\b(refactor|optimize|clean|improve|restructure)\b',
            r'\b(performance|efficiency|simplify)\b',
        ],
        TaskDomain.TESTING: [
            r'\b(test|pytest|unittest|coverage|assert|mock)\b',
            r'\b(integration|e2e|unit test)\b',
        ],
        TaskDomain.PLANNING: [
            r'\b(plan|design|architect|strategy|roadmap)\b',
            r'\b(specification|requirements|estimate)\b',
        ],
    }

    # Complexity thresholds
    COMPLEXITY_THRESHOLDS = {
        TaskComplexity.TRIVIAL: {"max_tools": 2, "max_duration": 300},
        TaskComplexity.SIMPLE: {"max_tools": 5, "max_duration": 900},
        TaskComplexity.MODERATE: {"max_tools": 15, "max_duration": 1800},
        TaskComplexity.COMPLEX: {"max_tools": 30, "max_duration": 3600},
        TaskComplexity.EPIC: {"max_tools": float('inf'), "max_duration": float('inf')},
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize task cost analyzer."""
        self.data_dir = data_dir or Path.home() / ".claude" / "evaluation" / "data"
        self.tasks_file = self.data_dir / "task_costs.jsonl"
        self.agent_costs_file = self.data_dir / "agent_costs.jsonl"

        self.data_dir.mkdir(parents=True, exist_ok=True)

    def classify_domain(self, description: str) -> TaskDomain:
        """
        Classify task domain based on description.

        Args:
            description: Task description or content

        Returns:
            TaskDomain enum value
        """
        description_lower = description.lower()
        scores = defaultdict(int)

        for domain, patterns in self.DOMAIN_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, description_lower, re.IGNORECASE)
                scores[domain] += len(matches) * 2

        if not scores:
            return TaskDomain.GENERAL

        return max(scores, key=scores.get)

    def classify_complexity(
        self,
        tool_calls: int,
        duration_seconds: int,
    ) -> TaskComplexity:
        """
        Classify task complexity based on metrics.

        Args:
            tool_calls: Number of tool calls
            duration_seconds: Task duration

        Returns:
            TaskComplexity enum value
        """
        for complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE,
                          TaskComplexity.MODERATE, TaskComplexity.COMPLEX]:
            thresholds = self.COMPLEXITY_THRESHOLDS[complexity]
            if tool_calls <= thresholds["max_tools"] and duration_seconds <= thresholds["max_duration"]:
                return complexity

        return TaskComplexity.EPIC

    def record_task(
        self,
        session_id: str,
        task_id: str,
        description: str,
        total_cost: float,
        token_cost: float,
        tool_cost: float,
        duration_seconds: int,
        tool_calls: int,
        tokens_used: int,
        success: bool = True,
    ) -> TaskCostRecord:
        """
        Record a completed task with cost analysis.

        Args:
            Various task metrics

        Returns:
            TaskCostRecord
        """
        domain = self.classify_domain(description)
        complexity = self.classify_complexity(tool_calls, duration_seconds)

        record = TaskCostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            task_id=task_id,
            domain=domain.value,
            complexity=complexity.value,
            description=description[:200],  # Truncate
            total_cost=total_cost,
            token_cost=token_cost,
            tool_cost=tool_cost,
            duration_seconds=duration_seconds,
            tool_calls=tool_calls,
            tokens_used=tokens_used,
            success=success,
        )

        with open(self.tasks_file, 'a') as f:
            f.write(json.dumps(asdict(record)) + "\n")

        return record

    def load_tasks(self, days: int = 30) -> List[TaskCostRecord]:
        """Load task records from file."""
        if not self.tasks_file.exists():
            return []

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        tasks = []
        with open(self.tasks_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        ts = self._parse_timestamp(data.get("timestamp", ""))
                        if ts >= cutoff:
                            tasks.append(TaskCostRecord(**data))
                    except (json.JSONDecodeError, TypeError):
                        continue

        return tasks

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO timestamp."""
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def analyze_by_domain(self, days: int = 30) -> Dict[str, DomainCostSummary]:
        """
        Analyze costs grouped by domain.

        Returns:
            Dictionary of domain -> summary
        """
        tasks = self.load_tasks(days)

        if not tasks:
            return {}

        # Group by domain
        domain_tasks = defaultdict(list)
        for task in tasks:
            domain_tasks[task.domain].append(task)

        summaries = {}
        for domain, domain_task_list in domain_tasks.items():
            total_cost = sum(t.total_cost for t in domain_task_list)
            task_count = len(domain_task_list)
            total_tokens = sum(t.tokens_used for t in domain_task_list)
            total_tool_calls = sum(t.tool_calls for t in domain_task_list)
            successful = [t for t in domain_task_list if t.success]

            most_expensive = max(domain_task_list, key=lambda t: t.total_cost)

            summaries[domain] = DomainCostSummary(
                domain=domain,
                total_cost=total_cost,
                task_count=task_count,
                avg_cost_per_task=total_cost / task_count if task_count > 0 else 0,
                total_tokens=total_tokens,
                total_tool_calls=total_tool_calls,
                avg_duration=sum(t.duration_seconds for t in domain_task_list) / task_count if task_count > 0 else 0,
                success_rate=len(successful) / task_count if task_count > 0 else 0,
                most_expensive_task=most_expensive.description[:50],
            )

        return summaries

    def analyze_by_complexity(self, days: int = 30) -> Dict[str, ComplexityCostSummary]:
        """
        Analyze costs grouped by complexity.

        Returns:
            Dictionary of complexity -> summary
        """
        tasks = self.load_tasks(days)

        if not tasks:
            return {}

        # Group by complexity
        complexity_tasks = defaultdict(list)
        for task in tasks:
            complexity_tasks[task.complexity].append(task)

        summaries = {}
        for complexity, complexity_task_list in complexity_tasks.items():
            total_cost = sum(t.total_cost for t in complexity_task_list)
            task_count = len(complexity_task_list)

            summaries[complexity] = ComplexityCostSummary(
                complexity=complexity,
                total_cost=total_cost,
                task_count=task_count,
                avg_cost_per_task=total_cost / task_count if task_count > 0 else 0,
                avg_duration=sum(t.duration_seconds for t in complexity_task_list) / task_count if task_count > 0 else 0,
                avg_tool_calls=sum(t.tool_calls for t in complexity_task_list) / task_count if task_count > 0 else 0,
            )

        return summaries

    def identify_expensive_patterns(self, days: int = 30) -> List[CostPattern]:
        """
        Identify patterns that lead to high costs.

        Returns:
            List of expensive patterns with optimization tips
        """
        tasks = self.load_tasks(days)

        if not tasks:
            return []

        patterns = []

        # Pattern 1: High tool count
        high_tool_tasks = [t for t in tasks if t.tool_calls > 20]
        if high_tool_tasks:
            avg_cost = sum(t.total_cost for t in high_tool_tasks) / len(high_tool_tasks)
            patterns.append(CostPattern(
                pattern_name="High Tool Usage",
                description="Tasks with >20 tool calls",
                avg_cost=avg_cost,
                frequency=len(high_tool_tasks),
                example_tasks=[t.description[:50] for t in high_tool_tasks[:3]],
                optimization_tip="Consider using subagents for parallel execution or breaking into smaller tasks",
            ))

        # Pattern 2: Long duration
        long_tasks = [t for t in tasks if t.duration_seconds > 1800]  # >30 min
        if long_tasks:
            avg_cost = sum(t.total_cost for t in long_tasks) / len(long_tasks)
            patterns.append(CostPattern(
                pattern_name="Long Running Tasks",
                description="Tasks taking >30 minutes",
                avg_cost=avg_cost,
                frequency=len(long_tasks),
                example_tasks=[t.description[:50] for t in long_tasks[:3]],
                optimization_tip="Break into subtasks, use checkpoints, or use haiku model for research phases",
            ))

        # Pattern 3: High token usage
        high_token_tasks = [t for t in tasks if t.tokens_used > 100000]
        if high_token_tasks:
            avg_cost = sum(t.total_cost for t in high_token_tasks) / len(high_token_tasks)
            patterns.append(CostPattern(
                pattern_name="High Token Usage",
                description="Tasks using >100k tokens",
                avg_cost=avg_cost,
                frequency=len(high_token_tasks),
                example_tasks=[t.description[:50] for t in high_token_tasks[:3]],
                optimization_tip="Use multi-turn optimization, checkpoint summarization, or context pruning",
            ))

        # Pattern 4: Failed tasks (wasted cost)
        failed_tasks = [t for t in tasks if not t.success]
        if failed_tasks:
            total_wasted = sum(t.total_cost for t in failed_tasks)
            patterns.append(CostPattern(
                pattern_name="Failed Tasks",
                description="Tasks that did not complete successfully",
                avg_cost=total_wasted / len(failed_tasks) if failed_tasks else 0,
                frequency=len(failed_tasks),
                example_tasks=[t.description[:50] for t in failed_tasks[:3]],
                optimization_tip="Review error patterns, add better validation, use retry with backoff",
            ))

        # Pattern 5: Security domain (typically expensive)
        security_tasks = [t for t in tasks if t.domain == TaskDomain.SECURITY.value]
        if security_tasks and len(security_tasks) >= 3:
            avg_cost = sum(t.total_cost for t in security_tasks) / len(security_tasks)
            general_avg = sum(t.total_cost for t in tasks) / len(tasks)
            if avg_cost > general_avg * 1.5:  # 50% more expensive
                patterns.append(CostPattern(
                    pattern_name="Security Tasks Premium",
                    description="Security tasks cost 50%+ more than average",
                    avg_cost=avg_cost,
                    frequency=len(security_tasks),
                    example_tasks=[t.description[:50] for t in security_tasks[:3]],
                    optimization_tip="Use specialized security skills, cache common scan results",
                ))

        return sorted(patterns, key=lambda p: p.avg_cost * p.frequency, reverse=True)

    def generate_recommendations(self, days: int = 30) -> List[str]:
        """
        Generate cost optimization recommendations.

        Returns:
            List of actionable recommendations
        """
        tasks = self.load_tasks(days)

        if not tasks:
            return ["No task data available for analysis"]

        recommendations = []

        # Analyze overall metrics
        total_cost = sum(t.total_cost for t in tasks)
        avg_cost = total_cost / len(tasks)
        success_rate = len([t for t in tasks if t.success]) / len(tasks)

        # Recommendation 1: Success rate
        if success_rate < 0.9:
            wasted = sum(t.total_cost for t in tasks if not t.success)
            recommendations.append(
                f"⚠️ Success rate is {success_rate*100:.1f}% — ${wasted:.2f} wasted on failed tasks. "
                f"Review error patterns and add validation."
            )

        # Recommendation 2: Domain-specific
        domain_costs = self.analyze_by_domain(days)
        if domain_costs:
            most_expensive_domain = max(domain_costs.values(), key=lambda d: d.avg_cost_per_task)
            if most_expensive_domain.avg_cost_per_task > avg_cost * 2:
                recommendations.append(
                    f"💡 {most_expensive_domain.domain.upper()} tasks cost ${most_expensive_domain.avg_cost_per_task:.3f} avg "
                    f"(2x+ average). Consider specialized optimization or subagent delegation."
                )

        # Recommendation 3: Complexity distribution
        complexity_costs = self.analyze_by_complexity(days)
        epic_count = sum(1 for t in tasks if t.complexity == TaskComplexity.EPIC.value)
        if epic_count > len(tasks) * 0.1:  # >10% epic tasks
            recommendations.append(
                f"📊 {epic_count} tasks ({epic_count/len(tasks)*100:.0f}%) are EPIC complexity. "
                f"Consider breaking these into smaller, more manageable subtasks."
            )

        # Recommendation 4: Tool efficiency
        avg_tools = sum(t.tool_calls for t in tasks) / len(tasks)
        if avg_tools > 15:
            recommendations.append(
                f"🔧 Average {avg_tools:.1f} tool calls per task. Consider tool caching, "
                f"batching operations, or using the Explore agent for research."
            )

        # Recommendation 5: Token efficiency
        avg_tokens = sum(t.tokens_used for t in tasks) / len(tasks)
        if avg_tokens > 50000:
            recommendations.append(
                f"📝 Average {avg_tokens/1000:.0f}k tokens per task. Enable multi-turn optimization "
                f"and checkpoint summarization for long conversations."
            )

        if not recommendations:
            recommendations.append("✅ Cost metrics look healthy. Continue monitoring.")

        return recommendations

    def generate_report(self, days: int = 30) -> TaskCostReport:
        """
        Generate complete task cost analysis report.

        Returns:
            TaskCostReport with all analysis
        """
        tasks = self.load_tasks(days)

        now = datetime.now(timezone.utc)
        period_start = (now - timedelta(days=days)).isoformat()
        period_end = now.isoformat()

        return TaskCostReport(
            period_start=period_start,
            period_end=period_end,
            total_tasks=len(tasks),
            total_cost=sum(t.total_cost for t in tasks),
            by_domain={k: asdict(v) for k, v in self.analyze_by_domain(days).items()},
            by_complexity={k: asdict(v) for k, v in self.analyze_by_complexity(days).items()},
            expensive_patterns=[asdict(p) for p in self.identify_expensive_patterns(days)],
            recommendations=self.generate_recommendations(days),
        )

    def generate_dashboard(self, days: int = 30) -> str:
        """Generate cost analysis dashboard."""
        report = self.generate_report(days)

        lines = [
            "",
            "=" * 70,
            "TASK COST ANALYSIS DASHBOARD",
            "=" * 70,
            "",
            f"Period: Last {days} days",
            f"Total Tasks: {report.total_tasks}",
            f"Total Cost: ${report.total_cost:.2f}",
            f"Avg Cost/Task: ${report.total_cost/report.total_tasks:.3f}" if report.total_tasks > 0 else "",
            "",
        ]

        # By Domain
        if report.by_domain:
            lines.append("─" * 70)
            lines.append("COST BY DOMAIN")
            lines.append("─" * 70)
            lines.append("")

            sorted_domains = sorted(report.by_domain.items(),
                                   key=lambda x: x[1]["total_cost"], reverse=True)

            for domain, summary in sorted_domains:
                pct = summary["total_cost"] / report.total_cost * 100 if report.total_cost > 0 else 0
                lines.append(
                    f"  {domain:15} ${summary['total_cost']:7.2f} ({pct:5.1f}%) "
                    f"| {summary['task_count']:3} tasks | ${summary['avg_cost_per_task']:.3f}/task"
                )

            lines.append("")

        # By Complexity
        if report.by_complexity:
            lines.append("─" * 70)
            lines.append("COST BY COMPLEXITY")
            lines.append("─" * 70)
            lines.append("")

            complexity_order = ["trivial", "simple", "moderate", "complex", "epic"]
            for complexity in complexity_order:
                if complexity in report.by_complexity:
                    summary = report.by_complexity[complexity]
                    lines.append(
                        f"  {complexity:10} ${summary['total_cost']:7.2f} "
                        f"| {summary['task_count']:3} tasks | ~{summary['avg_tool_calls']:.0f} tools/task"
                    )

            lines.append("")

        # Expensive Patterns
        if report.expensive_patterns:
            lines.append("─" * 70)
            lines.append("EXPENSIVE PATTERNS")
            lines.append("─" * 70)
            lines.append("")

            for pattern in report.expensive_patterns[:5]:
                lines.append(f"  ⚠️ {pattern['pattern_name']}")
                lines.append(f"     {pattern['description']}")
                lines.append(f"     Avg Cost: ${pattern['avg_cost']:.3f} | Frequency: {pattern['frequency']}")
                lines.append(f"     💡 {pattern['optimization_tip']}")
                lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("─" * 70)
            lines.append("RECOMMENDATIONS")
            lines.append("─" * 70)
            lines.append("")

            for rec in report.recommendations:
                lines.append(f"  {rec}")
                lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Task Cost Analyzer")
    parser.add_argument("--report", action="store_true", help="Generate full report")
    parser.add_argument("--by-domain", action="store_true", help="Show costs by domain")
    parser.add_argument("--by-complexity", action="store_true", help="Show costs by complexity")
    parser.add_argument("--expensive", action="store_true", help="Show expensive patterns")
    parser.add_argument("--recommendations", action="store_true", help="Show optimization tips")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze (default: 30)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    analyzer = TaskCostAnalyzer()

    if args.by_domain:
        domains = analyzer.analyze_by_domain(args.days)
        if args.json:
            print(json.dumps({k: asdict(v) for k, v in domains.items()}, indent=2))
        else:
            print("\nCost by Domain:")
            for domain, summary in sorted(domains.items(), key=lambda x: x[1].total_cost, reverse=True):
                print(f"  {domain}: ${summary.total_cost:.2f} ({summary.task_count} tasks)")

    elif args.by_complexity:
        complexity = analyzer.analyze_by_complexity(args.days)
        if args.json:
            print(json.dumps({k: asdict(v) for k, v in complexity.items()}, indent=2))
        else:
            print("\nCost by Complexity:")
            for level, summary in complexity.items():
                print(f"  {level}: ${summary.total_cost:.2f} ({summary.task_count} tasks)")

    elif args.expensive:
        patterns = analyzer.identify_expensive_patterns(args.days)
        if args.json:
            print(json.dumps([asdict(p) for p in patterns], indent=2))
        else:
            print("\nExpensive Patterns:")
            for pattern in patterns:
                print(f"\n  {pattern.pattern_name}")
                print(f"    Avg Cost: ${pattern.avg_cost:.3f}")
                print(f"    Tip: {pattern.optimization_tip}")

    elif args.recommendations:
        recs = analyzer.generate_recommendations(args.days)
        if args.json:
            print(json.dumps(recs, indent=2))
        else:
            print("\nRecommendations:")
            for rec in recs:
                print(f"  {rec}")

    elif args.report:
        report = analyzer.generate_report(args.days)
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print(analyzer.generate_dashboard(args.days))

    else:
        # Default: show dashboard
        print(analyzer.generate_dashboard(args.days))


if __name__ == "__main__":
    main()
