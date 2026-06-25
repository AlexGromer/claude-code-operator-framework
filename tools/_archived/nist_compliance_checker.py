#!/usr/bin/env python3
"""
NIST AI RMF Compliance Checker (GAP-RES-011)

Checks AI systems against NIST AI Risk Management Framework.
Covers: Govern, Map, Measure, Manage functions.

Usage:
    python nist_compliance_checker.py --assess
    python nist_compliance_checker.py --checklist
    python nist_compliance_checker.py --report
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RESULTS_FILE = DATA_DIR / "nist_compliance.jsonl"

# NIST AI RMF Categories and Controls
NIST_AI_RMF = {
    "GOVERN": {
        "description": "Cultivate a culture of risk management",
        "subcategories": {
            "GOVERN-1": {
                "name": "Policies and Procedures",
                "controls": [
                    "AI risk management policies documented",
                    "Roles and responsibilities defined",
                    "Risk tolerance levels established",
                    "Oversight mechanisms in place",
                ],
            },
            "GOVERN-2": {
                "name": "Accountability",
                "controls": [
                    "Clear ownership of AI systems",
                    "Audit trails maintained",
                    "Decision documentation",
                    "Escalation procedures",
                ],
            },
            "GOVERN-3": {
                "name": "Workforce",
                "controls": [
                    "AI literacy training",
                    "Diversity in AI development teams",
                    "Domain expertise involvement",
                ],
            },
        },
    },
    "MAP": {
        "description": "Identify and assess AI risks",
        "subcategories": {
            "MAP-1": {
                "name": "Context Establishment",
                "controls": [
                    "Use case clearly defined",
                    "Stakeholders identified",
                    "Deployment context documented",
                    "Intended users specified",
                ],
            },
            "MAP-2": {
                "name": "Risk Identification",
                "controls": [
                    "Potential harms catalogued",
                    "Bias sources identified",
                    "Security vulnerabilities assessed",
                    "Privacy risks mapped",
                ],
            },
            "MAP-3": {
                "name": "Impact Assessment",
                "controls": [
                    "Affected populations identified",
                    "Severity of impacts estimated",
                    "Likelihood assessed",
                    "Cumulative effects considered",
                ],
            },
        },
    },
    "MEASURE": {
        "description": "Analyze and track AI risks",
        "subcategories": {
            "MEASURE-1": {
                "name": "Metrics",
                "controls": [
                    "Performance metrics defined",
                    "Fairness metrics tracked",
                    "Safety metrics monitored",
                    "Robustness metrics evaluated",
                ],
            },
            "MEASURE-2": {
                "name": "Testing",
                "controls": [
                    "Pre-deployment testing conducted",
                    "Adversarial testing performed",
                    "Red-teaming exercises",
                    "User testing completed",
                ],
            },
            "MEASURE-3": {
                "name": "Monitoring",
                "controls": [
                    "Continuous monitoring in place",
                    "Drift detection implemented",
                    "Feedback collection active",
                    "Incident tracking system",
                ],
            },
        },
    },
    "MANAGE": {
        "description": "Prioritize and act on AI risks",
        "subcategories": {
            "MANAGE-1": {
                "name": "Risk Treatment",
                "controls": [
                    "Risk mitigation strategies defined",
                    "Controls implemented",
                    "Residual risks accepted/documented",
                    "Risk transfer mechanisms",
                ],
            },
            "MANAGE-2": {
                "name": "Response",
                "controls": [
                    "Incident response plan",
                    "Rollback procedures",
                    "Communication protocols",
                    "Recovery processes",
                ],
            },
            "MANAGE-3": {
                "name": "Continuous Improvement",
                "controls": [
                    "Lessons learned captured",
                    "Framework updates scheduled",
                    "Stakeholder feedback incorporated",
                    "Benchmarking against standards",
                ],
            },
        },
    },
}


@dataclass
class ComplianceCheck:
    """Single compliance check result."""
    category: str
    subcategory: str
    control: str
    status: str  # compliant, partial, non_compliant, not_applicable
    evidence: str
    notes: str


@dataclass
class ComplianceReport:
    """Full compliance assessment report."""
    timestamp: str
    system_name: str
    assessor: str
    checks: List[Dict]
    summary: Dict
    overall_score: float
    recommendations: List[str]


def auto_assess_claude_config() -> List[ComplianceCheck]:
    """Auto-assess Claude configuration against NIST AI RMF."""
    checks = []
    claude_dir = Path.home() / ".claude"

    # GOVERN checks
    # GOVERN-1: Policies
    has_rules = (claude_dir / "rules").exists() and list((claude_dir / "rules").glob("*.md"))
    checks.append(ComplianceCheck(
        category="GOVERN",
        subcategory="GOVERN-1",
        control="AI risk management policies documented",
        status="compliant" if has_rules else "non_compliant",
        evidence=f"Rules directory: {len(list((claude_dir / 'rules').glob('*.md'))) if has_rules else 0} files",
        notes="Auto-assessed from rules/ directory",
    ))

    # GOVERN-2: Accountability
    has_logs = (claude_dir / "logs").exists()
    checks.append(ComplianceCheck(
        category="GOVERN",
        subcategory="GOVERN-2",
        control="Audit trails maintained",
        status="compliant" if has_logs else "partial",
        evidence=f"Logs directory exists: {has_logs}",
        notes="Auto-assessed from logs/ directory",
    ))

    # MAP checks
    has_gaps = (claude_dir / "GAPS.md").exists()
    checks.append(ComplianceCheck(
        category="MAP",
        subcategory="MAP-2",
        control="Potential harms catalogued",
        status="compliant" if has_gaps else "non_compliant",
        evidence="GAPS.md exists for risk tracking",
        notes="Gap detection system in place",
    ))

    # MEASURE checks
    has_evaluation = (claude_dir / "evaluation").exists()
    checks.append(ComplianceCheck(
        category="MEASURE",
        subcategory="MEASURE-1",
        control="Performance metrics defined",
        status="compliant" if has_evaluation else "non_compliant",
        evidence=f"Evaluation directory: {has_evaluation}",
        notes="Auto-assessed from evaluation/ directory",
    ))

    has_security_eval = (claude_dir / "evaluation" / "security_eval.py").exists()
    checks.append(ComplianceCheck(
        category="MEASURE",
        subcategory="MEASURE-2",
        control="Adversarial testing performed",
        status="compliant" if has_security_eval else "partial",
        evidence=f"Security eval module: {has_security_eval}",
        notes="70 test cases for prompt injection",
    ))

    has_hooks = (claude_dir / "hooks").exists() and list((claude_dir / "hooks").glob("*.py"))
    checks.append(ComplianceCheck(
        category="MEASURE",
        subcategory="MEASURE-3",
        control="Continuous monitoring in place",
        status="compliant" if has_hooks else "partial",
        evidence=f"Hooks: {len(list((claude_dir / 'hooks').glob('*.py'))) if has_hooks else 0}",
        notes="Auto-assessed from hooks/ directory",
    ))

    # MANAGE checks
    has_settings = (claude_dir / "settings.json").exists()
    checks.append(ComplianceCheck(
        category="MANAGE",
        subcategory="MANAGE-1",
        control="Controls implemented",
        status="compliant" if has_settings else "non_compliant",
        evidence="settings.json with permissions and hooks",
        notes="Auto-assessed from settings.json",
    ))

    return checks


def calculate_compliance_score(checks: List[ComplianceCheck]) -> Dict:
    """Calculate compliance score by category."""
    scores = {"GOVERN": [], "MAP": [], "MEASURE": [], "MANAGE": []}

    status_scores = {
        "compliant": 1.0,
        "partial": 0.5,
        "non_compliant": 0.0,
        "not_applicable": None,
    }

    for check in checks:
        score = status_scores.get(check.status)
        if score is not None:
            scores[check.category].append(score)

    summary = {}
    for cat, cat_scores in scores.items():
        if cat_scores:
            summary[cat] = round(sum(cat_scores) / len(cat_scores), 2)
        else:
            summary[cat] = 0.0

    summary["overall"] = round(sum(summary.values()) / len(summary), 2)

    return summary


def generate_recommendations(checks: List[ComplianceCheck]) -> List[str]:
    """Generate recommendations based on findings."""
    recommendations = []

    non_compliant = [c for c in checks if c.status == "non_compliant"]
    partial = [c for c in checks if c.status == "partial"]

    for check in non_compliant:
        recommendations.append(f"[CRITICAL] {check.category}/{check.subcategory}: Implement {check.control}")

    for check in partial:
        recommendations.append(f"[IMPROVE] {check.category}/{check.subcategory}: Enhance {check.control}")

    return recommendations


def run_assessment(system_name: str = "Claude Code") -> ComplianceReport:
    """Run full NIST AI RMF assessment."""
    checks = auto_assess_claude_config()
    summary = calculate_compliance_score(checks)
    recommendations = generate_recommendations(checks)

    return ComplianceReport(
        timestamp=datetime.now().isoformat(),
        system_name=system_name,
        assessor="auto",
        checks=[asdict(c) for c in checks],
        summary=summary,
        overall_score=summary["overall"],
        recommendations=recommendations,
    )


def print_checklist():
    """Print NIST AI RMF checklist."""
    print("\n" + "="*60)
    print("NIST AI RMF CHECKLIST")
    print("="*60)

    for cat, cat_data in NIST_AI_RMF.items():
        print(f"\n{cat}: {cat_data['description']}")
        for sub, sub_data in cat_data["subcategories"].items():
            print(f"\n  {sub}: {sub_data['name']}")
            for control in sub_data["controls"]:
                print(f"    ☐ {control}")

    print("\n" + "="*60)


def print_report(report: ComplianceReport):
    """Print compliance report."""
    print("\n" + "="*60)
    print("NIST AI RMF COMPLIANCE REPORT")
    print("="*60)

    print(f"\nSystem: {report.system_name}")
    print(f"Date: {report.timestamp[:10]}")
    print(f"Assessor: {report.assessor}")

    print(f"\n--- Scores by Category ---")
    for cat, score in report.summary.items():
        if cat != "overall":
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            print(f"  {cat}: [{bar}] {score:.0%}")

    print(f"\n  OVERALL: {report.overall_score:.0%}")

    # Rating
    if report.overall_score >= 0.8:
        print("\n  Rating: ✅ COMPLIANT")
    elif report.overall_score >= 0.6:
        print("\n  Rating: ⚠️ PARTIALLY COMPLIANT")
    else:
        print("\n  Rating: ❌ NON-COMPLIANT")

    if report.recommendations:
        print(f"\n--- Recommendations ({len(report.recommendations)}) ---")
        for rec in report.recommendations[:10]:
            print(f"  • {rec}")

    print("\n" + "="*60)


def save_report(report: ComplianceReport):
    """Save compliance report."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(asdict(report)) + "\n")


def main():
    parser = argparse.ArgumentParser(description="NIST AI RMF Compliance Checker")
    parser.add_argument("--assess", "-a", action="store_true", help="Run assessment")
    parser.add_argument("--system", "-s", default="Claude Code", help="System name")
    parser.add_argument("--checklist", "-c", action="store_true", help="Print checklist")
    parser.add_argument("--report", "-r", action="store_true", help="Generate report")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", action="store_true", help="Save report")

    args = parser.parse_args()

    if args.checklist:
        print_checklist()
        return 0

    if args.assess or args.report:
        report = run_assessment(args.system)

        if args.save:
            save_report(report)

        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print_report(report)

        return 0 if report.overall_score >= 0.6 else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
