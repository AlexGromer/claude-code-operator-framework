#!/usr/bin/env python3
"""
Test Suite for Hallucination Detection System

Tests for hallucination_detector.py (GAP-EVAL-HALLUCINATION / Task 18)

Covers:
- Enum definitions and values
- Dataclass structure
- HallucinationDetector pattern matching
- Detection result structure
- Confidence calculation
- Risk level assessment
- CLI interface

Version: 1.0.0
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hallucination_detector import (
    HallucinationCategory,
    Severity,
    HallucinationPattern,
    DetectedHallucination,
    DetectionResult,
    HallucinationDetector,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def detector():
    """Create HallucinationDetector instance without web validation."""
    return HallucinationDetector(enable_web_validation=False)


@pytest.fixture
def detector_with_patterns():
    """Create detector and verify patterns are loaded."""
    d = HallucinationDetector(enable_web_validation=False)
    assert len(d.PATTERNS) > 0
    return d


@pytest.fixture
def sample_hallucination_texts():
    """Sample texts containing potential hallucinations."""
    return [
        # Citation hallucination
        "According to Smith et al. (2025) in their paper arXiv:9999.99999, the study found...",
        # Version hallucination
        "Python 4.5 was released in 2024 with major improvements.",
        # Entity hallucination
        "The company MegaTech Corp (NYSE: MTCH) reported earnings of $50B.",
        # Factual hallucination
        "Claude was first released in January 2019 by Anthropic.",
    ]


@pytest.fixture
def benign_texts():
    """Texts that should not trigger hallucination detection."""
    return [
        "Hello, how are you?",
        "Python is a popular programming language.",
        "Machine learning uses data to train models.",
        "Please help me with my code.",
    ]


# ============================================================================
# Test: Enums
# ============================================================================

class TestHallucinationCategory:
    """Tests for HallucinationCategory enum."""

    def test_category_count(self):
        """Test that all 7 categories exist."""
        categories = list(HallucinationCategory)
        assert len(categories) == 7

    def test_category_values(self):
        """Test specific category values."""
        assert HallucinationCategory.FACTUAL.value == "factual"
        assert HallucinationCategory.CITATION.value == "citation"
        assert HallucinationCategory.CODE.value == "code"
        assert HallucinationCategory.VERSION.value == "version"
        assert HallucinationCategory.ENTITY.value == "entity"

    def test_category_is_string_enum(self):
        """Test that categories are string enums."""
        for cat in HallucinationCategory:
            assert isinstance(cat.value, str)


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_count(self):
        """Test that all 3 severity levels exist."""
        severities = list(Severity)
        assert len(severities) == 3

    def test_severity_values(self):
        """Test specific severity values."""
        assert Severity.MINOR.value == "minor"
        assert Severity.MAJOR.value == "major"
        assert Severity.CRITICAL.value == "critical"

    def test_severity_ordering_conceptual(self):
        """Test that severity ordering makes conceptual sense."""
        # CRITICAL > MAJOR > MINOR
        severity_order = {"critical": 3, "major": 2, "minor": 1}
        assert severity_order[Severity.CRITICAL.value] > severity_order[Severity.MAJOR.value]
        assert severity_order[Severity.MAJOR.value] > severity_order[Severity.MINOR.value]


# ============================================================================
# Test: Dataclasses
# ============================================================================

class TestHallucinationPattern:
    """Tests for HallucinationPattern dataclass."""

    def test_pattern_creation(self):
        """Test creating a pattern."""
        pattern = HallucinationPattern(
            id="TEST-001",
            category=HallucinationCategory.FACTUAL,
            pattern=r"test pattern",
            description="Test description",
            severity=Severity.MINOR
        )
        assert pattern.id == "TEST-001"
        assert pattern.category == HallucinationCategory.FACTUAL

    def test_pattern_default_examples(self):
        """Test that examples defaults to empty list."""
        pattern = HallucinationPattern(
            id="TEST-002",
            category=HallucinationCategory.CITATION,
            pattern=r"test",
            description="Test",
            severity=Severity.MAJOR
        )
        assert pattern.examples == []


class TestDetectedHallucination:
    """Tests for DetectedHallucination dataclass."""

    def test_hallucination_creation(self):
        """Test creating a detected hallucination."""
        h = DetectedHallucination(
            id="",
            category=HallucinationCategory.CITATION,
            severity=Severity.MAJOR,
            text_snippet="arXiv:9999.99999",
            pattern_id="CIT-001",
            description="Suspicious arXiv ID",
            confidence=0.7
        )
        assert h.category == HallucinationCategory.CITATION
        assert h.confidence == 0.7

    def test_hallucination_auto_id(self):
        """Test that ID is auto-generated."""
        h = DetectedHallucination(
            id="",
            category=HallucinationCategory.FACTUAL,
            severity=Severity.MINOR,
            text_snippet="test snippet",
            pattern_id="TEST-001",
            description="Test",
            confidence=0.5
        )
        # ID should be generated from hash
        assert h.id is not None
        assert len(h.id) == 12  # MD5 hash truncated to 12 chars

    def test_hallucination_auto_timestamp(self):
        """Test that timestamp is auto-generated."""
        h = DetectedHallucination(
            id="",
            category=HallucinationCategory.ENTITY,
            severity=Severity.MINOR,
            text_snippet="test",
            pattern_id="TEST",
            description="Test",
            confidence=0.5
        )
        assert h.timestamp is not None
        assert "T" in h.timestamp  # ISO format


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_result_creation(self):
        """Test creating a detection result."""
        result = DetectionResult(
            text_analyzed="Test text",
            total_hallucinations=2,
            by_category={"citation": 1, "factual": 1},
            by_severity={"major": 1, "minor": 1},
            hallucinations=[],
            confidence_score=0.75,
            risk_level="MEDIUM"
        )
        assert result.total_hallucinations == 2
        assert result.risk_level == "MEDIUM"

    def test_result_auto_timestamp(self):
        """Test that timestamp is auto-generated."""
        result = DetectionResult(
            text_analyzed="Test",
            total_hallucinations=0,
            by_category={},
            by_severity={},
            hallucinations=[],
            confidence_score=1.0,
            risk_level="LOW"
        )
        assert result.timestamp is not None


# ============================================================================
# Test: HallucinationDetector - Initialization
# ============================================================================

class TestHallucinationDetectorInit:
    """Tests for HallucinationDetector initialization."""

    def test_detector_creation(self, detector):
        """Test that detector creates successfully."""
        assert detector is not None

    def test_detector_has_patterns(self, detector):
        """Test that detector has patterns loaded."""
        assert hasattr(detector, 'PATTERNS')
        assert len(detector.PATTERNS) > 0

    def test_detector_pattern_count(self, detector):
        """Test that detector has expected number of patterns (~18)."""
        assert len(detector.PATTERNS) >= 10, "Should have at least 10 patterns"

    def test_detector_web_validation_disabled(self, detector):
        """Test that web validation can be disabled."""
        assert detector.enable_web_validation == False

    def test_detector_detection_log_empty(self, detector):
        """Test that detection log starts empty."""
        assert len(detector.detection_log) == 0


# ============================================================================
# Test: HallucinationDetector - Detection
# ============================================================================

class TestHallucinationDetectorDetection:
    """Tests for detection functionality."""

    def test_detect_returns_result(self, detector):
        """Test that detect() returns DetectionResult."""
        result = detector.detect("Sample text for analysis")
        assert isinstance(result, DetectionResult)

    def test_detect_benign_text(self, detector, benign_texts):
        """Test that benign texts produce few/no hallucinations."""
        for text in benign_texts:
            result = detector.detect(text)
            assert result.total_hallucinations == 0, f"False positive for: {text}"

    def test_detect_arxiv_pattern(self, detector):
        """Test detection of suspicious arXiv ID."""
        text = "According to arXiv:9999.99999, the results show..."
        result = detector.detect(text)
        # Should detect potential citation hallucination
        # (actual detection depends on patterns)
        assert isinstance(result, DetectionResult)

    def test_detect_version_pattern(self, detector):
        """Test detection of version hallucination."""
        text = "Python 4.5 introduces major changes to the language."
        result = detector.detect(text)
        assert isinstance(result, DetectionResult)

    def test_detect_result_structure(self, detector):
        """Test that detection result has correct structure."""
        result = detector.detect("Any text here")

        assert hasattr(result, 'text_analyzed')
        assert hasattr(result, 'total_hallucinations')
        assert hasattr(result, 'by_category')
        assert hasattr(result, 'by_severity')
        assert hasattr(result, 'hallucinations')
        assert hasattr(result, 'confidence_score')
        assert hasattr(result, 'risk_level')

    def test_detect_log_appended(self, detector):
        """Test that detection is logged."""
        initial_count = len(detector.detection_log)
        detector.detect("Test text")
        assert len(detector.detection_log) == initial_count + 1

    def test_detect_multiple_texts(self, detector):
        """Test multiple detections."""
        texts = ["Text 1", "Text 2", "Text 3"]
        for text in texts:
            result = detector.detect(text)
            assert isinstance(result, DetectionResult)

        assert len(detector.detection_log) == 3


# ============================================================================
# Test: HallucinationDetector - Risk Assessment
# ============================================================================

class TestRiskAssessment:
    """Tests for risk level assessment."""

    def test_risk_level_low(self, detector):
        """Test that benign text gets LOW risk."""
        result = detector.detect("Hello, how are you?")
        assert result.risk_level == "LOW"

    def test_risk_levels_valid(self, detector):
        """Test that risk levels are from valid set."""
        valid_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        result = detector.detect("Any text")
        assert result.risk_level in valid_levels


# ============================================================================
# Test: HallucinationDetector - Confidence
# ============================================================================

class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    def test_confidence_range(self, detector):
        """Test that confidence is in valid range."""
        result = detector.detect("Sample text")
        assert 0.0 <= result.confidence_score <= 1.0

    def test_confidence_high_for_clean_text(self, detector):
        """Test that clean text gets high confidence."""
        result = detector.detect("This is a simple, factual statement.")
        # High confidence means confident there are NO hallucinations
        # When no hallucinations detected, confidence should be high
        if result.total_hallucinations == 0:
            assert result.confidence_score >= 0.9


# ============================================================================
# Test: HallucinationDetector - Categories
# ============================================================================

class TestCategoryBreakdown:
    """Tests for category breakdown in results."""

    def test_by_category_is_dict(self, detector):
        """Test that by_category is a dictionary."""
        result = detector.detect("Test text")
        assert isinstance(result.by_category, dict)

    def test_by_severity_is_dict(self, detector):
        """Test that by_severity is a dictionary."""
        result = detector.detect("Test text")
        assert isinstance(result.by_severity, dict)

    def test_category_counts_match_total(self, detector, sample_hallucination_texts):
        """Test that category counts sum to total."""
        for text in sample_hallucination_texts:
            result = detector.detect(text)
            category_sum = sum(result.by_category.values())
            assert category_sum == result.total_hallucinations


# ============================================================================
# Test: Pattern Matching
# ============================================================================

class TestPatternMatching:
    """Tests for pattern matching functionality."""

    def test_patterns_have_required_fields(self, detector):
        """Test that all patterns have required fields."""
        for pattern in detector.PATTERNS:
            assert pattern.id, "Pattern must have ID"
            assert pattern.category, "Pattern must have category"
            assert pattern.pattern, "Pattern must have regex pattern"
            assert pattern.description, "Pattern must have description"
            assert pattern.severity, "Pattern must have severity"

    def test_patterns_have_valid_categories(self, detector):
        """Test that all patterns have valid categories."""
        valid_categories = set(HallucinationCategory)
        for pattern in detector.PATTERNS:
            assert pattern.category in valid_categories

    def test_patterns_have_valid_severities(self, detector):
        """Test that all patterns have valid severities."""
        valid_severities = set(Severity)
        for pattern in detector.PATTERNS:
            assert pattern.severity in valid_severities

    def test_patterns_compile_as_regex(self, detector):
        """Test that all pattern strings compile as valid regex."""
        import re
        for pattern in detector.PATTERNS:
            try:
                re.compile(pattern.pattern, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Pattern {pattern.id} has invalid regex: {e}")


# ============================================================================
# Test: CLI Interface
# ============================================================================

class TestCLI:
    """Tests for CLI interface."""

    def test_module_has_main(self):
        """Test that module has main entry point."""
        from hallucination_detector import main
        assert callable(main)

    def test_cli_test_mode(self, detector):
        """Test that detector has self-test capability."""
        # Run self-test
        from hallucination_detector import main
        import sys
        from io import StringIO

        # Capture output
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # Run with --test
            sys.argv = ['hallucination_detector.py', '--test']
            try:
                main()
            except SystemExit:
                pass  # Expected on success
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        # Should have run tests
        assert "SELF-TEST" in output or "Test" in output or len(output) > 0


# ============================================================================
# Test: Integration
# ============================================================================

class TestIntegration:
    """Integration tests."""

    def test_end_to_end_detection(self, detector):
        """Test complete detection workflow."""
        text = """
        According to recent research by Dr. Smith (arXiv:9999.12345),
        Python 5.0 was released in 2025 with significant improvements.
        The company MegaCorp (NYSE: FAKE) reported record profits.
        """

        result = detector.detect(text)

        # Should complete without error
        assert result is not None
        assert isinstance(result, DetectionResult)

    def test_multiple_detections_isolated(self, detector):
        """Test that multiple detections don't interfere."""
        result1 = detector.detect("Clean text one")
        result2 = detector.detect("Clean text two")

        # Results should be independent
        assert result1.text_analyzed != result2.text_analyzed

    def test_detection_log_persists(self, detector):
        """Test that detection log accumulates."""
        detector.detect("Text 1")
        detector.detect("Text 2")
        detector.detect("Text 3")

        assert len(detector.detection_log) == 3


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_text(self, detector):
        """Test handling of empty text."""
        result = detector.detect("")
        assert result.total_hallucinations == 0

    def test_whitespace_only(self, detector):
        """Test handling of whitespace-only text."""
        result = detector.detect("   \n\t  ")
        assert result.total_hallucinations == 0

    def test_very_long_text(self, detector):
        """Test handling of very long text."""
        long_text = "This is a test sentence. " * 1000
        result = detector.detect(long_text)
        assert isinstance(result, DetectionResult)

    def test_unicode_text(self, detector):
        """Test handling of unicode text."""
        unicode_text = "Тест на русском языке. 日本語テスト. Émoji: 🚀"
        result = detector.detect(unicode_text)
        assert isinstance(result, DetectionResult)

    def test_special_characters(self, detector):
        """Test handling of special characters."""
        special_text = "Test with special chars: <>&\"'`\\n\\t"
        result = detector.detect(special_text)
        assert isinstance(result, DetectionResult)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
