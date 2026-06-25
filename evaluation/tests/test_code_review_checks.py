#!/usr/bin/env pytest
"""Tests for Code Review Checks."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "tools"))

from code_review_checks import (
    analyze_code, detect_language, PythonAnalyzer, ReviewResult
)


class TestCodeReviewChecks:
    """Test code review functionality."""

    def test_check_syntax_valid(self):
        """Test valid syntax check."""
        code = "def hello():\n    return 'world'"
        result = analyze_code(code, "test.py")
        assert isinstance(result, ReviewResult)
        # Valid syntax should not have CRITICAL syntax errors
        syntax_issues = [i for i in result.issues if i.category == "syntax"]
        assert len(syntax_issues) == 0

    def test_check_syntax_invalid(self):
        """Test invalid syntax detection."""
        code = "def hello(\n    return"  # Invalid
        result = analyze_code(code, "test.py")
        assert isinstance(result, ReviewResult)
        # Should detect syntax error
        syntax_issues = [i for i in result.issues if i.category == "syntax"]
        assert len(syntax_issues) > 0

    def test_check_security(self):
        """Test security checks."""
        code = "eval(user_input)"  # Security issue
        result = analyze_code(code, "test.py")
        security_issues = [i for i in result.issues if i.category == "security"]
        assert len(security_issues) > 0

    def test_analyze_code(self):
        """Test full review via analyze_code."""
        code = "print('hello')"
        result = analyze_code(code, "test.py")
        assert isinstance(result, ReviewResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
