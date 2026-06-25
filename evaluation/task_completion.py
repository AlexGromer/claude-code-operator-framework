#!/usr/bin/env python3
"""
Task Completion Quality Metrics
Version: 1.0.0

Automated assessment of task completion from session transcripts.
Measures whether agent ACTUALLY completed requested task, not just
whether it produced output.

Features:
- Task completion detection from JSONL transcripts
- Quality scoring via automated rubrics
- Full/partial/failed/abandoned classification
- Integration with agent_metrics.py

Usage:
    python3 task_completion.py --session-file SESSION.jsonl --report
    python3 task_completion.py --assess-task "Deploy API to production"
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

try:
    from agent_metrics import AgentMetrics, TaskOutcome
except ImportError:
    print("ERROR: agent_metrics.py not found. Ensure it's in the same directory.")
    sys.exit(1)


@dataclass
class TaskCriteria:
    """Criteria for task completion assessment."""
    task_description: str
    required_actions: List[str]  # Must complete ALL
    optional_actions: List[str]  # Bonus for completion
    quality_indicators: List[str]  # Indicators of high quality
    failure_indicators: List[str]  # Indicators of failure


@dataclass
class TaskAssessment:
    """Result of automated task assessment."""
    task_id: str
    task_description: str
    status: str  # "completed" | "partial" | "failed" | "abandoned"
    completion_pct: float  # 0-100%
    quality_score: float  # 1-5 scale
    required_completed: int
    required_total: int
    optional_completed: int
    optional_total: int
    quality_indicators_found: int
    quality_indicators_total: int
    failure_indicators_found: int
    confidence: float  # 0-1, confidence in assessment
    reasoning: str  # Explanation of assessment


class TaskCompletionAnalyzer:
    """
    Automated task completion assessment from session transcripts.

    Detects task boundaries, extracts actions, and assesses completion
    quality based on criteria matching.
    """

    def __init__(self):
        """Initialize task completion analyzer."""
        self.agent_metrics = AgentMetrics()

        # Common task patterns (keyword-based detection)
        self.task_start_patterns = [
            r"(?i)^(create|implement|add|build|deploy|fix|update|refactor|test)",
            r"(?i)^(write|generate|analyze|review|optimize|configure)",
            r"(?i)^(install|setup|integrate|migrate|upgrade)"
        ]

        # Completion indicators
        self.completion_indicators = [
            r"(?i)(completed|done|finished|success)",
            r"(?i)(all tests passing|✅|✓)",
            r"(?i)(deployed|committed|pushed)",
            r"(?i)(working as expected|validated)"
        ]

        # Failure indicators
        self.failure_indicators = [
            r"(?i)(failed|error|exception|crash)",
            r"(?i)(incomplete|abandoned|stuck)",
            r"(?i)(cannot|unable to|blocked)",
            r"(?i)(❌|✗)"
        ]

    def detect_tasks_from_session(self, session_file: Path) -> List[TaskCriteria]:
        """
        Detect task boundaries from session transcript.

        Analyzes user messages to identify task requests and extract
        criteria.

        Args:
            session_file: Path to session JSONL file

        Returns:
            List of detected tasks with criteria
        """
        if not session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")

        tasks = []

        with open(session_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Only process user messages
                    if entry.get('type') != 'input':
                        continue

                    # Get message text
                    message = entry.get('text', '').strip()
                    if not message:
                        continue

                    # Check if message is a task request
                    if self._is_task_request(message):
                        criteria = self._extract_criteria(message)
                        if criteria:
                            tasks.append(criteria)

                except json.JSONDecodeError:
                    continue

        return tasks

    def _is_task_request(self, message: str) -> bool:
        """
        Check if message is a task request.

        Args:
            message: User message text

        Returns:
            True if message is a task request
        """
        # Check against task start patterns
        for pattern in self.task_start_patterns:
            if re.search(pattern, message):
                return True

        # Check for imperative mood (command form)
        # Simple heuristic: starts with verb
        words = message.split()
        if words and words[0].lower() in [
            'create', 'implement', 'add', 'build', 'deploy', 'fix',
            'update', 'refactor', 'test', 'write', 'generate', 'analyze',
            'review', 'optimize', 'configure', 'install', 'setup',
            'integrate', 'migrate', 'upgrade', 'delete', 'remove'
        ]:
            return True

        return False

    def _extract_criteria(self, message: str) -> Optional[TaskCriteria]:
        """
        Extract task criteria from message.

        Args:
            message: Task request message

        Returns:
            TaskCriteria if extractable, None otherwise
        """
        # Simple extraction: use message as description
        # Extract required actions from keywords
        required_actions = []
        optional_actions = []
        quality_indicators = []
        failure_indicators = []

        # Extract actions (verbs)
        action_keywords = re.findall(
            r'\b(create|implement|add|build|deploy|fix|update|refactor|'
            r'test|write|generate|analyze|review|optimize|configure|'
            r'install|setup|integrate|migrate|upgrade)\b',
            message,
            re.IGNORECASE
        )
        required_actions = list(set(a.lower() for a in action_keywords))

        # Extract quality indicators from adverbs/adjectives
        quality_keywords = re.findall(
            r'\b(comprehensive|thorough|complete|high-quality|robust|'
            r'secure|optimized|tested|documented)\b',
            message,
            re.IGNORECASE
        )
        quality_indicators = list(set(q.lower() for q in quality_keywords))

        # Default failure indicators
        failure_indicators = ['error', 'failed', 'incomplete']

        return TaskCriteria(
            task_description=message[:200],  # Truncate long descriptions
            required_actions=required_actions if required_actions else ['complete'],
            optional_actions=optional_actions,
            quality_indicators=quality_indicators if quality_indicators else ['working', 'tested'],
            failure_indicators=failure_indicators
        )

    def assess_task(
        self,
        task_criteria: TaskCriteria,
        session_file: Path,
        task_start_index: int = 0
    ) -> TaskAssessment:
        """
        Assess task completion from session transcript.

        Args:
            task_criteria: Task criteria to assess against
            session_file: Path to session JSONL file
            task_start_index: Line number where task started

        Returns:
            TaskAssessment with completion status and quality score
        """
        if not session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")

        # Read session content starting from task start
        session_content = []
        with open(session_file, 'r') as f:
            for i, line in enumerate(f):
                if i >= task_start_index:
                    try:
                        entry = json.loads(line)
                        if entry.get('type') in ['output', 'input']:
                            session_content.append(entry.get('text', ''))
                    except json.JSONDecodeError:
                        continue

        # Join content for pattern matching
        full_content = '\n'.join(session_content)

        # Assess required actions
        required_completed = 0
        for action in task_criteria.required_actions:
            if self._action_completed(action, full_content):
                required_completed += 1

        # Assess optional actions
        optional_completed = 0
        for action in task_criteria.optional_actions:
            if self._action_completed(action, full_content):
                optional_completed += 1

        # Assess quality indicators
        quality_found = 0
        for indicator in task_criteria.quality_indicators:
            if re.search(rf'\b{re.escape(indicator)}\b', full_content, re.IGNORECASE):
                quality_found += 1

        # Check failure indicators
        failures_found = 0
        for indicator in task_criteria.failure_indicators:
            if re.search(rf'\b{re.escape(indicator)}\b', full_content, re.IGNORECASE):
                failures_found += 1

        # Calculate completion percentage
        required_total = len(task_criteria.required_actions)
        optional_total = len(task_criteria.optional_actions)

        if required_total > 0:
            completion_pct = (required_completed / required_total) * 100

            # Bonus for optional actions
            if optional_total > 0:
                optional_bonus = (optional_completed / optional_total) * 20  # Max +20%
                completion_pct = min(100, completion_pct + optional_bonus)
        else:
            # No required actions defined, assume completed if no failures
            completion_pct = 100.0 if failures_found == 0 else 0.0

        # Determine status
        if failures_found > 2:
            status = 'failed'
        elif completion_pct >= 90:
            status = 'completed'
        elif completion_pct >= 50:
            status = 'partial'
        elif completion_pct == 0:
            status = 'abandoned'
        else:
            status = 'partial'

        # Calculate quality score (1-5 scale)
        quality_score = self._calculate_quality_score(
            completion_pct,
            quality_found,
            len(task_criteria.quality_indicators),
            failures_found
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            required_total,
            optional_total,
            len(task_criteria.quality_indicators),
            len(session_content)
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            status,
            required_completed,
            required_total,
            optional_completed,
            optional_total,
            quality_found,
            failures_found
        )

        return TaskAssessment(
            task_id=f"task_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            task_description=task_criteria.task_description,
            status=status,
            completion_pct=completion_pct,
            quality_score=quality_score,
            required_completed=required_completed,
            required_total=required_total,
            optional_completed=optional_completed,
            optional_total=optional_total,
            quality_indicators_found=quality_found,
            quality_indicators_total=len(task_criteria.quality_indicators),
            failure_indicators_found=failures_found,
            confidence=confidence,
            reasoning=reasoning
        )

    def _action_completed(self, action: str, content: str) -> bool:
        """
        Check if action was completed in content.

        Args:
            action: Action keyword (e.g., "create", "deploy")
            content: Session content to check

        Returns:
            True if action appears to be completed
        """
        # Check for completion patterns with this action
        patterns = [
            rf'\b{action}[a-z]*\s+(completed|done|success)',
            rf'(completed|done)\s+{action}',
            rf'{action}[a-z]*\s+.*✅',
            rf'✅.*{action}'
        ]

        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # Check for generic completion indicators mentioning this action
        if re.search(rf'\b{action}\b', content, re.IGNORECASE):
            for indicator_pattern in self.completion_indicators:
                if re.search(indicator_pattern, content):
                    # Both action and completion indicator present
                    return True

        return False

    def _calculate_quality_score(
        self,
        completion_pct: float,
        quality_found: int,
        quality_total: int,
        failures_found: int
    ) -> float:
        """
        Calculate quality score (1-5 scale).

        Args:
            completion_pct: Completion percentage (0-100)
            quality_found: Number of quality indicators found
            quality_total: Total quality indicators expected
            failures_found: Number of failure indicators found

        Returns:
            Quality score (1.0-5.0)
        """
        # Base score from completion
        if completion_pct >= 95:
            base_score = 5.0
        elif completion_pct >= 80:
            base_score = 4.0
        elif completion_pct >= 60:
            base_score = 3.0
        elif completion_pct >= 40:
            base_score = 2.0
        else:
            base_score = 1.0

        # Adjust for quality indicators
        if quality_total > 0:
            quality_ratio = quality_found / quality_total
            quality_adjustment = (quality_ratio - 0.5) * 0.5  # -0.25 to +0.25
            base_score += quality_adjustment

        # Penalize for failures
        failure_penalty = min(1.0, failures_found * 0.2)
        base_score -= failure_penalty

        # Clamp to 1.0-5.0
        return max(1.0, min(5.0, base_score))

    def _calculate_confidence(
        self,
        required_total: int,
        optional_total: int,
        quality_total: int,
        content_lines: int
    ) -> float:
        """
        Calculate confidence in assessment (0-1).

        Args:
            required_total: Number of required actions
            optional_total: Number of optional actions
            quality_total: Number of quality indicators
            content_lines: Number of content lines analyzed

        Returns:
            Confidence score (0.0-1.0)
        """
        # More criteria = higher confidence
        criteria_score = min(1.0, (required_total + optional_total + quality_total) / 10)

        # More content = higher confidence
        content_score = min(1.0, content_lines / 50)

        # Combine
        confidence = (criteria_score + content_score) / 2

        return round(confidence, 2)

    def _generate_reasoning(
        self,
        status: str,
        required_completed: int,
        required_total: int,
        optional_completed: int,
        optional_total: int,
        quality_found: int,
        failures_found: int
    ) -> str:
        """
        Generate human-readable reasoning for assessment.

        Args:
            status: Assessment status
            required_completed: Required actions completed
            required_total: Total required actions
            optional_completed: Optional actions completed
            optional_total: Total optional actions
            quality_found: Quality indicators found
            failures_found: Failure indicators found

        Returns:
            Reasoning explanation
        """
        parts = []

        # Status explanation
        if status == 'completed':
            parts.append("Task appears fully completed.")
        elif status == 'partial':
            parts.append("Task partially completed.")
        elif status == 'failed':
            parts.append("Task failed with errors.")
        else:
            parts.append("Task was abandoned.")

        # Required actions
        if required_total > 0:
            parts.append(
                f"Required actions: {required_completed}/{required_total} completed "
                f"({required_completed/required_total*100:.0f}%)."
            )

        # Optional actions
        if optional_total > 0:
            parts.append(
                f"Optional actions: {optional_completed}/{optional_total} completed."
            )

        # Quality indicators
        if quality_found > 0:
            parts.append(f"Quality indicators found: {quality_found}.")

        # Failures
        if failures_found > 0:
            parts.append(f"⚠️ {failures_found} failure indicator(s) detected.")

        return ' '.join(parts)

    def log_to_agent_metrics(self, assessment: TaskAssessment, session_id: str):
        """
        Log assessment to agent_metrics.py for tracking.

        Args:
            assessment: TaskAssessment result
            session_id: Session identifier
        """
        # Calculate tool metrics (placeholder, would need actual tool call data)
        tool_calls_total = 10  # Example
        tool_calls_successful = 8  # Example
        tool_calls_redundant = 1  # Example
        errors_total = 2  # Example
        errors_recovered = 1  # Example
        user_corrections = 0  # Example

        self.agent_metrics.track_task(
            task_id=assessment.task_id,
            session_id=session_id,
            status=assessment.status,
            quality_score=assessment.quality_score,
            completion_pct=assessment.completion_pct,
            tool_calls_total=tool_calls_total,
            tool_calls_successful=tool_calls_successful,
            tool_calls_redundant=tool_calls_redundant,
            errors_total=errors_total,
            errors_recovered=errors_recovered,
            user_corrections=user_corrections
        )

    def format_assessment(self, assessment: TaskAssessment) -> str:
        """
        Format assessment as human-readable text.

        Args:
            assessment: TaskAssessment result

        Returns:
            Formatted assessment string
        """
        status_emoji = {
            'completed': '✅',
            'partial': '⚠️',
            'failed': '❌',
            'abandoned': '🚫'
        }

        emoji = status_emoji.get(assessment.status, '⚪')

        output = f"""
