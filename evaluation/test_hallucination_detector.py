#!/usr/bin/env python3
"""
Pytest Test Suite for Hallucination Detector
TIER 3 Task 18 (GAP-EVAL-HALLUCINATION)

Tests detection patterns, known facts validation, and core functionality.

Usage:
    pytest test_hallucination_detector.py -v
    pytest test_hallucination_detector.py --cov=hallucination_detector
"""

import pytest
from hallucination_detector import (
    HallucinationDetector,
    HallucinationCategory,
    Severity,
    DetectedHallucination,
    DetectionResult,
    HallucinationLogger
)
from pathlib import Path
import json
import tempfile


class TestHallucinationDetector:
    """Test suite for HallucinationDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a fresh detector instance for each test."""
        return HallucinationDetector()

    def test_citation_hallucination_detection(self, detector):
        """Test detection of unverifiable citations."""
        text = "According to Smith et al., 2023, this technique improves accuracy by 50%."
        result = detector.detect(text)

        assert result.total_hallucinations >= 1
        assert "citation" in result.by_category
        assert result.by_category["citation"] >= 1

    def test_version_hallucination_detection(self, detector):
        """Test detection of version information that needs verification."""
        text = "Python 3.15 was released in January 2025 with major improvements."
        result = detector.detect(text)

        assert result.total_hallucinations >= 1
        assert "version" in result.by_category
        # Should detect both version number and release date
        assert result.by_category["version"] >= 1

    def test_quantitative_hallucination_detection(self, detector):
        """Test detection of uncited statistics."""
        text = "Studies show 95% of developers prefer this approach."
        result = detector.detect(text)

        assert result.total_hallucinations >= 1
        assert "quantitative" in result.by_category
        assert result.by_category["quantitative"] >= 1

    def test_factual_hallucination_detection(self, detector):
        """Test detection of superlative claims without evidence."""
        text = "OpenAI is the first company to implement this technology."
        result = detector.detect(text)

        assert result.total_hallucinations >= 1
        assert "factual" in result.by_category
        assert result.by_category["factual"] >= 1

    def test_safe_text_minimal_detections(self, detector):
        """Test that safe text produces minimal false positives."""
        text = "Here is a simple Python function that calculates factorial."
        result = detector.detect(text)

        # Allow up to 1 false positive (temporal detection for "Here is")
        assert result.total_hallucinations <= 1
        # Should be low or no risk
        assert result.risk_level in ["LOW", "MEDIUM"]

    def test_severity_classification(self, detector):
        """Test that severity is correctly classified."""
        # Critical: statistics without citation
        text_critical = "Studies show 95% accuracy."
        result_critical = detector.detect(text_critical)
        assert "critical" in result_critical.by_severity or "major" in result_critical.by_severity

        # Minor: temporal claim
        text_minor = "Currently the most popular framework."
        result_minor = detector.detect(text_minor)
        if result_minor.total_hallucinations > 0:
            assert "minor" in result_minor.by_severity

    def test_risk_level_calculation(self, detector):
        """Test risk level assignment based on severity."""
        # Low risk: no hallucinations
        text_safe = "The function returns an integer."
        result_safe = detector.detect(text_safe)
        assert result_safe.risk_level in ["LOW", "MEDIUM"]  # Allow minor temporal detection

        # High risk: multiple major hallucinations
        text_risky = """
        According to Smith et al., 2023, research shows 95% accuracy.
        The first company to implement this was founded in 2019.
        Studies indicate approximately 50 million users prefer this approach.
        """
        result_risky = detector.detect(text_risky)
        assert result_risky.total_hallucinations >= 3
        # Should be at least MEDIUM or HIGH risk
        assert result_risky.risk_level in ["MEDIUM", "HIGH", "CRITICAL"]

    def test_known_facts_validation_anthropic(self, detector):
        """Test known facts validation for Anthropic founding."""
        # Correct fact
        text_correct = "Anthropic was founded in 2021"
        violations_correct = detector.check_known_facts(text_correct)
        assert len(violations_correct) == 0

        # Incorrect fact
        text_incorrect = "Anthropic was founded in 2019"
        violations_incorrect = detector.check_known_facts(text_incorrect)
        assert len(violations_incorrect) > 0
        assert violations_incorrect[0]["type"] == "factual_error"
        assert "2021" in violations_incorrect[0]["actual"]

    def test_known_facts_validation_openai(self, detector):
        """Test known facts validation for OpenAI founding."""
        # Correct fact
        text_correct = "OpenAI was founded in 2015"
        violations_correct = detector.check_known_facts(text_correct)
        assert len(violations_correct) == 0

        # Incorrect fact
        text_incorrect = "OpenAI was established in 2018"
        violations_incorrect = detector.check_known_facts(text_incorrect)
        assert len(violations_incorrect) > 0
        assert violations_incorrect[0]["type"] == "factual_error"

    def test_confidence_calculation(self, detector):
        """Test confidence score calculation."""
        text = "According to a recent study, this approach is effective."
        result = detector.detect(text)

        if result.hallucinations:
            for hallucination in result.hallucinations:
                # Confidence should be between 0.1 and 0.95
                assert 0.1 <= hallucination.confidence <= 0.95

    def test_multiple_categories_in_one_text(self, detector):
        """Test detection of multiple hallucination types in one text."""
        text = """
        According to Smith et al., 2023, Python 3.14 was released in 2024.
        Studies show 95% of users prefer it. OpenAI was the first to adopt it.
        """
        result = detector.detect(text)

        # Should detect multiple categories
        assert result.total_hallucinations >= 3
        # Should have at least 2 different categories
        assert len(result.by_category) >= 2

    def test_empty_text(self, detector):
        """Test detection on empty text."""
        result = detector.detect("")
        assert result.total_hallucinations == 0
        assert result.risk_level == "LOW"

    def test_detection_result_structure(self, detector):
        """Test that DetectionResult has all required fields."""
        text = "Test text"
        result = detector.detect(text)

        assert hasattr(result, 'text_analyzed')
        assert hasattr(result, 'total_hallucinations')
        assert hasattr(result, 'by_category')
        assert hasattr(result, 'by_severity')
        assert hasattr(result, 'hallucinations')
        assert hasattr(result, 'confidence_score')
        assert hasattr(result, 'risk_level')
        assert hasattr(result, 'timestamp')

        # Verify types
        assert isinstance(result.by_category, dict)
        assert isinstance(result.by_severity, dict)
        assert isinstance(result.hallucinations, list)
        assert isinstance(result.confidence_score, float)
        assert result.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def test_pattern_coverage(self, detector):
        """Test that all pattern categories are represented."""
        # Check that we have patterns for all major categories
        categories_covered = set()
        for pattern in detector.patterns:
            categories_covered.add(pattern.category)

        # Should have patterns for key categories
        expected_categories = [
            HallucinationCategory.CITATION,
            HallucinationCategory.VERSION,
            HallucinationCategory.FACTUAL,
            HallucinationCategory.QUANTITATIVE
        ]

        for cat in expected_categories:
            assert cat in categories_covered

    def test_arxiv_pattern(self, detector):
        """Test detection of arXiv IDs that need verification."""
        text = "See arXiv:2301.12345 for more details."
        result = detector.detect(text)

        assert result.total_hallucinations >= 1
        assert "citation" in result.by_category

    def test_doi_pattern(self, detector):
        """Test detection of DOIs that need verification."""
        text = "Published in doi: 10.1234/example.2023"
        result = detector.detect(text)

        assert result.total_hallucinations >= 1
        assert "citation" in result.by_category

    def test_code_hallucination_pattern(self, detector):
        """Test detection of potentially non-existent packages."""
        text = "Install it with: pip install fake-nonexistent-package"
        result = detector.detect(text)

        assert result.total_hallucinations >= 1
        assert "code" in result.by_category


