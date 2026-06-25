#!/usr/bin/env python3
"""
Pattern Extractor for Low-Score Discoveries

Extracts valuable patterns and tool ideas from ARCHIVE discoveries (score <40)
that don't meet direct CLI integration criteria but contain actionable insights.

Version: 1.0.0
Task: TIER 2E Task 31 (GAP-RES-039)

Usage:
    # Extract patterns from a discovery
    python pattern_extractor.py --url "https://..." --title "..."

    # List extracted patterns
    python pattern_extractor.py --list

    # List by category
    python pattern_extractor.py --list --category architectural

    # Search patterns
    python pattern_extractor.py --search "scaling"

    # Show statistics
    python pattern_extractor.py --stats

    # Process all ARCHIVE discoveries from database
    python pattern_extractor.py --process-archives

Integration:
    # Anacron (weekly pattern review)
    7  50  pattern_review_weekly  python3 ~/.claude/tools/pattern_extractor.py --stats

Workflow:
    1. ARCHIVE discovery → Read article/paper
    2. Identify pattern categories (architectural/prompting/integration/best practices)
    3. Extract tool ideas (CLI concepts, MCP candidates)
    4. Document in pattern library (~/.claude/patterns/)
    5. Tag for future reference
"""

import json
import os
import re
import sys
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
import hashlib
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PATTERN_LIBRARY_PATH = Path.home() / ".claude" / "patterns"
PATTERN_DB_PATH = Path.home() / ".claude" / "evaluation" / "data" / "pattern_library.json"
SCORED_DISCOVERIES_PATH = Path.home() / ".claude" / "evaluation" / "data" / "scored_discoveries.json"


class PatternCategory(str, Enum):
    """Categories for extracted patterns."""
    ARCHITECTURAL = "architectural"
    PROMPTING = "prompting"
    INTEGRATION = "integration"
    BEST_PRACTICES = "best_practices"
    TOOL_IDEAS = "tool_ideas"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATA_ENGINEERING = "data_engineering"


class ExtractionDecision(str, Enum):
    """Decision after pattern extraction analysis."""
    EXTRACT = "EXTRACT"      # Valuable pattern(s) found
    NO_VALUE = "NO_VALUE"    # No actionable content
    PARTIAL = "PARTIAL"      # Some value, limited applicability


@dataclass
class ExtractedPattern:
    """Represents an extracted pattern from a discovery."""
    id: str
    title: str
    category: PatternCategory
    description: str
    source_url: str
    source_title: str
    source_score: float
    tags: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    implementation_notes: str = ""
    cli_relevance: str = ""
    related_gaps: List[str] = field(default_factory=list)
    date_extracted: str = ""
    confidence: float = 0.0

    def __post_init__(self):
        if not self.date_extracted:
            self.date_extracted = datetime.now(timezone.utc).isoformat()
        if not self.id:
            self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID based on title and source."""
        content = f"{self.title}:{self.source_url}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class ToolIdea:
    """Represents a tool idea extracted from a discovery."""
    id: str
    name: str
    description: str
    tool_type: str  # CLI, MCP, Script, Library
    source_url: str
    source_title: str
    source_score: float
    features: List[str] = field(default_factory=list)
    implementation_complexity: str = ""  # LOW, MEDIUM, HIGH
    estimated_effort: str = ""
    priority: str = ""  # P1, P2, P3
    related_patterns: List[str] = field(default_factory=list)
    date_extracted: str = ""

    def __post_init__(self):
        if not self.date_extracted:
            self.date_extracted = datetime.now(timezone.utc).isoformat()
        if not self.id:
            self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID based on name and source."""
        content = f"{self.name}:{self.source_url}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class ExtractionResult:
    """Result of pattern extraction analysis."""
    source_url: str
    source_title: str
    source_score: float
    decision: ExtractionDecision
    patterns: List[ExtractedPattern] = field(default_factory=list)
    tool_ideas: List[ToolIdea] = field(default_factory=list)
    notes: str = ""
    date_analyzed: str = ""

    def __post_init__(self):
        if not self.date_analyzed:
            self.date_analyzed = datetime.now(timezone.utc).isoformat()


