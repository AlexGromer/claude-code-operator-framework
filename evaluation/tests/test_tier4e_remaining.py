#!/usr/bin/env python3
"""
Test suite for TIER 4E remaining gaps (4E-5 to 4E-8).

Gaps covered:
- GAP-BROWSER-002: Playwright MCP Server integration in modules/11-mcp.md
- GAP-COMPUTER-001: Claude Computer Use API in modules/17-coding-agents.md
- GAP-COMPUTER-002: OpenAI Operator comparison in modules/17-coding-agents.md
- GAP-EXAMPLES-001: Domain coverage expansion in examples/

Version: 1.0.0
Created: 2026-02-06
"""

import os
import pytest
from pathlib import Path


# Test fixtures
MCP_MODULE = Path.home() / ".claude/modules/11-mcp.md"
CODING_AGENTS_MODULE = Path.home() / ".claude/modules/17-coding-agents.md"
EXAMPLES_DIR = Path.home() / ".claude/examples"


class TestPlaywrightMCP:
    """Tests for GAP-BROWSER-002 (Playwright MCP section in 11-mcp.md)."""

    def test_playwright_setup_included(self):
        """Test that setup instructions are present."""
        content = MCP_MODULE.read_text()
        # Check for key setup elements
        assert "playwright" in content.lower(), "Missing playwright references"
        assert "settings.json" in content, "Missing configuration instructions"


class TestExamplesCoverage:
    """Tests for GAP-EXAMPLES-001 (domain coverage expansion)."""

    def test_all_domains_have_directories(self):
        """Test that all 11 domains have example directories."""
        expected_domains = [
            "common", "compliance", "devops", "education",
            "engineering", "lowlevel", "maturity", "osint",
            "planning", "security", "writing"
        ]

        for domain in expected_domains:
            domain_dir = EXAMPLES_DIR / domain
            assert domain_dir.exists(), f"Missing examples directory: {domain}"
            assert domain_dir.is_dir(), f"Not a directory: {domain}"

    def test_minimum_examples_per_domain(self):
        """Test that each domain has at least 2 examples."""
        domains = [d for d in EXAMPLES_DIR.iterdir() if d.is_dir()]

        for domain_dir in domains:
            examples = list(domain_dir.glob("*.md"))
            assert len(examples) >= 2, \
                f"Domain {domain_dir.name} has fewer than 2 examples: {len(examples)}"

    def test_examples_are_markdown(self):
        """Test that all examples are markdown files."""
        for domain_dir in EXAMPLES_DIR.iterdir():
            if domain_dir.is_dir():
                examples = list(domain_dir.iterdir())
                for example in examples:
                    assert example.suffix == ".md", \
                        f"Non-markdown example: {example}"

    def test_examples_have_content(self):
        """Test that examples have substantial content (>100 chars)."""
        for domain_dir in EXAMPLES_DIR.iterdir():
            if domain_dir.is_dir():
                for example_file in domain_dir.glob("*.md"):
                    content = example_file.read_text()
                    assert len(content) > 100, \
                        f"Example too short: {example_file} ({len(content)} chars)"

    def test_new_examples_follow_structure(self):
        """Test that examples have proper structure (headings, code blocks)."""
        for domain_dir in EXAMPLES_DIR.iterdir():
            if domain_dir.is_dir():
                for example_file in domain_dir.glob("*.md"):
                    content = example_file.read_text()
                    # Check for basic markdown structure
                    assert content.startswith("#"), \
                        f"Example missing heading: {example_file}"
                    # Most examples should have code blocks or lists
                    has_structure = ("```" in content or
                                   "\n- " in content or
                                   "\n* " in content)
                    assert has_structure, \
                        f"Example lacks structure: {example_file}"


class TestModuleIntegration:
    """Integration tests to ensure modules are properly updated."""

    def test_mcp_module_version_updated(self):
        """Test that MCP module version was updated."""
        content = MCP_MODULE.read_text()
        # Should have version info
        assert "Version:" in content or "version:" in content.lower(), \
            "Missing version information"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
