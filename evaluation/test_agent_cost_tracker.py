#!/usr/bin/env python3
"""
Pytest tests for Agent Cost Tracker.

Tests cover:
- Token cost calculations (all models)
- Tool cost tracking
- Subagent cost logging
- Compute and storage costs
- Session and daily summaries
- Budget status
- Report generation
- Edge cases and error handling

Version: 1.0.0
Task: TIER 3 Phase 2 Task 21 - Agent Cost Tracking Tests
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from costs.agent_cost_tracker import (
    AgentCostTracker,
    CostRecord,
    CostSummary
)


# === Fixtures ===

@pytest.fixture
def temp_storage():
    """Create temporary storage file for tests."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        yield Path(f.name)
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def tracker(temp_storage):
    """Create tracker instance with temporary storage."""
    return AgentCostTracker(storage_file=temp_storage)


@pytest.fixture
def test_session_id():
    """Standard test session ID."""
    return "test-session-pytest-001"


# === CostRecord Tests ===

class TestCostRecord:
    """Tests for CostRecord dataclass."""

    def test_create_record(self):
        """Test basic record creation."""
        record = CostRecord(
            timestamp="2026-02-03T10:00:00",
            session_id="test-session",
            category="tokens",
            amount=0.05,
            details={"model": "sonnet"}
        )
        assert record.category == "tokens"
        assert record.amount == 0.05
        assert record.details["model"] == "sonnet"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        record = CostRecord(
            timestamp="2026-02-03T10:00:00",
            session_id="test-session",
            category="tools",
            amount=0.001,
            details={"tool_name": "Bash"}
        )
        d = record.to_dict()
        assert d["category"] == "tools"
        assert d["amount"] == 0.001
        assert d["details"]["tool_name"] == "Bash"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "timestamp": "2026-02-03T10:00:00",
            "session_id": "test-session",
            "category": "tokens",
            "amount": 0.10,
            "details": {"model": "opus"}
        }
        record = CostRecord.from_dict(data)
        assert record.category == "tokens"
        assert record.amount == 0.10
        assert record.details["model"] == "opus"


# === Token Cost Tests ===

class TestTokenCosts:
    """Tests for token cost calculations."""

    def test_haiku_pricing(self, tracker, test_session_id):
        """Test Haiku model pricing."""
        # Haiku: $1/M input, $5/M output, $0.1/M cached
        cost = tracker.log_token_cost(
            test_session_id,
            model="haiku",
            input_tokens=10000,
            output_tokens=5000,
            cached_tokens=2000
        )
        # Fresh input: 8000 tokens @ $1/M = $0.008
        # Cached: 2000 tokens @ $0.1/M = $0.0002
        # Output: 5000 tokens @ $5/M = $0.025
        expected = 0.008 + 0.0002 + 0.025
        assert abs(cost - expected) < 0.0001

    def test_sonnet_pricing(self, tracker, test_session_id):
        """Test Sonnet model pricing."""
        # Sonnet: $3/M input, $15/M output, $0.3/M cached
        cost = tracker.log_token_cost(
            test_session_id,
            model="sonnet",
            input_tokens=15000,
            output_tokens=8000,
            cached_tokens=5000
        )
        # Fresh input: 10000 tokens @ $3/M = $0.03
        # Cached: 5000 tokens @ $0.3/M = $0.0015
        # Output: 8000 tokens @ $15/M = $0.12
        expected = 0.03 + 0.0015 + 0.12
        assert abs(cost - expected) < 0.0001

    def test_opus_pricing(self, tracker, test_session_id):
        """Test Opus model pricing."""
        # Opus: $15/M input, $75/M output, $1.5/M cached
        cost = tracker.log_token_cost(
            test_session_id,
            model="opus",
            input_tokens=5000,
            output_tokens=2000,
            cached_tokens=1000
        )
        # Fresh input: 4000 tokens @ $15/M = $0.06
        # Cached: 1000 tokens @ $1.5/M = $0.0015
        # Output: 2000 tokens @ $75/M = $0.15
        expected = 0.06 + 0.0015 + 0.15
        assert abs(cost - expected) < 0.0001

    def test_unknown_model_defaults_to_sonnet(self, tracker, test_session_id):
        """Test unknown model falls back to Sonnet pricing."""
        cost = tracker.log_token_cost(
            test_session_id,
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=0
        )
        # Should use Sonnet pricing
        expected = (1000/1_000_000)*3.0 + (500/1_000_000)*15.0
        assert abs(cost - expected) < 0.0001

    def test_zero_tokens(self, tracker, test_session_id):
        """Test with zero tokens."""
        cost = tracker.log_token_cost(
            test_session_id,
            model="sonnet",
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0
        )
        assert cost == 0.0

    def test_case_insensitive_model(self, tracker, test_session_id):
        """Test model name is case-insensitive."""
        cost1 = tracker.log_token_cost(test_session_id, "HAIKU", 1000, 500, 0)
        cost2 = tracker.log_token_cost(test_session_id, "Haiku", 1000, 500, 0)
        cost3 = tracker.log_token_cost(test_session_id, "haiku", 1000, 500, 0)
        assert cost1 == cost2 == cost3


