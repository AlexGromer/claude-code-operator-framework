#!/usr/bin/env python3
"""
Test Suite for TIER 4H: Models & Reasoning

TDD: Tests written FIRST, then implementation.
Tests verify presence of new sections and functionality.
"""

import pytest
import sys
import os
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path.home() / '.claude' / 'tools'))


class TestModuleSections:
    """Test that required sections exist in modules."""

    def test_tech_stack_deepseek_r1_section(self):
        """GAP-REASON-MODEL-005: DeepSeek R1 section exists."""
        tech_stack = Path.home() / '.claude/modules/10-tech-stack.md'
        content = tech_stack.read_text()

        assert 'DeepSeek R1' in content or 'DeepSeek-R1' in content
        assert 'reasoning' in content.lower()
        assert 'MIT' in content or 'open-source' in content.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
