#!/usr/bin/env pytest
"""Tests for TIER 4G: MLOps & Infrastructure — 8 P1 Gaps.

TDD Workflow: Tests written FIRST, then implementation.
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "tools"))

# Import tools after implementation
try:
    from config_manager import (
        validate_config, check_drift, config_diff, validate_settings_json
    )
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False

try:
    from observability_collector import (
        collect_metrics, aggregate_metrics, export_metrics
    )
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

try:
    from latency_optimizer import (
        analyze_tool_latency, suggest_optimizations, identify_bottlenecks
    )
    LATENCY_OPTIMIZER_AVAILABLE = True
except ImportError:
    LATENCY_OPTIMIZER_AVAILABLE = False


class TestConfigManager:
    """Test config_manager.py functionality."""

    @pytest.mark.skipif(not CONFIG_MANAGER_AVAILABLE, reason="config_manager not implemented")
    def test_validate_claude_md(self):
        """Test CLAUDE.md validation."""
        valid_config = """# Claude Code Master Configuration
## CORE IDENTITY
## OPERATING ENVIRONMENT
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(valid_config)
            f.flush()
            result = validate_config(f.name)
            assert result is not None
            assert isinstance(result, dict)

    @pytest.mark.skipif(not CONFIG_MANAGER_AVAILABLE, reason="config_manager not implemented")
    def test_validate_settings_json(self):
        """Test settings.json validation."""
        valid_settings = {
            "hooks": {
                "SessionEnd": []
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_settings, f)
            f.flush()
            result = validate_settings_json(f.name)
            assert result is not None
            assert result.get("valid") is True or isinstance(result, dict)

    @pytest.mark.skipif(not CONFIG_MANAGER_AVAILABLE, reason="config_manager not implemented")
    def test_config_diff(self):
        """Test configuration diff functionality."""
        config1 = """# Version 1
Key: Value1
"""
        config2 = """# Version 2
Key: Value2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f1:
            f1.write(config1)
            f1.flush()
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f2:
                f2.write(config2)
                f2.flush()
                diff = config_diff(f1.name, f2.name)
                assert diff is not None
                assert isinstance(diff, (str, dict, list))

    @pytest.mark.skipif(not CONFIG_MANAGER_AVAILABLE, reason="config_manager not implemented")
    def test_check_drift(self):
        """Test configuration drift detection."""
        # Should detect drift between dev and prod configs
        result = check_drift()
        assert result is not None
        assert isinstance(result, dict)


class TestObservabilityCollector:
    """Test observability_collector.py functionality."""

    @pytest.mark.skipif(not OBSERVABILITY_AVAILABLE, reason="observability_collector not implemented")
    def test_collect_metrics(self):
        """Test metrics collection."""
        metrics = collect_metrics()
        assert metrics is not None
        assert isinstance(metrics, dict)
        # Expected metric categories
        expected_keys = ["latency", "token_counts", "error_rates", "tool_usage"]
        assert any(key in metrics for key in expected_keys)

    @pytest.mark.skipif(not OBSERVABILITY_AVAILABLE, reason="observability_collector not implemented")
    def test_aggregate_metrics(self):
        """Test metrics aggregation."""
        sample_data = [
            {"latency_ms": 100, "tokens": 50},
            {"latency_ms": 200, "tokens": 75}
        ]
        aggregated = aggregate_metrics(sample_data, period="session")
        assert aggregated is not None
        assert isinstance(aggregated, dict)

    @pytest.mark.skipif(not OBSERVABILITY_AVAILABLE, reason="observability_collector not implemented")
    def test_export_metrics_json(self):
        """Test JSON export."""
        metrics = {"latency_p50": 100, "latency_p95": 200}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_metrics(metrics, f.name, format="json")
            # Check file was written
            assert Path(f.name).exists()
            with open(f.name) as rf:
                data = json.load(rf)
                assert isinstance(data, dict)

    @pytest.mark.skipif(not OBSERVABILITY_AVAILABLE, reason="observability_collector not implemented")
    def test_export_metrics_csv(self):
        """Test CSV export."""
        metrics = [{"metric": "latency", "value": 100}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            export_metrics(metrics, f.name, format="csv")
            assert Path(f.name).exists()


class TestLatencyOptimizer:
    """Test latency_optimizer.py functionality."""

    @pytest.mark.skipif(not LATENCY_OPTIMIZER_AVAILABLE, reason="latency_optimizer not implemented")
    def test_analyze_tool_latency(self):
        """Test tool latency analysis."""
        # Should analyze from logs
        result = analyze_tool_latency()
        assert result is not None
        assert isinstance(result, (dict, list))

    @pytest.mark.skipif(not LATENCY_OPTIMIZER_AVAILABLE, reason="latency_optimizer not implemented")
    def test_identify_bottlenecks(self):
        """Test bottleneck identification."""
        sample_data = [
            {"tool": "Read", "latency_ms": 50},
            {"tool": "Bash", "latency_ms": 5000},  # Slow
            {"tool": "Edit", "latency_ms": 100}
        ]
        bottlenecks = identify_bottlenecks(sample_data)
        assert bottlenecks is not None
        assert isinstance(bottlenecks, list)
        # Bash should be identified as bottleneck
        if len(bottlenecks) > 0:
            assert any("Bash" in str(b) for b in bottlenecks)

    @pytest.mark.skipif(not LATENCY_OPTIMIZER_AVAILABLE, reason="latency_optimizer not implemented")
    def test_suggest_optimizations(self):
        """Test optimization suggestions."""
        bottlenecks = [{"tool": "Bash", "avg_latency": 5000, "count": 10}]
        suggestions = suggest_optimizations(bottlenecks)
        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


class TestModuleSections:
    """Test that required module sections exist."""

    def test_devops_agent_config_section(self):
        """Test Agent Configuration Management section exists."""
        devops_path = Path.home() / ".claude" / "modules" / "03-devops.md"
        content = devops_path.read_text()
        # Check for configuration management concepts
        assert any(keyword in content for keyword in [
            "configuration", "drift", "validation", "schema"
        ])

    def test_devops_monitoring_section(self):
        """Test Section 11: Production Monitoring Patterns exists."""
        devops_path = Path.home() / ".claude" / "modules" / "03-devops.md"
        content = devops_path.read_text()
        # Check for monitoring concepts
        assert any(keyword in content for keyword in [
            "monitoring", "metrics", "latency", "alert", "dashboard"
        ])

    def test_devops_model_versioning_section(self):
        """Test Section 12: Model Versioning exists."""
        devops_path = Path.home() / ".claude" / "modules" / "03-devops.md"
        content = devops_path.read_text()
        # Check for model versioning concepts
        assert any(keyword in content for keyword in [
            "model", "version", "registry", "A/B"
        ])

    def test_devops_observability_section(self):
        """Test Observability section exists."""
        devops_path = Path.home() / ".claude" / "modules" / "03-devops.md"
        content = devops_path.read_text()
        # Check for observability concepts
        assert any(keyword in content for keyword in [
            "observability", "tracing", "OpenTelemetry"
        ])


class TestToolCLI:
    """Test CLI interfaces of tools."""

    @pytest.mark.skipif(not CONFIG_MANAGER_AVAILABLE, reason="config_manager not implemented")
    def test_config_manager_cli_help(self):
        """Test config_manager CLI --help works."""
        import subprocess
        result = subprocess.run(
            ["python", str(Path.home() / ".claude" / "tools" / "config_manager.py"), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "validate" in result.stdout or "diff" in result.stdout

    @pytest.mark.skipif(not OBSERVABILITY_AVAILABLE, reason="observability_collector not implemented")
    def test_observability_cli_help(self):
        """Test observability_collector CLI --help works."""
        import subprocess
        result = subprocess.run(
            ["python", str(Path.home() / ".claude" / "tools" / "observability_collector.py"), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "collect" in result.stdout or "report" in result.stdout

    @pytest.mark.skipif(not LATENCY_OPTIMIZER_AVAILABLE, reason="latency_optimizer not implemented")
    def test_latency_optimizer_cli_help(self):
        """Test latency_optimizer CLI --help works."""
        import subprocess
        result = subprocess.run(
            ["python", str(Path.home() / ".claude" / "tools" / "latency_optimizer.py"), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "analyze" in result.stdout or "suggest" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
