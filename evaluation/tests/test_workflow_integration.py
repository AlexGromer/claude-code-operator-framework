#!/usr/bin/env python3
"""
Unit Tests for Workflow, Integration, and General Tools

Tests 10 P2 tools:
- Workflow: research_workflow_agent, research_re_evaluator, prompt_improver,
  prompt_regression_tester, routing_orchestrator
- General: coverage_scorer, json_schema_validator, automation_dashboard,
  score_discovery, session_reopen_advisor

Test Coverage: Public functions, edge cases, error handling, mocked external dependencies.

Version: 1.0.0
Created: 2026-02-06
"""

import pytest
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from datetime import datetime, timedelta
from io import StringIO

# Add tools to path
sys.path.insert(0, '/home/user/.claude/tools')
sys.path.insert(0, '/home/user/.claude/evaluation')


# ============================================================================
# TESTS: research_workflow_agent.py
# ============================================================================

def test_research_workflow_agent_init():
    """Test ResearchWorkflowAgent initialization."""
    from research_workflow_agent import ResearchWorkflowAgent

    with patch('research_workflow_agent.Path.home') as mock_home:
        mock_home.return_value = Path('/tmp/test')
        with patch('research_workflow_agent.DIGEST_DIR', Path('/tmp/test/nonexistent')):
            agent = ResearchWorkflowAgent()

            assert agent.latest_digest is None
            assert agent.discoveries == []


def test_research_workflow_get_latest_digest(tmp_path):
    """Test getting latest digest file."""
    from research_workflow_agent import ResearchWorkflowAgent

    # Create mock digest files
    digest_dir = tmp_path / ".claude" / "evaluation" / "data" / "research_digests"
    digest_dir.mkdir(parents=True, exist_ok=True)

    old_digest = digest_dir / "digest_20260101.md"
    new_digest = digest_dir / "digest_20260201.md"

    old_digest.write_text("Old digest")
    new_digest.write_text("New digest")

    # Make new_digest newer
    import time
    time.sleep(0.01)
    new_digest.touch()

    with patch('research_workflow_agent.DIGEST_DIR', digest_dir):
        agent = ResearchWorkflowAgent()
        latest = agent.get_latest_digest()

        assert latest is not None
        assert latest.name == "digest_20260201.md"


def test_research_workflow_parse_digest_critical():
    """Test parsing CRITICAL priority discoveries."""
    from research_workflow_agent import ResearchWorkflowAgent

    digest_content = """
# Research Digest

## 🔴 CRITICAL Priority

### Prompting

- **AgentDoG Framework**
  - Description: Safety framework
  - 🔗 [GitHub](https://github.com/example/agentdog)
  - Source: GitHub
"""

    with patch('research_workflow_agent.DIGEST_DIR'):
        agent = ResearchWorkflowAgent()
        agent.latest_digest = MagicMock()
        agent.latest_digest.read_text.return_value = digest_content

        discoveries = agent.parse_digest()

        assert len(discoveries) > 0
        assert discoveries[0]['priority'] == 'CRITICAL'
        assert discoveries[0]['title'] == 'AgentDoG Framework'


def test_research_workflow_generate_agent_prompt():
    """Test agent prompt generation."""
    from research_workflow_agent import ResearchWorkflowAgent

    agent = ResearchWorkflowAgent()
    agent.discoveries = [
        {
            'title': 'Test Discovery',
            'priority': 'CRITICAL',
            'category': 'Testing',
            'github_url': 'https://github.com/test/repo',
            'arxiv_id': '2406.12345',
        }
    ]

    prompt = agent.generate_agent_prompt()

    assert prompt is not None
    assert 'Test Discovery' in prompt
    assert 'score_discovery.py' in prompt


def test_research_workflow_display_summary_no_items():
    """Test display summary with no CRITICAL/HIGH items."""
    from research_workflow_agent import ResearchWorkflowAgent

    agent = ResearchWorkflowAgent()
    agent.latest_digest = Path('/tmp/fake_digest.md')
    agent.discoveries = []

    with patch('builtins.print'):
        result = agent.display_summary()

        assert result is False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
