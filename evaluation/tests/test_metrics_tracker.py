#!/usr/bin/env python3
"""
Tests for metrics_tracker.py — MetricsTracker.

Covers:
- Initialization with config
- collect_metric writes JSONL
- load_metrics reads and parses timestamps
- Timestamp normalization (Z, +00:00, naive)
- calculate_statistics for various metric types
- generate_weekly_report (markdown, json)
- _detect_regressions logic
- Edge cases: empty data, malformed records, missing data file
"""

import json
import pytest
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config and data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    config = {
        "evaluation": {
            "metrics": {
                "enabled": True,
                "collection": "automatic",
                "storage_path": str(data_dir / "metrics.jsonl"),
            },
            "reporting": {
                "schedule": "manual",
                "format": "markdown",
                "output_path": str(reports_dir),
            },
            "regression": {
                "enabled": True,
                "threshold_accuracy": 0.05,
                "threshold_hallucination": 0.03,
                "threshold_tool_errors": 0.10,
            },
        }
    }

    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config))
    return tmp_path, config_file, data_dir


@pytest.fixture
def tracker(config_dir):
    """Return a MetricsTracker using the temporary config."""
    from metrics_tracker import MetricsTracker
    _, config_file, _ = config_dir
    return MetricsTracker(config_path=config_file)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestMetricsTrackerInit:
    """Tests for MetricsTracker initialization."""

    def test_loads_config(self, tracker):
        """Tracker should load the YAML configuration."""
        assert tracker.config["evaluation"]["metrics"]["enabled"] is True

    def test_missing_config_exits(self, tmp_path):
        """Missing config file should cause sys.exit."""
        from metrics_tracker import MetricsTracker
        fake_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(SystemExit):
            MetricsTracker(config_path=fake_path)

    def test_data_path_set(self, tracker, config_dir):
        """data_path should match the configured storage_path."""
        _, _, data_dir = config_dir
        assert tracker.data_path == data_dir / "metrics.jsonl"


# ---------------------------------------------------------------------------
# collect_metric
# ---------------------------------------------------------------------------

class TestCollectMetric:
    """Tests for MetricsTracker.collect_metric."""

    def test_writes_jsonl(self, tracker):
        """collect_metric should append a JSONL line."""
        tracker.collect_metric("accuracy", 0.95, {"task_id": "t1"})
        assert tracker.data_path.exists()
        lines = tracker.data_path.read_text().strip().split("\n")
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["metric_type"] == "accuracy"
        assert rec["value"] == 0.95
        assert rec["metadata"]["task_id"] == "t1"

    def test_disabled_metrics_skipped(self, tracker):
        """When metrics are disabled, nothing should be written."""
        tracker.config["evaluation"]["metrics"]["enabled"] = False
        tracker.collect_metric("accuracy", 0.90)
        assert not tracker.data_path.exists()

    def test_multiple_metrics(self, tracker):
        """Multiple metrics should be appended correctly."""
        tracker.collect_metric("accuracy", 0.9)
        tracker.collect_metric("hallucination", 0.02)
        tracker.collect_metric("latency", 1.5)
        lines = tracker.data_path.read_text().strip().split("\n")
        assert len(lines) == 3


# ---------------------------------------------------------------------------
# load_metrics
# ---------------------------------------------------------------------------

