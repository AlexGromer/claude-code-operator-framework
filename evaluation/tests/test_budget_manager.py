#!/usr/bin/env python3
"""
Tests for budget_manager.py — BudgetManager, BudgetConfig, SpendingRecord.

Covers:
- Dataclass creation and defaults
- Initialization with/without config file
- Spending recording and retrieval
- Budget checking at various levels
- Alert threshold triggering
- can_spend() blocking logic
- Edge cases: empty files, corrupted JSONL, missing config
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import asdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costs.budget_manager import (
    BudgetConfig,
    BudgetLevel,
    BudgetManager,
    BudgetStatus,
    BudgetType,
    SpendingRecord,
    BudgetAlert,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path):
    """Provide a temporary data directory for BudgetManager."""
    d = tmp_path / "eval_data"
    d.mkdir()
    return d


@pytest.fixture
def manager(data_dir):
    """Return a BudgetManager using a temporary directory."""
    return BudgetManager(data_dir=data_dir)


# ---------------------------------------------------------------------------
# BudgetConfig dataclass tests
# ---------------------------------------------------------------------------

class TestBudgetConfig:
    """Tests for BudgetConfig dataclass."""

    def test_creation_with_defaults(self):
        """BudgetConfig should populate default values correctly."""
        cfg = BudgetConfig(budget_type="session", limit=5.0)
        assert cfg.budget_type == "session"
        assert cfg.limit == 5.0
        assert cfg.soft_limit_pct == 90.0
        assert cfg.hard_limit_pct == 100.0
        assert cfg.alert_thresholds == [50.0, 75.0, 90.0]
        assert cfg.enabled is True
        assert cfg.created_at != ""

    def test_creation_with_custom_values(self):
        """BudgetConfig should accept custom values."""
        cfg = BudgetConfig(
            budget_type="daily",
            limit=20.0,
            soft_limit_pct=80.0,
            hard_limit_pct=95.0,
            alert_thresholds=[30.0, 60.0],
            enabled=False,
            created_at="2026-01-01T00:00:00+00:00",
        )
        assert cfg.soft_limit_pct == 80.0
        assert cfg.hard_limit_pct == 95.0
        assert cfg.alert_thresholds == [30.0, 60.0]
        assert cfg.enabled is False
        assert cfg.created_at == "2026-01-01T00:00:00+00:00"

    def test_created_at_auto_populated(self):
        """created_at should be auto-populated when empty."""
        cfg = BudgetConfig(budget_type="session", limit=1.0)
        ts = datetime.fromisoformat(cfg.created_at)
        assert ts.tzinfo is not None  # should be timezone-aware


# ---------------------------------------------------------------------------
# SpendingRecord dataclass tests
# ---------------------------------------------------------------------------

class TestSpendingRecord:
    """Tests for SpendingRecord dataclass."""

    def test_creation(self):
        """SpendingRecord fields should be set correctly."""
        rec = SpendingRecord(
            timestamp="2026-02-05T12:00:00+00:00",
            session_id="sess-1",
            task_id="task-1",
            amount=0.05,
            category="tokens",
            description="test spend",
        )
        assert rec.amount == 0.05
        assert rec.session_id == "sess-1"
        assert rec.task_id == "task-1"

    def test_asdict(self):
        """SpendingRecord should serialize via asdict."""
        rec = SpendingRecord(
            timestamp="t", session_id="s", task_id=None,
            amount=1.0, category="tools", description="d",
        )
        d = asdict(rec)
        assert d["amount"] == 1.0
        assert d["task_id"] is None


# ---------------------------------------------------------------------------
# BudgetManager initialization
# ---------------------------------------------------------------------------

class TestBudgetManagerInit:
    """Tests for BudgetManager initialization."""

    def test_default_config_created(self, data_dir):
        """When no config file exists, defaults should be created and saved."""
        mgr = BudgetManager(data_dir=data_dir)
        assert mgr.config_file.exists()
        assert "session" in mgr.config
        assert "daily" in mgr.config
        assert mgr.config["session"].limit == 5.0

    def test_existing_config_loaded(self, data_dir):
        """When a config file already exists it should be loaded."""
        config_data = {
            "session": {
                "budget_type": "session",
                "limit": 10.0,
                "soft_limit_pct": 90.0,
                "hard_limit_pct": 100.0,
                "alert_thresholds": [50.0, 75.0, 90.0],
                "enabled": True,
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        }
        config_file = data_dir / "budget_config.json"
        config_file.write_text(json.dumps(config_data))

        mgr = BudgetManager(data_dir=data_dir)
        assert mgr.config["session"].limit == 10.0

    def test_corrupted_config_uses_defaults(self, data_dir):
        """Corrupted config file should fall back to defaults."""
        config_file = data_dir / "budget_config.json"
        config_file.write_text("{invalid json!!")

        mgr = BudgetManager(data_dir=data_dir)
        # Should fall back to defaults
        assert "session" in mgr.config
        assert mgr.config["session"].limit == 5.0

    def test_data_dir_created(self, tmp_path):
        """data_dir should be created if it does not exist."""
        new_dir = tmp_path / "nonexistent" / "path"
        mgr = BudgetManager(data_dir=new_dir)
        assert new_dir.exists()


# ---------------------------------------------------------------------------
# record_spending
# ---------------------------------------------------------------------------

class TestRecordSpending:
    """Tests for BudgetManager.record_spending."""

    def test_writes_jsonl_line(self, manager):
        """record_spending should append a valid JSONL line."""
        manager.record_spending(
            amount=0.10,
            session_id="sess-1",
            category="tokens",
            description="api call",
        )
        assert manager.spending_file.exists()
        lines = manager.spending_file.read_text().strip().split("\n")
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["amount"] == 0.10
        assert rec["session_id"] == "sess-1"
        assert rec["category"] == "tokens"

    def test_multiple_records_appended(self, manager):
        """Multiple calls should append multiple lines."""
        for i in range(5):
            manager.record_spending(
                amount=float(i), session_id="s", category="c",
            )
        lines = manager.spending_file.read_text().strip().split("\n")
        assert len(lines) == 5

    def test_optional_task_id(self, manager):
        """task_id should be stored when provided."""
        manager.record_spending(
            amount=0.01, session_id="s", category="c", task_id="t-42",
        )
        rec = json.loads(manager.spending_file.read_text().strip())
        assert rec["task_id"] == "t-42"


# ---------------------------------------------------------------------------
# get_spending
# ---------------------------------------------------------------------------

class TestGetSpending:
    """Tests for BudgetManager.get_spending."""

    def test_empty_file_returns_zero(self, manager):
        """No spending file should return 0.0."""
        assert manager.get_spending(BudgetType.SESSION, session_id="s") == 0.0

    def test_sums_for_session(self, manager):
        """Should sum amounts filtered by session_id."""
        manager.record_spending(amount=1.0, session_id="s1", category="c")
        manager.record_spending(amount=2.0, session_id="s1", category="c")
        manager.record_spending(amount=5.0, session_id="s2", category="c")

        total = manager.get_spending(BudgetType.SESSION, session_id="s1")
        assert total == pytest.approx(3.0)

    def test_sums_for_task(self, manager):
        """Should sum amounts filtered by task_id."""
        manager.record_spending(amount=0.5, session_id="s", category="c", task_id="t1")
        manager.record_spending(amount=0.3, session_id="s", category="c", task_id="t1")
        manager.record_spending(amount=9.0, session_id="s", category="c", task_id="t2")

        total = manager.get_spending(BudgetType.TASK, task_id="t1")
        assert total == pytest.approx(0.8)

    def test_daily_spending_includes_recent(self, manager):
        """Daily spending should include records from the last 24 hours."""
        # Current records are timestamped 'now', so they should be included.
        manager.record_spending(amount=1.0, session_id="s", category="c")
        manager.record_spending(amount=2.0, session_id="s", category="c")

        total = manager.get_spending(BudgetType.DAILY)
        assert total == pytest.approx(3.0)

    def test_corrupted_jsonl_lines_skipped(self, manager):
        """Corrupted lines in JSONL should be skipped without error."""
        manager.record_spending(amount=1.0, session_id="s1", category="c")
        # Append a bad line
        with open(manager.spending_file, "a") as f:
            f.write("this is not valid json\n")
        manager.record_spending(amount=2.0, session_id="s1", category="c")

        total = manager.get_spending(BudgetType.SESSION, session_id="s1")
        assert total == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# check_budget
# ---------------------------------------------------------------------------

class TestCheckBudget:
    """Tests for BudgetManager.check_budget."""

    def test_healthy_status(self, manager):
        """Under 50% should be HEALTHY."""
        # Session budget default = $5, spend $1 = 20%
        manager.record_spending(amount=1.0, session_id="s", category="c")
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert status.level == BudgetLevel.HEALTHY.value
        assert status.can_proceed is True
        assert status.requires_confirmation is False

    def test_warning_status(self, manager):
        """50-75% should be WARNING."""
        # Session budget $5, spend $3 = 60%
        manager.record_spending(amount=3.0, session_id="s", category="c")
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert status.level == BudgetLevel.WARNING.value
        assert status.can_proceed is True

    def test_critical_status(self, manager):
        """75-90% should be CRITICAL."""
        # Session budget $5, spend $4 = 80%
        manager.record_spending(amount=4.0, session_id="s", category="c")
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert status.level == BudgetLevel.CRITICAL.value
        assert status.can_proceed is True

    def test_exceeded_soft_limit(self, manager):
        """90-100% (soft limit) should be EXCEEDED and require confirmation."""
        # Session budget $5, spend $4.7 = 94%
        manager.record_spending(amount=4.7, session_id="s", category="c")
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert status.level == BudgetLevel.EXCEEDED.value
        assert status.can_proceed is True
        assert status.requires_confirmation is True

    def test_blocked_hard_limit(self, manager):
        """Over 100% should be BLOCKED."""
        # Session budget $5, spend $5.5 = 110%
        manager.record_spending(amount=5.5, session_id="s", category="c")
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert status.level == BudgetLevel.BLOCKED.value
        assert status.can_proceed is False

    def test_proposed_spend_included(self, manager):
        """proposed_spend should be added to current spending for check."""
        # Spend $2 actual, propose $3 more => $5/$5 = 100% => BLOCKED
        manager.record_spending(amount=2.0, session_id="s", category="c")
        status = manager.check_budget(
            BudgetType.SESSION, session_id="s", proposed_spend=3.0,
        )
        assert status.level == BudgetLevel.BLOCKED.value

    def test_disabled_budget_allows_all(self, manager):
        """Disabled budget should always return HEALTHY and can_proceed=True."""
        manager.config["session"].enabled = False
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert status.can_proceed is True
        assert status.level == BudgetLevel.HEALTHY.value

    def test_alert_thresholds_triggered(self, manager):
        """Alerts should fire when thresholds are crossed."""
        # Session budget $5, spend $3 = 60% => triggers 50% threshold
        manager.record_spending(amount=3.0, session_id="s", category="c")
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert len(status.alerts_triggered) >= 1
        # The alerts file should have been written
        assert manager.alerts_file.exists()

    def test_alert_not_re_triggered(self, manager):
        """Same threshold should not trigger twice for same budget key."""
        manager.record_spending(amount=3.0, session_id="s", category="c")
        status1 = manager.check_budget(BudgetType.SESSION, session_id="s")
        alerts_first = len(status1.alerts_triggered)

        # Check again without additional spending
        status2 = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert len(status2.alerts_triggered) == 0  # no NEW alerts


# ---------------------------------------------------------------------------
# can_spend
# ---------------------------------------------------------------------------

class TestCanSpend:
    """Tests for BudgetManager.can_spend."""

    def test_allows_when_under_budget(self, manager):
        """can_spend should return True when all budgets are within limits."""
        can, reasons = manager.can_spend(0.50, session_id="s")
        assert can is True
        assert reasons == []

    def test_blocks_when_over_session_budget(self, manager):
        """can_spend should block when session budget would be exceeded."""
        manager.record_spending(amount=4.5, session_id="s", category="c")
        can, reasons = manager.can_spend(1.0, session_id="s")
        assert can is False
        assert len(reasons) >= 1

    def test_blocks_when_over_task_budget(self, manager):
        """can_spend should block when task budget would be exceeded."""
        # Task budget default = $1, try to spend $1.5
        can, reasons = manager.can_spend(1.5, session_id="s", task_id="t")
        assert can is False
        assert len(reasons) >= 1


# ---------------------------------------------------------------------------
# set_budget and get_budget
# ---------------------------------------------------------------------------

class TestSetGetBudget:
    """Tests for set_budget and get_budget."""

    def test_set_budget_updates_config(self, manager):
        """set_budget should update the in-memory config and save to disk."""
        manager.set_budget(BudgetType.SESSION, 15.0)
        assert manager.config["session"].limit == 15.0
        # Verify persisted
        with open(manager.config_file) as f:
            data = json.load(f)
        assert data["session"]["limit"] == 15.0

    def test_get_budget_returns_config(self, manager):
        """get_budget should return the BudgetConfig for a given type."""
        cfg = manager.get_budget(BudgetType.SESSION)
        assert cfg is not None
        assert cfg.budget_type == "session"

    def test_get_budget_returns_none_for_unknown(self, manager):
        """get_budget should return None if budget type has been removed."""
        del manager.config["session"]
        assert manager.get_budget(BudgetType.SESSION) is None


# ---------------------------------------------------------------------------
# Budget history and alerts history
# ---------------------------------------------------------------------------

class TestBudgetHistory:
    """Tests for get_budget_history and get_alerts_history."""

    def test_empty_history(self, manager):
        """Empty spending file should return empty list."""
        assert manager.get_budget_history() == []

    def test_history_aggregates_by_day(self, manager):
        """Spending should be aggregated by date."""
        manager.record_spending(amount=1.0, session_id="s", category="tokens")
        manager.record_spending(amount=2.0, session_id="s", category="tools")

        history = manager.get_budget_history(days=1)
        assert len(history) == 1
        assert history[0]["total"] == pytest.approx(3.0)
        assert history[0]["count"] == 2
        assert "tokens" in history[0]["by_category"]

    def test_alerts_history_empty(self, manager):
        """No alerts file should return empty list."""
        assert manager.get_alerts_history() == []

    def test_alerts_history_after_trigger(self, manager):
        """After triggering alerts, they should appear in history."""
        manager.record_spending(amount=4.0, session_id="s", category="c")
        manager.check_budget(BudgetType.SESSION, session_id="s")

        alerts = manager.get_alerts_history(days=1)
        assert len(alerts) > 0
        assert isinstance(alerts[0], BudgetAlert)


# ---------------------------------------------------------------------------
# reset_session_budget
# ---------------------------------------------------------------------------

class TestResetSessionBudget:
    """Tests for reset_session_budget."""

    def test_clears_triggered_alerts(self, manager):
        """After reset, alerts should fire again."""
        manager.record_spending(amount=3.0, session_id="s", category="c")
        manager.check_budget(BudgetType.SESSION, session_id="s")

        manager.reset_session_budget("s")

        # Check again - should trigger alerts again
        status = manager.check_budget(BudgetType.SESSION, session_id="s")
        assert len(status.alerts_triggered) >= 1


# ---------------------------------------------------------------------------
# generate_dashboard
# ---------------------------------------------------------------------------

class TestGenerateDashboard:
    """Tests for generate_dashboard."""

    def test_dashboard_returns_string(self, manager):
        """Dashboard should return a non-empty string."""
        dashboard = manager.generate_dashboard(session_id="s")
        assert isinstance(dashboard, str)
        assert "BUDGET STATUS DASHBOARD" in dashboard

    def test_dashboard_with_spending(self, manager):
        """Dashboard should reflect current spending."""
        manager.record_spending(amount=2.0, session_id="s", category="tokens")
        dashboard = manager.generate_dashboard(session_id="s")
        assert "$2.00" in dashboard or "2.00" in dashboard
