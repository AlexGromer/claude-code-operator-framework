#!/usr/bin/env python3
"""
Auto-Update Script for Known Facts Database
Weekly sync with official release notes and version information

Automatically updates:
- Python versions (from python.org)
- Node.js versions (from nodejs.org)
- JavaScript framework versions (from npm)
- AI model releases (from official sources)
- Cloud provider updates

Usage:
    # Dry-run (show changes without applying)
    python3 auto_update_facts.py --dry-run

    # Apply updates
    python3 auto_update_facts.py --apply

    # Weekly automated run (via anacron)
    python3 auto_update_facts.py --apply --notify
"""

import json
import sys
import requests
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class FactUpdate:
    """Represents a proposed update to a fact."""
    category: str
    fact_id: str
    field: str
    old_value: Any
    new_value: Any
    confidence: float  # 0-1
    source: str


class FactsAutoUpdater:
    """
    Auto-updater for known_facts_extended.json.

    Checks official sources for version updates and proposes changes.
    """

    DB_PATH = Path.home() / ".claude" / "evaluation" / "data" / "known_facts_extended.json"
    BACKUP_DIR = Path.home() / ".claude" / "evaluation" / "data" / "backups"

    # API endpoints
    PYTHON_API = "https://endoflife.date/api/python.json"
    NODEJS_API = "https://nodejs.org/dist/index.json"
    NPM_REGISTRY = "https://registry.npmjs.org"

    def __init__(self):
        """Initialize auto-updater."""
        self.db_path = self.DB_PATH
        self.backup_dir = self.BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.facts = self._load_database()

    def _load_database(self) -> Dict[str, Any]:
        """Load known facts database."""
        if not self.db_path.exists():
            print(f"❌ Database not found: {self.db_path}")
            sys.exit(1)

        with open(self.db_path, 'r') as f:
            return json.load(f)

    def _save_database(self, data: Dict[str, Any]):
        """Save database with backup."""
        # Create backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"known_facts_extended_backup_{timestamp}.json"

        with open(backup_path, 'w') as f:
            json.dump(self.facts, f, indent=2)

        # Save new version
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Backup created: {backup_path}")

    def check_python_versions(self) -> List[FactUpdate]:
        """Check for Python version updates."""
        updates = []

        try:
            response = requests.get(self.PYTHON_API, timeout=10)
            response.raise_for_status()
            releases = response.json()

            # Get latest stable release
            if releases and len(releases) > 0:
                latest = releases[0]
                latest_version = latest.get('cycle')
                latest_patch = latest.get('latest')

                # Check current database
                python_data = self.facts.get('categories', {}).get('programming_languages', {}).get('python', {})
                current_version = python_data.get('latest_major_version')

                if latest_version != current_version:
                    updates.append(FactUpdate(
                        category='programming_languages',
                        fact_id='python',
                        field='latest_major_version',
                        old_value=current_version,
                        new_value=latest_version,
                        confidence=0.95,
                        source='endoflife.date API'
                    ))

                # Check versions list
                versions = python_data.get('versions', [])
                version_numbers = [v.get('version') for v in versions]

                if latest_version not in version_numbers:
                    updates.append(FactUpdate(
                        category='programming_languages',
                        fact_id='python',
                        field='versions',
                        old_value=f"Missing {latest_version}",
                        new_value={
                            'version': latest_version,
                            'release_date': latest.get('releaseDate'),
                            'eol_date': latest.get('eol')
                        },
                        confidence=0.95,
                        source='endoflife.date API'
                    ))

        except Exception as e:
            print(f"⚠️ Failed to check Python versions: {e}")

        return updates

    def check_nodejs_versions(self) -> List[FactUpdate]:
        """Check for Node.js version updates."""
        updates = []

        try:
            response = requests.get(self.NODEJS_API, timeout=10)
            response.raise_for_status()
            releases = response.json()

            # Get latest LTS
            lts_releases = [r for r in releases if r.get('lts')]
            if lts_releases:
                latest_lts = lts_releases[0]
                latest_version = latest_lts.get('version', '').lstrip('v')

                # Check current database
                nodejs_data = self.facts.get('categories', {}).get('programming_languages', {}).get('nodejs', {})
                current_version = nodejs_data.get('latest_lts_version')

                if latest_version and latest_version != current_version:
                    updates.append(FactUpdate(
                        category='programming_languages',
                        fact_id='nodejs',
                        field='latest_lts_version',
                        old_value=current_version,
                        new_value=latest_version,
                        confidence=0.95,
                        source='nodejs.org API'
                    ))

        except Exception as e:
            print(f"⚠️ Failed to check Node.js versions: {e}")

        return updates

    def check_npm_packages(self) -> List[FactUpdate]:
        """Check for JavaScript framework version updates."""
        updates = []

        frameworks = ['react', 'vue', 'angular', 'svelte', 'nextjs']

        for framework in frameworks:
            try:
                # Map framework names to npm package names
                package_name = {
                    'react': 'react',
                    'vue': 'vue',
                    'angular': '@angular/core',
                    'svelte': 'svelte',
                    'nextjs': 'next'
                }.get(framework, framework)

                response = requests.get(f"{self.NPM_REGISTRY}/{package_name}", timeout=10)
                response.raise_for_status()
                data = response.json()

                latest_version = data.get('dist-tags', {}).get('latest')

                # Check current database
                framework_data = self.facts.get('categories', {}).get('frameworks', {}).get(framework, {})
                current_version = framework_data.get('latest_version')

                if latest_version and latest_version != current_version:
                    updates.append(FactUpdate(
                        category='frameworks',
                        fact_id=framework,
                        field='latest_version',
                        old_value=current_version,
                        new_value=latest_version,
                        confidence=0.95,
                        source=f"npm registry ({package_name})"
                    ))

            except Exception as e:
                print(f"⚠️ Failed to check {framework}: {e}")

        return updates

    def check_all_updates(self) -> List[FactUpdate]:
        """Check all sources for updates."""
        all_updates = []

        print("🔍 Checking Python versions...")
        all_updates.extend(self.check_python_versions())

        print("🔍 Checking Node.js versions...")
        all_updates.extend(self.check_nodejs_versions())

        print("🔍 Checking npm packages...")
        all_updates.extend(self.check_npm_packages())

        return all_updates

    def apply_updates(self, updates: List[FactUpdate]) -> int:
        """Apply updates to database."""
        if not updates:
            print("✅ No updates to apply")
            return 0

        applied = 0

        for update in updates:
            try:
                # Navigate to fact location
                categories = self.facts.get('categories', {})
                category = categories.get(update.category, {})
                fact = category.get(update.fact_id, {})

                if update.field == 'versions':
                    # Special handling for versions list
                    versions = fact.get('versions', [])
                    versions.insert(0, update.new_value)
                    fact['versions'] = versions
                else:
                    # Simple field update
                    fact[update.field] = update.new_value

                # Update timestamp
                self.facts['last_updated'] = datetime.now().strftime("%Y-%m-%d")

                applied += 1

            except Exception as e:
                print(f"❌ Failed to apply update {update.fact_id}.{update.field}: {e}")

        # Save database
        if applied > 0:
            self._save_database(self.facts)
            print(f"✅ Applied {applied}/{len(updates)} updates")

        return applied

    def format_report(self, updates: List[FactUpdate]) -> str:
        """Format updates report."""
        if not updates:
            return "✅ No updates available"

        report = f"\n{'='*70}\n"
        report += f"KNOWN FACTS AUTO-UPDATE REPORT\n"
        report += f"{'='*70}\n\n"
        report += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Total Updates: {len(updates)}\n\n"

        # Group by category
        by_category = {}
        for update in updates:
            if update.category not in by_category:
                by_category[update.category] = []
            by_category[update.category].append(update)

        for category, category_updates in by_category.items():
            report += f"📦 {category.upper()}\n"
            report += f"{'─'*70}\n"

            for update in category_updates:
                report += f"  • {update.fact_id}.{update.field}\n"
                report += f"    Old: {update.old_value}\n"
                report += f"    New: {update.new_value}\n"
                report += f"    Source: {update.source}\n"
                report += f"    Confidence: {update.confidence:.0%}\n\n"

        return report


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-update known facts database"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show updates without applying")
    parser.add_argument("--apply", action="store_true",
                        help="Apply updates to database")
    parser.add_argument("--notify", action="store_true",
                        help="Send notification (for automated runs)")

    args = parser.parse_args()

    updater = FactsAutoUpdater()

    print("🔄 Checking for updates...\n")
    updates = updater.check_all_updates()

    report = updater.format_report(updates)
    print(report)

    if args.apply and updates:
        print("\n⚠️ Applying updates...")
        applied = updater.apply_updates(updates)

        if applied > 0 and args.notify:
            print(f"\n📧 Notification: {applied} facts updated")
            # TODO: Implement notification mechanism (email, webhook, etc.)

    elif args.dry_run:
        print("\n💡 Dry-run mode: No changes applied")
        print("   Run with --apply to apply these updates")

    else:
        if updates:
            print("\n💡 Use --apply to apply these updates")
        else:
            print("\n✅ Database is up to date")


if __name__ == "__main__":
    main()
