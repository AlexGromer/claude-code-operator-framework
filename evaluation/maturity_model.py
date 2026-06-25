#!/usr/bin/env python3
"""
Configuration Maturity Model
Version: 2.0.0

Measures configuration completeness via maturity levels (0-5).
Provides assessment criteria, current maturity calculation, and
progression path recommendations.

Maturity Levels:
- Level 0: Initial (no structured configuration)
- Level 1: Basic (core identity, manual versioning)
- Level 2: Structured (modular architecture, gap tracking)
- Level 3: Optimized (evaluation, caching, MCP, improvement protocol)
- Level 4: Innovative (self-improving, A/B testing, multi-agent)
- Level 5: Leading (industry contributions, published methodologies)

Usage:
    python3 maturity_model.py --assess
    python3 maturity_model.py --dashboard
    python3 maturity_model.py --progression
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple


@dataclass
class MaturityCriteria:
    """Criteria for a maturity level."""
    level: int
    name: str
    description: str
    requirements: List[str]
    metrics: Dict[str, Any]


@dataclass
class MaturityAssessment:
    """Result of maturity assessment."""
    current_level: int
    current_level_name: str
    score: float  # 0-5 scale (can be fractional, e.g., 2.7)
    level_completion_pct: float  # % complete toward next level
    strengths: List[str]
    gaps: List[str]
    next_level: int
    next_level_requirements: List[str]
    progression_path: List[str]
    timestamp: str


class MaturityModel:
    """
    Configuration Maturity Model for Agent Configuration.

    Assesses current maturity level, identifies gaps, and provides
    progression recommendations.
    """

    def __init__(self, claude_dir: Optional[Path] = None):
        """
        Initialize maturity model.

        Args:
            claude_dir: Path to ~/.claude directory (default: ~/.claude)
        """
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self.criteria = self._load_criteria()

    def _load_criteria(self) -> Dict[int, MaturityCriteria]:
        """
        Load maturity criteria for all levels.

        Returns:
            Dictionary of level -> MaturityCriteria
        """
        return {
            0: MaturityCriteria(
                level=0,
                name="Initial",
                description="No structured configuration, ad-hoc prompts",
                requirements=[
                    "No CLAUDE.md file",
                    "No modular architecture",
                    "No versioning",
                    "No tracking or metrics"
                ],
                metrics={
                    'modules': 0,
                    'examples': 0,
                    'gaps_tracked': False,
                    'versioning': False
                }
            ),
            1: MaturityCriteria(
                level=1,
                name="Basic",
                description="Core identity with basic role definitions",
                requirements=[
                    "CLAUDE.md with core identity section",
                    "Basic role definitions (at least 2 modules)",
                    "Manual versioning in place",
                    "At least 5 modules total",
                    "At least 10 examples across modules"
                ],
                metrics={
                    'modules': 5,
                    'examples': 10,
                    'gaps_tracked': False,
                    'versioning': True
                }
            ),
            2: MaturityCriteria(
                level=2,
                name="Structured",
                description="Modular architecture with gap tracking",
                requirements=[
                    "Modular architecture (10+ modules)",
                    "Few-shot examples library (50+ examples)",
                    "Gap tracking (GAPS.md)",
                    "Automated versioning",
                    "All primary domains covered",
                    "80%+ example coverage"
                ],
                metrics={
                    'modules': 10,
                    'examples': 50,
                    'gaps_tracked': True,
                    'versioning': True,
                    'domain_coverage': 0.80
                }
            ),
            3: MaturityCriteria(
                level=3,
                name="Optimized",
                description="Evaluation framework with continuous improvement",
                requirements=[
                    "Evaluation framework deployed (~/.claude/evaluation/)",
                    "Metrics tracking active (>30 days data)",
                    "Prompt caching implemented",
                    "MCP server active (≥1 server enabled)",
                    "Gap detection rate <10%",
                    "All P1 gaps resolved",
                    "Weekly monitoring established",
                    "95%+ configuration coverage"
                ],
                metrics={
                    'modules': 12,
                    'examples': 100,
                    'evaluation_framework': True,
                    'metrics_tracking': True,
                    'prompt_caching': True,
                    'mcp_servers': 1,  # Changed from mcp_tools: 5
                    'p1_gaps_resolved': True,
                    'coverage': 0.95
                }
            ),
            4: MaturityCriteria(
                level=4,
                name="Innovative",
                description="Self-improving with advanced capabilities",
                requirements=[
                    "Self-improving capabilities (automated gap detection)",
                    "A/B testing framework for prompt optimization",
                    "Multi-agent orchestration",
                    "Research-to-practice pipeline (automated)",
                    "Measurable ROI from configuration",
                    "Industry-leading practices adopted"
                ],
                metrics={
                    'self_improving': True,
                    'ab_testing': True,
                    'multi_agent': True,
                    'research_pipeline': True,
                    'roi_measured': True
                }
            ),
            5: MaturityCriteria(
                level=5,
                name="Leading",
                description="Industry contributions and published methodologies",
                requirements=[
                    "Contributes to industry standards",
                    "Published methodologies (papers, blog posts)",
                    "Community adoption of practices",
                    "External recognition",
                    "Replication by others"
                ],
                metrics={
                    'industry_contributions': True,
                    'published_methodologies': True,
                    'community_adoption': True,
                    'external_recognition': True
                }
            )
        }

    def assess_current_level(self) -> MaturityAssessment:
        """
        Assess current maturity level based on configuration.

        Analyzes ~/.claude directory structure and content to determine
        maturity level and completion percentage.

        Returns:
            MaturityAssessment with current level and recommendations
        """
        # Check what exists
        stats = self._collect_stats()

        # Determine level
        current_level = self._calculate_level(stats)
        current_criteria = self.criteria[current_level]

        # Calculate score (fractional level based on progress)
        score = self._calculate_score(stats, current_level)

        # Calculate completion toward next level
        if current_level < 5:
            next_level = current_level + 1
            next_criteria = self.criteria[next_level]
            level_completion_pct = self._calculate_completion(stats, next_criteria)
        else:
            next_level = 5
            next_criteria = self.criteria[5]
            level_completion_pct = 100.0

        # Identify strengths and gaps
        strengths = self._identify_strengths(stats, current_criteria)
        gaps = self._identify_gaps(stats, next_criteria if current_level < 5 else current_criteria)

        # Generate progression path
        progression_path = self._generate_progression_path(current_level, gaps)

        return MaturityAssessment(
            current_level=current_level,
            current_level_name=current_criteria.name,
            score=score,
            level_completion_pct=level_completion_pct,
            strengths=strengths,
            gaps=gaps,
            next_level=next_level,
            next_level_requirements=next_criteria.requirements,
            progression_path=progression_path,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def _collect_stats(self) -> Dict[str, Any]:
        """
        Collect statistics about current configuration.

        Returns:
            Dictionary of configuration statistics
        """
        stats = {
            'has_claude_md': False,
            'has_gaps_md': False,
            'has_evaluation': False,
            'module_count': 0,
            'example_count': 0,
            'rule_count': 0,
            'tool_count': 0,
            'hook_count': 0,
            'test_count': 0,
            'gaps_tracked': False,
            'versioning': False,
            'metrics_tracking': False,
            'prompt_caching': False,
            'mcp_servers_count': 0,
            'p1_gaps_count': 0,
            'p1_gaps_resolved_count': 0,
            'p2_gaps_count': 0,
            'p3_gaps_count': 0,
            'coverage': 0.0,
            # Level 4 indicators
            'has_gap_detection_hooks': False,
            'has_multi_agent': False,
            'has_research_pipeline': False,
            'has_ab_testing': False,
            'has_roi_measurement': False,
            'level4_met': 0,
            'level4_total': 6,
            # Level 5 indicators
            'has_published_methodology': False,
            'has_community_adoption': False,
        }

        # Check for CLAUDE.md
        claude_md = self.claude_dir / "CLAUDE.md"
        if claude_md.exists():
            stats['has_claude_md'] = True
            stats['versioning'] = self._check_versioning(claude_md)

        # Check for GAPS.md
        gaps_md = self.claude_dir / "GAPS.md"
        if gaps_md.exists():
            stats['has_gaps_md'] = True
            stats['gaps_tracked'] = True
            gap_stats = self._analyze_gaps(gaps_md)
            stats['p1_gaps_count'] = gap_stats['p1_total']
            stats['p1_gaps_resolved_count'] = gap_stats['p1_resolved']
            stats['p2_gaps_count'] = gap_stats['p2_total']
            stats['p3_gaps_count'] = gap_stats['p3_total']

        # Count modules
        modules_dir = self.claude_dir / "modules"
        if modules_dir.exists():
            stats['module_count'] = len(list(modules_dir.glob("*.md")))

        # Count rules
        rules_dir = self.claude_dir / "rules"
        if rules_dir.exists():
            stats['rule_count'] = len(list(rules_dir.glob("*.md")))

        # Count examples
        examples_dir = self.claude_dir / "examples"
        if examples_dir.exists():
            stats['example_count'] = len(list(examples_dir.rglob("*.md")))

        # Count tools
        tools_dir = self.claude_dir / "tools"
        if tools_dir.exists():
            stats['tool_count'] = len(list(tools_dir.glob("*.py")))

        # Count hooks
        hooks_dir = self.claude_dir / "hooks"
        if hooks_dir.exists():
            stats['hook_count'] = len(list(hooks_dir.glob("*.py")))

        # Check for evaluation framework
        eval_dir = self.claude_dir / "evaluation"
        if eval_dir.exists():
            stats['has_evaluation'] = True

            if (eval_dir / "metrics_tracker.py").exists():
                stats['metrics_tracking'] = True

            # Count tests
            tests_dir = eval_dir / "tests"
            if tests_dir.exists():
                stats['test_count'] = len(list(tests_dir.glob("test_*.py")))

        # Check for MCP servers (read from settings.json and .mcp.json)
        settings_json = self.claude_dir / "settings.json"
        mcp_json = self.claude_dir / ".mcp.json"
        mcp_count = 0

        if settings_json.exists():
            try:
                with open(settings_json, 'r') as f:
                    settings = json.load(f)
                    enabled = settings.get('enabledMcpjsonServers', [])
                    mcp_count += len(enabled) if enabled else 0
                    # Also check mcpServers in settings
                    mcp_servers = settings.get('mcpServers', {})
                    mcp_count += len(mcp_servers)
            except Exception:
                pass

        if mcp_json.exists():
            try:
                with open(mcp_json, 'r') as f:
                    mcp_config = json.load(f)
                    mcp_count += len(mcp_config)
            except Exception:
                pass

        stats['mcp_servers_count'] = mcp_count

        # Check for prompt caching
        if stats['has_claude_md']:
            with open(claude_md, 'r') as f:
                content = f.read()
                if 'PROMPT CACHING' in content or 'Prompt Caching' in content or 'cache_control' in content:
                    stats['prompt_caching'] = True

        # Estimate coverage based on modules and rules
        if stats['module_count'] >= 15 and stats['rule_count'] >= 8:
            stats['coverage'] = 0.97
        elif stats['module_count'] >= 12:
            stats['coverage'] = 0.95
        elif stats['module_count'] >= 10:
            stats['coverage'] = 0.85
        elif stats['module_count'] >= 5:
            stats['coverage'] = 0.70
        else:
            stats['coverage'] = 0.50

        # === Level 4 indicator detection ===

        # 1. Self-improving: automated gap detection via hooks
        hooks_dir = self.claude_dir / "hooks"
        if hooks_dir.exists():
            for hook_file in hooks_dir.glob("*.py"):
                try:
                    content = hook_file.read_text(errors='ignore')
                    if 'gap' in content.lower() and ('detect' in content.lower() or 'log' in content.lower()):
                        stats['has_gap_detection_hooks'] = True
                        break
                except Exception:
                    pass

        # 2. Multi-agent orchestration
        orch_module = self.claude_dir / "modules" / "13-orchestration-reference.md"
        orch_rule = self.claude_dir / "rules" / "subagent-orchestration.md"
        stats['has_multi_agent'] = orch_module.exists() or orch_rule.exists()

        # 3. Research-to-practice pipeline
        research_indicators = [
            self.claude_dir / "tools" / "research_workflow_agent.py",
            self.claude_dir / "tools" / "score_discovery.py",
            self.claude_dir / "evaluation" / "research_workflow.md",
        ]
        stats['has_research_pipeline'] = any(t.exists() for t in research_indicators)

        # 4. A/B testing framework
        ab_indicators = [
            self.claude_dir / "tools" / "ab_testing.py",
            self.claude_dir / "evaluation" / "ab_testing.py",
            self.claude_dir / "tools" / "prompt_ab_tester.py",
        ]
        stats['has_ab_testing'] = any(t.exists() for t in ab_indicators)

        # 5. ROI measurement
        roi_indicators = [
            self.claude_dir / "tools" / "roi_calculator.py",
            self.claude_dir / "evaluation" / "roi_tracker.py",
            self.claude_dir / "tools" / "roi_tracker.py",
        ]
        stats['has_roi_measurement'] = any(t.exists() for t in roi_indicators)

        # 6. Industry-leading practices (proxy: 15+ modules, 50+ examples, 70+ tools)
        has_leading_practices = (
            stats['module_count'] >= 15 and
            stats['example_count'] >= 50 and
            stats['tool_count'] >= 50
        )

        # Count Level 4 criteria met
        stats['level4_met'] = sum([
            stats['has_gap_detection_hooks'],
            stats['has_ab_testing'],
            stats['has_multi_agent'],
            stats['has_research_pipeline'],
            stats['has_roi_measurement'],
            has_leading_practices,
        ])
        stats['level4_total'] = 6

        # === Level 5 indicator detection ===
        # Published methodology (public GitHub repo with docs)
        public_repo = Path("/opt/claude-code-agent-addition")
        stats['has_published_methodology'] = (
            public_repo.exists() and
            (public_repo / ".git").exists()
        )

        return stats

    def _check_versioning(self, claude_md: Path) -> bool:
        """
        Check if versioning is in place.

        Args:
            claude_md: Path to CLAUDE.md

        Returns:
            True if versioning found
        """
        with open(claude_md, 'r') as f:
            content = f.read()
            # Look for version number
            if 'Version:' in content or 'v3.' in content or 'v2.' in content:
                return True
        return False

    def _analyze_gaps(self, gaps_md: Path) -> Dict[str, int]:
        """
        Analyze GAPS.md for gap statistics.

        Uses regex to match gap status lines precisely:
        Format: - **Status**: <status> | **Priority**: P<N> | **Category**: <cat>

        Args:
            gaps_md: Path to GAPS.md

        Returns:
            Dictionary with gap statistics
        """
        stats = {
            'p1_total': 0,
            'p1_resolved': 0,
            'p2_total': 0,
            'p2_resolved': 0,
            'p3_total': 0,
            'p3_resolved': 0,
        }

        # Match status lines: - **Status**: ... | **Priority**: P1 | ...
        status_pattern = re.compile(
            r'\*\*Status\*\*:\s*(.+?)\s*\|\s*\*\*Priority\*\*:\s*(P[123])'
        )
        resolved_pattern = re.compile(r'✅\s*Resolved')

        with open(gaps_md, 'r', errors='ignore') as f:
            for line in f:
                match = status_pattern.search(line)
                if not match:
                    continue

                status_text = match.group(1)
                priority = match.group(2)
                is_resolved = bool(resolved_pattern.search(status_text))

                if priority == 'P1':
                    stats['p1_total'] += 1
                    if is_resolved:
                        stats['p1_resolved'] += 1
                elif priority == 'P2':
                    stats['p2_total'] += 1
                    if is_resolved:
                        stats['p2_resolved'] += 1
                elif priority == 'P3':
                    stats['p3_total'] += 1
                    if is_resolved:
                        stats['p3_resolved'] += 1

        return stats

    def _calculate_level(self, stats: Dict[str, Any]) -> int:
        """
        Calculate current maturity level.

        Levels 0-3: Fully automated detection.
        Level 4: Automated (4+ of 6 criteria must be met).
        Level 5: Requires external validation (published, adopted).

        Args:
            stats: Configuration statistics

        Returns:
            Current maturity level (0-5)
        """
        # Level 0: No configuration
        if not stats['has_claude_md']:
            return 0

        # Level 1: Basic — need 10+ modules and gap tracking
        if stats['module_count'] < 10 or not stats['gaps_tracked']:
            return 1

        # Level 2: Structured — need evaluation and metrics
        if not stats['has_evaluation'] or not stats['metrics_tracking']:
            return 2

        # Level 3: Optimized — need eval + caching + MCP + P1 resolved
        level3_met = (
            stats['has_evaluation'] and
            stats['metrics_tracking'] and
            stats['prompt_caching'] and
            stats['mcp_servers_count'] >= 1 and
            stats['p1_gaps_count'] > 0 and
            stats['p1_gaps_resolved_count'] / max(1, stats['p1_gaps_count']) >= 0.90
        )
        if not level3_met:
            return 2

        # Level 4: Innovative — need 4+ of 6 criteria
        level4_met = stats.get('level4_met', 0)
        if level4_met >= 4:
            # Level 5: Leading — requires published methodology + community adoption
            if (stats.get('has_published_methodology', False) and
                    stats.get('has_community_adoption', False)):
                return 5
            return 4

        # All Level 3 criteria met but not enough Level 4
        return 3

    def _calculate_score(self, stats: Dict[str, Any], current_level: int) -> float:
        """
        Calculate fractional maturity score.

        Args:
            stats: Configuration statistics
            current_level: Current maturity level

        Returns:
            Fractional score (0.0-5.0)
        """
        # Base score is current level
        base_score = float(current_level)

        # Add fractional progress toward next level
        if current_level < 5:
            next_criteria = self.criteria[current_level + 1]
            completion_pct = self._calculate_completion(stats, next_criteria)
            base_score += (completion_pct / 100.0)

        return round(base_score, 2)

    def _calculate_completion(self, stats: Dict[str, Any], criteria: MaturityCriteria) -> float:
        """
        Calculate completion percentage toward criteria.

        Args:
            stats: Configuration statistics
            criteria: Target criteria

        Returns:
            Completion percentage (0-100)
        """
        total_requirements = len(criteria.requirements)
        if total_requirements == 0:
            return 100.0

        met_requirements = 0

        for req in criteria.requirements:
            req_lower = req.lower()

            # Level 1-3 checks
            if 'module' in req_lower and 'architecture' in req_lower:
                if stats['module_count'] >= criteria.metrics.get('modules', 0):
                    met_requirements += 1

            elif 'gap tracking' in req_lower or 'gaps.md' in req_lower:
                if stats['gaps_tracked']:
                    met_requirements += 1

            elif 'versioning' in req_lower:
                if stats['versioning']:
                    met_requirements += 1

            elif 'evaluation' in req_lower and 'framework' in req_lower:
                if stats['has_evaluation']:
                    met_requirements += 1

            elif 'metrics tracking' in req_lower:
                if stats['metrics_tracking']:
                    met_requirements += 1

            elif 'prompt caching' in req_lower:
                if stats['prompt_caching']:
                    met_requirements += 1

            elif 'mcp' in req_lower:
                if stats['mcp_servers_count'] >= criteria.metrics.get('mcp_servers', 1):
                    met_requirements += 1

            elif 'p1 gaps' in req_lower:
                if stats['p1_gaps_count'] > 0:
                    resolved_ratio = stats['p1_gaps_resolved_count'] / stats['p1_gaps_count']
                    if resolved_ratio >= 0.90:
                        met_requirements += 1

            # Level 4 checks
            elif 'self-improving' in req_lower or 'automated gap detection' in req_lower:
                if stats.get('has_gap_detection_hooks', False):
                    met_requirements += 1

            elif 'a/b testing' in req_lower:
                if stats.get('has_ab_testing', False):
                    met_requirements += 1

            elif 'multi-agent' in req_lower:
                if stats.get('has_multi_agent', False):
                    met_requirements += 1

            elif 'research' in req_lower and 'pipeline' in req_lower:
                if stats.get('has_research_pipeline', False):
                    met_requirements += 1

            elif 'roi' in req_lower:
                if stats.get('has_roi_measurement', False):
                    met_requirements += 1

            elif 'industry' in req_lower and 'leading' in req_lower:
                if (stats['module_count'] >= 15 and
                        stats['example_count'] >= 50 and
                        stats.get('tool_count', 0) >= 50):
                    met_requirements += 1

            # Level 5 checks
            elif 'published' in req_lower:
                if stats.get('has_published_methodology', False):
                    met_requirements += 1

            elif 'community' in req_lower and 'adoption' in req_lower:
                if stats.get('has_community_adoption', False):
                    met_requirements += 1

            elif 'domain' in req_lower and 'covered' in req_lower:
                if stats['module_count'] >= 10:
                    met_requirements += 1

            elif 'example' in req_lower and 'coverage' in req_lower:
                if stats['example_count'] >= criteria.metrics.get('examples', 0):
                    met_requirements += 1

            elif 'example' in req_lower and 'library' in req_lower:
                if stats['example_count'] >= criteria.metrics.get('examples', 0):
                    met_requirements += 1

            elif 'claude.md' in req_lower:
                if stats['has_claude_md']:
                    met_requirements += 1

            elif 'role' in req_lower and 'definition' in req_lower:
                if stats['module_count'] >= 2:
                    met_requirements += 1

            elif 'weekly' in req_lower and 'monitoring' in req_lower:
                if stats['metrics_tracking']:
                    met_requirements += 1

            elif 'coverage' in req_lower and '95' in req_lower:
                if stats['coverage'] >= 0.95:
                    met_requirements += 1

            elif 'gap detection rate' in req_lower:
                if stats['p1_gaps_count'] > 0 and stats['p1_gaps_resolved_count'] >= stats['p1_gaps_count'] * 0.9:
                    met_requirements += 1

        completion_pct = (met_requirements / total_requirements) * 100
        return round(completion_pct, 1)

    def _identify_strengths(self, stats: Dict[str, Any], criteria: MaturityCriteria) -> List[str]:
        """
        Identify configuration strengths.

        Args:
            stats: Configuration statistics
            criteria: Current level criteria

        Returns:
            List of strength descriptions
        """
        strengths = []

        if stats['has_claude_md']:
            strengths.append("✅ CLAUDE.md present with core identity")

        if stats['gaps_tracked']:
            p1_total = stats['p1_gaps_count']
            p1_resolved = stats['p1_gaps_resolved_count']
            total_gaps = p1_total + stats['p2_gaps_count'] + stats['p3_gaps_count']
            strengths.append(f"✅ Gap tracking ({total_gaps} total, {p1_resolved}/{p1_total} P1 resolved)")

        if stats['module_count'] >= 10:
            strengths.append(f"✅ Modular architecture ({stats['module_count']} modules, {stats['rule_count']} rules)")

        if stats['example_count'] >= 50:
            strengths.append(f"✅ Examples library ({stats['example_count']} examples)")

        if stats['tool_count'] >= 50:
            strengths.append(f"✅ Production tools ({stats['tool_count']} tools)")

        if stats['has_evaluation']:
            test_info = f", {stats['test_count']} test files" if stats['test_count'] > 0 else ""
            strengths.append(f"✅ Evaluation framework deployed{test_info}")

        if stats['metrics_tracking']:
            strengths.append("✅ Metrics tracking active")

        if stats['prompt_caching']:
            strengths.append("✅ Prompt caching implemented")

        if stats['mcp_servers_count'] >= 1:
            strengths.append(f"✅ MCP servers enabled ({stats['mcp_servers_count']} server(s))")

        # Level 4 strengths
        if stats.get('has_gap_detection_hooks'):
            strengths.append("✅ Automated gap detection (hooks)")

        if stats.get('has_multi_agent'):
            strengths.append("✅ Multi-agent orchestration (documented + active)")

        if stats.get('has_research_pipeline'):
            strengths.append("✅ Research-to-practice pipeline (digest + scoring)")

        if stats.get('has_published_methodology'):
            strengths.append("✅ Public methodology repo exists")

        return strengths

    def _identify_gaps(self, stats: Dict[str, Any], criteria: MaturityCriteria) -> List[str]:
        """
        Identify gaps preventing progression to next level.

        Args:
            stats: Configuration statistics
            criteria: Target level criteria

        Returns:
            List of gap descriptions
        """
        gaps = []

        for req in criteria.requirements:
            req_lower = req.lower()

            # Level 1-3 gaps
            if 'module' in req_lower and 'architecture' in req_lower:
                target = criteria.metrics.get('modules', 0)
                if stats['module_count'] < target:
                    gaps.append(f"❌ Need {target - stats['module_count']} more modules (current: {stats['module_count']})")

            elif 'gap tracking' in req_lower and not stats['gaps_tracked']:
                gaps.append("❌ Gap tracking not implemented (need GAPS.md)")

            elif 'evaluation' in req_lower and 'framework' in req_lower and not stats['has_evaluation']:
                gaps.append("❌ Evaluation framework not deployed")

            elif 'metrics tracking' in req_lower and not stats['metrics_tracking']:
                gaps.append("❌ Metrics tracking not active")

            elif 'prompt caching' in req_lower and not stats['prompt_caching']:
                gaps.append("❌ Prompt caching not implemented")

            elif 'mcp' in req_lower:
                target = criteria.metrics.get('mcp_servers', 1)
                if stats['mcp_servers_count'] < target:
                    gaps.append(f"❌ Need {target - stats['mcp_servers_count']} more MCP server(s)")

            elif 'p1 gaps' in req_lower:
                if stats['p1_gaps_count'] > 0:
                    remaining = stats['p1_gaps_count'] - stats['p1_gaps_resolved_count']
                    if remaining > 0:
                        gaps.append(f"❌ {remaining} P1 gaps remaining (need all resolved)")

            # Level 4 gaps
            elif 'a/b testing' in req_lower and not stats.get('has_ab_testing'):
                gaps.append("❌ A/B testing framework not implemented")

            elif ('self-improving' in req_lower or 'automated gap detection' in req_lower) and not stats.get('has_gap_detection_hooks'):
                gaps.append("❌ Automated gap detection not active")

            elif 'multi-agent' in req_lower and not stats.get('has_multi_agent'):
                gaps.append("❌ Multi-agent orchestration not documented")

            elif 'research' in req_lower and 'pipeline' in req_lower and not stats.get('has_research_pipeline'):
                gaps.append("❌ Research-to-practice pipeline not implemented")

            elif 'roi' in req_lower and not stats.get('has_roi_measurement'):
                gaps.append("❌ ROI measurement not implemented")

            elif 'industry' in req_lower and 'leading' in req_lower:
                if not (stats['module_count'] >= 15 and stats['example_count'] >= 50):
                    gaps.append("❌ Industry-leading practices threshold not met")

            # Level 5 gaps
            elif 'published' in req_lower and not stats.get('has_published_methodology'):
                gaps.append("❌ Methodology not published externally")

            elif 'community' in req_lower and 'adoption' in req_lower and not stats.get('has_community_adoption'):
                gaps.append("❌ No community adoption (stars, forks, users)")

            elif 'external recognition' in req_lower:
                gaps.append("❌ No external recognition yet")

            elif 'replication' in req_lower:
                gaps.append("❌ Not replicated by others yet")

        return gaps

    def _generate_progression_path(self, current_level: int, gaps: List[str]) -> List[str]:
        """
        Generate recommended progression path.

        Args:
            current_level: Current maturity level
            gaps: List of identified gaps

        Returns:
            List of recommended actions
        """
        path = []

        # Immediate actions based on detected gaps
        for gap in gaps[:3]:
            path.append(gap.replace("❌", "📌"))

        # Level-specific recommendations
        if current_level == 0:
            path.append("📌 Create CLAUDE.md with core identity")
            path.append("📌 Define 2-3 primary roles/modules")
            path.append("📌 Implement manual versioning")

        elif current_level == 1:
            path.append("📌 Expand to 10+ modules covering all domains")
            path.append("📌 Create GAPS.md for gap tracking")
            path.append("📌 Build examples library (50+ examples)")

        elif current_level == 2:
            path.append("📌 Deploy evaluation framework (~/.claude/evaluation/)")
            path.append("📌 Implement metrics tracking")
            path.append("📌 Set up prompt caching strategy")
            path.append("📌 Resolve all P1 gaps")

        elif current_level == 3:
            path.append("📌 Build A/B testing framework for prompt optimization")
            path.append("📌 Implement ROI measurement (time/quality/cost tracking)")

        elif current_level == 4:
            path.append("📌 Publish methodology (blog, Habr, conference)")
            path.append("📌 Build community around framework (docs, onboarding)")
            path.append("📌 Get external validation (reviews, stars, forks)")

        return path[:6]

    def format_dashboard(self, assessment: MaturityAssessment) -> str:
        """
        Format assessment as dashboard.

        Args:
            assessment: MaturityAssessment result

        Returns:
            Formatted dashboard string
        """
        # Progress bar
        progress_bar = self._generate_progress_bar(assessment.score, max_level=5)

        output = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    CONFIGURATION MATURITY DASHBOARD                       ║
╚═══════════════════════════════════════════════════════════════════════════╝

Current Maturity Level: {assessment.current_level} - {assessment.current_level_name.upper()}
Maturity Score: {assessment.score:.2f}/5.0

{progress_bar}

Progress to Level {assessment.next_level}: {assessment.level_completion_pct:.1f}%

───────────────────────────────────────────────────────────────────────────

✅ STRENGTHS:
"""

        for strength in assessment.strengths:
            output += f"  {strength}\n"

        output += f"""
───────────────────────────────────────────────────────────────────────────

❌ GAPS (Next Level Requirements):
"""

        for gap in assessment.gaps:
            output += f"  {gap}\n"

        output += f"""
───────────────────────────────────────────────────────────────────────────

📌 PROGRESSION PATH:
"""

        for step in assessment.progression_path:
            output += f"  {step}\n"

        output += f"""
───────────────────────────────────────────────────────────────────────────

Next Level ({assessment.next_level} - {self.criteria[assessment.next_level].name}):
Requirements:
"""

        for req in assessment.next_level_requirements[:5]:
            output += f"  • {req}\n"

        if len(assessment.next_level_requirements) > 5:
            output += f"  ... and {len(assessment.next_level_requirements) - 5} more\n"

        output += f"""
───────────────────────────────────────────────────────────────────────────

Generated: {datetime.fromisoformat(assessment.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

        return output

    def _generate_progress_bar(self, score: float, max_level: int = 5, width: int = 50) -> str:
        """
        Generate ASCII progress bar.

        Args:
            score: Current maturity score
            max_level: Maximum maturity level
            width: Width of progress bar

        Returns:
            ASCII progress bar string
        """
        filled = int((score / max_level) * width)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        percentage = (score / max_level) * 100

        return f"[{bar}] {percentage:.1f}%"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Configuration Maturity Model')
    parser.add_argument('--assess', action='store_true', help='Assess current maturity level')
    parser.add_argument('--dashboard', action='store_true', help='Display maturity dashboard')
    parser.add_argument('--progression', action='store_true', help='Show progression path')
    parser.add_argument('--claude-dir', type=Path, help='Path to ~/.claude directory')

    args = parser.parse_args()

    model = MaturityModel(claude_dir=args.claude_dir)

    if args.assess or args.dashboard:
        assessment = model.assess_current_level()

        if args.dashboard:
            print(model.format_dashboard(assessment))
        else:
            print(f"\nCurrent Maturity Level: {assessment.current_level} - {assessment.current_level_name}")
            print(f"Maturity Score: {assessment.score:.2f}/5.0")
            print(f"Progress to Level {assessment.next_level}: {assessment.level_completion_pct:.1f}%")

    elif args.progression:
        assessment = model.assess_current_level()
        print(f"\n📌 Progression Path (Current Level: {assessment.current_level}):\n")
        for step in assessment.progression_path:
            print(f"  {step}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