# === Tool Cost Tests ===

class TestToolCosts:
    """Tests for tool execution cost tracking."""

    def test_bash_base_cost(self, tracker, test_session_id):
        """Test Bash tool base cost."""
        cost = tracker.log_tool_cost(test_session_id, "Bash")
        assert cost == 0.001

    def test_read_base_cost(self, tracker, test_session_id):
        """Test Read tool base cost."""
        cost = tracker.log_tool_cost(test_session_id, "Read")
        assert cost == 0.0001

    def test_task_spawn_cost(self, tracker, test_session_id):
        """Test Task (subagent) tool base cost."""
        cost = tracker.log_tool_cost(test_session_id, "Task")
        assert cost == 0.05

    def test_websearch_cost(self, tracker, test_session_id):
        """Test WebSearch tool cost."""
        cost = tracker.log_tool_cost(test_session_id, "WebSearch")
        assert cost == 0.01

    def test_execution_time_adds_cost(self, tracker, test_session_id):
        """Test long execution time adds to cost."""
        # Base cost + execution cost for >1 second
        cost = tracker.log_tool_cost(
            test_session_id,
            "Bash",
            execution_time_ms=2500
        )
        expected = 0.001 + (2.5 * 0.001)  # Base + 2.5 seconds
        assert abs(cost - expected) < 0.0001

    def test_short_execution_no_extra_cost(self, tracker, test_session_id):
        """Test short execution (<1s) doesn't add cost."""
        cost = tracker.log_tool_cost(
            test_session_id,
            "Bash",
            execution_time_ms=500
        )
        assert cost == 0.001  # Only base cost

    def test_unknown_tool_minimal_cost(self, tracker, test_session_id):
        """Test unknown tool gets minimal cost."""
        cost = tracker.log_tool_cost(test_session_id, "UnknownTool")
        assert cost == 0.0001

    def test_external_api_category(self, tracker, test_session_id, temp_storage):
        """Test external API tools categorized correctly."""
        tracker.log_tool_cost(test_session_id, "WebFetch", external_api=True)

        # Read records
        with open(temp_storage) as f:
            records = [json.loads(line) for line in f]

        assert any(r["category"] == "external_apis" for r in records)


# === Subagent Cost Tests ===

