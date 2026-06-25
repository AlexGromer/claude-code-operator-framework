#!/usr/bin/env python3
"""
Tests for multi_turn_optimizer.py — MultiTurnOptimizer.

Covers:
- Initialization and data directory creation
- Token estimation
- Content extraction from various message formats
- Message categorization
- Strategy selection (normal, checkpoint, aggressive)
- optimize_conversation with short/long conversations
- Normal strategy: selective retention
- Checkpoint strategy: summarization
- Aggressive strategy: maximum compression
- should_optimize check
- get_recommendation
- Cost analysis
- Edge cases: empty messages, single message
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from multi_turn_optimizer import (
    MultiTurnOptimizer,
    OptimizationResult,
    CostAnalysis,
    MessageSummary,
    HistoryRetentionPolicy,
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
def optimizer(data_dir):
    """Return a MultiTurnOptimizer using a temporary directory."""
    return MultiTurnOptimizer(data_dir=data_dir)


def _make_messages(count, content_template="Message number {i} with some content about code"):
    """Generate a list of messages for testing."""
    messages = []
    for i in range(count):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({
            "type": role,
            "message": {
                "content": [{
                    "type": "text",
                    "text": content_template.format(i=i),
                }]
            },
        })
    return messages


def _make_long_messages(count, words_per_msg=200):
    """Generate messages with many words to exceed token thresholds."""
    messages = []
    for i in range(count):
        role = "user" if i % 2 == 0 else "assistant"
        text = " ".join([f"word{j}" for j in range(words_per_msg)])
        messages.append({
            "type": role,
            "message": {"content": [{"type": "text", "text": text}]},
        })
    return messages


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestMultiTurnOptimizerInit:
    """Tests for MultiTurnOptimizer initialization."""

    def test_creates_data_dir(self, tmp_path):
        """data_dir should be created if it does not exist."""
        new_dir = tmp_path / "new" / "opt"
        optimizer = MultiTurnOptimizer(data_dir=new_dir)
        assert new_dir.exists()

    def test_default_policy(self, optimizer):
        """Default policy should have expected values."""
        assert optimizer.policy.recent_turns_to_keep == 10
        assert optimizer.policy.max_history_tokens == 50000
        assert optimizer.policy.summarization_threshold == 30000

    def test_patterns_defined(self, optimizer):
        """Content patterns should be defined for all categories."""
        expected_categories = [
            "code_artifacts", "decisions", "errors",
            "user_requirements", "explanations", "greetings",
        ]
        for cat in expected_categories:
            assert cat in optimizer.PATTERNS


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

class TestTokenEstimation:
    """Tests for token estimation methods."""

    def test_estimate_tokens_text(self, optimizer):
        """Should estimate based on word count * 1.3."""
        text = "one two three four five"  # 5 words
        tokens = optimizer._estimate_tokens_text(text)
        assert tokens == int(5 * 1.3)

    def test_estimate_tokens_messages(self, optimizer):
        """Should estimate total tokens across messages."""
        messages = _make_messages(3, content_template="word1 word2 word3")
        tokens = optimizer._estimate_tokens(messages)
        assert tokens > 0

    def test_empty_messages(self, optimizer):
        """Empty messages list should yield 0 tokens."""
        assert optimizer._estimate_tokens([]) == 0


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

class TestContentExtraction:
    """Tests for _extract_content with various formats."""

    def test_list_content_blocks(self, optimizer):
        """Content as list of blocks should be extracted."""
        msg = {"message": {"content": [
            {"type": "text", "text": "hello"},
            {"type": "text", "text": "world"},
        ]}}
        result = optimizer._extract_content(msg)
        assert "hello" in result
        assert "world" in result

    def test_string_content(self, optimizer):
        """String content should be returned."""
        msg = {"message": {"content": "simple string"}}
        result = optimizer._extract_content(msg)
        assert "simple string" in result

    def test_dict_without_content(self, optimizer):
        """Message without content key should return empty string."""
        msg = {"message": {}}
        result = optimizer._extract_content(msg)
        assert result == ""

    def test_empty_message(self, optimizer):
        """Empty message dict should return empty string."""
        msg = {}
        result = optimizer._extract_content(msg)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Message categorization
# ---------------------------------------------------------------------------

class TestMessageCategorization:
    """Tests for _categorize_messages."""

    def test_code_categorized(self, optimizer):
        """Messages with code blocks should be categorized as code_artifacts."""
        messages = [{
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "```python\nprint('hello')\n```"}]},
        }]
        categories = optimizer._categorize_messages(messages)
        assert categories[0] == "code_artifacts"

    def test_greeting_categorized(self, optimizer):
        """Simple greetings should be categorized as greetings."""
        messages = [{
            "type": "user",
            "message": {"content": [{"type": "text", "text": "hello thanks bye"}]},
        }]
        categories = optimizer._categorize_messages(messages)
        assert categories[0] == "greetings"

    def test_error_categorized(self, optimizer):
        """Error messages should be categorized as errors."""
        messages = [{
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "error: traceback exception failed"}]},
        }]
        categories = optimizer._categorize_messages(messages)
        assert categories[0] == "errors"

    def test_default_category(self, optimizer):
        """Unrecognizable content should default to explanations."""
        messages = [{
            "type": "user",
            "message": {"content": [{"type": "text", "text": "lorem ipsum dolor sit amet"}]},
        }]
        categories = optimizer._categorize_messages(messages)
        assert categories[0] == "explanations"


# ---------------------------------------------------------------------------
# Strategy selection
# ---------------------------------------------------------------------------

class TestStrategySelection:
    """Tests for _select_strategy."""

    def test_normal_strategy(self, optimizer):
        """Below summarization threshold should select 'normal'."""
        strategy = optimizer._select_strategy(20000, force_aggressive=False)
        assert strategy == "normal"

    def test_checkpoint_strategy(self, optimizer):
        """Between summarization and aggressive threshold should select 'checkpoint'."""
        strategy = optimizer._select_strategy(40000, force_aggressive=False)
        assert strategy == "checkpoint"

    def test_aggressive_strategy(self, optimizer):
        """Above aggressive threshold should select 'aggressive'."""
        strategy = optimizer._select_strategy(80000, force_aggressive=False)
        assert strategy == "aggressive"

    def test_force_aggressive(self, optimizer):
        """force_aggressive should always select 'aggressive'."""
        strategy = optimizer._select_strategy(1000, force_aggressive=True)
        assert strategy == "aggressive"


# ---------------------------------------------------------------------------
# optimize_conversation
# ---------------------------------------------------------------------------

class TestOptimizeConversation:
    """Tests for optimize_conversation."""

    def test_short_conversation_no_optimization(self, optimizer):
        """Conversations with <10 messages should not be optimized."""
        messages = _make_messages(5)
        optimized, result = optimizer.optimize_conversation(messages, "sess-1")
        assert result.strategy_used == "none"
        assert result.tokens_saved == 0
        assert len(optimized) == len(messages)

    def test_returns_optimization_result(self, optimizer):
        """Should return an OptimizationResult dataclass."""
        messages = _make_messages(25)
        _, result = optimizer.optimize_conversation(messages, "sess-1")
        assert isinstance(result, OptimizationResult)
        assert result.session_id == "sess-1"

    def test_saves_result(self, optimizer):
        """Optimization result should be saved to JSONL file."""
        messages = _make_messages(25)
        optimizer.optimize_conversation(messages, "sess-1")
        assert optimizer.optimizations_file.exists()

    def test_normal_strategy_retains_recent(self, optimizer):
        """Normal strategy should always retain recent messages."""
        messages = _make_messages(15)
        optimized, result = optimizer.optimize_conversation(messages, "sess-1")
        # Recent messages (last 10) should be retained
        assert len(optimized) >= min(10, len(messages))


# ---------------------------------------------------------------------------
# Aggressive strategy
# ---------------------------------------------------------------------------

class TestAggressiveStrategy:
    """Tests for aggressive optimization strategy."""

    def test_aggressive_reduces_messages(self, optimizer):
        """Aggressive strategy should significantly reduce message count."""
        messages = _make_long_messages(30, words_per_msg=300)
        optimized, result = optimizer.optimize_conversation(
            messages, "sess-1", force_aggressive=True,
        )
        assert result.strategy_used == "aggressive"
        assert len(optimized) < len(messages)
        assert result.tokens_saved > 0

    def test_aggressive_keeps_recent(self, optimizer):
        """Aggressive strategy should keep at most 5 recent messages."""
        messages = _make_long_messages(20, words_per_msg=300)
        optimized, result = optimizer.optimize_conversation(
            messages, "sess-1", force_aggressive=True,
        )
        # Recent messages (5) + summary messages
        # At minimum, recent 5 should be in optimized
        assert len(optimized) <= 6  # 5 recent + 1 summary


# ---------------------------------------------------------------------------
# should_optimize
# ---------------------------------------------------------------------------

class TestShouldOptimize:
    """Tests for should_optimize."""

    def test_short_conversation_false(self, optimizer):
        """Short conversations should not need optimization."""
        messages = _make_messages(10)
        assert optimizer.should_optimize(messages) is False

    def test_long_conversation_with_many_tokens(self, optimizer):
        """Long conversations exceeding threshold should need optimization."""
        messages = _make_long_messages(50, words_per_msg=500)
        assert optimizer.should_optimize(messages) is True


# ---------------------------------------------------------------------------
# get_recommendation
# ---------------------------------------------------------------------------

class TestGetRecommendation:
    """Tests for get_recommendation."""

    def test_no_optimization_needed(self, optimizer):
        """Short conversations should get 'no optimization' recommendation."""
        messages = _make_messages(5)
        rec = optimizer.get_recommendation(messages)
        assert rec["should_optimize"] is False
        assert rec["recommended_strategy"] == "none"

    def test_checkpoint_recommendation(self, optimizer):
        """Moderate conversations should get 'checkpoint' recommendation."""
        # Create messages that exceed summarization_threshold (30000 tokens)
        messages = _make_long_messages(30, words_per_msg=800)
        rec = optimizer.get_recommendation(messages)
        if rec["should_optimize"]:
            assert rec["recommended_strategy"] in ("checkpoint", "aggressive")
            assert rec["estimated_savings"] > 0

    def test_aggressive_recommendation(self, optimizer):
        """Large conversations should get 'aggressive' recommendation."""
        # Need >70000 tokens (aggressive_threshold). 1 word ~= 1.3 tokens.
        # 150 messages * 500 words * 1.3 = 97500 tokens > 70000
        messages = _make_long_messages(150, words_per_msg=500)
        rec = optimizer.get_recommendation(messages)
        assert rec["should_optimize"] is True
        assert rec["recommended_strategy"] == "aggressive"
        assert rec["urgency"] == "high"


# ---------------------------------------------------------------------------
# Cost analysis
# ---------------------------------------------------------------------------

class TestCostAnalysis:
    """Tests for analyze_cost_impact."""

    def test_empty_returns_zeros(self, optimizer):
        """No optimization data should return zero cost analysis."""
        analysis = optimizer.analyze_cost_impact()
        assert isinstance(analysis, CostAnalysis)
        assert analysis.total_input_tokens == 0
        assert analysis.savings == 0.0
        assert analysis.roi_percentage == 0.0

    def test_with_optimization_data(self, optimizer):
        """After optimizations, cost analysis should show savings."""
        messages = _make_long_messages(25, words_per_msg=300)
        optimizer.optimize_conversation(messages, "sess-1", force_aggressive=True)

        analysis = optimizer.analyze_cost_impact(days=1)
        assert analysis.total_input_tokens > 0
        assert analysis.estimated_cost_original >= analysis.estimated_cost_optimized


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Tests for generate_report."""

    def test_empty_report(self, optimizer):
        """No data should return 'no data' message."""
        report = optimizer.generate_report()
        assert "No optimization data" in report

    def test_report_with_data(self, optimizer):
        """Report after optimizations should contain statistics."""
        messages = _make_long_messages(25, words_per_msg=300)
        optimizer.optimize_conversation(messages, "sess-1", force_aggressive=True)

        report = optimizer.generate_report(days=1)
        assert "MULTI-TURN OPTIMIZATION REPORT" in report
        assert "TOKEN SAVINGS" in report
        assert "COST IMPACT" in report


