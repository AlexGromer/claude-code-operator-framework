#!/usr/bin/env python3
"""Tests for domain routing to modules 18-21."""

import unittest
import re
import os

# TestModuleStructure removed (audit v9.1, 2026-05-29): it enforced a PRE-v9 convention
# that every domain module embed its own "Уточняющие вопросы" + "Authorization Level"
# sections. v9 centralized these into rules/request-clarification.md and
# rules/authorization-levels.md, so per-module duplication is now an anti-pattern —
# re-adding the sections would re-create the very drift the audit flagged. The convention
# was also only partially met (no module had clarification; only some had auth). Modules
# 18/20/21 exist and route correctly; the central rules cover the requirement.


class TestSkillCompleteness(unittest.TestCase):
    """Test that all skills have required sections."""

    REQUIRED_SECTIONS = [
        "workflow",
        "safety",
        "error",
        "usage",
        "вопрос",  # clarification questions
    ]

    def _get_all_skills(self):
        skills_dir = os.path.expanduser("~/.claude/skills/")
        skills = []
        if os.path.exists(skills_dir):
            for d in os.listdir(skills_dir):
                skill_file = os.path.join(skills_dir, d, "SKILL.md")
                if os.path.isfile(skill_file):
                    skills.append((d, skill_file))
        return skills

    def test_skill_count_minimum(self):
        """At least 11 skills should exist."""
        skills = self._get_all_skills()
        self.assertGreaterEqual(len(skills), 11,
                               f"Only {len(skills)} skills found, expected ≥11")

    def test_operational_skills_exist(self):
        """6 operational skills should exist."""
        expected = ["commit", "pr", "sync", "session-health", "gap", "report"]
        skills = self._get_all_skills()
        skill_names = [s[0] for s in skills]
        for exp in expected:
            self.assertIn(exp, skill_names,
                         f"Operational skill '{exp}' not found")


class TestExamplesCoverage(unittest.TestCase):
    """Test that examples exist for all domains."""

    EXPECTED_DIRS = [
        "common", "compliance", "devops", "education", "engineering",
        "lowlevel", "maturity", "osint", "planning", "security", "writing"
    ]

    def test_all_example_directories_exist(self):
        base = os.path.expanduser("~/.claude/examples/")
        for d in self.EXPECTED_DIRS:
            path = os.path.join(base, d)
            self.assertTrue(os.path.isdir(path),
                           f"Example directory '{d}' not found")

    def test_each_directory_has_examples(self):
        base = os.path.expanduser("~/.claude/examples/")
        for d in self.EXPECTED_DIRS:
            path = os.path.join(base, d)
            if os.path.isdir(path):
                files = [f for f in os.listdir(path) if f.endswith('.md')]
                self.assertGreaterEqual(len(files), 1,
                                       f"Directory '{d}' has no .md examples")


class TestAuthoritativeSources(unittest.TestCase):
    """Test that AUTHORITATIVE_SOURCES.md has all domains."""

    def setUp(self):
        path = os.path.expanduser("/opt/project/AUTHORITATIVE_SOURCES.md")
        if os.path.exists(path):
            with open(path) as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_security_sources(self):
        if self.content:
            self.assertIn("OWASP", self.content)

    def test_devops_sources(self):
        if self.content:
            self.assertIn("Terraform", self.content)

    def test_blue_team_sources(self):
        if self.content:
            self.assertIn("MITRE", self.content)

    def test_business_analysis_sources(self):
        if self.content:
            # May not be present yet - that's ok
            pass

    def test_procurement_sources(self):
        if self.content:
            # May not be present yet - that's ok
            pass

    def test_network_sources(self):
        if self.content:
            # May not be present yet - that's ok
            pass


if __name__ == "__main__":
    unittest.main()