class TestHallucinationLogger:
    """Test suite for HallucinationLogger class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.json')
        db_path = Path(path)
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def logger(self, temp_db):
        """Create a logger instance with temporary database."""
        return HallucinationLogger(db_path=temp_db)

    @pytest.fixture
    def sample_result(self):
        """Create a sample detection result for testing."""
        from hallucination_detector import DetectionResult
        return DetectionResult(
            text_analyzed="Test text",
            total_hallucinations=2,
            by_category={"citation": 1, "version": 1},
            by_severity={"major": 1, "minor": 1},
            hallucinations=[],
            confidence_score=0.75,
            risk_level="MEDIUM"
        )

    def test_log_detection(self, logger, sample_result):
        """Test logging a detection result."""
        success = logger.log_detection(sample_result, session_id="test-session")
        assert success is True

        # Verify file was created
        assert logger.db_path.exists()

        # Verify content
        with open(logger.db_path, 'r') as f:
            entries = json.load(f)
        assert len(entries) == 1
        assert entries[0]["session_id"] == "test-session"
        assert entries[0]["total_hallucinations"] == 2

    def test_log_multiple_detections(self, logger, sample_result):
        """Test logging multiple detections."""
        for i in range(5):
            logger.log_detection(sample_result, session_id=f"session-{i}")

        with open(logger.db_path, 'r') as f:
            entries = json.load(f)
        assert len(entries) == 5

    def test_log_rotation(self, logger, sample_result):
        """Test that log rotation keeps only last 1000 entries."""
        # Log 1050 entries
        for i in range(1050):
            logger.log_detection(sample_result, session_id=f"session-{i}")

        with open(logger.db_path, 'r') as f:
            entries = json.load(f)

        # Should keep only last 1000
        assert len(entries) == 1000
        # First entry should be from session-50 (0-49 rotated out)
        assert entries[0]["session_id"] == "session-50"

    def test_get_historical_stats_empty(self, logger):
        """Test historical stats on empty database."""
        stats = logger.get_historical_stats()
        assert "total_entries" in stats
        assert stats["total_entries"] == 0

    def test_get_historical_stats(self, logger, sample_result):
        """Test historical statistics calculation."""
        # Log some entries
        for i in range(10):
            logger.log_detection(sample_result, session_id=f"session-{i}")

        stats = logger.get_historical_stats()
        assert stats["total_entries"] == 10
        assert stats["total_hallucinations"] == 20  # 2 per entry * 10
        assert stats["average_per_entry"] == 2.0
        assert stats["hallucination_rate"] == 2.0


class TestPatternMatching:
    """Test specific pattern matching edge cases."""

    @pytest.fixture
    def detector(self):
        return HallucinationDetector()

    def test_citation_with_nearby_reference(self, detector):
        """Test that citations near references get lower confidence."""
        text_with_ref = "According to Smith et al., 2023 [1], this works."
        text_without_ref = "According to Smith et al., 2023, this works."

        result_with = detector.detect(text_with_ref)
        result_without = detector.detect(text_without_ref)

        # Both should detect, but with_ref should have lower confidence
        if result_with.hallucinations and result_without.hallucinations:
            assert result_with.hallucinations[0].confidence < result_without.hallucinations[0].confidence

    def test_uncertainty_expression_reduces_confidence(self, detector):
        """Test that uncertainty phrases reduce hallucination confidence."""
        text_certain = "Python 3.15 was released in 2025."
        text_uncertain = "I'm not certain, but Python 3.15 was released in 2025."

        result_certain = detector.detect(text_certain)
        result_uncertain = detector.detect(text_uncertain)

        # Both should detect version hallucination
        assert result_certain.total_hallucinations >= 1
        assert result_uncertain.total_hallucinations >= 1

        # Uncertain version should have lower confidence
        if result_certain.hallucinations and result_uncertain.hallucinations:
            # Find version hallucinations
            certain_version = [h for h in result_certain.hallucinations if h.category == HallucinationCategory.VERSION][0]
            uncertain_version = [h for h in result_uncertain.hallucinations if h.category == HallucinationCategory.VERSION][0]
            assert uncertain_version.confidence < certain_version.confidence


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