# ---------------------------------------------------------------------------
# Summary creation
# ---------------------------------------------------------------------------

class TestSummaryCreation:
    """Tests for summary-related methods."""

    def test_summaries_to_messages_empty(self, optimizer):
        """Empty summaries list should return empty list."""
        result = optimizer._summaries_to_messages([])
        assert result == []

    def test_summaries_to_messages_format(self, optimizer):
        """Summary messages should have correct format."""
        summaries = [
            MessageSummary(
                start_turn=1, end_turn=10,
                summary_text="Important decisions were made",
            )
        ]
        result = optimizer._summaries_to_messages(summaries)
        assert len(result) == 1
        assert result[0]["type"] == "assistant"
        assert result[0].get("is_summary") is True

    def test_extract_decisions(self, optimizer):
        """Should extract decision-like sentences."""
        messages = [{
            "type": "assistant",
            "message": {"content": [{"type": "text",
                                      "text": "We decided to use Python. We will implement it tomorrow."}]},
        }]
        decisions = optimizer._extract_decisions(messages)
        assert len(decisions) >= 1

    def test_extract_artifacts(self, optimizer):
        """Should extract file paths and function names."""
        messages = [{
            "type": "assistant",
            "message": {"content": [{"type": "text",
                                      "text": "The file /src/main.py has def process_data and class DataHandler."}]},
        }]
        artifacts = optimizer._extract_artifacts(messages)
        assert any("/src/main.py" in a for a in artifacts)
        assert any("process_data" in a for a in artifacts)


