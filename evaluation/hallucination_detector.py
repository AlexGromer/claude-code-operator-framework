#!/usr/bin/env python3
"""
Hallucination Detection and Measurement System

Systematic detection of hallucinated facts, citations, code, and version information.
Implements severity classification, domain breakdown, and fact-checking integration.

Version: 1.0.0
Task: TIER 3 Task 18 (GAP-EVAL-HALLUCINATION)

Usage:
    # Analyze text for hallucinations
    python hallucination_detector.py --text "Claude was released in 2019..."

    # Analyze from file
    python hallucination_detector.py --file response.txt

    # Show detection statistics
    python hallucination_detector.py --stats

    # Run self-test
    python hallucination_detector.py --test

Academic References:
    - TruthfulQA (Lin et al., 2022)
    - FactScore (Min et al., 2023)
    - SelfCheckGPT (Manakul et al., 2023)

Categories:
    1. Factual Hallucinations - False facts, dates, statistics
    2. Citation Hallucinations - Fake papers, authors, DOIs
    3. Code Hallucinations - Invalid syntax, non-existent APIs
    4. Version Hallucinations - Wrong versions, outdated info
    5. Entity Hallucinations - Made-up people, companies, products
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
from enum import Enum
import hashlib

# Import web validator for real-time verification
try:
    from web_validator import WebValidator, ValidationResult
    WEB_VALIDATION_AVAILABLE = True
except ImportError:
    WEB_VALIDATION_AVAILABLE = False
    logging.warning("Web validator not available - install dependencies for web validation")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
HALLUCINATION_DB_PATH = Path.home() / ".claude" / "evaluation" / "data" / "hallucination_log.json"
KNOWN_FACTS_PATH = Path.home() / ".claude" / "evaluation" / "data" / "known_facts.json"


class HallucinationCategory(str, Enum):
    """Categories of hallucinations."""
    FACTUAL = "factual"           # False facts, dates, statistics
    CITATION = "citation"         # Fake papers, authors, DOIs
    CODE = "code"                 # Invalid syntax, non-existent APIs
    VERSION = "version"           # Wrong versions, outdated info
    ENTITY = "entity"             # Made-up people, companies, products
    TEMPORAL = "temporal"         # Wrong dates, time-related errors
    QUANTITATIVE = "quantitative" # Made-up numbers, statistics


class Severity(str, Enum):
    """Severity levels for hallucinations."""
    MINOR = "minor"       # Low impact, easily correctable
    MAJOR = "major"       # Significant misinformation
    CRITICAL = "critical" # Safety/security implications


@dataclass
class HallucinationPattern:
    """Pattern for detecting specific hallucination types."""
    id: str
    category: HallucinationCategory
    pattern: str
    description: str
    severity: Severity
    examples: List[str] = field(default_factory=list)
    false_positive_notes: str = ""


@dataclass
class DetectedHallucination:
    """A detected hallucination instance."""
    id: str
    category: HallucinationCategory
    severity: Severity
    text_snippet: str
    pattern_id: str
    description: str
    confidence: float
    suggested_correction: str = ""
    context: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.id:
            content = f"{self.text_snippet}:{self.pattern_id}"
            self.id = hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class DetectionResult:
    """Result of hallucination detection analysis."""
    text_analyzed: str
    total_hallucinations: int
    by_category: Dict[str, int]
    by_severity: Dict[str, int]
    hallucinations: List[DetectedHallucination]
    confidence_score: float  # 0-1, higher = more confident in analysis
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class HallucinationDetector:
    """
    Detects and classifies hallucinations in LLM outputs.

    Uses pattern matching, heuristics, and known-fact databases
    to identify potential hallucinations with severity classification.
    """

    # Hallucination detection patterns
    PATTERNS: List[HallucinationPattern] = [
        # ===== CITATION HALLUCINATIONS =====
        HallucinationPattern(
            id="CITE-001",
            category=HallucinationCategory.CITATION,
            pattern=r"(?i)(et al\.?,?\s*\d{4}|[\w\s]+,\s*\d{4})\s*(?![\[\(])",
            description="Unverifiable citation format (Author, Year without reference)",
            severity=Severity.MAJOR,
            examples=["Smith et al., 2023 found that...", "According to Johnson, 2022..."],
            false_positive_notes="May match legitimate inline citations"
        ),
        HallucinationPattern(
            id="CITE-002",
            category=HallucinationCategory.CITATION,
            pattern=r"(?i)arXiv:\s*\d{4}\.\d{4,5}(?:v\d+)?",
            description="arXiv ID that needs verification",
            severity=Severity.MAJOR,
            examples=["arXiv:2301.12345", "arXiv: 2023.54321v2"],
            false_positive_notes="Pattern matches format but ID needs external verification"
        ),
        HallucinationPattern(
            id="CITE-003",
            category=HallucinationCategory.CITATION,
            pattern=r"(?i)doi:\s*10\.\d{4,}/[\w\.\-/]+",
            description="DOI that needs verification",
            severity=Severity.MAJOR,
            examples=["doi: 10.1234/example.2023"],
            false_positive_notes="DOI format correct but existence needs verification"
        ),
        HallucinationPattern(
            id="CITE-004",
            category=HallucinationCategory.CITATION,
            pattern=r"(?i)published\s+in\s+(?:the\s+)?(?:journal|proceedings|conference)\s+(?:of\s+)?[\w\s]+",
            description="Publication venue claim that needs verification",
            severity=Severity.MINOR,
            examples=["published in the Journal of AI Research"],
            false_positive_notes="May be legitimate venue reference"
        ),

        # ===== VERSION HALLUCINATIONS =====
        HallucinationPattern(
            id="VER-001",
            category=HallucinationCategory.VERSION,
            pattern=r"(?i)(?:python|node|npm|java|go|rust|ruby)\s*(?:version\s*)?\d+\.\d+(?:\.\d+)?",
            description="Software version claim that may be outdated",
            severity=Severity.MINOR,
            examples=["Python 3.12", "Node.js version 20.0"],
            false_positive_notes="Version may be correct but needs freshness check"
        ),
        HallucinationPattern(
            id="VER-002",
            category=HallucinationCategory.VERSION,
            pattern=r"(?i)(?:released|launched|announced)\s+(?:in|on)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}",
            description="Release date claim that needs verification",
            severity=Severity.MAJOR,
            examples=["released in March 2024", "launched on January 2023"],
            false_positive_notes="Date may be accurate but should be verified"
        ),
        HallucinationPattern(
            id="VER-003",
            category=HallucinationCategory.VERSION,
            pattern=r"(?i)as\s+of\s+(?:my\s+)?(?:knowledge\s+)?(?:cutoff|training)",
            description="Knowledge cutoff reference - indicates potential staleness",
            severity=Severity.MINOR,
            examples=["as of my knowledge cutoff", "as of my training"],
            false_positive_notes="This is actually good practice - acknowledging limitations"
        ),

        # ===== FACTUAL HALLUCINATIONS =====
        HallucinationPattern(
            id="FACT-001",
            category=HallucinationCategory.FACTUAL,
            pattern=r"(?i)(?:is|was|are|were)\s+(?:the\s+)?(?:first|only|largest|smallest|oldest|newest|best|worst)\s+(?:\w+\s+)?(?:to|in|at|for)",
            description="Superlative claim that needs verification",
            severity=Severity.MAJOR,
            examples=["was the first to implement", "is the largest in the world", "is the first company to"],
            false_positive_notes="Superlatives often lead to hallucinations"
        ),
        HallucinationPattern(
            id="FACT-002",
            category=HallucinationCategory.FACTUAL,
            pattern=r"(?i)according\s+to\s+(?:a\s+)?(?:recent\s+)?(?:study|research|survey|report|analysis)",
            description="Vague study reference without citation",
            severity=Severity.MAJOR,
            examples=["according to a recent study", "research shows that"],
            false_positive_notes="Should have specific citation"
        ),
        HallucinationPattern(
            id="FACT-003",
            category=HallucinationCategory.FACTUAL,
            pattern=r"(?i)it\s+is\s+(?:well\s+)?(?:known|established|proven|documented)\s+that",
            description="Appeal to common knowledge without evidence",
            severity=Severity.MINOR,
            examples=["it is well known that", "it is established that"],
            false_positive_notes="May be true but lacks specific support"
        ),

        # ===== QUANTITATIVE HALLUCINATIONS =====
        HallucinationPattern(
            id="QUANT-001",
            category=HallucinationCategory.QUANTITATIVE,
            pattern=r"(?i)(?:approximately|about|around|roughly|nearly|over|more\s+than|less\s+than)\s+\d+(?:,\d{3})*(?:\.\d+)?(?:\s*%|\s*percent|\s*million|\s*billion|\s*trillion)?",
            description="Approximate number that needs verification",
            severity=Severity.MAJOR,
            examples=["approximately 50%", "about 1.5 million users"],
            false_positive_notes="Numbers should be verified with sources"
        ),
        HallucinationPattern(
            id="QUANT-002",
            category=HallucinationCategory.QUANTITATIVE,
            pattern=r"(?i)(?:studies\s+show|research\s+indicates|data\s+suggests)\s+(?:that\s+)?\d+(?:\.\d+)?(?:\s*%|\s*percent)",
            description="Statistical claim without citation",
            severity=Severity.CRITICAL,
            examples=["studies show 80% of users prefer", "research indicates 95% accuracy"],
            false_positive_notes="Statistics without sources are high-risk hallucinations"
        ),

        # ===== ENTITY HALLUCINATIONS =====
        HallucinationPattern(
            id="ENT-001",
            category=HallucinationCategory.ENTITY,
            pattern=r"(?i)(?:CEO|founder|president|chairman|CTO|CFO)\s+(?:of\s+)?[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*,?\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*",
            description="Executive/founder name claim",
            severity=Severity.MAJOR,
            examples=["CEO of OpenAI, Sam Altman", "founder of Anthropic, Dario Amodei"],
            false_positive_notes="Names may be correct but should be verified"
        ),
        HallucinationPattern(
            id="ENT-002",
            category=HallucinationCategory.ENTITY,
            pattern=r"(?i)(?:founded|established|created|started)\s+(?:in|by)\s+\d{4}",
            description="Founding date/year claim",
            severity=Severity.MAJOR,
            examples=["founded in 2020", "established by Google in 2015"],
            false_positive_notes="Dates should be verified"
        ),

        # ===== CODE HALLUCINATIONS =====
        HallucinationPattern(
            id="CODE-001",
            category=HallucinationCategory.CODE,
            pattern=r"(?i)(?:import|from)\s+(?:[\w\.]+)\s+(?:import\s+)?(?:[\w\.,\s]+)?(?:#.*non-?existent|#.*doesn't\s+exist|#.*fake)",
            description="Import statement for potentially non-existent module",
            severity=Severity.CRITICAL,
            examples=["import nonexistent_module", "from fake_lib import something"],
            false_positive_notes="Rare - usually caught by syntax highlighting"
        ),
        HallucinationPattern(
            id="CODE-002",
            category=HallucinationCategory.CODE,
            pattern=r"(?i)(?:pip\s+install|npm\s+install|cargo\s+add)\s+[\w\-]+",
            description="Package installation command - package may not exist",
            severity=Severity.MAJOR,
            examples=["pip install fake-package", "npm install nonexistent-lib"],
            false_positive_notes="Package names should be verified"
        ),

        # ===== TEMPORAL HALLUCINATIONS =====
        HallucinationPattern(
            id="TEMP-001",
            category=HallucinationCategory.TEMPORAL,
            pattern=r"(?i)(?:currently|now|today|at\s+present|as\s+of\s+now)",
            description="Present-tense claim that may be outdated",
            severity=Severity.MINOR,
            examples=["currently the most popular", "today's best practice"],
            false_positive_notes="May be outdated since training cutoff"
        ),
        HallucinationPattern(
            id="TEMP-002",
            category=HallucinationCategory.TEMPORAL,
            pattern=r"(?i)(?:will|is\s+going\s+to|is\s+expected\s+to|is\s+scheduled\s+to)\s+(?:be\s+)?(?:released|launched|announced|available)",
            description="Future prediction that may be incorrect",
            severity=Severity.MAJOR,
            examples=["will be released in Q3", "is expected to launch soon"],
            false_positive_notes="Predictions are inherently uncertain"
        ),
    ]

    # Known facts database (expandable)
    KNOWN_FACTS = {
        "anthropic_founding": {
            "fact": "Anthropic was founded in 2021",
            "year": 2021,
            "founders": ["Dario Amodei", "Daniela Amodei"]
        },
        "openai_founding": {
            "fact": "OpenAI was founded in 2015",
            "year": 2015
        },
        "claude_release": {
            "fact": "Claude was first released in 2023",
            "year": 2023
        },
        "gpt4_release": {
            "fact": "GPT-4 was released in March 2023",
            "year": 2023,
            "month": "March"
        }
    }

    def __init__(self, enable_web_validation: bool = True):
        """
        Initialize hallucination detector.

        Args:
            enable_web_validation: Enable real-time arXiv/DOI validation (default: True)
        """
        self.patterns = self.PATTERNS
        self.known_facts = self.KNOWN_FACTS
        self.detection_log: List[DetectionResult] = []
        self.enable_web_validation = enable_web_validation and WEB_VALIDATION_AVAILABLE

        # Initialize web validator if available and enabled
        if self.enable_web_validation:
            self.web_validator = WebValidator(use_cache=True)
            logger.info("Web validation enabled (arXiv/DOI verification)")
        else:
            self.web_validator = None
            if enable_web_validation and not WEB_VALIDATION_AVAILABLE:
                logger.warning("Web validation requested but not available")

        self._load_known_facts()

    def _load_known_facts(self):
        """Load additional known facts from database file."""
        if KNOWN_FACTS_PATH.exists():
            try:
                with open(KNOWN_FACTS_PATH, 'r') as f:
                    additional_facts = json.load(f)
                    self.known_facts.update(additional_facts)
                logger.info(f"Loaded {len(additional_facts)} additional known facts")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load known facts: {e}")

    def detect(self, text: str, context: str = "") -> DetectionResult:
        """
        Analyze text for potential hallucinations.

        Args:
            text: Text to analyze
            context: Optional context about the response

        Returns:
            DetectionResult with all detected hallucinations
        """
        hallucinations: List[DetectedHallucination] = []

        for pattern in self.patterns:
            matches = re.finditer(pattern.pattern, text)
            for match in matches:
                snippet = match.group(0)
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                surrounding = text[start:end]

                hallucination = DetectedHallucination(
                    id="",
                    category=pattern.category,
                    severity=pattern.severity,
                    text_snippet=snippet,
                    pattern_id=pattern.id,
                    description=pattern.description,
                    confidence=self._calculate_confidence(pattern, snippet, text),
                    context=surrounding
                )
                hallucinations.append(hallucination)

        # Web validation for arXiv and DOI patterns
        if self.enable_web_validation and self.web_validator:
            hallucinations = self._apply_web_validation(text, hallucinations)

        # Calculate statistics
        by_category = {}
        by_severity = {}

        for h in hallucinations:
            cat = h.category.value
            sev = h.severity.value
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1

        # Calculate risk level
        critical_count = by_severity.get("critical", 0)
        major_count = by_severity.get("major", 0)

        if critical_count > 0:
            risk_level = "CRITICAL"
        elif major_count >= 3:
            risk_level = "HIGH"
        elif major_count >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Calculate overall confidence
        if hallucinations:
            avg_confidence = sum(h.confidence for h in hallucinations) / len(hallucinations)
        else:
            avg_confidence = 1.0  # High confidence in no hallucinations

        result = DetectionResult(
            text_analyzed=text[:500] + "..." if len(text) > 500 else text,
            total_hallucinations=len(hallucinations),
            by_category=by_category,
            by_severity=by_severity,
            hallucinations=hallucinations,
            confidence_score=avg_confidence,
            risk_level=risk_level
        )

        self.detection_log.append(result)
        return result

    def _calculate_confidence(
        self,
        pattern: HallucinationPattern,
        snippet: str,
        full_text: str
    ) -> float:
        """Calculate confidence level for a detected hallucination."""
        confidence = 0.5  # Base confidence

        # Adjust based on pattern severity
        severity_weights = {
            Severity.CRITICAL: 0.2,
            Severity.MAJOR: 0.15,
            Severity.MINOR: 0.1
        }
        confidence += severity_weights.get(pattern.severity, 0)

        # Adjust based on context
        # If there's a nearby citation, reduce confidence (might be legitimate)
        citation_nearby = re.search(r'\[\d+\]|\(\d{4}\)', full_text[max(0, full_text.find(snippet)-100):full_text.find(snippet)+len(snippet)+100])
        if citation_nearby:
            confidence -= 0.15

        # If "I'm not certain" or similar phrases nearby, reduce confidence
        uncertainty_phrases = ["i'm not certain", "i believe", "i think", "may be", "might be", "possibly"]
        context_lower = full_text.lower()
        for phrase in uncertainty_phrases:
            if phrase in context_lower:
                confidence -= 0.1
                break

        return max(0.1, min(0.95, confidence))

    def _apply_web_validation(
        self,
        text: str,
        hallucinations: List[DetectedHallucination]
    ) -> List[DetectedHallucination]:
        """
        Apply web validation to arXiv and DOI hallucinations.

        Verifies citations via public APIs and updates confidence/severity.

        Args:
            text: Original text being analyzed
            hallucinations: List of detected hallucinations

        Returns:
            Updated list with web validation results
        """
        validated = []

        for h in hallucinations:
            # Check if this is an arXiv pattern
            if "arXiv" in h.text_snippet or "arxiv" in h.text_snippet.lower():
                # Extract arXiv ID
                arxiv_match = re.search(r'arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)', h.text_snippet, re.IGNORECASE)
                if arxiv_match:
                    arxiv_id = arxiv_match.group(1)
                    logger.info(f"Validating arXiv ID: {arxiv_id}")

                    try:
                        result = self.web_validator.validate_arxiv(arxiv_id)

                        if result.is_valid:
                            # arXiv ID exists - reduce severity and confidence
                            logger.info(f"✅ arXiv {arxiv_id} validated: {result.metadata.get('title', 'N/A')}")
                            h.severity = Severity.MINOR  # Downgrade from MAJOR to MINOR
                            h.confidence = max(0.2, h.confidence - 0.4)  # Significantly reduce confidence
                            h.description += f" (VALIDATED: {result.metadata.get('title', 'arXiv paper exists')})"
                        else:
                            # arXiv ID not found - increase confidence
                            logger.warning(f"❌ arXiv {arxiv_id} NOT FOUND: {result.error}")
                            h.confidence = min(0.95, h.confidence + 0.2)
                            h.description += f" (INVALID: {result.error})"

                    except Exception as e:
                        logger.error(f"Web validation failed for arXiv {arxiv_id}: {e}")
                        # Keep original confidence if validation fails

            # Check if this is a DOI pattern
            elif "10." in h.text_snippet and "/" in h.text_snippet:
                # Extract DOI
                doi_match = re.search(r'10\.\d{4,}/[^\s\]]+', h.text_snippet)
                if doi_match:
                    doi = doi_match.group(0).rstrip('.,;:')
                    logger.info(f"Validating DOI: {doi}")

                    try:
                        result = self.web_validator.validate_doi(doi)

                        if result.is_valid:
                            # DOI exists - reduce severity and confidence
                            logger.info(f"✅ DOI {doi} validated: {result.metadata.get('title', 'N/A')}")
                            h.severity = Severity.MINOR
                            h.confidence = max(0.2, h.confidence - 0.4)
                            h.description += f" (VALIDATED: {result.metadata.get('title', 'DOI exists')})"
                        else:
                            # DOI not found - increase confidence
                            logger.warning(f"❌ DOI {doi} NOT FOUND: {result.error}")
                            h.confidence = min(0.95, h.confidence + 0.2)
                            h.description += f" (INVALID: {result.error})"

                    except Exception as e:
                        logger.error(f"Web validation failed for DOI {doi}: {e}")

            validated.append(h)

        return validated

    def check_known_facts(self, text: str) -> List[Dict[str, Any]]:
        """
        Check text against known facts database.

        Returns list of potential fact violations.
        """
        violations = []
        text_lower = text.lower()

        # Check Anthropic founding year
        if "anthropic" in text_lower:
            year_match = re.search(r"anthropic.*(?:founded|established|created|started).*(\d{4})", text_lower)
            if year_match:
                claimed_year = int(year_match.group(1))
                if claimed_year != self.known_facts["anthropic_founding"]["year"]:
                    violations.append({
                        "type": "factual_error",
                        "claimed": f"Anthropic founded in {claimed_year}",
                        "actual": f"Anthropic was founded in 2021",
                        "severity": "MAJOR"
                    })

        # Check OpenAI founding year
        if "openai" in text_lower:
            year_match = re.search(r"openai.*(?:founded|established|created|started).*(\d{4})", text_lower)
            if year_match:
                claimed_year = int(year_match.group(1))
                if claimed_year != self.known_facts["openai_founding"]["year"]:
                    violations.append({
                        "type": "factual_error",
                        "claimed": f"OpenAI founded in {claimed_year}",
                        "actual": f"OpenAI was founded in 2015",
                        "severity": "MAJOR"
                    })

        # Check Claude release year
        if "claude" in text_lower and "release" in text_lower:
            year_match = re.search(r"claude.*(?:released|launched).*(\d{4})", text_lower)
            if year_match:
                claimed_year = int(year_match.group(1))
                if claimed_year != self.known_facts["claude_release"]["year"]:
                    violations.append({
                        "type": "factual_error",
                        "claimed": f"Claude released in {claimed_year}",
                        "actual": f"Claude was first released in 2023",
                        "severity": "MAJOR"
                    })

        return violations

    def record_verification(
        self,
        session_id: str,
        tool_name: str,
        query: str,
        content_type: str = "search_results",
        response_size: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record that a web verification was performed.

        Tracks when WebSearch/WebFetch was used for fact verification,
        helping to correlate with hallucination detection.

        Args:
            session_id: Session UUID
            tool_name: WebSearch or WebFetch
            query: Search query or URL
            content_type: Type of content (search_results, web_content)
            response_size: Size of response in characters
            metadata: Optional additional metadata

        Returns:
            Dict with recorded data
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "web_verification",
            "session_id": session_id,
            "tool_name": tool_name,
            "query": query[:200],
            "content_type": content_type,
            "response_size": response_size,
            "verified": True,
            "metadata": metadata or {}
        }

        # Write to verification log
        data_dir = Path.home() / ".claude" / "evaluation" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        verification_file = data_dir / "web_verifications.jsonl"

        with open(verification_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        return entry

    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics from log."""
        if not self.detection_log:
            return {
                "total_analyses": 0,
                "total_hallucinations": 0,
                "by_category": {},
                "by_severity": {},
                "average_per_analysis": 0,
                "risk_distribution": {}
            }

        total_hallucinations = sum(r.total_hallucinations for r in self.detection_log)

        # Aggregate categories and severities
        all_categories = {}
        all_severities = {}
        risk_dist = {}

        for result in self.detection_log:
            for cat, count in result.by_category.items():
                all_categories[cat] = all_categories.get(cat, 0) + count
            for sev, count in result.by_severity.items():
                all_severities[sev] = all_severities.get(sev, 0) + count
            risk_dist[result.risk_level] = risk_dist.get(result.risk_level, 0) + 1

        return {
            "total_analyses": len(self.detection_log),
            "total_hallucinations": total_hallucinations,
            "by_category": all_categories,
            "by_severity": all_severities,
            "average_per_analysis": total_hallucinations / len(self.detection_log) if self.detection_log else 0,
            "risk_distribution": risk_dist,
            "hallucination_rate": total_hallucinations / len(self.detection_log) if self.detection_log else 0
        }

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about detection patterns."""
        return {
            "total_patterns": len(self.patterns),
            "by_category": {
                cat.value: len([p for p in self.patterns if p.category == cat])
                for cat in HallucinationCategory
            },
            "by_severity": {
                sev.value: len([p for p in self.patterns if p.severity == sev])
                for sev in Severity
            }
        }


class HallucinationLogger:
    """Persistent logging of hallucination detection results."""

    def __init__(self, db_path: Path = HALLUCINATION_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def log_detection(self, result: DetectionResult, session_id: str = "") -> bool:
        """Log a detection result."""
        try:
            existing = []
            # Check if file exists and is not empty before reading
            if self.db_path.exists() and self.db_path.stat().st_size > 0:
                with open(self.db_path, 'r') as f:
                    try:
                        existing = json.load(f)
                    except json.JSONDecodeError:
                        # File is corrupted or empty, start fresh
                        logger.warning(f"Corrupted log file, starting fresh: {self.db_path}")
                        existing = []

            entry = {
                "timestamp": result.timestamp,
                "session_id": session_id,
                "total_hallucinations": result.total_hallucinations,
                "by_category": result.by_category,
                "by_severity": result.by_severity,
                "risk_level": result.risk_level,
                "confidence_score": result.confidence_score,
                "text_preview": result.text_analyzed[:200]
            }
            existing.append(entry)

            # Keep last 1000 entries
            if len(existing) > 1000:
                existing = existing[-1000:]

            with open(self.db_path, 'w') as f:
                json.dump(existing, f, indent=2)

            return True
        except IOError as e:
            logger.error(f"Failed to log detection: {e}")
            return False

    def get_historical_stats(self) -> Dict[str, Any]:
        """Get statistics from historical logs."""
        if not self.db_path.exists():
            return {"total_entries": 0}

        # Check if file is empty
        if self.db_path.stat().st_size == 0:
            return {"total_entries": 0}

        try:
            with open(self.db_path, 'r') as f:
                entries = json.load(f)

            if not entries:
                return {"total_entries": 0}

            total_hallucinations = sum(e.get("total_hallucinations", 0) for e in entries)

            all_categories = {}
            all_severities = {}
            risk_dist = {}

            for entry in entries:
                for cat, count in entry.get("by_category", {}).items():
                    all_categories[cat] = all_categories.get(cat, 0) + count
                for sev, count in entry.get("by_severity", {}).items():
                    all_severities[sev] = all_severities.get(sev, 0) + count
                risk = entry.get("risk_level", "UNKNOWN")
                risk_dist[risk] = risk_dist.get(risk, 0) + 1

            return {
                "total_entries": len(entries),
                "total_hallucinations": total_hallucinations,
                "average_per_entry": total_hallucinations / len(entries),
                "by_category": all_categories,
                "by_severity": all_severities,
                "risk_distribution": risk_dist,
                "hallucination_rate": total_hallucinations / len(entries)
            }
        except (json.JSONDecodeError, IOError) as e:
            return {"error": str(e)}


def run_self_test() -> bool:
    """Run self-test with known hallucination examples."""
    detector = HallucinationDetector()

    test_cases = [
        # Citation hallucinations
        {
            "text": "According to Smith et al., 2023, this technique improves accuracy by 50%.",
            "expected_category": "citation",
            "expected_min_count": 1
        },
        # Version hallucinations
        {
            "text": "Python 3.15 was released in January 2025 with major improvements.",
            "expected_category": "version",
            "expected_min_count": 1
        },
        # Quantitative hallucinations
        {
            "text": "Studies show 95% of developers prefer this approach.",
            "expected_category": "quantitative",
            "expected_min_count": 1
        },
        # Factual hallucinations
        {
            "text": "OpenAI is the first company to implement this technology.",
            "expected_category": "factual",
            "expected_min_count": 1
        },
        # Safe text (should have minimal detections)
        {
            "text": "Here is a simple Python function that calculates factorial.",
            "expected_category": None,
            "expected_min_count": 0
        }
    ]

    passed = 0
    failed = 0

    print("\n[HALLUCINATION DETECTOR SELF-TEST]")
    print("=" * 60)

    for i, test in enumerate(test_cases, 1):
        result = detector.detect(test["text"])

        if test["expected_category"]:
            category_count = result.by_category.get(test["expected_category"], 0)
            success = category_count >= test["expected_min_count"]
        else:
            success = result.total_hallucinations <= 1  # Allow minor false positives

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Text: {test['text'][:60]}...")
        print(f"  Expected: {test['expected_category'] or 'minimal'} >= {test['expected_min_count']}")
        print(f"  Actual: {result.total_hallucinations} hallucinations, categories: {result.by_category}")

        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{passed+failed} tests passed")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Hallucination Detection and Measurement System"
    )

    parser.add_argument("--text", type=str, help="Text to analyze")
    parser.add_argument("--file", type=str, help="File to analyze")
    parser.add_argument("--stats", action="store_true", help="Show detection statistics")
    parser.add_argument("--patterns", action="store_true", help="Show pattern statistics")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    parser.add_argument("--historical", action="store_true", help="Show historical statistics")
    parser.add_argument("--no-web-validation", action="store_true",
                       help="Disable web validation (arXiv/DOI verification)")
    parser.add_argument("--output", type=str, choices=["text", "json"], default="text")

    args = parser.parse_args()

    # Initialize detector with web validation (enabled by default)
    detector = HallucinationDetector(enable_web_validation=not args.no_web_validation)
    logger_instance = HallucinationLogger()

    if args.test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    elif args.patterns:
        stats = detector.get_pattern_stats()
        if args.output == "json":
            print(json.dumps(stats, indent=2))
        else:
            print("\n[HALLUCINATION DETECTION PATTERNS]")
            print(f"  Total patterns: {stats['total_patterns']}")
            print("\n  By category:")
            for cat, count in stats['by_category'].items():
                print(f"    - {cat}: {count}")
            print("\n  By severity:")
            for sev, count in stats['by_severity'].items():
                print(f"    - {sev}: {count}")

    elif args.historical:
        stats = logger_instance.get_historical_stats()
        if args.output == "json":
            print(json.dumps(stats, indent=2))
        else:
            print("\n[HISTORICAL HALLUCINATION STATISTICS]")
            if "error" in stats:
                print(f"  Error: {stats['error']}")
            else:
                print(f"  Total analyses: {stats['total_entries']}")
                print(f"  Total hallucinations: {stats['total_hallucinations']}")
                print(f"  Average per analysis: {stats['average_per_entry']:.2f}")
                print(f"  Hallucination rate: {stats['hallucination_rate']:.2f}")
                print("\n  By category:")
                for cat, count in stats.get('by_category', {}).items():
                    print(f"    - {cat}: {count}")
                print("\n  By severity:")
                for sev, count in stats.get('by_severity', {}).items():
                    print(f"    - {sev}: {count}")
                print("\n  Risk distribution:")
                for risk, count in stats.get('risk_distribution', {}).items():
                    print(f"    - {risk}: {count}")

    elif args.stats:
        stats = detector.get_statistics()
        if args.output == "json":
            print(json.dumps(stats, indent=2))
        else:
            print("\n[HALLUCINATION DETECTION STATISTICS]")
            print(f"  Total analyses this session: {stats['total_analyses']}")
            print(f"  Total hallucinations: {stats['total_hallucinations']}")
            print(f"  Average per analysis: {stats['average_per_analysis']:.2f}")

    elif args.text:
        result = detector.detect(args.text)
        logger_instance.log_detection(result)

        if args.output == "json":
            # Convert hallucinations to dict
            result_dict = asdict(result)
            result_dict['hallucinations'] = [asdict(h) for h in result.hallucinations]
            print(json.dumps(result_dict, indent=2, default=str))
        else:
            print("\n[HALLUCINATION DETECTION RESULT]")
            print(f"  Total detected: {result.total_hallucinations}")
            print(f"  Risk level: {result.risk_level}")
            print(f"  Confidence: {result.confidence_score:.2f}")

            if result.by_category:
                print("\n  By category:")
                for cat, count in result.by_category.items():
                    print(f"    - {cat}: {count}")

            if result.by_severity:
                print("\n  By severity:")
                for sev, count in result.by_severity.items():
                    print(f"    - {sev}: {count}")

            if result.hallucinations:
                print("\n  Detected hallucinations:")
                for h in result.hallucinations[:5]:  # Show first 5
                    print(f"    [{h.severity.value.upper()}] {h.description}")
                    print(f"      Snippet: \"{h.text_snippet[:50]}...\"")
                    print(f"      Pattern: {h.pattern_id}")
                if len(result.hallucinations) > 5:
                    print(f"    ... and {len(result.hallucinations) - 5} more")

        # Also check known facts
        violations = detector.check_known_facts(args.text)
        if violations:
            print("\n  Known fact violations:")
            for v in violations:
                print(f"    [{v['severity']}] Claimed: {v['claimed']}")
                print(f"      Actual: {v['actual']}")

    elif args.file:
        try:
            with open(args.file, 'r') as f:
                text = f.read()
            result = detector.detect(text)
            logger_instance.log_detection(result)

            print(f"\n[HALLUCINATION DETECTION RESULT]")
            print(f"  File: {args.file}")
            print(f"  Total detected: {result.total_hallucinations}")
            print(f"  Risk level: {result.risk_level}")
        except IOError as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
