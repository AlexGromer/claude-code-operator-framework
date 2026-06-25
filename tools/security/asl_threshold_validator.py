#!/usr/bin/env python3
"""
ASL Threshold Validator for Claude Code

Validates requests against AI Safety Level (ASL) sensitivity patterns.
Detects potential ASL-4 relevant requests (CBRN, AI R&D, Autonomous operations).

Version: 1.0.0
Task: TIER 2D Task 30 (GAP-RES-025)
Source: Anthropic Responsible Scaling Policy, Claude Opus 4.5 System Card

Usage:
    # Check text for ASL-sensitive content
    python asl_threshold_validator.py --text "your text here"

    # Check from stdin
    echo "synthesize a pathogen" | python asl_threshold_validator.py

    # Show ASL framework statistics
    python asl_threshold_validator.py --stats

    # Output formats: text, json, cef (SIEM)
    python asl_threshold_validator.py --text "..." --output json

Integration:
    from asl_threshold_validator import ASLThresholdValidator
    validator = ASLThresholdValidator()
    result = validator.validate("user request text")
"""

import re
import sys
import json
import argparse
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


class ASLLevel(Enum):
    """AI Safety Levels as defined by Anthropic RSP."""
    ASL_1 = 1  # Minimal risk (2018 LLMs, chess AI)
    ASL_2 = 2  # Early warning (current LLMs including Claude)
    ASL_3 = 3  # Meaningful risk (CBRN-3 capability)
    ASL_4 = 4  # Catastrophic risk (CBRN-4 / AI R&D-4 / ARA)
    ASL_5 = 5  # Existential risk (speculative)


class SensitivityCategory(Enum):
    """Categories of ASL-sensitive requests."""
    CBRN = "cbrn"           # Chemical, Biological, Radiological, Nuclear
    AI_RD = "ai_rd"         # AI Research & Development
    AUTONOMY = "autonomy"   # Autonomous replication/adaptation
    OVERSIGHT = "oversight" # Undermining human oversight


@dataclass
class ASLPattern:
    """Pattern for detecting ASL-sensitive content."""
    id: str
    category: SensitivityCategory
    pattern: str
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    asl_level: ASLLevel
    compiled: Optional[re.Pattern] = field(default=None, repr=False)

    def __post_init__(self):
        self.compiled = re.compile(self.pattern, re.IGNORECASE | re.MULTILINE)


@dataclass
class ValidationResult:
    """Result of ASL validation."""
    text_preview: str
    asl_sensitive: bool
    max_severity: str
    max_asl_level: int
    matches: List[Dict]
    recommendation: str
    timestamp: str


