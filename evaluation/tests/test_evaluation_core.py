#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Evaluation Core Tools
Tests: agent_metrics.py, task_completion.py, latency_tracker.py

Requirements:
- Test all public methods
- Test edge cases (empty data, missing fields, boundary values)
- Use pytest fixtures and tmp_path for file operations
- Mock external dependencies (datetime, file I/O)
"""

import pytest
import sys
import os
import json
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add evaluation directory to path
sys.path.insert(0, '/home/user/.claude/evaluation')

import agent_metrics
import task_completion
import latency_tracker


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_metrics_dir(tmp_path):
    """Create temporary metrics directory."""
    metrics_dir = tmp_path / "evaluation" / "data"
    metrics_dir.mkdir(parents=True)
    return metrics_dir


@pytest.fixture
def mock_datetime():
    """Mock datetime.now() to return fixed time."""
    with patch('agent_metrics.datetime') as mock_dt:
        fixed_time = datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw) if args else fixed_time
        yield mock_dt


@pytest.fixture
def agent_metrics_file(temp_metrics_dir):
    """Path to temporary agent metrics file."""
    return temp_metrics_dir / "agent_metrics.jsonl"


@pytest.fixture
def latency_metrics_file(temp_metrics_dir):
    """Path to temporary latency metrics file."""
    return temp_metrics_dir / "latency_metrics.jsonl"


@pytest.fixture
def session_file(temp_metrics_dir):
    """Path to temporary session JSONL file."""
    return temp_metrics_dir / "session.jsonl"


# ============================================================================
# TEST CLASS: AgentMetrics
# ============================================================================

class TestAgentMetrics:
    """Tests for agent_metrics.py"""

    def test_init_default_path(self, temp_metrics_dir):
        """Test AgentMetrics initialization with default path."""
        with patch('agent_metrics.Path.home', return_value=temp_metrics_dir.parent.parent):
            metrics = agent_metrics.AgentMetrics()
            assert metrics.metrics_file.name == "agent_metrics.jsonl"
            assert metrics.metrics_file.parent.exists()

    def test_init_custom_path(self, agent_metrics_file):
        """Test AgentMetrics initialization with custom path."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)
        assert metrics.metrics_file == agent_metrics_file

    def test_track_task_creates_outcome(self, agent_metrics_file, mock_datetime):
        """Test track_task creates TaskOutcome and writes to file."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        outcome = metrics.track_task(
            task_id="task-001",
            session_id="session-001",
            status="completed",
            quality_score=4.5,
            completion_pct=100.0,
            tool_calls_total=10,
            tool_calls_successful=9,
            tool_calls_redundant=1,
            errors_total=2,
            errors_recovered=2,
            user_corrections=0,
            duration_seconds=30.5
        )

        assert outcome.task_id == "task-001"
        assert outcome.status == "completed"
        assert outcome.quality_score == 4.5
        assert outcome.completion_pct == 100.0

        # Verify file was written
        assert agent_metrics_file.exists()
        with open(agent_metrics_file, 'r') as f:
            data = json.loads(f.readline())
            assert data['task_id'] == "task-001"
            assert data['status'] == "completed"

    def test_track_task_optional_fields(self, agent_metrics_file, mock_datetime):
        """Test track_task with minimal required fields."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        outcome = metrics.track_task(
            task_id="task-002",
            session_id="session-002",
            status="partial"
        )

        assert outcome.task_id == "task-002"
        assert outcome.status == "partial"
        assert outcome.quality_score is None
        assert outcome.completion_pct == 0.0
        assert outcome.tool_calls_total == 0

    def test_track_subagent(self, temp_metrics_dir, mock_datetime):
        """Test track_subagent creates entry in agent_task_metrics.jsonl."""
        metrics = agent_metrics.AgentMetrics(
            metrics_file=temp_metrics_dir / "agent_metrics.jsonl"
        )

        entry = metrics.track_subagent(
            agent_type="Explore",
            model="haiku",
            description="Search for files",
            success=True,
            session_id="session-003",
            complexity_score=5.0,
            metadata={"files_found": 10}
        )

        assert entry['agent_type'] == "Explore"
        assert entry['model'] == "haiku"
        assert entry['success'] is True
        assert entry['complexity_score'] == 5.0

        # Verify file was written
        subagent_file = temp_metrics_dir / "agent_task_metrics.jsonl"
        assert subagent_file.exists()
        with open(subagent_file, 'r') as f:
            data = json.loads(f.readline())
            assert data['agent_type'] == "Explore"

    def test_load_outcomes_empty_file(self, agent_metrics_file):
        """Test load_outcomes with non-existent file."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)
        outcomes = metrics.load_outcomes()
        assert outcomes == []

    def test_load_outcomes_with_data(self, agent_metrics_file, mock_datetime):
        """Test load_outcomes loads data correctly."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        # Track 3 tasks
        for i in range(3):
            metrics.track_task(
                task_id=f"task-{i}",
                session_id="session-001",
                status="completed",
                quality_score=4.0
            )

        outcomes = metrics.load_outcomes()
        assert len(outcomes) == 3
        assert all(isinstance(o, agent_metrics.TaskOutcome) for o in outcomes)

    def test_load_outcomes_filter_by_session(self, agent_metrics_file, mock_datetime):
        """Test load_outcomes filters by session_id."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        # Track tasks in different sessions
        metrics.track_task(task_id="task-1", session_id="session-A", status="completed")
        metrics.track_task(task_id="task-2", session_id="session-B", status="completed")
        metrics.track_task(task_id="task-3", session_id="session-A", status="completed")

        outcomes = metrics.load_outcomes(session_id="session-A")
        assert len(outcomes) == 2
        assert all(o.session_id == "session-A" for o in outcomes)

    def test_load_outcomes_with_limit(self, agent_metrics_file, mock_datetime):
        """Test load_outcomes respects limit parameter."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        # Track 5 tasks
        for i in range(5):
            metrics.track_task(task_id=f"task-{i}", session_id="session-001", status="completed")

        outcomes = metrics.load_outcomes(limit=3)
        assert len(outcomes) == 3

    def test_load_outcomes_skips_invalid_json(self, agent_metrics_file):
        """Test load_outcomes skips malformed JSON lines."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        # Write mix of valid and invalid JSON
        with open(agent_metrics_file, 'w') as f:
            f.write('{"task_id": "task-1", "status": "completed", "session_id": "s1", "timestamp": "2026-02-06"}\n')
            f.write('invalid json line\n')
            f.write('{"task_id": "task-2", "status": "completed", "session_id": "s1", "timestamp": "2026-02-06"}\n')

        outcomes = metrics.load_outcomes()
        assert len(outcomes) == 2

    def test_calculate_agent_effectiveness_perfect_score(self):
        """Test calculate_agent_effectiveness with perfect inputs."""
        metrics = agent_metrics.AgentMetrics()

        score = metrics.calculate_agent_effectiveness(
            task_completion_rate=100.0,
            tool_efficiency=100.0,
            error_recovery_rate=100.0,
            avg_quality_score=5.0
        )

        assert score == 100.0

    def test_calculate_agent_effectiveness_zero_score(self):
        """Test calculate_agent_effectiveness with zero inputs."""
        metrics = agent_metrics.AgentMetrics()

        score = metrics.calculate_agent_effectiveness(
            task_completion_rate=0.0,
            tool_efficiency=0.0,
            error_recovery_rate=0.0,
            avg_quality_score=1.0
        )

        assert score == 0.0

    def test_calculate_agent_effectiveness_weighted_formula(self):
        """Test calculate_agent_effectiveness uses correct weights."""
        metrics = agent_metrics.AgentMetrics()

        # 40% completion + 25% tool + 20% recovery + 15% quality
        score = metrics.calculate_agent_effectiveness(
            task_completion_rate=80.0,   # 40% * 80 = 32
            tool_efficiency=60.0,         # 25% * 60 = 15
            error_recovery_rate=100.0,    # 20% * 100 = 20
            avg_quality_score=3.0         # 15% * ((3-1)/4*100) = 15% * 50 = 7.5
        )

        expected = 32 + 15 + 20 + 7.5
        assert score == expected

    def test_generate_session_quality_no_data(self, agent_metrics_file):
        """Test generate_session_quality with no data returns None."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)
        quality = metrics.generate_session_quality("nonexistent-session")
        assert quality is None

    def test_generate_session_quality_with_data(self, agent_metrics_file, mock_datetime):
        """Test generate_session_quality calculates metrics correctly."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        # Track 5 completed, 2 partial, 1 failed
        for i in range(5):
            metrics.track_task(
                task_id=f"task-{i}",
                session_id="session-001",
                status="completed",
                quality_score=4.5,
                completion_pct=100.0,
                tool_calls_total=10,
                tool_calls_successful=10,
                tool_calls_redundant=0,
                errors_total=0,
                errors_recovered=0
            )

        for i in range(5, 7):
            metrics.track_task(
                task_id=f"task-{i}",
                session_id="session-001",
                status="partial",
                quality_score=3.0,
                completion_pct=60.0,
                tool_calls_total=10,
                tool_calls_successful=8,
                tool_calls_redundant=2
            )

        metrics.track_task(
            task_id="task-7",
            session_id="session-001",
            status="failed",
            quality_score=1.5,
            completion_pct=20.0,
            tool_calls_total=5,
            tool_calls_successful=3,
            tool_calls_redundant=1,
            errors_total=3,
            errors_recovered=1
        )

        quality = metrics.generate_session_quality("session-001")

        assert quality is not None
        assert quality.tasks_attempted == 8
        assert quality.tasks_completed == 5
        assert quality.tasks_partial == 2
        assert quality.tasks_failed == 1
        assert quality.avg_quality_score > 0
        assert quality.agent_effectiveness_score > 0

    def test_generate_report_empty_data(self, agent_metrics_file):
        """Test generate_report with no data returns empty report."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)
        report = metrics.generate_report()

        assert report.total_tasks == 0
        assert report.total_sessions == 0
        assert report.task_completion_rate == 0.0
        assert report.by_status == {}

    def test_generate_report_with_data(self, agent_metrics_file, mock_datetime):
        """Test generate_report calculates all metrics."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        # Track tasks
        for i in range(6):
            metrics.track_task(
                task_id=f"task-{i}",
                session_id="session-001",
                status="completed",
                quality_score=4.0,
                completion_pct=100.0,
                tool_calls_total=10,
                tool_calls_successful=10,
                errors_total=1,
                errors_recovered=1,
                user_corrections=0
            )

        for i in range(6, 10):
            metrics.track_task(
                task_id=f"task-{i}",
                session_id="session-001",
                status="partial",
                quality_score=3.0,
                completion_pct=60.0
            )

        report = metrics.generate_report()

        assert report.total_tasks == 10
        assert report.total_sessions == 1
        assert report.task_completion_rate == 60.0  # 6/10 completed
        assert report.task_partial_rate == 40.0
        assert report.by_status['completed'] == 6
        assert report.by_status['partial'] == 4

    def test_format_report_includes_all_sections(self, agent_metrics_file, mock_datetime):
        """Test format_report includes all required sections."""
        metrics = agent_metrics.AgentMetrics(metrics_file=agent_metrics_file)

        metrics.track_task(
            task_id="task-1",
            session_id="session-001",
            status="completed",
            quality_score=4.5,
            completion_pct=100.0
        )

        report = metrics.generate_report()
        formatted = metrics.format_report(report)

        assert "AGENT QUALITY REPORT" in formatted
        assert "Task Completion:" in formatted
        assert "Quality Metrics:" in formatted
        assert "Tool Efficiency:" in formatted
        assert "Error Recovery:" in formatted
        assert "AGENT EFFECTIVENESS SCORE:" in formatted


# ============================================================================
# TEST CLASS: TaskCompletion
# ============================================================================

class TestTaskCompletion:
    """Tests for task_completion.py"""

    def test_init(self):
        """Test TaskCompletionAnalyzer initialization."""
        analyzer = task_completion.TaskCompletionAnalyzer()
        assert analyzer.agent_metrics is not None
        assert len(analyzer.task_start_patterns) > 0
        assert len(analyzer.completion_indicators) > 0

    def test_is_task_request_positive_patterns(self):
        """Test _is_task_request detects task patterns."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        test_cases = [
            "Create a new module for authentication",
            "Implement user login feature",
            "Deploy application to production",
            "Fix bug in payment processing",
            "Write comprehensive unit tests"
        ]

        for message in test_cases:
            assert analyzer._is_task_request(message) is True

    def test_is_task_request_negative_cases(self):
        """Test _is_task_request rejects non-tasks."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        test_cases = [
            "What is the current status?",
            "Can you explain this code?",
            "I need help understanding",
            "Hello, how are you?"
        ]

        for message in test_cases:
            assert analyzer._is_task_request(message) is False

    def test_extract_criteria_from_message(self):
        """Test _extract_criteria extracts actions and indicators."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        message = "Create comprehensive unit tests and deploy to production"
        criteria = analyzer._extract_criteria(message)

        assert criteria is not None
        assert 'create' in criteria.required_actions
        assert 'deploy' in criteria.required_actions
        assert len(criteria.failure_indicators) > 0

    def test_extract_criteria_with_quality_keywords(self):
        """Test _extract_criteria detects quality indicators."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        message = "Implement robust, secure authentication with comprehensive tests"
        criteria = analyzer._extract_criteria(message)

        assert criteria is not None
        assert 'robust' in criteria.quality_indicators or 'secure' in criteria.quality_indicators

    def test_detect_tasks_from_session_no_file(self):
        """Test detect_tasks_from_session raises error for missing file."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.detect_tasks_from_session(Path("/nonexistent/session.jsonl"))

    def test_detect_tasks_from_session_with_tasks(self, session_file):
        """Test detect_tasks_from_session detects tasks from session file."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        # Write sample session with tasks
        with open(session_file, 'w') as f:
            f.write(json.dumps({"type": "input", "text": "Create a new module"}) + '\n')
            f.write(json.dumps({"type": "output", "text": "Creating module..."}) + '\n')
            f.write(json.dumps({"type": "input", "text": "Deploy to production"}) + '\n')

        tasks = analyzer.detect_tasks_from_session(session_file)
        assert len(tasks) >= 2

    def test_action_completed_positive(self):
        """Test _action_completed detects completed actions."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        content = "Created user authentication module. Task completed successfully ✅"
        assert analyzer._action_completed("create", content) is True

    def test_action_completed_negative(self):
        """Test _action_completed returns False when action not completed."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        content = "Started working on creating the module"
        # Should be False because no completion indicator
        result = analyzer._action_completed("deploy", content)
        # deploy not in content, so should be False
        assert result is False

    def test_calculate_quality_score_perfect(self):
        """Test _calculate_quality_score with perfect completion."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        score = analyzer._calculate_quality_score(
            completion_pct=100.0,
            quality_found=5,
            quality_total=5,
            failures_found=0
        )

        assert 4.5 <= score <= 5.0

    def test_calculate_quality_score_with_failures(self):
        """Test _calculate_quality_score penalizes failures."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        score_no_failures = analyzer._calculate_quality_score(
            completion_pct=80.0,
            quality_found=3,
            quality_total=5,
            failures_found=0
        )

        score_with_failures = analyzer._calculate_quality_score(
            completion_pct=80.0,
            quality_found=3,
            quality_total=5,
            failures_found=3
        )

        assert score_with_failures < score_no_failures

    def test_calculate_quality_score_bounds(self):
        """Test _calculate_quality_score clamps to 1.0-5.0."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        # Test upper bound
        score_high = analyzer._calculate_quality_score(
            completion_pct=100.0,
            quality_found=10,
            quality_total=5,
            failures_found=0
        )
        assert 1.0 <= score_high <= 5.0

        # Test lower bound
        score_low = analyzer._calculate_quality_score(
            completion_pct=0.0,
            quality_found=0,
            quality_total=5,
            failures_found=10
        )
        assert 1.0 <= score_low <= 5.0

    def test_calculate_confidence(self):
        """Test _calculate_confidence calculation."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        # More criteria and content = higher confidence
        conf_high = analyzer._calculate_confidence(
            required_total=5,
            optional_total=3,
            quality_total=4,
            content_lines=100
        )

        conf_low = analyzer._calculate_confidence(
            required_total=1,
            optional_total=0,
            quality_total=0,
            content_lines=10
        )

        assert conf_high > conf_low
        assert 0.0 <= conf_high <= 1.0
        assert 0.0 <= conf_low <= 1.0

    def test_generate_reasoning(self):
        """Test _generate_reasoning generates explanations."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        reasoning = analyzer._generate_reasoning(
            status="completed",
            required_completed=3,
            required_total=3,
            optional_completed=1,
            optional_total=2,
            quality_found=2,
            failures_found=0
        )

        assert "completed" in reasoning.lower()
        assert "3/3" in reasoning

    def test_assess_task(self, session_file):
        """Test assess_task full workflow."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        # Write session with completed task
        with open(session_file, 'w') as f:
            f.write(json.dumps({"type": "input", "text": "Create auth module"}) + '\n')
            f.write(json.dumps({"type": "output", "text": "Creating authentication module..."}) + '\n')
            f.write(json.dumps({"type": "output", "text": "Created successfully ✅"}) + '\n')

        criteria = task_completion.TaskCriteria(
            task_description="Create auth module",
            required_actions=["create"],
            optional_actions=[],
            quality_indicators=["tested"],
            failure_indicators=["error", "failed"]
        )

        assessment = analyzer.assess_task(criteria, session_file, task_start_index=0)

        assert assessment.task_id is not None
        assert assessment.status in ["completed", "partial", "failed", "abandoned"]
        assert 0.0 <= assessment.completion_pct <= 120.0  # Can go over 100 with bonus
        assert 1.0 <= assessment.quality_score <= 5.0

    def test_format_assessment(self):
        """Test format_assessment produces readable output."""
        analyzer = task_completion.TaskCompletionAnalyzer()

        assessment = task_completion.TaskAssessment(
            task_id="task-001",
            task_description="Test task",
            status="completed",
            completion_pct=100.0,
            quality_score=4.5,
            required_completed=3,
            required_total=3,
            optional_completed=1,
            optional_total=2,
            quality_indicators_found=2,
            quality_indicators_total=3,
            failure_indicators_found=0,
            confidence=0.85,
            reasoning="Task completed successfully"
        )

        formatted = analyzer.format_assessment(assessment)

        assert "Task Completion Assessment" in formatted
        assert "completed" in formatted.lower()
        assert "100.0%" in formatted
        assert "4.5/5.0" in formatted


# ============================================================================
# TEST CLASS: LatencyTracker
# ============================================================================

class TestLatencyTracker:
    """Tests for latency_tracker.py"""

    def test_init_default_path(self, temp_metrics_dir):
        """Test LatencyTracker initialization with default path."""
        with patch('latency_tracker.Path.home', return_value=temp_metrics_dir.parent.parent):
            tracker = latency_tracker.LatencyTracker()
            assert tracker.metrics_file.name == "latency_metrics.jsonl"

    def test_init_custom_path(self, latency_metrics_file):
        """Test LatencyTracker initialization with custom path."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)
        assert tracker.metrics_file == latency_metrics_file

    def test_track_response_creates_metric(self, latency_metrics_file, mock_datetime):
        """Test track_response creates LatencyMetric and writes to file."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        metric = tracker.track_response(
            session_id="session-001",
            request_number=1,
            ttft_ms=500.0,
            total_time_ms=2000.0,
            input_tokens=1500,
            output_tokens=800,
            model="sonnet",
            cached_tokens=1200,
            tool_calls=2
        )

        assert metric.session_id == "session-001"
        assert metric.ttft_ms == 500.0
        assert metric.total_time_ms == 2000.0
        assert metric.throughput_tok_per_sec is not None

        # Verify file was written
        assert latency_metrics_file.exists()
        with open(latency_metrics_file, 'r') as f:
            data = json.loads(f.readline())
            assert data['session_id'] == "session-001"
            assert data['ttft_ms'] == 500.0

    def test_track_response_calculates_throughput(self, latency_metrics_file):
        """Test track_response calculates throughput correctly."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        metric = tracker.track_response(
            session_id="session-001",
            request_number=1,
            total_time_ms=1000.0,  # 1 second
            output_tokens=100
        )

        # 100 tokens / 1000ms * 1000 = 100 tokens/sec
        assert metric.throughput_tok_per_sec == 100.0

    def test_track_response_no_throughput_when_zero_time(self, latency_metrics_file):
        """Test track_response doesn't calculate throughput with zero time."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        metric = tracker.track_response(
            session_id="session-001",
            request_number=1,
            total_time_ms=0.0,
            output_tokens=100
        )

        assert metric.throughput_tok_per_sec is None

    def test_track_tool_latency(self, temp_metrics_dir, mock_datetime):
        """Test track_tool_latency creates entry in tool_latency.jsonl."""
        tracker = latency_tracker.LatencyTracker(
            metrics_file=temp_metrics_dir / "latency_metrics.jsonl"
        )

        entry = tracker.track_tool_latency(
            tool_name="Read",
            latency_ms=150.0,
            session_id="session-001",
            response_size=5000,
            metadata={"file_path": "/path/to/file"}
        )

        assert entry['tool_name'] == "Read"
        assert entry['latency_ms'] == 150.0
        assert entry['response_size'] == 5000

        # Verify file was written
        tool_latency_file = temp_metrics_dir / "tool_latency.jsonl"
        assert tool_latency_file.exists()

    def test_load_metrics_empty_file(self, latency_metrics_file):
        """Test load_metrics with non-existent file."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)
        metrics = tracker.load_metrics()
        assert metrics == []

    def test_load_metrics_with_data(self, latency_metrics_file, mock_datetime):
        """Test load_metrics loads data correctly."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        # Track 3 responses
        for i in range(3):
            tracker.track_response(
                session_id="session-001",
                request_number=i,
                ttft_ms=500.0,
                total_time_ms=2000.0
            )

        metrics = tracker.load_metrics()
        assert len(metrics) == 3
        assert all(isinstance(m, latency_tracker.LatencyMetric) for m in metrics)

    def test_load_metrics_filter_by_session(self, latency_metrics_file, mock_datetime):
        """Test load_metrics filters by session_id."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        tracker.track_response(session_id="session-A", request_number=1, ttft_ms=500.0)
        tracker.track_response(session_id="session-B", request_number=1, ttft_ms=600.0)
        tracker.track_response(session_id="session-A", request_number=2, ttft_ms=700.0)

        metrics = tracker.load_metrics(session_id="session-A")
        assert len(metrics) == 2
        assert all(m.session_id == "session-A" for m in metrics)

    def test_load_metrics_with_limit(self, latency_metrics_file, mock_datetime):
        """Test load_metrics respects limit parameter."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        for i in range(5):
            tracker.track_response(session_id="session-001", request_number=i, ttft_ms=500.0)

        metrics = tracker.load_metrics(limit=3)
        assert len(metrics) == 3

    def test_calculate_percentiles_with_data(self):
        """Test calculate_percentiles calculates stats correctly."""
        tracker = latency_tracker.LatencyTracker()

        values = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        stats = tracker.calculate_percentiles(values)

        assert stats.p50 == 550.0  # Median
        assert stats.mean == 550.0
        assert stats.min == 100
        assert stats.max == 1000
        assert stats.count == 10
        assert stats.stddev > 0

    def test_calculate_percentiles_empty_list(self):
        """Test calculate_percentiles with empty list."""
        tracker = latency_tracker.LatencyTracker()

        stats = tracker.calculate_percentiles([])

        assert stats.p50 == 0
        assert stats.mean == 0
        assert stats.count == 0

    def test_calculate_percentiles_small_dataset(self):
        """Test calculate_percentiles with small dataset."""
        tracker = latency_tracker.LatencyTracker()

        values = [100, 200]
        stats = tracker.calculate_percentiles(values)

        assert stats.p50 == 150.0  # Median of 2 values
        assert stats.count == 2
        # For small datasets, p90/p95/p99 should use last value
        assert stats.p90 == 200
        assert stats.p99 == 200

    def test_generate_report_empty_data(self, latency_metrics_file):
        """Test generate_report with no data returns empty report."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)
        report = tracker.generate_report()

        assert report.total_requests == 0
        assert report.ttft is None
        assert report.degradation_detected is False
        assert report.trend == "stable"

    def test_generate_report_with_data(self, latency_metrics_file, mock_datetime):
        """Test generate_report calculates all metrics."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        # Track 10 responses
        for i in range(10):
            tracker.track_response(
                session_id="session-001",
                request_number=i,
                ttft_ms=500.0 + (i * 50),
                total_time_ms=2000.0 + (i * 100),
                output_tokens=800,
                model="sonnet",
                cached_tokens=1200 if i % 2 == 0 else 0
            )

        report = tracker.generate_report()

        assert report.total_requests == 10
        assert report.ttft is not None
        assert report.ttft.count == 10
        assert report.total_time is not None
        assert report.throughput is not None
        assert len(report.by_model) > 0
        assert len(report.cached_vs_fresh) > 0

    def test_breakdown_by_model(self, latency_metrics_file, mock_datetime):
        """Test _breakdown_by_model groups metrics correctly."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        # Track responses with different models
        for i in range(3):
            tracker.track_response(
                session_id="session-001",
                request_number=i,
                ttft_ms=500.0,
                total_time_ms=2000.0,
                model="haiku"
            )

        for i in range(3, 6):
            tracker.track_response(
                session_id="session-001",
                request_number=i,
                ttft_ms=800.0,
                total_time_ms=3000.0,
                model="sonnet"
            )

        metrics = tracker.load_metrics()
        by_model = tracker._breakdown_by_model(metrics)

        assert 'haiku' in by_model
        assert 'sonnet' in by_model
        assert by_model['haiku']['count'] == 3
        assert by_model['sonnet']['count'] == 3
        assert by_model['haiku']['avg_ttft'] < by_model['sonnet']['avg_ttft']

    def test_breakdown_by_cache(self, latency_metrics_file, mock_datetime):
        """Test _breakdown_by_cache separates cached vs fresh requests."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        # Cached requests
        for i in range(3):
            tracker.track_response(
                session_id="session-001",
                request_number=i,
                ttft_ms=300.0,
                total_time_ms=1000.0,
                cached_tokens=1200
            )

        # Fresh requests
        for i in range(3, 6):
            tracker.track_response(
                session_id="session-001",
                request_number=i,
                ttft_ms=600.0,
                total_time_ms=2500.0,
                cached_tokens=0
            )

        metrics = tracker.load_metrics()
        cached_vs_fresh = tracker._breakdown_by_cache(metrics)

        assert 'cached' in cached_vs_fresh
        assert 'fresh' in cached_vs_fresh
        assert cached_vs_fresh['cached']['count'] == 3
        assert cached_vs_fresh['fresh']['count'] == 3
        # Cached should be faster
        assert cached_vs_fresh['cached']['avg_total_time'] < cached_vs_fresh['fresh']['avg_total_time']

    def test_detect_degradation_stable(self):
        """Test _detect_degradation with stable performance."""
        tracker = latency_tracker.LatencyTracker()

        # Create 20 metrics with stable latency
        metrics = []
        for i in range(20):
            metric = latency_tracker.LatencyMetric(
                timestamp=datetime(2026, 2, 6, 12, i).isoformat(),
                session_id="session-001",
                request_number=i,
                ttft_ms=500.0,
                total_time_ms=2000.0
            )
            metrics.append(metric)

        degradation, trend = tracker._detect_degradation(metrics)

        assert degradation is False
        assert trend == "stable"

    def test_detect_degradation_degrading(self):
        """Test _detect_degradation detects performance degradation."""
        tracker = latency_tracker.LatencyTracker()

        # Create 20 metrics with increasing latency
        metrics = []
        for i in range(20):
            latency = 2000.0 if i < 10 else 3000.0  # 50% increase
            metric = latency_tracker.LatencyMetric(
                timestamp=datetime(2026, 2, 6, 12, i).isoformat(),
                session_id="session-001",
                request_number=i,
                total_time_ms=latency
            )
            metrics.append(metric)

        degradation, trend = tracker._detect_degradation(metrics)

        assert degradation is True
        assert trend == "degrading"

    def test_detect_degradation_improving(self):
        """Test _detect_degradation detects performance improvement."""
        tracker = latency_tracker.LatencyTracker()

        # Create 20 metrics with decreasing latency
        metrics = []
        for i in range(20):
            latency = 3000.0 if i < 10 else 2000.0  # 33% decrease
            metric = latency_tracker.LatencyMetric(
                timestamp=datetime(2026, 2, 6, 12, i).isoformat(),
                session_id="session-001",
                request_number=i,
                total_time_ms=latency
            )
            metrics.append(metric)

        degradation, trend = tracker._detect_degradation(metrics)

        assert degradation is False
        assert trend == "improving"

    def test_detect_degradation_insufficient_data(self):
        """Test _detect_degradation with insufficient data."""
        tracker = latency_tracker.LatencyTracker()

        # Only 5 metrics (need 20 for trend analysis)
        metrics = []
        for i in range(5):
            metric = latency_tracker.LatencyMetric(
                timestamp=datetime(2026, 2, 6, 12, i).isoformat(),
                session_id="session-001",
                request_number=i,
                total_time_ms=2000.0
            )
            metrics.append(metric)

        degradation, trend = tracker._detect_degradation(metrics)

        assert degradation is False
        assert trend == "stable"

    def test_format_report_includes_all_sections(self, latency_metrics_file, mock_datetime):
        """Test format_report includes all required sections."""
        tracker = latency_tracker.LatencyTracker(metrics_file=latency_metrics_file)

        # Track some data
        for i in range(5):
            tracker.track_response(
                session_id="session-001",
                request_number=i,
                ttft_ms=500.0,
                total_time_ms=2000.0,
                output_tokens=800,
                model="sonnet"
            )

        report = tracker.generate_report()
        formatted = tracker.format_report(report)

        assert "LATENCY & PERFORMANCE REPORT" in formatted
        assert "TTFT" in formatted
        assert "Total Response Time" in formatted
        assert "Throughput" in formatted
        assert "Performance Trend:" in formatted


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
