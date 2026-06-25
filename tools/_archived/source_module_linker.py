#!/usr/bin/env python3
"""
Source-Module Linker (GAP-DOM-008)

Map sources to modules they inform:
- Link sources to module sections
- Track which modules reference which sources
- Find modules without source backing (orphans)
- Generate source citation reports

Usage:
    python source_module_linker.py --link <source> <module> --section "Section Name"
    python source_module_linker.py --report
    python source_module_linker.py --orphans
    python source_module_linker.py --coverage
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import re

# Import source registry
sys.path.insert(0, str(Path(__file__).parent))
from source_registry import (
    load_registry, lookup_source, normalize_url
)

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LINKS_FILE = DATA_DIR / "source_module_links.json"
CLAUDE_DIR = Path.home() / ".claude"
MODULES_DIR = CLAUDE_DIR / "modules"


@dataclass
class SourceModuleLink:
    """Source-to-module link."""
    link_id: str
    source_url: str
    module_path: str
    section: str
    linked_at: str
    metadata: Dict


class SourceModuleLinker:
    """Link sources to modules they inform."""

    def __init__(self):
        """Initialize linker."""
        self.links = self._load_links()
        self.source_registry = load_registry()

    def _load_links(self) -> Dict:
        """Load links from file."""
        if LINKS_FILE.exists():
            return json.loads(LINKS_FILE.read_text())

        return {
            "links": {},
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
        }

    def _save_links(self):
        """Save links to file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.links["last_updated"] = datetime.now().isoformat()
        with open(LINKS_FILE, "w") as f:
            json.dump(self.links, f, indent=2)

    def _generate_link_id(self) -> str:
        """Generate unique link ID."""
        import hashlib
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:12]

    def link(
        self,
        source_url: str,
        module_path: str,
        section: str = "",
        metadata: Dict = None
    ) -> Dict:
        """
        Create link between source and module.

        Args:
            source_url: Source URL
            module_path: Path to module file
            section: Section name in module (optional)
            metadata: Additional metadata (optional)

        Returns:
            Link result dict
        """
        # Normalize source URL
        normalized_url = normalize_url(source_url)

        # Verify source exists in registry
        source = lookup_source(normalized_url)
        if not source:
            return {
                "success": False,
                "error": f"Source not in registry: {normalized_url}"
            }

        # Verify module exists
        module_full_path = Path(module_path).expanduser()
        if not module_full_path.exists():
            return {
                "success": False,
                "error": f"Module not found: {module_path}"
            }

        # Generate link ID
        link_id = self._generate_link_id()

        # Create link
        link = SourceModuleLink(
            link_id=link_id,
            source_url=normalized_url,
            module_path=str(module_full_path),
            section=section,
            linked_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        # Store link
        self.links["links"][link_id] = asdict(link)
        self._save_links()

        return {
            "success": True,
            "link_id": link_id,
            "source_url": normalized_url,
            "module_path": str(module_full_path),
            "section": section,
        }

    def get_module_sources(self, module_path: str) -> List[Dict]:
        """
        Get all sources linked to a module.

        Args:
            module_path: Path to module file

        Returns:
            List of linked sources
        """
        module_full_path = str(Path(module_path).expanduser())

        sources = []
        for link_id, link in self.links["links"].items():
            if link["module_path"] == module_full_path:
                # Get source details from registry
                source = lookup_source(link["source_url"])
                if source:
                    sources.append({
                        "url": link["source_url"],
                        "section": link["section"],
                        "tier": source.get("tier", "TIER_4"),
                        "quality_score": source.get("quality_score", 0.0),
                        "linked_at": link["linked_at"],
                    })

        return sources

    def get_source_modules(self, source_url: str) -> List[str]:
        """
        Get all modules that reference a source.

        Args:
            source_url: Source URL

        Returns:
            List of module paths
        """
        normalized_url = normalize_url(source_url)

        modules = []
        for link_id, link in self.links["links"].items():
            if link["source_url"] == normalized_url:
                modules.append(link["module_path"])

        return list(set(modules))  # Remove duplicates

    def find_orphaned_modules(self) -> List[Dict]:
        """
        Find modules without source backing.

        Returns:
            List of orphaned modules
        """
        if not MODULES_DIR.exists():
            return []

        # Get all module files
        all_modules = list(MODULES_DIR.glob("*.md"))

        # Get modules with links
        linked_modules = set()
        for link in self.links["links"].values():
            linked_modules.add(link["module_path"])

        # Find orphans
        orphans = []
        for module in all_modules:
            module_path = str(module)
            if module_path not in linked_modules:
                orphans.append({
                    "module_path": module_path,
                    "module_name": module.name,
                    "size_bytes": module.stat().st_size,
                })

        return orphans

    def generate_coverage_report(self) -> Dict:
        """
        Generate source coverage report.

        Returns:
            Coverage report dict
        """
        if not MODULES_DIR.exists():
            return {"error": "Modules directory not found"}

        all_modules = list(MODULES_DIR.glob("*.md"))
        total_modules = len(all_modules)

        # Count modules with sources
        modules_with_sources = set()
        for link in self.links["links"].values():
            modules_with_sources.add(link["module_path"])

        modules_with_sources_count = len(modules_with_sources)

        # Calculate coverage
        coverage_percentage = 0.0
        if total_modules > 0:
            coverage_percentage = round(
                (modules_with_sources_count / total_modules) * 100, 2
            )

        # Source distribution by tier
        source_tier_distribution = {}
        for link in self.links["links"].values():
            source = lookup_source(link["source_url"])
            if source:
                tier = source.get("tier", "TIER_4")
                source_tier_distribution[tier] = source_tier_distribution.get(tier, 0) + 1

        report = {
            "total_modules": total_modules,
            "modules_with_sources": modules_with_sources_count,
            "modules_without_sources": total_modules - modules_with_sources_count,
            "coverage_percentage": coverage_percentage,
            "total_links": len(self.links["links"]),
            "source_tier_distribution": source_tier_distribution,
            "orphaned_modules": self.find_orphaned_modules(),
        }

        return report

    def remove_link(self, link_id: str) -> bool:
        """
        Remove source-module link.

        Args:
            link_id: Link ID to remove

        Returns:
            True if removed, False if not found
        """
        if link_id in self.links["links"]:
            del self.links["links"][link_id]
            self._save_links()
            return True

        return False

    def scan_module_for_sources(self, module_path: str) -> List[str]:
        """
        Scan module file for source URLs (auto-detect citations).

        Args:
            module_path: Path to module file

        Returns:
            List of URLs found in module
        """
        module_file = Path(module_path).expanduser()
        if not module_file.exists():
            return []

        content = module_file.read_text()

        # Extract URLs using regex
        url_pattern = r'https?://[^\s\)\]<>]+'
        urls = re.findall(url_pattern, content)

        # Normalize and deduplicate
        normalized_urls = list(set(normalize_url(url) for url in urls))

        return normalized_urls


def link_source_to_module(
    source_url: str,
    module_path: str,
    section: str = ""
) -> Dict:
    """
    Link source to module (convenience function).

    Args:
        source_url: Source URL
        module_path: Module file path
        section: Section name (optional)

    Returns:
        Link result dict
    """
    linker = SourceModuleLinker()
    return linker.link(source_url, module_path, section)


def get_module_sources(module_path: str) -> List[Dict]:
    """
    Get sources for module (convenience function).

    Args:
        module_path: Module file path

    Returns:
        List of sources
    """
    linker = SourceModuleLinker()
    return linker.get_module_sources(module_path)


def find_orphaned_modules() -> List[Dict]:
    """
    Find orphaned modules (convenience function).

    Returns:
        List of orphaned modules
    """
    linker = SourceModuleLinker()
    return linker.find_orphaned_modules()


def print_coverage_report(report: Dict):
    """Print coverage report in formatted output."""
    print("\n" + "="*70)
    print("SOURCE-MODULE COVERAGE REPORT")
    print("="*70)

    print(f"\nTotal Modules: {report['total_modules']}")
    print(f"Modules with Sources: {report['modules_with_sources']}")
    print(f"Modules without Sources: {report['modules_without_sources']}")
    print(f"Coverage: {report['coverage_percentage']:.1f}%")

    print(f"\nTotal Links: {report['total_links']}")

    print("\nSource Tier Distribution:")
    for tier, count in report.get("source_tier_distribution", {}).items():
        print(f"  {tier}: {count} links")

    if report.get("orphaned_modules"):
        print(f"\nOrphaned Modules ({len(report['orphaned_modules'])}):")
        for orphan in report["orphaned_modules"]:
            print(f"  - {orphan['module_name']}")

    print("\n" + "="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Source-Module Linker")
    parser.add_argument("--link", help="Link source to module (provide source URL)")
    parser.add_argument("--module", help="Module path (for --link)")
    parser.add_argument("--section", help="Section name (optional, for --link)")
    parser.add_argument("--sources", help="Show sources for module")
    parser.add_argument("--modules", help="Show modules for source URL")
    parser.add_argument("--orphans", action="store_true", help="Show orphaned modules")
    parser.add_argument("--coverage", action="store_true", help="Show coverage report")
    parser.add_argument("--report", action="store_true", help="Alias for --coverage")
    parser.add_argument("--scan", help="Scan module for source URLs")
    parser.add_argument("--remove", help="Remove link by ID")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    linker = SourceModuleLinker()

    if args.link:
        if not args.module:
            print("❌ Error: --module required with --link", file=sys.stderr)
            return 1

        result = linker.link(args.link, args.module, args.section or "")

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"✅ Linked: {result['source_url']}")
                print(f"   Module: {result['module_path']}")
                if result.get("section"):
                    print(f"   Section: {result['section']}")
                print(f"   Link ID: {result['link_id']}")
            else:
                print(f"❌ Error: {result['error']}")

        return 0

    if args.sources:
        sources = linker.get_module_sources(args.sources)

        if args.json:
            print(json.dumps(sources, indent=2))
        else:
            print(f"\nSources for {Path(args.sources).name}:\n")
            if sources:
                for source in sources:
                    print(f"  - {source['url']}")
                    print(f"    Tier: {source['tier']}, Quality: {source['quality_score']}")
                    if source.get('section'):
                        print(f"    Section: {source['section']}")
            else:
                print("  No sources linked")

        return 0

    if args.modules:
        modules = linker.get_source_modules(args.modules)

        if args.json:
            print(json.dumps(modules, indent=2))
        else:
            print(f"\nModules referencing {args.modules}:\n")
            if modules:
                for module in modules:
                    print(f"  - {module}")
            else:
                print("  No modules linked")

        return 0

    if args.orphans:
        orphans = linker.find_orphaned_modules()

        if args.json:
            print(json.dumps(orphans, indent=2))
        else:
            print(f"\nOrphaned Modules ({len(orphans)}):\n")
            if orphans:
                for orphan in orphans:
                    print(f"  - {orphan['module_name']} ({orphan['size_bytes']} bytes)")
            else:
                print("  No orphaned modules found")

        return 0

    if args.coverage or args.report:
        report = linker.generate_coverage_report()

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print_coverage_report(report)

        return 0

    if args.scan:
        urls = linker.scan_module_for_sources(args.scan)

        if args.json:
            print(json.dumps(urls, indent=2))
        else:
            print(f"\nURLs found in {Path(args.scan).name}:\n")
            if urls:
                for url in urls:
                    print(f"  - {url}")
            else:
                print("  No URLs found")

        return 0

    if args.remove:
        success = linker.remove_link(args.remove)

        if args.json:
            print(json.dumps({"success": success, "link_id": args.remove}, indent=2))
        else:
            if success:
                print(f"✅ Removed link: {args.remove}")
            else:
                print(f"❌ Link not found: {args.remove}")

        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
