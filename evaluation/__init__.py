"""
Claude Evaluation Framework
Version: 1.0.0

A comprehensive evaluation and metrics tracking framework for Claude agents.

Modules:
- metrics_tracker: Core metrics collection and reporting
- regression_suite: Regression detection and baseline comparison
- ab_testing: Statistical A/B testing for prompt strategies
"""

__version__ = "1.0.0"
__author__ = "Claude Configuration Project"

from pathlib import Path

# Framework paths
EVALUATION_ROOT = Path.home() / ".claude" / "evaluation"
CONFIG_PATH = EVALUATION_ROOT / "config.yaml"
DATA_PATH = EVALUATION_ROOT / "data"
REPORTS_PATH = EVALUATION_ROOT / "reports"

# Ensure data directories exist
DATA_PATH.mkdir(parents=True, exist_ok=True)
REPORTS_PATH.mkdir(parents=True, exist_ok=True)