=== Task Completion Assessment ===

Task: {assessment.task_description}
Status: {emoji} {assessment.status.upper()}
Completion: {assessment.completion_pct:.1f}%
Quality Score: {assessment.quality_score:.1f}/5.0
Confidence: {assessment.confidence:.0%}

Breakdown:
  Required Actions: {assessment.required_completed}/{assessment.required_total} completed
  Optional Actions: {assessment.optional_completed}/{assessment.optional_total} completed
  Quality Indicators: {assessment.quality_indicators_found}/{assessment.quality_indicators_total} found
  Failure Indicators: {assessment.failure_indicators_found} detected

Reasoning:
  {assessment.reasoning}
"""

        return output


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Task Completion Quality Metrics')
    parser.add_argument('--session-file', type=Path, help='Session JSONL file')
    parser.add_argument('--assess-task', type=str, help='Task description to assess')
    parser.add_argument('--report', action='store_true', help='Generate assessment report')
    parser.add_argument('--log-to-agent-metrics', action='store_true', help='Log to agent_metrics.py')

    args = parser.parse_args()

    analyzer = TaskCompletionAnalyzer()

    if args.report and args.session_file:
        # Detect all tasks from session
        tasks = analyzer.detect_tasks_from_session(args.session_file)

        if not tasks:
            print("No tasks detected in session.")
            sys.exit(0)

        print(f"\n=== Detected {len(tasks)} Task(s) ===\n")

        # Assess each task
        for i, task in enumerate(tasks):
            assessment = analyzer.assess_task(task, args.session_file, task_start_index=i*10)
            print(analyzer.format_assessment(assessment))

            if args.log_to_agent_metrics:
                session_id = args.session_file.stem
                analyzer.log_to_agent_metrics(assessment, session_id)
                print(f"✅ Logged to agent_metrics (session: {session_id})")

            print("\n" + "="*60 + "\n")

    elif args.assess_task:
        # Manual task assessment (no session file)
        print("❌ Error: --assess-task requires --session-file")
        sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