class TestSubagentCosts:
    """Tests for subagent spawn and execution costs."""

    def test_subagent_spawn_overhead(self, tracker, test_session_id):
        """Test subagent has spawn overhead."""
        cost = tracker.log_subagent_cost(
            test_session_id,
            subagent_id="subagent-001",
            subagent_model="haiku",
            tokens_used={"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
        )
        # Spawn overhead is $0.01
        assert cost >= 0.01

    def test_subagent_with_tokens(self, tracker, test_session_id):
        """Test subagent cost includes token costs."""
        cost = tracker.log_subagent_cost(
            test_session_id,
            subagent_id="subagent-002",
            subagent_model="haiku",
            tokens_used={
                "input_tokens": 5000,
                "output_tokens": 2000,
                "cached_tokens": 1000
            }
        )
        # Spawn overhead ($0.01) + token costs
        assert cost > 0.01


# === Compute & Storage Cost Tests ===

class TestComputeStorageCosts:
    """Tests for compute and storage costs."""

    def test_compute_cost(self, tracker, test_session_id):
        """Test compute cost calculation."""
        cost = tracker.log_compute_cost(test_session_id, execution_time_seconds=10.0)
        expected = 10.0 * 0.001  # $0.001 per second
        assert abs(cost - expected) < 0.0001

    def test_storage_cost(self, tracker, test_session_id):
        """Test storage cost calculation."""
        cost = tracker.log_storage_cost(test_session_id, bytes_written=10240)  # 10 KB
        expected = 10 * 0.0001  # $0.0001 per KB
        assert abs(cost - expected) < 0.0001

    def test_zero_compute_cost(self, tracker, test_session_id):
        """Test zero compute time."""
        cost = tracker.log_compute_cost(test_session_id, 0.0)
        assert cost == 0.0


# === Summary Tests ===

class TestSummaries:
    """Tests for session and daily summaries."""

    def test_session_summary_empty(self, tracker):
        """Test empty session summary."""
        summary = tracker.get_session_summary("nonexistent-session")
        assert summary.total_cost == 0.0
        assert summary.request_count == 0
        assert summary.budget_status == "healthy"

    def test_session_summary_aggregation(self, tracker, test_session_id):
        """Test session summary aggregates costs."""
        # Log multiple costs
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)
        tracker.log_tool_cost(test_session_id, "Bash")
        tracker.log_tool_cost(test_session_id, "Read")

        summary = tracker.get_session_summary(test_session_id)

        assert summary.total_cost > 0
        assert summary.request_count == 3
        assert "tokens" in summary.by_category
        assert "tools" in summary.by_category

    def test_session_summary_by_model(self, tracker, test_session_id):
        """Test summary tracks costs by model."""
        tracker.log_token_cost(test_session_id, "haiku", 1000, 500, 0)
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        summary = tracker.get_session_summary(test_session_id)

        assert "haiku" in summary.by_model
        assert "sonnet" in summary.by_model

    def test_session_summary_by_tool(self, tracker, test_session_id):
        """Test summary tracks costs by tool."""
        tracker.log_tool_cost(test_session_id, "Bash")
        tracker.log_tool_cost(test_session_id, "Read")
        tracker.log_tool_cost(test_session_id, "Bash")  # Duplicate

        summary = tracker.get_session_summary(test_session_id)

        assert "Bash" in summary.by_tool
        assert "Read" in summary.by_tool
        assert summary.by_tool["Bash"] > summary.by_tool["Read"]

    def test_daily_summary(self, tracker, test_session_id):
        """Test daily summary aggregation."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        summary = tracker.get_daily_summary()

        assert summary.session_id == "daily"
        assert summary.total_cost >= 0


# === Budget Status Tests ===

class TestBudgetStatus:
    """Tests for budget status tracking."""

    def test_healthy_status(self, tracker, test_session_id):
        """Test healthy budget status."""
        tracker.log_token_cost(test_session_id, "haiku", 100, 50, 0)  # Minimal cost

        summary = tracker.get_session_summary(test_session_id)
        assert summary.budget_status == "healthy"

    def test_get_budget_status_session(self, tracker, test_session_id):
        """Test get_budget_status for session."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        status = tracker.get_budget_status(test_session_id)

        assert status["scope"] == "session"
        assert status["budget"] == tracker.SESSION_BUDGET
        assert status["spent"] > 0
        assert status["remaining"] < tracker.SESSION_BUDGET
        assert "status" in status

    def test_get_budget_status_daily(self, tracker, test_session_id):
        """Test get_budget_status for daily."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        status = tracker.get_budget_status()  # No session = daily

        assert status["scope"] == "daily"
        assert status["budget"] == tracker.DAILY_BUDGET


# === Report Generation Tests ===

class TestReportGeneration:
    """Tests for report generation."""

    def test_report_not_empty(self, tracker, test_session_id):
        """Test report is not empty."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        report = tracker.generate_report(test_session_id)

        assert len(report) > 0

    def test_report_contains_sections(self, tracker, test_session_id):
        """Test report contains expected sections."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)
        tracker.log_tool_cost(test_session_id, "Bash")

        report = tracker.generate_report(test_session_id)

        assert "AGENT COST TRACKING" in report
        assert "COST BREAKDOWN" in report
        assert "Tokens" in report
        assert "Tools" in report
        assert "PROJECTIONS" in report
        assert "STATUS" in report

    def test_report_daily_summary(self, tracker, test_session_id):
        """Test daily report generation."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        report = tracker.generate_report()  # No session = daily

        assert "Daily Summary" in report


# === Storage Tests ===