class PatternLibrary:
    """
    Manages the pattern library - storage and retrieval of extracted patterns.
    """

    def __init__(self, db_path: Path = PATTERN_DB_PATH, lib_path: Path = PATTERN_LIBRARY_PATH):
        self.db_path = db_path
        self.lib_path = lib_path
        self.patterns: Dict[str, ExtractedPattern] = {}
        self.tool_ideas: Dict[str, ToolIdea] = {}
        self.extractions: List[ExtractionResult] = []
        self._ensure_structure()
        self._load()

    def _ensure_structure(self):
        """Ensure pattern library directory structure exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lib_path.mkdir(parents=True, exist_ok=True)

        # Create category subdirectories
        for category in PatternCategory:
            (self.lib_path / category.value).mkdir(exist_ok=True)

    def _load(self):
        """Load patterns from JSON database."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    self.patterns = {
                        k: ExtractedPattern(**v)
                        for k, v in data.get("patterns", {}).items()
                    }
                    self.tool_ideas = {
                        k: ToolIdea(**v)
                        for k, v in data.get("tool_ideas", {}).items()
                    }
                    # Don't load full extractions history (can be large)
                logger.info(f"Loaded {len(self.patterns)} patterns, {len(self.tool_ideas)} tool ideas")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to load pattern library: {e}")
                self.patterns = {}
                self.tool_ideas = {}

    def _save(self):
        """Save patterns to JSON database."""
        data = {
            "patterns": {k: asdict(v) for k, v in self.patterns.items()},
            "tool_ideas": {k: asdict(v) for k, v in self.tool_ideas.items()},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.patterns)} patterns, {len(self.tool_ideas)} tool ideas")

    def add_pattern(self, pattern: ExtractedPattern) -> bool:
        """Add a pattern to the library."""
        if pattern.id in self.patterns:
            logger.info(f"Pattern {pattern.id} already exists, updating")
        self.patterns[pattern.id] = pattern
        self._save()
        self._write_pattern_file(pattern)
        return True

    def add_tool_idea(self, tool_idea: ToolIdea) -> bool:
        """Add a tool idea to the library."""
        if tool_idea.id in self.tool_ideas:
            logger.info(f"Tool idea {tool_idea.id} already exists, updating")
        self.tool_ideas[tool_idea.id] = tool_idea
        self._save()
        self._write_tool_idea_file(tool_idea)
        return True

    def _write_pattern_file(self, pattern: ExtractedPattern):
        """Write pattern to markdown file in library."""
        category_dir = self.lib_path / pattern.category
        filename = f"{pattern.id}_{self._slugify(pattern.title)}.md"
        filepath = category_dir / filename

        content = f"""# {pattern.title}

**ID:** {pattern.id}
**Category:** {pattern.category}
**Date Extracted:** {pattern.date_extracted}
**Confidence:** {pattern.confidence:.2f}

## Source

- **Title:** {pattern.source_title}
- **URL:** {pattern.source_url}
- **Original Score:** {pattern.source_score}

## Description

{pattern.description}

## Use Cases

{chr(10).join(f"- {uc}" for uc in pattern.use_cases) if pattern.use_cases else "- (none specified)"}

## Implementation Notes

{pattern.implementation_notes if pattern.implementation_notes else "(none)"}

## CLI Relevance

{pattern.cli_relevance if pattern.cli_relevance else "(not specified)"}

## Tags

{", ".join(pattern.tags) if pattern.tags else "(none)"}

## Related Gaps

{", ".join(pattern.related_gaps) if pattern.related_gaps else "(none)"}
"""
        with open(filepath, 'w') as f:
            f.write(content)

    def _write_tool_idea_file(self, tool_idea: ToolIdea):
        """Write tool idea to markdown file in library."""
        category_dir = self.lib_path / "tool_ideas"
        filename = f"{tool_idea.id}_{self._slugify(tool_idea.name)}.md"
        filepath = category_dir / filename

        content = f"""# Tool Idea: {tool_idea.name}

**ID:** {tool_idea.id}
**Type:** {tool_idea.tool_type}
**Priority:** {tool_idea.priority}
**Complexity:** {tool_idea.implementation_complexity}
**Estimated Effort:** {tool_idea.estimated_effort}
**Date Extracted:** {tool_idea.date_extracted}

## Source

- **Title:** {tool_idea.source_title}
- **URL:** {tool_idea.source_url}
- **Original Score:** {tool_idea.source_score}

## Description

{tool_idea.description}

## Features

{chr(10).join(f"- {f}" for f in tool_idea.features) if tool_idea.features else "- (none specified)"}

## Related Patterns

{", ".join(tool_idea.related_patterns) if tool_idea.related_patterns else "(none)"}
"""
        with open(filepath, 'w') as f:
            f.write(content)

    def _slugify(self, text: str) -> str:
        """Convert text to filesystem-safe slug."""
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return slug[:50]  # Limit length

    def get_pattern(self, id_: str) -> Optional[ExtractedPattern]:
        """Get pattern by ID."""
        return self.patterns.get(id_)

    def get_tool_idea(self, id_: str) -> Optional[ToolIdea]:
        """Get tool idea by ID."""
        return self.tool_ideas.get(id_)

    def list_patterns(self, category: Optional[PatternCategory] = None) -> List[ExtractedPattern]:
        """List all patterns, optionally filtered by category."""
        patterns = list(self.patterns.values())
        if category:
            patterns = [p for p in patterns if p.category == category.value]
        return sorted(patterns, key=lambda p: p.date_extracted, reverse=True)

    def list_tool_ideas(self, priority: Optional[str] = None) -> List[ToolIdea]:
        """List all tool ideas, optionally filtered by priority."""
        ideas = list(self.tool_ideas.values())
        if priority:
            ideas = [i for i in ideas if i.priority == priority]
        return sorted(ideas, key=lambda i: i.date_extracted, reverse=True)

    def search(self, query: str) -> Tuple[List[ExtractedPattern], List[ToolIdea]]:
        """Search patterns and tool ideas by keyword."""
        query_lower = query.lower()
        matching_patterns = []
        matching_ideas = []

        for pattern in self.patterns.values():
            if (query_lower in pattern.title.lower() or
                query_lower in pattern.description.lower() or
                any(query_lower in tag.lower() for tag in pattern.tags)):
                matching_patterns.append(pattern)

        for idea in self.tool_ideas.values():
            if (query_lower in idea.name.lower() or
                query_lower in idea.description.lower()):
                matching_ideas.append(idea)

        return matching_patterns, matching_ideas

    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics."""
        stats = {
            "total_patterns": len(self.patterns),
            "total_tool_ideas": len(self.tool_ideas),
            "by_category": {},
            "by_priority": {},
            "by_tool_type": {}
        }

        # Patterns by category
        for pattern in self.patterns.values():
            cat = pattern.category
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        # Tool ideas by priority
        for idea in self.tool_ideas.values():
            prio = idea.priority or "unset"
            stats["by_priority"][prio] = stats["by_priority"].get(prio, 0) + 1

            # By tool type
            tool_type = idea.tool_type or "unset"
            stats["by_tool_type"][tool_type] = stats["by_tool_type"].get(tool_type, 0) + 1

        return stats


class PatternExtractor:
    """
    Extracts patterns and tool ideas from low-score discoveries.

    Uses heuristics and content analysis to identify valuable patterns
    even when direct CLI integration is not applicable.
    """

    # Pattern detection keywords by category
    CATEGORY_KEYWORDS = {
        PatternCategory.ARCHITECTURAL: [
            "architecture", "scaling", "distributed", "microservices", "monolith",
            "database", "caching", "load balancing", "sharding", "replication",
            "high availability", "fault tolerance", "resilience", "disaster recovery",
            "horizontal scale", "vertical scale", "event-driven", "message queue"
        ],
        PatternCategory.PROMPTING: [
            "prompt", "prompting", "few-shot", "zero-shot", "chain-of-thought",
            "instruction", "system prompt", "conversation", "dialogue", "chat",
            "generation", "completion", "template", "context window"
        ],
        PatternCategory.INTEGRATION: [
            "api", "integration", "webhook", "oauth", "authentication",
            "rate limit", "retry", "backoff", "timeout", "circuit breaker",
            "sdk", "client library", "rest", "graphql", "grpc"
        ],
        PatternCategory.BEST_PRACTICES: [
            "best practice", "recommendation", "guideline", "standard",
            "convention", "anti-pattern", "code quality", "maintainability",
            "testing", "documentation", "code review", "deployment"
        ],
        PatternCategory.SECURITY: [
            "security", "authentication", "authorization", "encryption",
            "vulnerability", "exploit", "attack", "defense", "protection",
            "audit", "compliance", "privacy", "gdpr", "pci"
        ],
        PatternCategory.PERFORMANCE: [
            "performance", "optimization", "latency", "throughput", "benchmark",
            "profiling", "bottleneck", "caching", "memory", "cpu", "gpu"
        ],
        PatternCategory.DATA_ENGINEERING: [
            "data pipeline", "etl", "data lake", "data warehouse", "streaming",
            "batch processing", "real-time", "analytics", "ml pipeline",
            "feature store", "data quality", "data governance"
        ]
    }

    # Tool type detection keywords
    TOOL_TYPE_KEYWORDS = {
        "CLI": ["cli", "command-line", "terminal", "bash", "shell", "script"],
        "MCP": ["mcp", "model context protocol", "tool server", "plugin"],
        "Library": ["library", "sdk", "package", "module", "framework"],
        "Script": ["script", "automation", "utility", "helper"]
    }

    def __init__(self, library: PatternLibrary):
        self.library = library

    def analyze_discovery(
        self,
        url: str,
        title: str,
        score: float,
        content_summary: Optional[str] = None
    ) -> ExtractionResult:
        """
        Analyze a discovery for extractable patterns and tool ideas.

        Args:
            url: Source URL
            title: Discovery title
            score: Original relevance score
            content_summary: Optional content summary for analysis

        Returns:
            ExtractionResult with patterns and tool ideas found
        """
        result = ExtractionResult(
            source_url=url,
            source_title=title,
            source_score=score,
            decision=ExtractionDecision.NO_VALUE
        )

        # Analyze title for pattern categories
        detected_categories = self._detect_categories(title, content_summary)

        if not detected_categories:
            result.notes = "No recognizable patterns in title"
            return result

        # Create patterns for detected categories
        for category, confidence in detected_categories:
            pattern = ExtractedPattern(
                id="",  # Will be auto-generated
                title=f"{title} - {category.value.title()} Pattern",
                category=category,
                description=f"Pattern extracted from: {title}",
                source_url=url,
                source_title=title,
                source_score=score,
                tags=self._extract_tags(title, category),
                confidence=confidence
            )
            result.patterns.append(pattern)

        # Check for tool ideas
        tool_types = self._detect_tool_types(title, content_summary)
        for tool_type, confidence in tool_types:
            tool_idea = ToolIdea(
                id="",  # Will be auto-generated
                name=f"{self._extract_tool_name(title)} Tool",
                description=f"Tool concept extracted from: {title}",
                tool_type=tool_type,
                source_url=url,
                source_title=title,
                source_score=score,
                implementation_complexity=self._estimate_complexity(title),
                priority=self._estimate_priority(score, confidence)
            )
            result.tool_ideas.append(tool_idea)

        # Determine decision
        if result.patterns or result.tool_ideas:
            if len(result.patterns) >= 2 or len(result.tool_ideas) >= 1:
                result.decision = ExtractionDecision.EXTRACT
            else:
                result.decision = ExtractionDecision.PARTIAL
            result.notes = f"Found {len(result.patterns)} patterns, {len(result.tool_ideas)} tool ideas"
        else:
            result.notes = "No actionable patterns or tool ideas found"

        return result

    def _detect_categories(
        self,
        title: str,
        content: Optional[str] = None
    ) -> List[Tuple[PatternCategory, float]]:
        """Detect pattern categories from text."""
        text = f"{title} {content or ''}".lower()
        detected = []

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                # Confidence based on keyword matches
                confidence = min(0.9, 0.3 + (matches * 0.15))
                detected.append((category, confidence))

        return sorted(detected, key=lambda x: x[1], reverse=True)[:3]  # Top 3 categories

    def _detect_tool_types(
        self,
        title: str,
        content: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Detect potential tool types from text."""
        text = f"{title} {content or ''}".lower()
        detected = []

        for tool_type, keywords in self.TOOL_TYPE_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                confidence = min(0.8, 0.2 + (matches * 0.2))
                detected.append((tool_type, confidence))

        return detected

    def _extract_tags(self, title: str, category: PatternCategory) -> List[str]:
        """Extract relevant tags from title."""
        tags = []

        # Add category keywords that match
        for kw in self.CATEGORY_KEYWORDS.get(category, []):
            if kw in title.lower():
                tags.append(kw)

        # Extract technical terms
        tech_terms = re.findall(r'\b(AI|ML|LLM|API|SDK|CLI|MCP|GPU|CPU|DB|SQL)\b', title, re.IGNORECASE)
        tags.extend([t.upper() for t in tech_terms])

        return list(set(tags))[:10]  # Limit to 10 tags

    def _extract_tool_name(self, title: str) -> str:
        """Extract a tool name from title."""
        # Remove common prefixes/suffixes
        name = title.split(':')[0]
        name = re.sub(r'^(How|What|Why|When|Inside|Introducing)\s+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(Guide|Tutorial|Overview|Introduction)$', '', name, flags=re.IGNORECASE)
        return name[:40]  # Limit length

    def _estimate_complexity(self, title: str) -> str:
        """Estimate implementation complexity."""
        title_lower = title.lower()

        high_complexity_keywords = ["distributed", "scale", "enterprise", "architecture", "framework"]
        medium_complexity_keywords = ["integration", "api", "pipeline", "workflow"]

        if any(kw in title_lower for kw in high_complexity_keywords):
            return "HIGH"
        elif any(kw in title_lower for kw in medium_complexity_keywords):
            return "MEDIUM"
        return "LOW"

    def _estimate_priority(self, score: float, confidence: float) -> str:
        """Estimate priority based on score and confidence."""
        if score >= 30 and confidence >= 0.6:
            return "P2"
        elif score >= 20 and confidence >= 0.4:
            return "P3"
        return "P3"

    def process_archives(self, dry_run: bool = False) -> List[ExtractionResult]:
        """
        Process all ARCHIVE discoveries from the scored discoveries database.

        Args:
            dry_run: If True, don't save extracted patterns

        Returns:
            List of extraction results
        """
        results = []

        if not SCORED_DISCOVERIES_PATH.exists():
            logger.warning(f"Scored discoveries database not found: {SCORED_DISCOVERIES_PATH}")
            return results

        try:
            with open(SCORED_DISCOVERIES_PATH, 'r') as f:
                discoveries = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load discoveries: {e}")
            return results

        for discovery_id, discovery in discoveries.items():
            # Skip non-archives
            if discovery.get("original_decision") != "ARCHIVE":
                continue

            # Skip already processed (check if patterns exist for this URL)
            url = discovery.get("url", "")
            existing = [p for p in self.library.patterns.values() if p.source_url == url]
            if existing:
                logger.info(f"Skipping already processed: {discovery.get('title', 'Unknown')[:50]}")
                continue

            result = self.analyze_discovery(
                url=url,
                title=discovery.get("title", "Unknown"),
                score=discovery.get("original_score", 0)
            )

            if result.decision != ExtractionDecision.NO_VALUE:
                logger.info(f"Extracted from: {result.source_title[:50]}")

                if not dry_run:
                    # Save patterns and tool ideas
                    for pattern in result.patterns:
                        self.library.add_pattern(pattern)
                    for idea in result.tool_ideas:
                        self.library.add_tool_idea(idea)

            results.append(result)

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Pattern Extractor for Low-Score Discoveries"
    )

    # Actions
    parser.add_argument("--extract", action="store_true",
                       help="Extract patterns from a discovery")
    parser.add_argument("--list", action="store_true",
                       help="List extracted patterns")
    parser.add_argument("--search", type=str,
                       help="Search patterns by keyword")
    parser.add_argument("--stats", action="store_true",
                       help="Show library statistics")
    parser.add_argument("--process-archives", action="store_true",
                       help="Process all ARCHIVE discoveries")

    # Parameters
    parser.add_argument("--url", type=str, help="Source URL")
    parser.add_argument("--title", type=str, help="Discovery title")
    parser.add_argument("--score", type=float, default=20.0, help="Original score")
    parser.add_argument("--category", type=str,
                       choices=[c.value for c in PatternCategory],
                       help="Filter by category")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't save changes")
    parser.add_argument("--output", type=str, choices=["text", "json"],
                       default="text", help="Output format")

    args = parser.parse_args()

    # Initialize library and extractor
    library = PatternLibrary()
    extractor = PatternExtractor(library)

    # Execute action
    if args.stats:
        stats = library.get_statistics()
        if args.output == "json":
            print(json.dumps(stats, indent=2))
        else:
            print("\n[PATTERN LIBRARY STATISTICS]")
            print(f"  Total patterns: {stats['total_patterns']}")
            print(f"  Total tool ideas: {stats['total_tool_ideas']}")
            print("\n  By category:")
            for cat, count in sorted(stats['by_category'].items()):
                print(f"    - {cat}: {count}")
            print("\n  Tool ideas by priority:")
            for prio, count in sorted(stats['by_priority'].items()):
                print(f"    - {prio}: {count}")
            print("\n  Tool ideas by type:")
            for tool_type, count in sorted(stats['by_tool_type'].items()):
                print(f"    - {tool_type}: {count}")

    elif args.list:
        category = PatternCategory(args.category) if args.category else None
        patterns = library.list_patterns(category)

        if args.output == "json":
            print(json.dumps([asdict(p) for p in patterns], indent=2))
        else:
            print(f"\n[PATTERNS{' - ' + args.category if args.category else ''}]")
            for pattern in patterns:
                print(f"  [{pattern.id}] {pattern.title[:60]}")
                print(f"    Category: {pattern.category}")
                print(f"    Source: {pattern.source_title[:40]}")
                print(f"    Confidence: {pattern.confidence:.2f}")
                print()

            # Also list tool ideas
            ideas = library.list_tool_ideas()
            print(f"\n[TOOL IDEAS]")
            for idea in ideas:
                print(f"  [{idea.id}] {idea.name}")
                print(f"    Type: {idea.tool_type}, Priority: {idea.priority}")
                print(f"    Complexity: {idea.implementation_complexity}")
                print()

    elif args.search:
        patterns, ideas = library.search(args.search)

        if args.output == "json":
            print(json.dumps({
                "patterns": [asdict(p) for p in patterns],
                "tool_ideas": [asdict(i) for i in ideas]
            }, indent=2))
        else:
            print(f"\n[SEARCH RESULTS: '{args.search}']")
            print(f"  Patterns: {len(patterns)}")
            for pattern in patterns:
                print(f"    - [{pattern.id}] {pattern.title[:50]}")
            print(f"  Tool ideas: {len(ideas)}")
            for idea in ideas:
                print(f"    - [{idea.id}] {idea.name}")

    elif args.extract and args.url and args.title:
        result = extractor.analyze_discovery(
            url=args.url,
            title=args.title,
            score=args.score
        )

        if args.output == "json":
            print(json.dumps(asdict(result), indent=2, default=str))
        else:
            print(f"\n[EXTRACTION RESULT]")
            print(f"  Source: {result.source_title}")
            print(f"  Decision: {result.decision.value}")
            print(f"  Patterns found: {len(result.patterns)}")
            print(f"  Tool ideas found: {len(result.tool_ideas)}")
            print(f"  Notes: {result.notes}")

            if result.patterns:
                print("\n  Patterns:")
                for p in result.patterns:
                    print(f"    - {p.title} ({p.category}, confidence: {p.confidence:.2f})")

            if result.tool_ideas:
                print("\n  Tool Ideas:")
                for i in result.tool_ideas:
                    print(f"    - {i.name} ({i.tool_type}, {i.priority})")

        # Save if not dry run
        if not args.dry_run and result.decision != ExtractionDecision.NO_VALUE:
            for pattern in result.patterns:
                library.add_pattern(pattern)
            for idea in result.tool_ideas:
                library.add_tool_idea(idea)
            print("\n  ✅ Saved to pattern library")

    elif args.process_archives:
        results = extractor.process_archives(dry_run=args.dry_run)

        # Summarize
        extracted = sum(1 for r in results if r.decision == ExtractionDecision.EXTRACT)
        partial = sum(1 for r in results if r.decision == ExtractionDecision.PARTIAL)
        no_value = sum(1 for r in results if r.decision == ExtractionDecision.NO_VALUE)
        total_patterns = sum(len(r.patterns) for r in results)
        total_ideas = sum(len(r.tool_ideas) for r in results)

        if args.output == "json":
            print(json.dumps({
                "total_processed": len(results),
                "extracted": extracted,
                "partial": partial,
                "no_value": no_value,
                "patterns": total_patterns,
                "tool_ideas": total_ideas
            }, indent=2))
        else:
            print(f"\n[ARCHIVE PROCESSING SUMMARY]")
            print(f"  Total processed: {len(results)}")
            print(f"  EXTRACT: {extracted}")
            print(f"  PARTIAL: {partial}")
            print(f"  NO_VALUE: {no_value}")
            print(f"  Total patterns: {total_patterns}")
            print(f"  Total tool ideas: {total_ideas}")

            if args.dry_run:
                print("\n  (dry-run mode - nothing saved)")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
