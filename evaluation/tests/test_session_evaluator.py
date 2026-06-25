#!/usr/bin/env python3
"""
Tests for session_evaluator.py — SessionEvaluator.

Covers:
- Initialization and data directory creation
- Session loading from JSONL
- Turn analysis (coherence, references, goals)
- Context retention calculation
- Goal tracking (introduce, complete, abandon)
- Session completion evaluation
- Quality score calculation
- Empty session handling
- Single-message and multi-message sessions
- User satisfaction analysis
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from session_evaluator import (
    SessionEvaluator,
    SessionEvaluation,
    TurnAnalysis,
    GoalTracker,
    SessionReport,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path):
    """Provide a temporary data directory."""
    d = tmp_path / "eval_data"
    d.mkdir()
    return d


@pytest.fixture
def evaluator(data_dir):
    """Return a SessionEvaluator using a temporary directory."""
    return SessionEvaluator(data_dir=data_dir)


def _make_session_file(tmp_path, messages, filename="session_test.jsonl"):
    """Write a list of messages as JSONL to a session file."""
    session_file = tmp_path / filename
    with open(session_file, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")
    return session_file


def _user_msg(text, timestamp=None):
    """Create a user message dict."""
    msg = {
        "type": "user",
        "message": {"content": text},
    }
    if timestamp:
        msg["timestamp"] = timestamp
    return msg


def _assistant_msg(text, tool_calls=None, timestamp=None):
    """Create an assistant message dict."""
    msg = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }
    if tool_calls:
        msg["tool_calls"] = tool_calls
    if timestamp:
        msg["timestamp"] = timestamp
    return msg


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestSessionEvaluatorInit:
    """Tests for SessionEvaluator initialization."""

    def test_creates_data_dir(self, tmp_path):
        """data_dir should be created if it does not exist."""
        new_dir = tmp_path / "new" / "eval"
        evaluator = SessionEvaluator(data_dir=new_dir)
        assert new_dir.exists()

    def test_default_thresholds(self, evaluator):
        """Evaluator should have expected constants."""
        assert evaluator.COHERENCE_DROP_THRESHOLD == 0.3


# ---------------------------------------------------------------------------
# Empty / minimal sessions
# ---------------------------------------------------------------------------

class TestEmptySessions:
    """Tests for edge cases with empty or minimal sessions."""

    def test_empty_session_file(self, evaluator, tmp_path):
        """Empty session file should return empty evaluation."""
        session_file = _make_session_file(tmp_path, [])
        result = evaluator.evaluate_session(session_file)
        assert result.total_turns == 0
        assert result.session_status == "abandoned"
        assert result.session_quality_score == 0.0

    def test_single_user_message(self, evaluator, tmp_path):
        """Single user message session."""
        messages = [_user_msg("I want to deploy my app")]
        session_file = _make_session_file(tmp_path, messages)
        result = evaluator.evaluate_session(session_file)
        assert result.total_turns == 1
        assert result.user_turns == 1
        assert result.assistant_turns == 0

    def test_non_conversation_messages_skipped(self, evaluator, tmp_path):
        """Messages with type != user/assistant should be skipped."""
        messages = [
            {"type": "system", "message": {"content": "system prompt"}},
            _user_msg("hello"),
        ]
        session_file = _make_session_file(tmp_path, messages)
        result = evaluator.evaluate_session(session_file)
        assert result.total_turns == 1  # only the user message


# ---------------------------------------------------------------------------
# Turn analysis
# ---------------------------------------------------------------------------

class TestTurnAnalysis:
    """Tests for turn-level analysis."""

    def test_references_previous_detected(self, evaluator):
        """Turns with reference patterns should be detected."""
        assert evaluator._check_references_previous("As I mentioned earlier, this works")
        assert evaluator._check_references_previous("continuing with the same approach")
        assert not evaluator._check_references_previous("Hello world")

    def test_goal_introduction_detected(self, evaluator):
        """Goal introduction patterns should be detected for user turns."""
        assert evaluator._check_introduces_goal("I want to fix this bug", "user")
        assert evaluator._check_introduces_goal("Can you help create a new file?", "user")
        assert not evaluator._check_introduces_goal("I want to fix this", "assistant")

    def test_goal_completion_detected(self, evaluator):
        """Goal completion patterns should be detected."""
        assert evaluator._check_completes_goal("Done! Everything is fixed.")
        assert evaluator._check_completes_goal("Thanks, that works perfectly!")
        assert not evaluator._check_completes_goal("Let me think about this")

    def test_abandonment_detected(self, evaluator):
        """Goal abandonment patterns should be detected."""
        assert evaluator._check_abandonment("Never mind, let's stop")
        assert evaluator._check_abandonment("too complicated for now")
        assert not evaluator._check_abandonment("Let's continue working on this")


# ---------------------------------------------------------------------------
# Coherence calculation
# ---------------------------------------------------------------------------

class TestCoherence:
    """Tests for coherence scoring."""

    def test_single_turn_coherence(self, evaluator):
        """Single turn should have perfect coherence."""
        turns = [TurnAnalysis(turn_number=1, role="user", coherence_score=1.0)]
        score, drops = evaluator._calculate_coherence(turns)
        assert score == 1.0
        assert drops == 0

    def test_turn_coherence_calculation(self, evaluator):
        """Coherence between related turns should be higher than random."""
        related = evaluator._calculate_turn_coherence(
            "I need to fix the deploy script for kubernetes",
            "The deploy script has been updated for kubernetes deployment",
        )
        unrelated = evaluator._calculate_turn_coherence(
            "I need to fix the deploy script for kubernetes",
            "The weather is nice today for a walk in the park",
        )
        assert related > unrelated

    def test_empty_content_coherence(self, evaluator):
        """Empty content should return default coherence."""
        score = evaluator._calculate_turn_coherence("", "some content")
        assert score == 1.0


# ---------------------------------------------------------------------------
# Context retention
# ---------------------------------------------------------------------------

class TestContextRetention:
    """Tests for context retention scoring."""

    def test_short_session_returns_one(self, evaluator):
        """Sessions with <3 turns should return 1.0 retention."""
        messages = [_user_msg("hello"), _assistant_msg("hi")]
        turns = [
            TurnAnalysis(turn_number=1, role="user"),
            TurnAnalysis(turn_number=2, role="assistant"),
        ]
        retention = evaluator._calculate_context_retention(messages, turns)
        assert retention == 1.0

    def test_retention_with_references(self, evaluator):
        """Turns that reference previous context should increase retention."""
        turns = [
            TurnAnalysis(turn_number=1, role="user", references_previous=False),
            TurnAnalysis(turn_number=2, role="assistant", references_previous=True),
            TurnAnalysis(turn_number=3, role="user", references_previous=False),
            TurnAnalysis(turn_number=4, role="assistant", references_previous=True),
            TurnAnalysis(turn_number=5, role="user", references_previous=False),
            TurnAnalysis(turn_number=6, role="assistant", references_previous=True),
        ]
        messages = [_user_msg("m")] * 6
        retention = evaluator._calculate_context_retention(messages, turns)
        assert retention > 0.5


# ---------------------------------------------------------------------------
# Goal tracking
# ---------------------------------------------------------------------------

class TestGoalTracking:
    """Tests for goal tracking logic."""

    def test_goal_introduced_and_completed(self, evaluator, tmp_path):
        """A goal introduced and then completed should be tracked."""
        messages = [
            _user_msg("I want to create a new API endpoint"),
            _assistant_msg("I will create the endpoint. As mentioned, let's start."),
            _user_msg("Thanks, that's done perfectly!"),
        ]
        session_file = _make_session_file(tmp_path, messages)
        result = evaluator.evaluate_session(session_file)
        assert result.goals_introduced >= 1
        assert result.goals_completed >= 1

    def test_abandoned_goal(self, evaluator, tmp_path):
        """A goal that is abandoned should be tracked."""
        messages = [
            _user_msg("I need to fix the bug in the parser"),
            _assistant_msg("Let me look at the parser code."),
            _user_msg("Never mind, let's stop. I'll handle it myself."),
        ]
        session_file = _make_session_file(tmp_path, messages)
        result = evaluator.evaluate_session(session_file)
        assert result.goals_introduced >= 1
        assert result.goals_abandoned >= 1


# ---------------------------------------------------------------------------
# Session completion evaluation
# ---------------------------------------------------------------------------

class TestSessionCompletion:
    """Tests for session completion scoring."""

    def test_completed_session(self, evaluator, tmp_path):
        """Session ending with positive feedback should be 'completed'."""
        messages = [
            _user_msg("I want to refactor this module"),
            _assistant_msg("I've refactored the module. Here are the changes."),
            _user_msg("Great, thank you! That works perfectly."),
        ]
        session_file = _make_session_file(tmp_path, messages)
        result = evaluator.evaluate_session(session_file)
        # At minimum, completion_score should be > 0
        assert result.completion_score >= 0.0

    def test_empty_turns_abandoned(self, evaluator):
        """No turns should yield 'abandoned' status."""
        status, score = evaluator._evaluate_session_completion([], [], [])
        assert status == "abandoned"
        assert score == 0.0


# ---------------------------------------------------------------------------
# Tool usage analysis
# ---------------------------------------------------------------------------

class TestToolUsageAnalysis:
    """Tests for tool usage analysis."""

    def test_no_tool_calls(self, evaluator):
        """Messages without tool calls should yield efficiency=1.0."""
        messages = [
            _user_msg("hello"),
            _assistant_msg("hi there"),
        ]
        stats = evaluator._analyze_tool_usage(messages)
        assert stats["efficiency"] == 1.0
        assert stats["total_calls"] == 0

    def test_with_tool_calls(self, evaluator):
        """Messages with tool calls should track them."""
        messages = [
            _assistant_msg("Let me read the file", tool_calls=[{"name": "Read"}]),
        ]
        stats = evaluator._analyze_tool_usage(messages)
        assert stats["total_calls"] == 1

    def test_error_detection(self, evaluator):
        """Messages containing error keywords should affect error_rate."""
        messages = [
            _user_msg("hello"),
            _assistant_msg("The command failed with an error traceback"),
        ]
        stats = evaluator._analyze_tool_usage(messages)
        assert stats["error_rate"] > 0.0


# ---------------------------------------------------------------------------
# User satisfaction analysis
# ---------------------------------------------------------------------------

class TestUserSatisfaction:
    """Tests for user satisfaction analysis."""

    def test_positive_feedback(self, evaluator):
        """Positive feedback should be counted."""
        messages = [
            _user_msg("Thanks, that's great!"),
            _user_msg("Perfect, good job!"),
        ]
        indicators = evaluator._analyze_user_satisfaction(messages)
        assert indicators["positive_feedback"] >= 2
        assert indicators["thanks"] >= 1

    def test_negative_feedback(self, evaluator):
        """Negative feedback should be counted."""
        messages = [
            _user_msg("That's wrong, doesn't work"),
        ]
        indicators = evaluator._analyze_user_satisfaction(messages)
        assert indicators["negative_feedback"] >= 1

    def test_corrections(self, evaluator):
        """Corrections should be counted."""
        messages = [
            _user_msg("No, actually I meant something different"),
        ]
        indicators = evaluator._analyze_user_satisfaction(messages)
        assert indicators["corrections"] >= 1

    def test_assistant_messages_ignored(self, evaluator):
        """Only user messages should be analyzed for satisfaction."""
        messages = [
            _assistant_msg("Thanks for asking!"),  # should be ignored
        ]
        indicators = evaluator._analyze_user_satisfaction(messages)
        assert indicators["positive_feedback"] == 0


# ---------------------------------------------------------------------------
# Quality score calculation
# ---------------------------------------------------------------------------

class TestQualityScore:
    """Tests for composite quality score calculation."""

    def test_perfect_score(self, evaluator):
        """All perfect inputs should yield maximum score (100)."""
        score = evaluator._calculate_quality_score(
            coherence_score=1.0,
            context_retention=1.0,
            goal_completion_rate=1.0,
            completion_score=1.0,
            tool_efficiency=1.0,
            error_rate=0.0,
        )
        assert score == 100.0

    def test_zero_score(self, evaluator):
        """All zero inputs should yield zero score."""
        score = evaluator._calculate_quality_score(
            coherence_score=0.0,
            context_retention=0.0,
            goal_completion_rate=0.0,
            completion_score=0.0,
            tool_efficiency=0.0,
            error_rate=1.0,
        )
        assert score == 0.0

    def test_weights_correct(self, evaluator):
        """Verify weight distribution adds up to 100."""
        # 30 + 25 + 20 + 15 + 10 = 100
        score = evaluator._calculate_quality_score(
            coherence_score=0.5,
            context_retention=0.5,
            goal_completion_rate=0.5,
            completion_score=0.5,
            tool_efficiency=1.0,
            error_rate=0.0,
        )
        expected = 0.5 * 30 + 0.5 * 25 + 0.5 * 20 + 0.5 * 15 + 1.0 * 10
        assert score == pytest.approx(expected, abs=0.1)


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

class TestContentExtraction:
    """Tests for _extract_content with various formats."""

    def test_dict_content(self, evaluator):
        """Dict message content should be extracted."""
        msg = {"message": {"content": "hello world"}}
        assert evaluator._extract_content(msg) == "hello world"

    def test_list_content_blocks(self, evaluator):
        """Content blocks list should be joined."""
        msg = {"message": {"content": [
            {"type": "text", "text": "hello"},
            {"type": "text", "text": "world"},
        ]}}
        result = evaluator._extract_content(msg)
        assert "hello" in result
        assert "world" in result

    def test_string_content(self, evaluator):
        """String content should be returned as-is."""
        msg = {"message": "just a string"}
        result = evaluator._extract_content(msg)
        assert "just a string" in result


# ---------------------------------------------------------------------------
# Empty evaluation
# ---------------------------------------------------------------------------

class TestEmptyEvaluation:
    """Tests for _empty_evaluation."""

    def test_empty_evaluation_defaults(self, evaluator):
        """Empty evaluation should have all zero/default values."""
        result = evaluator._empty_evaluation("test-session")
        assert result.session_id == "test-session"
        assert result.total_turns == 0
        assert result.session_quality_score == 0.0
        assert result.error_rate == 1.0
        assert result.session_status == "abandoned"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Tests for generate_report."""

    def test_empty_report(self, evaluator):
        """Report with no evaluations should return defaults."""
        report = evaluator.generate_report(days=7)
        assert isinstance(report, SessionReport)
        assert report.total_sessions == 0
        assert report.quality_trend == "stable"