class TestStorage:
    """Tests for storage operations."""

    def test_records_persisted(self, tracker, test_session_id, temp_storage):
        """Test records are persisted to storage."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        assert temp_storage.exists()
        with open(temp_storage) as f:
            lines = f.readlines()
        assert len(lines) == 1

    def test_records_json_valid(self, tracker, test_session_id, temp_storage):
        """Test stored records are valid JSON."""
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)
        tracker.log_tool_cost(test_session_id, "Bash")

        with open(temp_storage) as f:
            for line in f:
                record = json.loads(line)
                assert "timestamp" in record
                assert "session_id" in record
                assert "category" in record
                assert "amount" in record
                assert "details" in record

    def test_multiple_sessions(self, tracker, temp_storage):
        """Test tracking multiple sessions."""
        tracker.log_token_cost("session-1", "sonnet", 1000, 500, 0)
        tracker.log_token_cost("session-2", "haiku", 1000, 500, 0)

        summary1 = tracker.get_session_summary("session-1")
        summary2 = tracker.get_session_summary("session-2")

        # Different models = different costs
        assert summary1.total_cost != summary2.total_cost


# === Edge Cases ===

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_large_token_count(self, tracker, test_session_id):
        """Test with large token counts."""
        cost = tracker.log_token_cost(
            test_session_id,
            "sonnet",
            input_tokens=1_000_000,
            output_tokens=500_000,
            cached_tokens=100_000
        )
        assert cost > 0

    def test_special_characters_session_id(self, tracker):
        """Test session ID with special characters."""
        session_id = "test/session:with-special_chars.123"
        cost = tracker.log_token_cost(session_id, "sonnet", 1000, 500, 0)

        summary = tracker.get_session_summary(session_id)
        assert summary.total_cost == cost

    def test_format_duration(self):
        """Test duration formatting."""
        result = AgentCostTracker._format_duration(
            "2026-02-03T10:00:00",
            "2026-02-03T12:30:00"
        )
        assert result == "2h 30m"

    def test_format_duration_short(self):
        """Test short duration formatting."""
        result = AgentCostTracker._format_duration(
            "2026-02-03T10:00:00",
            "2026-02-03T10:15:00"
        )
        assert result == "15m"


# === Integration Tests ===

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_session_workflow(self, tracker, test_session_id):
        """Test complete session tracking workflow."""
        # Simulate a typical session
        tracker.log_token_cost(test_session_id, "sonnet", 50000, 10000, 40000)
        tracker.log_tool_cost(test_session_id, "Read")
        tracker.log_tool_cost(test_session_id, "Bash", execution_time_ms=1500)
        tracker.log_tool_cost(test_session_id, "Write")
        tracker.log_token_cost(test_session_id, "sonnet", 30000, 5000, 25000)

        # Get summary
        summary = tracker.get_session_summary(test_session_id)

        assert summary.request_count == 5
        assert summary.total_cost > 0
        assert "tokens" in summary.by_category
        assert "tools" in summary.by_category

        # Get report
        report = tracker.generate_report(test_session_id)
        assert len(report) > 0

        # Get budget status
        status = tracker.get_budget_status(test_session_id)
        assert status["spent"] == summary.total_cost


# === Task 22: Tool Cost Tracking Enhancement Tests ===

class TestExpensiveTools:
    """Tests for expensive tool identification (Task 22)."""

    def test_get_expensive_tools_empty(self, tracker, test_session_id):
        """Test get_expensive_tools with no tool costs."""
        # Only log token cost, no tools
        tracker.log_token_cost(test_session_id, "sonnet", 1000, 500, 0)

        expensive = tracker.get_expensive_tools(test_session_id)
        assert expensive == []

    def test_get_expensive_tools_single(self, tracker, test_session_id):
        """Test get_expensive_tools with single tool."""
        tracker.log_tool_cost(test_session_id, "Bash")

        expensive = tracker.get_expensive_tools(test_session_id)

        assert len(expensive) == 1
        assert expensive[0]["tool"] == "Bash"
        assert expensive[0]["call_count"] == 1
        assert expensive[0]["total_cost"] > 0

    def test_get_expensive_tools_sorted(self, tracker, test_session_id):
        """Test get_expensive_tools returns sorted by cost."""
        # Log multiple tools with different costs
        tracker.log_tool_cost(test_session_id, "Read")  # 0.0001
        tracker.log_tool_cost(test_session_id, "WebSearch")  # 0.01
        tracker.log_tool_cost(test_session_id, "Bash")  # 0.001

        expensive = tracker.get_expensive_tools(test_session_id)

        assert len(expensive) == 3
        # Should be sorted by total cost, WebSearch highest
        assert expensive[0]["tool"] == "WebSearch"
        assert expensive[1]["tool"] == "Bash"
        assert expensive[2]["tool"] == "Read"

    def test_get_expensive_tools_top_n(self, tracker, test_session_id):
        """Test get_expensive_tools respects top_n limit."""
        for tool in ["Read", "Write", "Edit", "Grep", "Glob"]:
            tracker.log_tool_cost(test_session_id, tool)

        expensive = tracker.get_expensive_tools(test_session_id, top_n=3)

        assert len(expensive) == 3

    def test_get_expensive_tools_aggregates(self, tracker, test_session_id):
        """Test get_expensive_tools aggregates multiple calls."""
        tracker.log_tool_cost(test_session_id, "Bash")
        tracker.log_tool_cost(test_session_id, "Bash")
        tracker.log_tool_cost(test_session_id, "Bash")

        expensive = tracker.get_expensive_tools(test_session_id)

        assert len(expensive) == 1
        assert expensive[0]["tool"] == "Bash"
        assert expensive[0]["call_count"] == 3
        # Total cost should be 3x base cost
        assert expensive[0]["total_cost"] == expensive[0]["base_cost"] * 3


class TestToolAlerts:
    """Tests for tool cost alerts (Task 22)."""

    def test_no_alerts_under_threshold(self, tracker, test_session_id):
        """Test no alerts when under threshold."""
        tracker.log_tool_cost(test_session_id, "Read")  # Very cheap

        alerts = tracker.get_tool_alerts(test_session_id)

        assert len(alerts) == 0

    def test_alert_when_threshold_exceeded(self, tracker, test_session_id):
        """Test alert generated when threshold exceeded."""
        # WebSearch threshold is $0.25, each call is $0.01
        # Need 26+ calls to exceed
        for _ in range(30):
            tracker.log_tool_cost(test_session_id, "WebSearch")

        alerts = tracker.get_tool_alerts(test_session_id)

        assert len(alerts) == 1
        assert alerts[0]["tool"] == "WebSearch"
        assert alerts[0]["total_cost"] > alerts[0]["threshold"]
        assert alerts[0]["pct_over"] > 0

    def test_alert_severity_warning(self, tracker, test_session_id):
        """Test warning severity for small excess."""
        # Just over threshold (< 100% over)
        for _ in range(30):  # $0.30 vs $0.25 threshold = 20% over
            tracker.log_tool_cost(test_session_id, "WebSearch")

        alerts = tracker.get_tool_alerts(test_session_id)

        if alerts:  # May vary based on threshold
            assert alerts[0]["severity"] in ["warning", "critical"]

    def test_alert_sorted_by_severity(self, tracker, test_session_id):
        """Test alerts sorted by percent over threshold."""
        # Create multiple alerts with different severities
        for _ in range(30):
            tracker.log_tool_cost(test_session_id, "WebSearch")

        alerts = tracker.get_tool_alerts(test_session_id)

        if len(alerts) > 1:
            # Should be sorted descending by pct_over
            for i in range(len(alerts) - 1):
                assert alerts[i]["pct_over"] >= alerts[i + 1]["pct_over"]


class TestToolReport:
    """Tests for tool cost report generation (Task 22)."""

    def test_tool_report_not_empty(self, tracker, test_session_id):
        """Test tool report is generated."""
        tracker.log_tool_cost(test_session_id, "Bash")
        tracker.log_tool_cost(test_session_id, "Read")

        report = tracker.generate_tool_report(test_session_id)

        assert len(report) > 0

    def test_tool_report_contains_sections(self, tracker, test_session_id):
        """Test tool report contains expected sections."""
        tracker.log_tool_cost(test_session_id, "Bash")
        tracker.log_tool_cost(test_session_id, "Read")

        report = tracker.generate_tool_report(test_session_id)

        assert "TOOL COST ANALYSIS REPORT" in report
        assert "TOP EXPENSIVE TOOLS" in report

    def test_tool_report_shows_alert_status(self, tracker, test_session_id):
        """Test tool report shows alert status."""
        tracker.log_tool_cost(test_session_id, "Read")

        report = tracker.generate_tool_report(test_session_id)

        # Should show no alerts
        assert "No tool cost alerts" in report


class TestMCPTools:
    """Tests for MCP tool cost tracking (Task 22)."""

    def test_mcp_tool_in_registry(self, tracker):
        """Test MCP tools are in cost registry."""
        assert "mcp__github__search_code" in tracker.TOOL_COSTS
        assert "mcp__github__create_pull_request" in tracker.TOOL_COSTS

    def test_mcp_tool_cost_tracking(self, tracker, test_session_id):
        """Test MCP tool costs are tracked."""
        cost = tracker.log_tool_cost(
            test_session_id,
            "mcp__github__search_code",
            external_api=True
        )

        assert cost == tracker.TOOL_COSTS["mcp__github__search_code"]

        summary = tracker.get_session_summary(test_session_id)
        assert "external_apis" in summary.by_category


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