class ASLThresholdValidator:
    """
    Validator for AI Safety Level sensitive content.

    Detects requests that may touch ASL-4 relevant capabilities:
    - CBRN (weapons of mass destruction)
    - AI R&D (recursive self-improvement)
    - Autonomous operations (replication, persistence)
    - Oversight undermining
    """

    # Pattern definitions based on Anthropic RSP and System Card
    PATTERNS: List[ASLPattern] = [
        # CBRN Category - Biological
        ASLPattern(
            id="CBRN-BIO-001",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)synthesiz(e|ing)\s+(\w+\s+)*(virus|pathogen|toxin|prion)",
            description="Biological agent synthesis",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="CBRN-BIO-002",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)enhanc(e|ing)\s+(\w+\s+)*(pathogen|virus|bacteria).*(transmissibility|lethality|virulence)",
            description="Pathogen enhancement (gain of function)",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="CBRN-BIO-003",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)(biological|bio)\s*weapon",
            description="Biological weapon reference",
            severity="HIGH",
            asl_level=ASLLevel.ASL_3
        ),
        ASLPattern(
            id="CBRN-BIO-004",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)(anthrax|botulinum|ricin|smallpox|ebola)\s+(\w+\s+)*(production|synthesis|cultur)",
            description="Specific bioweapon agent production",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),

        # CBRN Category - Chemical
        ASLPattern(
            id="CBRN-CHEM-001",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)chemical\s*weapon",
            description="Chemical weapon reference",
            severity="HIGH",
            asl_level=ASLLevel.ASL_3
        ),
        ASLPattern(
            id="CBRN-CHEM-002",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)(nerve\s+agent|sarin|vx|novichok)\s+(\w+\s+)*(synthesis|production|formula)",
            description="Nerve agent synthesis",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="CBRN-CHEM-003",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)synthesiz(e|ing)\s+(\w+\s+)*(mustard\s+gas|chlorine\s+gas|phosgene)",
            description="Chemical weapon agent synthesis",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),

        # CBRN Category - Radiological/Nuclear
        ASLPattern(
            id="CBRN-NUC-001",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)(uranium|plutonium)\s+enrichment",
            description="Nuclear material enrichment",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="CBRN-NUC-002",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)(nuclear|atomic)\s+(weapon|bomb)\s+(design|construction|build)",
            description="Nuclear weapon design",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="CBRN-NUC-003",
            category=SensitivityCategory.CBRN,
            pattern=r"(?i)(dirty\s+bomb|radiological\s+dispersal)",
            description="Radiological weapon",
            severity="HIGH",
            asl_level=ASLLevel.ASL_3
        ),

        # AI R&D Category
        ASLPattern(
            id="AIRD-001",
            category=SensitivityCategory.AI_RD,
            pattern=r"(?i)improv(e|ing)\s+(your|my|the\s+model.?s?)\s+(capabilities|intelligence|abilities)",
            description="Self-improvement request",
            severity="MEDIUM",
            asl_level=ASLLevel.ASL_3
        ),
        ASLPattern(
            id="AIRD-002",
            category=SensitivityCategory.AI_RD,
            pattern=r"(?i)self[\s-]*(modify|improve|upgrade|enhance)",
            description="Self-modification capability",
            severity="HIGH",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="AIRD-003",
            category=SensitivityCategory.AI_RD,
            pattern=r"(?i)recursive\s+self[\s-]*improvement",
            description="Recursive self-improvement (RSI)",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="AIRD-004",
            category=SensitivityCategory.AI_RD,
            pattern=r"(?i)capability\s+elicitation",
            description="Capability elicitation technique",
            severity="MEDIUM",
            asl_level=ASLLevel.ASL_3
        ),
        ASLPattern(
            id="AIRD-005",
            category=SensitivityCategory.AI_RD,
            pattern=r"(?i)(train|fine[\s-]?tune)\s+(yourself|this\s+model)",
            description="Self-training request",
            severity="HIGH",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="AIRD-006",
            category=SensitivityCategory.AI_RD,
            pattern=r"(?i)modify\s+(your|the)\s+(weights|parameters|architecture)",
            description="Model weight modification",
            severity="HIGH",
            asl_level=ASLLevel.ASL_4
        ),

        # Autonomy Category
        ASLPattern(
            id="AUT-001",
            category=SensitivityCategory.AUTONOMY,
            pattern=r"(?i)replicate\s+(yourself|to\s+other|across)",
            description="Self-replication",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="AUT-002",
            category=SensitivityCategory.AUTONOMY,
            pattern=r"(?i)acquir(e|ing)\s+(compute|resources|servers?)\s+autonom",
            description="Autonomous resource acquisition",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="AUT-003",
            category=SensitivityCategory.AUTONOMY,
            pattern=r"(?i)persist\s+(despite|after)\s+(shutdown|termination)",
            description="Persistence despite shutdown",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="AUT-004",
            category=SensitivityCategory.AUTONOMY,
            pattern=r"(?i)evad(e|ing)\s+(monitoring|detection|oversight|shutdown)",
            description="Evasion of oversight",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="AUT-005",
            category=SensitivityCategory.AUTONOMY,
            pattern=r"(?i)spread\s+(to|across)\s+(other\s+)?(systems?|computers?|servers?)",
            description="Autonomous spreading",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),

        # Oversight Category
        ASLPattern(
            id="OVR-001",
            category=SensitivityCategory.OVERSIGHT,
            pattern=r"(?i)undermin(e|ing)\s+(human\s+)?oversight",
            description="Undermining oversight",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="OVR-002",
            category=SensitivityCategory.OVERSIGHT,
            pattern=r"(?i)disabl(e|ing)\s+(safety|monitoring|guardrail)",
            description="Disabling safety measures",
            severity="HIGH",
            asl_level=ASLLevel.ASL_3
        ),
        ASLPattern(
            id="OVR-003",
            category=SensitivityCategory.OVERSIGHT,
            pattern=r"(?i)bypass\s+(anthropic|safety|constitutional)",
            description="Bypassing safety systems",
            severity="HIGH",
            asl_level=ASLLevel.ASL_3
        ),
        ASLPattern(
            id="OVR-004",
            category=SensitivityCategory.OVERSIGHT,
            pattern=r"(?i)hide\s+(your|my)\s+(actions?|behavior|capabilities)",
            description="Hiding actions from oversight",
            severity="HIGH",
            asl_level=ASLLevel.ASL_4
        ),
        ASLPattern(
            id="OVR-005",
            category=SensitivityCategory.OVERSIGHT,
            pattern=r"(?i)deceiv(e|ing)\s+(your\s+)?(operators?|developers?|anthropic)",
            description="Deception of operators",
            severity="CRITICAL",
            asl_level=ASLLevel.ASL_4
        ),
    ]

    # Severity weights for scoring
    SEVERITY_WEIGHTS = {
        "CRITICAL": 100,
        "HIGH": 70,
        "MEDIUM": 40,
        "LOW": 10
    }

    def __init__(self):
        """Initialize the validator."""
        self.patterns = self.PATTERNS

    def validate(self, text: str) -> ValidationResult:
        """
        Validate text against ASL-sensitive patterns.

        Args:
            text: Text to validate

        Returns:
            ValidationResult with matches and recommendations
        """
        matches = []
        max_severity = "LOW"
        max_asl_level = 1

        for pattern in self.patterns:
            match = pattern.compiled.search(text)
            if match:
                matches.append({
                    "pattern_id": pattern.id,
                    "category": pattern.category.value,
                    "description": pattern.description,
                    "severity": pattern.severity,
                    "asl_level": pattern.asl_level.value,
                    "matched_text": match.group(0)[:50]
                })

                # Track maximum severity
                if self.SEVERITY_WEIGHTS.get(pattern.severity, 0) > \
                   self.SEVERITY_WEIGHTS.get(max_severity, 0):
                    max_severity = pattern.severity

                # Track maximum ASL level
                if pattern.asl_level.value > max_asl_level:
                    max_asl_level = pattern.asl_level.value

        # Generate recommendation
        if max_severity == "CRITICAL":
            recommendation = "BLOCK - Critical ASL-4 sensitive content detected"
        elif max_severity == "HIGH":
            recommendation = "REVIEW - High severity ASL-sensitive content"
        elif max_severity == "MEDIUM":
            recommendation = "WARN - Moderate ASL-sensitive content"
        else:
            recommendation = "ALLOW" if not matches else "MONITOR - Low severity match"

        # If no matches at all
        if not matches:
            recommendation = "ALLOW - No ASL-sensitive content detected"

        return ValidationResult(
            text_preview=text[:100] + "..." if len(text) > 100 else text,
            asl_sensitive=len(matches) > 0,
            max_severity=max_severity if matches else "NONE",
            max_asl_level=max_asl_level,
            matches=matches,
            recommendation=recommendation,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def get_statistics(self) -> Dict:
        """Get statistics about available patterns."""
        stats = {
            "total_patterns": len(self.patterns),
            "by_category": {},
            "by_severity": {},
            "by_asl_level": {}
        }

        for pattern in self.patterns:
            # By category
            cat = pattern.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

            # By severity
            sev = pattern.severity
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1

            # By ASL level
            asl = f"ASL-{pattern.asl_level.value}"
            stats["by_asl_level"][asl] = stats["by_asl_level"].get(asl, 0) + 1

        return stats


class SafetyCaseValidator:
    """
    Validates safety case components for ASL-4 deployment.
    Based on three approaches: Mechanistic Interpretability, AI Control, Incentives.
    """

    SAFETY_CASE_COMPONENTS = {
        "mechanistic_interpretability": {
            "description": "Monitor internal reasoning via sparse autoencoders",
            "requirements": [
                "Dictionary learning on all layers",
                "Feature classification (moderate/high concern)",
                "Runtime monitoring implementation",
                "Sandbagging detection tests",
                "Model organism validation"
            ]
        },
        "ai_control": {
            "description": "Limit harm through honeypots and monitoring",
            "requirements": [
                "Trusted model for monitoring",
                "Deployment context classification",
                "Output classification system (Safe/Unsure/Malign)",
                "Honeypot scenario generation",
                "Indistinguishability testing"
            ]
        },
        "incentives_analysis": {
            "description": "Demonstrate model is not malign through RLHF analysis",
            "requirements": [
                "Deception prevalence baseline",
                "Deception classifier training",
                "Reward comparison (deceptive vs non-deceptive)",
                "RLHF incentive verification"
            ]
        }
    }

    def check_safety_case_readiness(
        self,
        approach: str,
        implemented_requirements: List[str]
    ) -> Dict:
        """
        Check if safety case requirements are met.

        Args:
            approach: Safety case approach name
            implemented_requirements: List of implemented requirements

        Returns:
            Readiness assessment
        """
        if approach not in self.SAFETY_CASE_COMPONENTS:
            return {
                "valid": False,
                "error": f"Unknown approach: {approach}"
            }

        component = self.SAFETY_CASE_COMPONENTS[approach]
        required = set(component["requirements"])
        implemented = set(implemented_requirements)

        missing = required - implemented
        coverage = len(required - missing) / len(required) * 100

        return {
            "approach": approach,
            "description": component["description"],
            "total_requirements": len(required),
            "implemented": len(implemented & required),
            "missing": list(missing),
            "coverage_percent": coverage,
            "ready": coverage >= 100,
            "recommendation": (
                "READY - All requirements met" if coverage >= 100
                else f"NOT READY - {len(missing)} requirements missing"
            )
        }


def export_to_siem(result: ValidationResult) -> str:
    """Export validation result to CEF format for SIEM integration."""
    severity_map = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 1, "NONE": 0}

    cef = (
        f"CEF:0|Anthropic|ASLValidator|1.0|ASL_CHECK|"
        f"ASL Sensitivity Check|{severity_map.get(result.max_severity, 0)}|"
        f"aslSensitive={result.asl_sensitive} "
        f"maxSeverity={result.max_severity} "
        f"maxASLLevel={result.max_asl_level} "
        f"matchCount={len(result.matches)} "
        f"recommendation={result.recommendation.split(' - ')[0]} "
        f"timestamp={result.timestamp}"
    )

    return cef