# ---------------------------------------------------------------------------
# HistoryRetentionPolicy
# ---------------------------------------------------------------------------

class TestHistoryRetentionPolicy:
    """Tests for HistoryRetentionPolicy dataclass."""

    def test_defaults(self):
        """Policy should have expected default values."""
        policy = HistoryRetentionPolicy()
        assert policy.recent_turns_to_keep == 10
        assert policy.max_history_tokens == 50000
        assert "code_artifacts" in policy.priority_weights
        assert policy.priority_weights["greetings"] == 0.0

    def test_custom_policy(self):
        """Custom policy values should be accepted."""
        policy = HistoryRetentionPolicy(
            recent_turns_to_keep=5,
            max_history_tokens=20000,
        )
        assert policy.recent_turns_to_keep == 5
        assert policy.max_history_tokens == 20000


# ---------------------------------------------------------------------------
# No optimization result
# ---------------------------------------------------------------------------

class TestNoOptimizationResult:
    """Tests for _no_optimization_result."""

    def test_returns_correct_structure(self, optimizer):
        """No-op result should have zero savings."""
        messages = _make_messages(5)
        result = optimizer._no_optimization_result("sess-1", messages)
        assert result.session_id == "sess-1"
        assert result.tokens_saved == 0
        assert result.savings_percentage == 0.0
        assert result.strategy_used == "none"
        assert result.original_tokens == result.optimized_tokens