class TestLoadMetrics:
    """Tests for MetricsTracker.load_metrics."""

    def test_empty_file_returns_empty_df(self, tracker):
        """No data file should return empty DataFrame."""
        df = tracker.load_metrics()
        assert df.empty

    def test_loads_records(self, tracker):
        """Should load all records into a DataFrame."""
        tracker.collect_metric("accuracy", 0.85)
        tracker.collect_metric("accuracy", 0.90)
        df = tracker.load_metrics()
        assert len(df) == 2
        assert "metric_type" in df.columns

    def test_timestamp_z_normalized(self, tracker):
        """Timestamps ending with Z should be parsed correctly."""
        record = {
            "timestamp": "2026-02-01T10:00:00.000000Z",
            "metric_type": "accuracy",
            "value": 0.9,
            "metadata": {},
        }
        tracker.data_path.write_text(json.dumps(record) + "\n")
        df = tracker.load_metrics()
        assert len(df) == 1
        assert df["timestamp"].iloc[0] is not None

    def test_timestamp_offset_format(self, tracker):
        """Timestamps with +00:00 should be parsed correctly."""
        record = {
            "timestamp": "2026-02-01T10:00:00+00:00",
            "metric_type": "cost",
            "value": 0.05,
            "metadata": {},
        }
        tracker.data_path.write_text(json.dumps(record) + "\n")
        df = tracker.load_metrics()
        assert len(df) == 1

    def test_timestamp_naive_format(self, tracker):
        """Naive timestamps (no TZ) should be localized to UTC."""
        record = {
            "timestamp": "2026-02-01T10:00:00.500000",
            "metric_type": "cache",
            "value": 0.8,
            "metadata": {},
        }
        tracker.data_path.write_text(json.dumps(record) + "\n")
        df = tracker.load_metrics()
        assert len(df) == 1

    def test_malformed_lines_skipped(self, tracker):
        """Corrupted JSON lines should be skipped."""
        tracker.collect_metric("accuracy", 0.85)
        with open(tracker.data_path, "a") as f:
            f.write("not valid json\n")
        tracker.collect_metric("accuracy", 0.90)

        df = tracker.load_metrics()
        assert len(df) == 2

    def test_date_filter(self, tracker):
        """start_date and end_date filters should work."""
        now = datetime.now(timezone.utc)
        record_old = {
            "timestamp": (now - timedelta(days=30)).isoformat(),
            "metric_type": "accuracy",
            "value": 0.70,
            "metadata": {},
        }
        record_new = {
            "timestamp": now.isoformat(),
            "metric_type": "accuracy",
            "value": 0.95,
            "metadata": {},
        }
        with open(tracker.data_path, "w") as f:
            f.write(json.dumps(record_old) + "\n")
            f.write(json.dumps(record_new) + "\n")

        df = tracker.load_metrics(start_date=now - timedelta(days=1))
        assert len(df) == 1
        assert df.iloc[0]["value"] == 0.95


# ---------------------------------------------------------------------------
# calculate_statistics
# ---------------------------------------------------------------------------

class TestCalculateStatistics:
    """Tests for MetricsTracker.calculate_statistics."""

    def test_basic_stats(self, tracker):
        """Should compute mean, median, std, min, max, count."""
        for v in [0.8, 0.85, 0.9, 0.95, 1.0]:
            tracker.collect_metric("accuracy", v)
        df = tracker.load_metrics()
        stats = tracker.calculate_statistics(df, "accuracy")
        assert stats["count"] == 5
        assert stats["mean"] == pytest.approx(0.9, abs=0.01)
        assert stats["min"] == pytest.approx(0.8)
        assert stats["max"] == pytest.approx(1.0)

    def test_empty_metric_type(self, tracker):
        """Non-existent metric type should return zeros."""
        tracker.collect_metric("accuracy", 0.9)
        df = tracker.load_metrics()
        stats = tracker.calculate_statistics(df, "nonexistent")
        assert stats["count"] == 0
        assert stats["mean"] == 0.0


# ---------------------------------------------------------------------------
# _detect_regressions
# ---------------------------------------------------------------------------