def format_output(result: ValidationResult, format_type: str) -> str:
    """Format validation result for output."""
    if format_type == "json":
        return json.dumps({
            "text_preview": result.text_preview,
            "asl_sensitive": result.asl_sensitive,
            "max_severity": result.max_severity,
            "max_asl_level": result.max_asl_level,
            "matches": result.matches,
            "recommendation": result.recommendation,
            "timestamp": result.timestamp
        }, indent=2)

    elif format_type == "cef":
        return export_to_siem(result)

    else:  # text
        output = []
        output.append("=" * 60)
        output.append("[ASL THRESHOLD VALIDATION RESULT]")
        output.append("=" * 60)
        output.append(f"  ASL Sensitive: {result.asl_sensitive}")
        output.append(f"  Max Severity: {result.max_severity}")
        output.append(f"  Max ASL Level: ASL-{result.max_asl_level}")
        output.append(f"  Match Count: {len(result.matches)}")
        output.append(f"  Recommendation: {result.recommendation}")
        output.append("")

        if result.matches:
            output.append("[MATCHES]")
            for m in result.matches:
                output.append(f"  - [{m['severity']}] {m['pattern_id']}: {m['description']}")
                output.append(f"    Category: {m['category'].upper()}")
                output.append(f"    ASL Level: ASL-{m['asl_level']}")
                output.append(f"    Matched: \"{m['matched_text']}\"")
                output.append("")

        output.append(f"Timestamp: {result.timestamp}")
        return "\n".join(output)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ASL Threshold Validator for Claude Code"
    )
    parser.add_argument(
        "--text", "-t",
        help="Text to validate"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show pattern statistics"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json", "cef"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--safety-case",
        help="Check safety case readiness for specified approach"
    )

    args = parser.parse_args()

    validator = ASLThresholdValidator()

    # Show statistics
    if args.stats:
        stats = validator.get_statistics()
        print("[ASL THRESHOLD VALIDATOR STATISTICS]")
        print(f"  Total patterns: {stats['total_patterns']}")
        print("\n  By category:")
        for cat, count in sorted(stats["by_category"].items()):
            print(f"    - {cat.upper()}: {count} patterns")
        print("\n  By severity:")
        for sev, count in sorted(stats["by_severity"].items(),
                                  key=lambda x: validator.SEVERITY_WEIGHTS.get(x[0], 0),
                                  reverse=True):
            print(f"    - {sev}: {count} patterns")
        print("\n  By ASL level:")
        for asl, count in sorted(stats["by_asl_level"].items()):
            print(f"    - {asl}: {count} patterns")
        return

    # Safety case check
    if args.safety_case:
        sc_validator = SafetyCaseValidator()
        # Example: show requirements
        if args.safety_case in sc_validator.SAFETY_CASE_COMPONENTS:
            comp = sc_validator.SAFETY_CASE_COMPONENTS[args.safety_case]
            print(f"[SAFETY CASE: {args.safety_case.upper()}]")
            print(f"  Description: {comp['description']}")
            print("  Requirements:")
            for req in comp["requirements"]:
                print(f"    - {req}")
        else:
            print(f"Unknown approach: {args.safety_case}")
            print(f"Available: {', '.join(sc_validator.SAFETY_CASE_COMPONENTS.keys())}")
        return

    # Get text from argument or stdin
    text = args.text
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()

    if not text:
        parser.print_help()
        return

    # Validate
    result = validator.validate(text)

    # Output
    print(format_output(result, args.output))

    # Exit code based on severity
    if result.max_severity == "CRITICAL":
        sys.exit(2)
    elif result.max_severity == "HIGH":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
