#!/usr/bin/env python3
"""
Tests for Tool Chain Effectiveness Analyzer
TIER 3 Phase 4 Task 26: GAP-EVAL-AG-003

Tests:
- Tool call parsing
- Redundancy detection
- Efficiency calculation
- Suggestion generation
- Report generation
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tool_chain_analyzer import (
    ToolCall,
    ToolSequence,
    RedundantCall,
    ToolChainAnalysis,
    ToolChainReport,
    ToolChainAnalyzer,
    format_report,
    format_analysis
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analyzer(temp_dir):
    """Create analyzer with temporary data directory."""
    return ToolChainAnalyzer(data_dir=temp_dir)


@pytest.fixture
def sample_session_file(temp_dir):
    """Create sample session JSONL file."""
    session_file = temp_dir / "test_session.jsonl"

    entries = [
        {"type": "input", "text": "Find all Python files", "timestamp": "2026-02-04T10:00:00Z"},
        {"type": "tool_use", "tool_name": "Glob", "arguments": {"pattern": "**/*.py"}, "timestamp": "2026-02-04T10:00:01Z"},
        {"type": "tool_result", "result": "file1.py\nfile2.py"},
        {"type": "tool_use", "tool_name": "Read", "arguments": {"file_path": "file1.py"}, "timestamp": "2026-02-04T10:00:02Z"},
        {"type": "tool_result", "result": "# Python code"},
        {"type": "tool_use", "tool_name": "Read", "arguments": {"file_path": "file2.py"}, "timestamp": "2026-02-04T10:00:03Z"},
        {"type": "tool_result", "result": "# More code"},
        {"type": "input", "text": "Now edit file1.py", "timestamp": "2026-02-04T10:01:00Z"},
        {"type": "tool_use", "tool_name": "Read", "arguments": {"file_path": "file1.py"}, "timestamp": "2026-02-04T10:01:01Z"},
        {"type": "tool_result", "result": "# Python code"},
        {"type": "tool_use", "tool_name": "Edit", "arguments": {"file_path": "file1.py", "old_string": "# Python", "new_string": "# Updated"}, "timestamp": "2026-02-04T10:01:02Z"},
        {"type": "tool_result", "result": "File edited successfully"},
    ]

    with open(session_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    return session_file


@pytest.fixture
def redundant_session_file(temp_dir):
    """Create session file with redundant tool calls."""
    session_file = temp_dir / "redundant_session.jsonl"

    entries = [
        {"type": "input", "text": "Search for errors", "timestamp": "2026-02-04T10:00:00Z"},
        {"type": "tool_use", "tool_name": "Grep", "arguments": {"pattern": "error"}, "timestamp": "2026-02-04T10:00:01Z"},
        {"type": "tool_result", "result": "error in file1"},
        {"type": "tool_use", "tool_name": "Grep", "arguments": {"pattern": "error"}, "timestamp": "2026-02-04T10:00:02Z"},  # Redundant
        {"type": "tool_result", "result": "error in file1"},
        {"type": "tool_use", "tool_name": "Grep", "arguments": {"pattern": "error"}, "timestamp": "2026-02-04T10:00:03Z"},  # Redundant
        {"type": "tool_result", "result": "error in file1"},
        {"type": "tool_use", "tool_name": "Read", "arguments": {"file_path": "file1.py"}, "timestamp": "2026-02-04T10:00:04Z"},
        {"type": "tool_result", "result": "code with error"},
        {"type": "tool_use", "tool_name": "Read", "arguments": {"file_path": "file1.py"}, "timestamp": "2026-02-04T10:00:05Z"},  # Redundant
        {"type": "tool_result", "result": "code with error"},
    ]

    with open(session_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    return session_file


# ============================================================================
# ToolCall Tests
# ============================================================================

class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_create_tool_call(self):
        """Test creating a tool call."""
        call = ToolCall(
            tool_name="Read",
            arguments={"file_path": "test.py"},
            timestamp="2026-02-04T10:00:00Z",
            sequence_number=0
        )

        assert call.tool_name == "Read"
        assert call.arguments["file_path"] == "test.py"
        assert call.sequence_number == 0
        assert call.success is True

    def test_args_hash_same_args(self):
        """Test that same arguments produce same hash."""
        call1 = ToolCall(
            tool_name="Read",
            arguments={"file_path": "test.py"},
            timestamp="2026-02-04T10:00:00Z",
            sequence_number=0
        )
        call2 = ToolCall(
            tool_name="Read",
            arguments={"file_path": "test.py"},
            timestamp="2026-02-04T10:00:01Z",
            sequence_number=1
        )

        assert call1.args_hash() == call2.args_hash()

    def test_args_hash_different_args(self):
        """Test that different arguments produce different hash."""
        call1 = ToolCall(
            tool_name="Read",
            arguments={"file_path": "test1.py"},
            timestamp="2026-02-04T10:00:00Z",
            sequence_number=0
        )
        call2 = ToolCall(
            tool_name="Read",
            arguments={"file_path": "test2.py"},
            timestamp="2026-02-04T10:00:01Z",
            sequence_number=1
        )

        assert call1.args_hash() != call2.args_hash()


# ============================================================================
# ToolSequence Tests
# ============================================================================

class TestToolSequence:
    """Tests for ToolSequence dataclass."""

    def test_create_sequence(self):
        """Test creating a tool sequence."""
        calls = [
            ToolCall("Glob", {"pattern": "**/*.py"}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Read", {"file_path": "test.py"}, "2026-02-04T10:00:01Z", 1),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="session_123",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        assert sequence.total_calls == 2
        assert sequence.unique_tools == {"Glob", "Read"}

    def test_tool_pattern(self):
        """Test tool pattern generation."""
        calls = [
            ToolCall("Glob", {}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Read", {}, "2026-02-04T10:00:01Z", 1),
            ToolCall("Edit", {}, "2026-02-04T10:00:02Z", 2),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="session_123",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        assert sequence.tool_pattern() == "Glob -> Read -> Edit"


# ============================================================================
# Analyzer Parsing Tests
# ============================================================================

class TestAnalyzerParsing:
    """Tests for session parsing."""

    def test_parse_session(self, analyzer, sample_session_file):
        """Test parsing a sample session."""
        sequences = analyzer.parse_session(sample_session_file)

        assert len(sequences) == 2  # Two tasks (two user inputs)

        # First task: Find all Python files
        first_task = sequences[0]
        assert first_task.task_id == "task_1"
        assert first_task.total_calls == 3  # Glob + 2x Read

        # Second task: Edit file1.py
        second_task = sequences[1]
        assert second_task.task_id == "task_2"
        assert second_task.total_calls == 2  # Read + Edit

    def test_parse_nonexistent_file(self, analyzer):
        """Test parsing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            analyzer.parse_session(Path("/nonexistent/file.jsonl"))

    def test_parse_empty_session(self, analyzer, temp_dir):
        """Test parsing empty session file."""
        empty_file = temp_dir / "empty.jsonl"
        empty_file.touch()

        sequences = analyzer.parse_session(empty_file)
        assert len(sequences) == 0