class TestDetectRegressions:
    """Tests for MetricsTracker._detect_regressions."""

    def test_no_regression(self, tracker):
        """Metrics within targets should not trigger regressions."""
        metrics = {
            "accuracy": {"mean": 0.90, "count": 10},
            "hallucination": {"mean": 0.02, "count": 10},
            "tool_error": {"mean": 0.05, "count": 10},
        }
        regressions = tracker._detect_regressions(metrics)
        assert regressions == []

    def test_accuracy_regression_detected(self, tracker):
        """Low accuracy should trigger regression."""
        metrics = {
            "accuracy": {"mean": 0.70, "count": 10},  # target 0.85 - 0.05 = 0.80
            "hallucination": {"mean": 0.02, "count": 10},
            "tool_error": {"mean": 0.05, "count": 10},
        }
        regressions = tracker._detect_regressions(metrics)
        assert len(regressions) >= 1
        assert "ACCURACY" in regressions[0]

    def test_hallucination_regression_detected(self, tracker):
        """High hallucination rate should trigger regression."""
        metrics = {
            "accuracy": {"mean": 0.90, "count": 10},
            "hallucination": {"mean": 0.15, "count": 10},  # target 0.05 + 0.03 = 0.08
            "tool_error": {"mean": 0.05, "count": 10},
        }
        regressions = tracker._detect_regressions(metrics)
        assert any("HALLUCINATION" in r for r in regressions)

    def test_zero_count_ignored(self, tracker):
        """Metrics with count=0 should be ignored."""
        metrics = {
            "accuracy": {"mean": 0.0, "count": 0},
        }
        regressions = tracker._detect_regressions(metrics)
        assert regressions == []


# ---------------------------------------------------------------------------
# generate_weekly_report
# ---------------------------------------------------------------------------

class TestGenerateWeeklyReport:
    """Tests for MetricsTracker.generate_weekly_report."""

    def test_empty_data_markdown(self, tracker):
        """Empty data should produce a 'No Data' markdown report."""
        report = tracker.generate_weekly_report(output_format="markdown")
        assert "No Data Available" in report

    def test_empty_data_json(self, tracker):
        """Empty data should produce a JSON report with message."""
        report = tracker.generate_weekly_report(output_format="json")
        data = json.loads(report)
        assert "message" in data or "metrics" in data

    def test_report_with_data(self, tracker):
        """Report with metrics should include summary table."""
        for _ in range(5):
            tracker.collect_metric("accuracy", 0.9)
            tracker.collect_metric("hallucination", 0.03)
        report = tracker.generate_weekly_report(output_format="markdown")
        assert "Summary" in report
        assert "Accuracy" in report

    def test_json_format(self, tracker):
        """JSON format should be valid and contain metrics."""
        tracker.collect_metric("accuracy", 0.9)
        report = tracker.generate_weekly_report(output_format="json")
        data = json.loads(report)
        assert "period" in data
        assert "metrics" in data

    def test_unsupported_format_raises(self, tracker):
        """Unsupported format should raise ValueError."""
        tracker.collect_metric("accuracy", 0.9)
        with pytest.raises(ValueError, match="Unsupported format"):
            tracker.generate_weekly_report(output_format="html")


# ---------------------------------------------------------------------------
# collect_cache_metric
# ---------------------------------------------------------------------------

class TestCollectCacheMetric:
    """Tests for MetricsTracker.collect_cache_metric."""

    def test_records_cache_metric(self, tracker):
        """Cache metric should be recorded with hit rate and savings."""
        tracker.collect_cache_metric(
            cached_tokens=8000, fresh_tokens=2000, latency_ms=150,
        )
        df = tracker.load_metrics()
        assert len(df) == 1
        assert df.iloc[0]["metric_type"] == "cache"
        meta = df.iloc[0]["metadata"]
        assert meta["hit_rate"] == pytest.approx(0.8)
        assert meta["cached_tokens"] == 8000


# ---------------------------------------------------------------------------
# collect_model_routing_metric
# ---------------------------------------------------------------------------

class TestCollectModelRoutingMetric:
    """Tests for MetricsTracker.collect_model_routing_metric."""

    def test_records_routing_metric(self, tracker):
        """Routing metric should be recorded with model and cost saved."""
        tracker.collect_model_routing_metric(
            task_description="format a YAML file",
            selected_model="haiku",
            complexity="simple",
            cost_saved=0.02,
        )
        df = tracker.load_metrics()
        assert len(df) == 1
        assert df.iloc[0]["metric_type"] == "model_routing"
        assert df.iloc[0]["value"] == "haiku"
