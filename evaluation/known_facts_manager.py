#!/usr/bin/env python3
"""
Known Facts Database Manager
Extension for hallucination_detector.py

Manages extended known facts database with multiple categories:
- AI companies and organizations
- AI models and versions
- Programming languages and frameworks
- Cloud providers
- Security standards
- Academic papers

Usage:
    from known_facts_manager import KnownFactsManager

    manager = KnownFactsManager()

    # Check fact
    result = manager.check_fact("Anthropic was founded in 2019")
    # Returns: {"valid": False, "actual": "Anthropic was founded in 2021", ...}

    # Get fact
    fact = manager.get_fact("anthropic", category="ai_companies")

    # List categories
    categories = manager.list_categories()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class FactCheckResult:
    """Result of fact checking."""
    fact_id: str
    category: str
    claim: str
    is_valid: bool
    confidence: float  # 0-1
    actual_value: Optional[str] = None
    violation_type: str = ""  # "wrong_year", "wrong_name", "wrong_date", etc.
    severity: str = "MINOR"  # MINOR, MAJOR, CRITICAL


class KnownFactsManager:
    """
    Manages extended known facts database for hallucination detection.

    Loads facts from known_facts_extended.json and provides
    validation methods for different categories.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize with database path."""
        self.db_path = db_path or Path.home() / ".claude" / "evaluation" / "data" / "known_facts_extended.json"
        self.facts = self._load_database()

    def _load_database(self) -> Dict[str, Any]:
        """Load known facts database from JSON."""
        if not self.db_path.exists():
            print(f"Warning: Extended facts database not found at {self.db_path}")
            return {"categories": {}}

        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            print(f"✅ Loaded extended facts database (version {data.get('version', 'unknown')})")
            return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"❌ Error loading facts database: {e}")
            return {"categories": {}}

    def list_categories(self) -> List[str]:
        """List all available categories."""
        return list(self.facts.get("categories", {}).keys())

    def get_fact(self, fact_id: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific fact by ID and category.

        Args:
            fact_id: ID of the fact (e.g., "anthropic", "python")
            category: Category name (e.g., "ai_companies", "programming_languages")

        Returns:
            Fact data or None if not found
        """
        categories = self.facts.get("categories", {})
        category_data = categories.get(category, {})
        return category_data.get(fact_id)

    def check_company_founding(self, text: str) -> List[FactCheckResult]:
        """
        Check company founding year claims.

        Patterns:
        - "Anthropic was founded in 2019"
        - "OpenAI founded in 2016"
        - "Google DeepMind established in 2009"
        """
        results = []
        text_lower = text.lower()

        ai_companies = self.facts.get("categories", {}).get("ai_companies", {})

        for company_id, company_data in ai_companies.items():
            company_name = company_data.get("name", "")
            actual_year = company_data.get("founded")

            # Search for founding year claims
            pattern = rf"{re.escape(company_name.lower())}.*(?:founded|established|created|started).*?(\d{{4}})"
            match = re.search(pattern, text_lower)

            if match:
                claimed_year = int(match.group(1))
                is_valid = (claimed_year == actual_year)

                result = FactCheckResult(
                    fact_id=company_id,
                    category="ai_companies",
                    claim=f"{company_name} founded in {claimed_year}",
                    is_valid=is_valid,
                    confidence=0.95,  # High confidence for structured data
                    actual_value=f"{company_name} was founded in {actual_year}",
                    violation_type="wrong_year" if not is_valid else "",
                    severity="MAJOR" if not is_valid else "MINOR"
                )
                results.append(result)

        return results

    def check_model_release_date(self, text: str) -> List[FactCheckResult]:
        """
        Check AI model release date claims.

        Patterns:
        - "GPT-4 was released in March 2023"
        - "Claude 3 released on March 4, 2024"
        """
        results = []
        text_lower = text.lower()

        ai_models = self.facts.get("categories", {}).get("ai_models", {})

        for model_id, model_data in ai_models.items():
            model_name = model_data.get("name", "")
            versions = model_data.get("versions", [])

            for version_data in versions:
                version_name = version_data.get("name", "")
                release_date = version_data.get("release_date", "")

                # Search for release date claims
                # Pattern: "GPT-4 was released in March 2023"
                pattern = rf"{re.escape(version_name.lower())}.*(?:released|launched).*?(\w+\s+\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}})"
                match = re.search(pattern, text_lower)

                if match:
                    claimed_date = match.group(1)
                    actual_date = release_date

                    # Simple date comparison (can be improved)
                    is_valid = (claimed_date in actual_date or actual_date in claimed_date)

                    result = FactCheckResult(
                        fact_id=f"{model_id}_{version_name.replace(' ', '_').lower()}",
                        category="ai_models",
                        claim=f"{version_name} released {claimed_date}",
                        is_valid=is_valid,
                        confidence=0.90,
                        actual_value=f"{version_name} was released on {actual_date}",
                        violation_type="wrong_date" if not is_valid else "",
                        severity="MAJOR" if not is_valid else "MINOR"
                    )
                    results.append(result)

        return results

    def check_python_version(self, text: str) -> List[FactCheckResult]:
        """
        Check Python version claims.

        Patterns:
        - "Python 3.15 was released in 2025"
        - "Python 3.13 released October 2024"
        """
        results = []
        text_lower = text.lower()

        python_data = self.get_fact("python", "programming_languages")
        if not python_data:
            return results

        versions = python_data.get("versions", [])
        latest_version = python_data.get("latest_major_version")

        # Check for non-existent Python versions
        pattern = r"python\s+(\d+\.\d+)"
        matches = re.finditer(pattern, text_lower)

        for match in matches:
            claimed_version = match.group(1)

            # Check if version exists
            version_exists = any(
                v.get("version") == claimed_version for v in versions
            )

            if not version_exists:
                # Check if it's a future version (> latest)
                try:
                    claimed_major, claimed_minor = map(int, claimed_version.split('.'))
                    latest_major, latest_minor = map(int, latest_version.split('.'))

                    is_future = (claimed_major > latest_major) or \
                               (claimed_major == latest_major and claimed_minor > latest_minor)

                    result = FactCheckResult(
                        fact_id="python_version",
                        category="programming_languages",
                        claim=f"Python {claimed_version}",
                        is_valid=False,
                        confidence=0.95,
                        actual_value=f"Latest Python version is {latest_version}. Python {claimed_version} {'may be a future release' if is_future else 'does not exist'}.",
                        violation_type="wrong_version",
                        severity="MAJOR"
                    )
                    results.append(result)
                except ValueError:
                    pass

        return results

    def check_text(self, text: str) -> List[FactCheckResult]:
        """
        Check text against all known facts categories.

        Returns list of fact check results for any violations found.
        """
        all_results = []

        # Run all check methods
        all_results.extend(self.check_company_founding(text))
        all_results.extend(self.check_model_release_date(text))
        all_results.extend(self.check_python_version(text))

        return all_results

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the facts database."""
        categories = self.facts.get("categories", {})

        stats = {
            "version": self.facts.get("version", "unknown"),
            "last_updated": self.facts.get("last_updated", "unknown"),
            "total_categories": len(categories),
            "facts_by_category": {}
        }

        for category_name, category_data in categories.items():
            stats["facts_by_category"][category_name] = len(category_data)

        stats["total_facts"] = sum(stats["facts_by_category"].values())

        return stats

    def format_report(self, results: List[FactCheckResult]) -> str:
        """Format fact check results as a report."""
        if not results:
            return "✅ No fact violations found"

        report = f"\n{'='*70}\n"
        report += f"KNOWN FACTS VALIDATION REPORT\n"
        report += f"{'='*70}\n\n"
        report += f"Total Violations: {len(results)}\n\n"

        for i, result in enumerate(results, 1):
            icon = "❌" if not result.is_valid else "✅"
            report += f"{i}. [{result.severity}] {icon} {result.claim}\n"
            if not result.is_valid:
                report += f"   Actual: {result.actual_value}\n"
                report += f"   Confidence: {result.confidence:.0%}\n"
                report += f"   Category: {result.category}\n"
            report += "\n"

        return report


def main():
    """CLI interface for known facts manager."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Known Facts Database Manager"
    )
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--categories", action="store_true", help="List all categories")
    parser.add_argument("--check", type=str, help="Check text for fact violations")
    parser.add_argument("--get", type=str, help="Get specific fact (format: category:fact_id)")

    args = parser.parse_args()

    manager = KnownFactsManager()

    if args.stats:
        stats = manager.get_statistics()
        print(f"\n📊 Database Statistics:")
        print(f"  Version: {stats['version']}")
        print(f"  Last Updated: {stats['last_updated']}")
        print(f"  Total Categories: {stats['total_categories']}")
        print(f"  Total Facts: {stats['total_facts']}")
        print(f"\n  Facts by Category:")
        for category, count in stats['facts_by_category'].items():
            print(f"    - {category}: {count}")

    elif args.categories:
        categories = manager.list_categories()
        print(f"\n📁 Available Categories ({len(categories)}):")
        for category in categories:
            print(f"  - {category}")

    elif args.check:
        results = manager.check_text(args.check)
        print(manager.format_report(results))

    elif args.get:
        if ":" not in args.get:
            print("❌ Error: Format should be category:fact_id")
            return

        category, fact_id = args.get.split(":", 1)
        fact = manager.get_fact(fact_id, category)

        if fact:
            print(f"\n✅ Fact Found:")
            print(json.dumps(fact, indent=2))
        else:
            print(f"❌ Fact not found: {fact_id} in category {category}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