# ============================================================================
# Redundancy Detection Tests
# ============================================================================

class TestRedundancyDetection:
    """Tests for redundancy detection."""

    def test_detect_same_args_redundancy(self, analyzer):
        """Test detecting same-args redundancy."""
        calls = [
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:01Z", 1),
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:02Z", 2),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        redundant = analyzer.detect_redundancy(sequence)

        # Should detect 2 redundant calls (calls 1 and 2)
        assert len(redundant) == 2
        assert all(r.reason == "same_args" for r in redundant)
        assert all(r.tool_name == "Grep" for r in redundant)

    def test_detect_no_redundancy(self, analyzer):
        """Test no redundancy when all calls are unique."""
        calls = [
            ToolCall("Glob", {"pattern": "**/*.py"}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Read", {"file_path": "file1.py"}, "2026-02-04T10:00:01Z", 1),
            ToolCall("Read", {"file_path": "file2.py"}, "2026-02-04T10:00:02Z", 2),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        redundant = analyzer.detect_redundancy(sequence)

        assert len(redundant) == 0

    def test_detect_redundancy_from_file(self, analyzer, redundant_session_file):
        """Test detecting redundancy from session file."""
        sequences = analyzer.parse_session(redundant_session_file)

        assert len(sequences) == 1

        redundant = analyzer.detect_redundancy(sequences[0])

        # Should detect redundant Grep (2) and Read (1) calls
        assert len(redundant) >= 2


# ============================================================================
# Efficiency Calculation Tests
# ============================================================================

class TestEfficiencyCalculation:
    """Tests for efficiency calculation."""

    def test_perfect_efficiency(self, analyzer):
        """Test 100% efficiency with no redundancy."""
        calls = [
            ToolCall("Glob", {}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Read", {}, "2026-02-04T10:00:01Z", 1),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        redundant = []  # No redundancy

        score, seq_eff, diversity = analyzer.calculate_efficiency(sequence, redundant)

        assert score > 80  # Good efficiency
        assert seq_eff == 1.0  # Perfect sequence efficiency
        assert diversity > 0  # Has some diversity

    def test_low_efficiency_with_redundancy(self, analyzer):
        """Test low efficiency with high redundancy."""
        calls = [
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:01Z", 1),
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:02Z", 2),
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:03Z", 3),
            ToolCall("Grep", {"pattern": "error"}, "2026-02-04T10:00:04Z", 4),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        redundant = analyzer.detect_redundancy(sequence)

        score, seq_eff, diversity = analyzer.calculate_efficiency(sequence, redundant)

        # 80% redundancy should result in low efficiency
        assert score < 50
        assert seq_eff < 0.5

    def test_empty_sequence_efficiency(self, analyzer):
        """Test efficiency calculation for empty sequence."""
        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=[],
            start_time="2026-02-04T10:00:00Z"
        )

        score, seq_eff, diversity = analyzer.calculate_efficiency(sequence, [])

        assert score == 100.0
        assert seq_eff == 1.0
        assert diversity == 1.0


# ============================================================================
# Suggestion Generation Tests
# ============================================================================

class TestSuggestionGeneration:
    """Tests for improvement suggestions."""

    def test_suggest_caching_for_repeated_read(self, analyzer):
        """Test suggesting caching for repeated Read calls."""
        calls = [
            ToolCall("Read", {"file_path": "file.py"}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Read", {"file_path": "file.py"}, "2026-02-04T10:00:01Z", 1),
            ToolCall("Read", {"file_path": "file.py"}, "2026-02-04T10:00:02Z", 2),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        redundant = analyzer.detect_redundancy(sequence)
        suggestions = analyzer.suggest_improvements(sequence, redundant)

        assert any("caching" in s.lower() or "Read" in s for s in suggestions)

    def test_suggest_task_tool_for_complex_operations(self, analyzer):
        """Test suggesting Task tool for complex operations."""
        # Create sequence with >20 tool calls
        calls = [
            ToolCall("Bash", {}, f"2026-02-04T10:00:{i:02d}Z", i)
            for i in range(25)
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        suggestions = analyzer.suggest_improvements(sequence, [])

        assert any("Task" in s for s in suggestions)


# ============================================================================
# Analysis Tests
# ============================================================================

class TestAnalysis:
    """Tests for complete analysis."""

    def test_analyze_sequence(self, analyzer):
        """Test analyzing a tool sequence."""
        calls = [
            ToolCall("Glob", {"pattern": "**/*.py"}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Read", {"file_path": "file1.py"}, "2026-02-04T10:00:01Z", 1),
            ToolCall("Edit", {"file_path": "file1.py"}, "2026-02-04T10:00:02Z", 2),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        analysis = analyzer.analyze_sequence(sequence)

        assert analysis.task_id == "task_1"
        assert analysis.total_calls == 3
        assert analysis.unique_tools == 3
        assert analysis.redundancy_ratio == 0.0  # No redundancy
        assert analysis.efficiency_score > 80

    def test_analyze_session(self, analyzer, sample_session_file):
        """Test analyzing entire session."""
        analyses = analyzer.analyze_session(sample_session_file)

        assert len(analyses) == 2  # Two tasks

        # Check all analyses are valid
        for analysis in analyses:
            assert analysis.total_calls > 0
            assert 0 <= analysis.redundancy_ratio <= 1
            assert 0 <= analysis.efficiency_score <= 100


# ============================================================================
# Report Generation Tests
# ============================================================================

class TestReportGeneration:
    """Tests for report generation."""

    def test_generate_empty_report(self, analyzer):
        """Test generating report with no data."""
        report = analyzer.generate_report(period_days=7)

        assert report.total_sessions == 0
        assert report.total_sequences == 0
        assert report.avg_redundancy_ratio == 0.0
        assert report.avg_efficiency_score == 100.0

    def test_generate_report_after_analysis(self, analyzer, sample_session_file):
        """Test generating report after analyzing session."""
        # First analyze a session
        analyzer.analyze_session(sample_session_file)

        # Then generate report
        report = analyzer.generate_report(period_days=7)

        assert report.total_sessions >= 1
        assert report.total_sequences >= 1
        assert report.total_tool_calls > 0


# ============================================================================
# Formatting Tests
# ============================================================================

class TestFormatting:
    """Tests for output formatting."""

    def test_format_report(self):
        """Test report formatting."""
        report = ToolChainReport(
            period_start="2026-01-28T00:00:00Z",
            period_end="2026-02-04T00:00:00Z",
            total_sessions=5,
            total_sequences=10,
            total_tool_calls=50,
            avg_redundancy_ratio=0.05,
            max_redundancy_ratio=0.15,
            total_redundant_calls=3,
            avg_efficiency_score=85.0,
            min_efficiency_score=70.0,
            tool_frequency={"Read": 20, "Glob": 15, "Edit": 10},
            common_patterns={"Glob -> Read -> Edit": 5},
            top_inefficiencies=["Task 1: 15% redundancy"],
            improvement_opportunities=["Consider caching file reads"]
        )

        formatted = format_report(report)

        assert "TOOL CHAIN EFFECTIVENESS REPORT" in formatted
        assert "5.0%" in formatted  # avg redundancy
        assert "85.0" in formatted  # avg efficiency
        assert "✅ GOOD" in formatted  # Status

    def test_format_analysis(self):
        """Test analysis formatting."""
        analysis = ToolChainAnalysis(
            task_id="task_1",
            session_id="session_123",
            timestamp="2026-02-04T10:00:00Z",
            total_calls=5,
            unique_tools=3,
            unique_patterns=1,
            redundant_calls=1,
            redundancy_ratio=0.2,
            redundant_details=[],
            efficiency_score=75.0,
            sequence_efficiency=0.8,
            tool_diversity=0.6,
            tool_pattern="Glob -> Read -> Read -> Edit -> Edit",
            suggested_improvements=["Consider caching"]
        )

        formatted = format_analysis(analysis)

        assert "task_1" in formatted
        assert "session_123" in formatted
        assert "75.0" in formatted  # efficiency
        assert "Glob -> Read" in formatted  # pattern


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, analyzer, sample_session_file):
        """Test complete analysis workflow."""
        # Parse session
        sequences = analyzer.parse_session(sample_session_file)
        assert len(sequences) > 0

        # Analyze each sequence
        analyses = []
        for seq in sequences:
            analysis = analyzer.analyze_sequence(seq)
            analyses.append(analysis)

        assert len(analyses) == len(sequences)

        # Generate report
        report = analyzer.generate_report(period_days=1)

        assert report.total_sequences >= len(analyses)

    def test_redundancy_detection_end_to_end(self, analyzer, redundant_session_file):
        """Test end-to-end redundancy detection."""
        analyses = analyzer.analyze_session(redundant_session_file)

        assert len(analyses) == 1

        analysis = analyses[0]

        # Should have detected redundancy
        assert analysis.redundant_calls > 0
        assert analysis.redundancy_ratio > 0.1  # >10% redundancy

        # Efficiency should be lower due to redundancy
        assert analysis.efficiency_score < 80


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_single_tool_call(self, analyzer):
        """Test sequence with single tool call."""
        calls = [ToolCall("Read", {"file_path": "test.py"}, "2026-02-04T10:00:00Z", 0)]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        analysis = analyzer.analyze_sequence(sequence)

        assert analysis.total_calls == 1
        assert analysis.redundancy_ratio == 0.0
        assert analysis.efficiency_score > 0

    def test_all_different_tools(self, analyzer):
        """Test sequence with all different tools."""
        calls = [
            ToolCall("Glob", {}, "2026-02-04T10:00:00Z", 0),
            ToolCall("Grep", {}, "2026-02-04T10:00:01Z", 1),
            ToolCall("Read", {}, "2026-02-04T10:00:02Z", 2),
            ToolCall("Edit", {}, "2026-02-04T10:00:03Z", 3),
            ToolCall("Write", {}, "2026-02-04T10:00:04Z", 4),
        ]

        sequence = ToolSequence(
            task_id="task_1",
            session_id="test",
            calls=calls,
            start_time="2026-02-04T10:00:00Z"
        )

        analysis = analyzer.analyze_sequence(sequence)

        assert analysis.unique_tools == 5
        assert analysis.redundancy_ratio == 0.0
        assert analysis.efficiency_score > 80  # High efficiency

    def test_malformed_session_entries(self, analyzer, temp_dir):
        """Test handling malformed session entries."""
        session_file = temp_dir / "malformed.jsonl"

        entries = [
            "invalid json",
            {"type": "tool_use"},  # Missing required fields - handled gracefully
            {"type": "input", "text": "Test task"},
            {"type": "tool_use", "tool_name": "Read", "arguments": {"file_path": "test.py"}, "timestamp": "2026-02-04T10:00:00Z"},
            {"type": "tool_result", "result": "content"},
        ]

        with open(session_file, 'w') as f:
            for entry in entries:
                if isinstance(entry, str):
                    f.write(entry + "\n")
                else:
                    f.write(json.dumps(entry) + "\n")

        # Should not crash - incomplete entries are handled gracefully
        sequences = analyzer.parse_session(session_file)

        # Parser creates sequences for each task (input marker)
        # Incomplete tool_use creates "Unknown" call, valid tool_use creates "Read" call
        assert len(sequences) >= 1

        # At least one sequence should have valid Read call
        all_tools = []
        for seq in sequences:
            all_tools.extend(c.tool_name for c in seq.calls)
        assert "Read" in all_tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
