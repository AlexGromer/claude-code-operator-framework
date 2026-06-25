#!/usr/bin/env python3
"""
Research Archive Re-evaluator

Automatically re-evaluates ARCHIVE discoveries (score <40) after aging period.
Promotes discoveries to appropriate priority if they now meet thresholds.

Version: 1.0.0
Task: TIER 2E Task 30 (GAP-RES-037)

Usage:
    # Find and re-evaluate old archives
    python research_re_evaluator.py --check

    # Re-evaluate specific discovery
    python research_re_evaluator.py --discovery "AgentDoG" --force

    # Show statistics
    python research_re_evaluator.py --stats

    # Dry run (no database changes)
    python research_re_evaluator.py --check --dry-run

Integration:
    # Anacron (monthly on 1st)
    30  10  research_archive_review  python3 ~/.claude/tools/research_re_evaluator.py --check

Workflow:
    1. Parse historical digests for ARCHIVE items >6 months old
    2. Re-score using score_discovery.py logic
    3. Compare new score with original
    4. If new score >=60: promote to gap, notify user
    5. Log all re-evaluations to database
"""

import json
import os
import re
import sys
import argparse
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
CLAUDE_DIR = Path.home() / ".claude"
DIGESTS_DIR = CLAUDE_DIR / "evaluation" / "data" / "research_digests"
SCORED_DB_PATH = CLAUDE_DIR / "evaluation" / "data" / "scored_discoveries.json"
RE_EVAL_LOG_PATH = CLAUDE_DIR / "evaluation" / "data" / "re_evaluation_log.json"
GAPS_FILE = CLAUDE_DIR / "GAPS.md"

# Thresholds
ARCHIVE_MAX_SCORE = 39
PROMOTION_MIN_SCORE = 60
DEFAULT_AGE_MONTHS = 6

# Decision thresholds (from score_discovery.py)
DECISION_THRESHOLDS = {
    "P1_CRITICAL": {"min": 80, "max": 100, "action": "Immediate PoC (<1 week)"},
    "P2_HIGH": {"min": 60, "max": 79, "action": "Planned PoC (<1 month)"},
    "P3_MEDIUM": {"min": 40, "max": 59, "action": "Backlog (<1 quarter)"},
    "ARCHIVE": {"min": 0, "max": 39, "action": "Monitor only"}
}


@dataclass
class ScoredDiscovery:
    """Scored discovery record."""
    id: str  # SHA256 hash of title + url
    title: str
    url: str
    source: str
    date_discovered: str
    original_score: float
    original_decision: str
    current_score: Optional[float] = None
    last_re_evaluation: Optional[str] = None
    re_evaluation_count: int = 0
    promoted: bool = False
    promoted_to: Optional[str] = None
    promoted_date: Optional[str] = None
    github_url: Optional[str] = None
    arxiv_id: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class ReEvaluationResult:
    """Result of re-evaluation."""
    discovery_id: str
    title: str
    original_score: float
    new_score: float
    score_delta: float
    action: str  # "NO_CHANGE", "PROMOTED", "SCORE_INCREASED", "SCORE_DECREASED"
    new_decision: str
    timestamp: str
    metrics: Dict


class ScoredDiscoveryDatabase:
    """
    Database for tracking scored discoveries.
    Uses JSON file for simplicity (could be SQLite for scale).
    """

    def __init__(self, db_path: Path = SCORED_DB_PATH):
        self.db_path = db_path
        self.discoveries: Dict[str, ScoredDiscovery] = {}
        self._load()

    def _load(self):
        """Load database from file."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    for id_, record in data.items():
                        self.discoveries[id_] = ScoredDiscovery(**record)
                logger.info(f"Loaded {len(self.discoveries)} discoveries from database")
            except Exception as e:
                logger.error(f"Error loading database: {e}")
                self.discoveries = {}
        else:
            logger.info("No existing database, starting fresh")

    def _save(self):
        """Save database to file."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w') as f:
            data = {id_: asdict(d) for id_, d in self.discoveries.items()}
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved {len(self.discoveries)} discoveries to database")

    def add_discovery(self, discovery: ScoredDiscovery) -> bool:
        """Add new discovery. Returns True if new, False if exists."""
        if discovery.id in self.discoveries:
            return False
        self.discoveries[discovery.id] = discovery
        self._save()
        return True

    def update_discovery(self, discovery: ScoredDiscovery):
        """Update existing discovery."""
        self.discoveries[discovery.id] = discovery
        self._save()

    def get_discovery(self, id_: str) -> Optional[ScoredDiscovery]:
        """Get discovery by ID."""
        return self.discoveries.get(id_)

    def get_archives_for_review(self, age_months: int = DEFAULT_AGE_MONTHS) -> List[ScoredDiscovery]:
        """
        Get ARCHIVE discoveries older than age_months that need re-evaluation.
        """
        cutoff_date = datetime.now() - timedelta(days=age_months * 30)
        archives = []

        for discovery in self.discoveries.values():
            # Skip non-archives
            if discovery.original_decision != "ARCHIVE":
                continue

            # Skip already promoted
            if discovery.promoted:
                continue

            # Check age
            try:
                date_str = discovery.date_discovered
                # Handle various date formats
                if 'T' in date_str:
                    # Full ISO format with time
                    discovered = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    # Convert to naive for comparison
                    if discovered.tzinfo is not None:
                        discovered = discovered.replace(tzinfo=None)
                else:
                    # Simple date format (YYYY-MM-DD)
                    discovered = datetime.strptime(date_str, "%Y-%m-%d")

                if discovered <= cutoff_date:
                    archives.append(discovery)
            except (ValueError, AttributeError):
                # Include if date is invalid (safer)
                archives.append(discovery)

        return archives

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        stats = {
            "total": len(self.discoveries),
            "by_decision": {},
            "promoted": 0,
            "re_evaluated": 0,
            "average_score": 0.0
        }

        total_score = 0
        for d in self.discoveries.values():
            decision = d.original_decision or "UNKNOWN"
            stats["by_decision"][decision] = stats["by_decision"].get(decision, 0) + 1

            if d.promoted:
                stats["promoted"] += 1

            if d.re_evaluation_count > 0:
                stats["re_evaluated"] += 1

            total_score += d.original_score or 0

        if stats["total"] > 0:
            stats["average_score"] = round(total_score / stats["total"], 2)

        return stats


class ArchiveReEvaluator:
    """
    Re-evaluates ARCHIVE discoveries to check for promotion.
    """

    def __init__(self, db: ScoredDiscoveryDatabase):
        self.db = db
        self.re_eval_log: List[ReEvaluationResult] = []
        self._load_log()

    def _load_log(self):
        """Load re-evaluation log."""
        if RE_EVAL_LOG_PATH.exists():
            try:
                with open(RE_EVAL_LOG_PATH, 'r') as f:
                    data = json.load(f)
                    self.re_eval_log = [ReEvaluationResult(**r) for r in data]
            except Exception as e:
                logger.error(f"Error loading re-evaluation log: {e}")

    def _save_log(self, result: ReEvaluationResult):
        """Append to re-evaluation log."""
        self.re_eval_log.append(result)
        RE_EVAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RE_EVAL_LOG_PATH, 'w') as f:
            json.dump([asdict(r) for r in self.re_eval_log], f, indent=2, default=str)

    def _generate_discovery_id(self, title: str, url: str) -> str:
        """Generate unique ID for discovery."""
        content = f"{title}|{url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_decision(self, score: float) -> str:
        """Get decision based on score."""
        for decision, thresholds in DECISION_THRESHOLDS.items():
            if thresholds["min"] <= score <= thresholds["max"]:
                return decision
        return "ARCHIVE"

    def _fetch_current_metrics(self, discovery: ScoredDiscovery) -> Dict:
        """
        Fetch current metrics for discovery.
        Uses GitHub API and Semantic Scholar.
        """
        metrics = {
            "github_stars": 0,
            "github_forks": 0,
            "citations": 0,
            "last_updated": None
        }

        # Fetch GitHub metrics
        if discovery.github_url:
            try:
                import requests
                match = re.search(r'github\.com/([^/]+)/([^/]+)', discovery.github_url)
                if match:
                    owner, repo = match.groups()
                    repo = repo.replace(".git", "")
                    api_url = f"https://api.github.com/repos/{owner}/{repo}"

                    headers = {"Accept": "application/vnd.github.v3+json"}
                    github_token = os.getenv("GITHUB_TOKEN")
                    if github_token:
                        headers["Authorization"] = f"token {github_token}"

                    response = requests.get(api_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        metrics["github_stars"] = data.get("stargazers_count", 0)
                        metrics["github_forks"] = data.get("forks_count", 0)
                        metrics["last_updated"] = data.get("updated_at")
            except Exception as e:
                logger.warning(f"GitHub API error for {discovery.github_url}: {e}")

        # Fetch citation count
        if discovery.arxiv_id:
            try:
                import requests
                api_url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{discovery.arxiv_id}"
                params = {"fields": "citationCount"}
                response = requests.get(api_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    metrics["citations"] = data.get("citationCount", 0)
            except Exception as e:
                logger.warning(f"Semantic Scholar API error for {discovery.arxiv_id}: {e}")

        return metrics

    def _calculate_new_score(self, discovery: ScoredDiscovery, metrics: Dict) -> float:
        """
        Calculate new score based on current metrics.

        Scoring adjustments based on growth:
        - GitHub stars: +0.1 per 100 stars (up to +10)
        - Citations: +2 per citation (up to +20)
        - Activity: +5 if updated in last 3 months
        """
        base_score = discovery.original_score or 0

        # GitHub stars bonus (adoption velocity)
        stars = metrics.get("github_stars", 0)
        star_bonus = min(10, stars / 100 * 0.1)

        # Citations bonus (academic validation)
        citations = metrics.get("citations", 0)
        citation_bonus = min(20, citations * 2)

        # Recent activity bonus
        activity_bonus = 0
        last_updated = metrics.get("last_updated")
        if last_updated:
            try:
                updated_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) - updated_date < timedelta(days=90):
                    activity_bonus = 5
            except ValueError:
                pass

        # Calculate new score
        new_score = base_score + star_bonus + citation_bonus + activity_bonus

        # Cap at 100
        return min(100, round(new_score, 2))

    def re_evaluate_discovery(
        self,
        discovery: ScoredDiscovery,
        dry_run: bool = False
    ) -> ReEvaluationResult:
        """
        Re-evaluate a single discovery.

        Args:
            discovery: Discovery to re-evaluate
            dry_run: If True, don't update database

        Returns:
            ReEvaluationResult with evaluation details
        """
        logger.info(f"Re-evaluating: {discovery.title}")

        # Fetch current metrics
        metrics = self._fetch_current_metrics(discovery)

        # Calculate new score
        new_score = self._calculate_new_score(discovery, metrics)
        new_decision = self._get_decision(new_score)
        score_delta = new_score - (discovery.original_score or 0)

        # Determine action
        if new_score >= PROMOTION_MIN_SCORE and not discovery.promoted:
            action = "PROMOTED"
        elif score_delta > 10:
            action = "SCORE_INCREASED"
        elif score_delta < -10:
            action = "SCORE_DECREASED"
        else:
            action = "NO_CHANGE"

        # Create result
        result = ReEvaluationResult(
            discovery_id=discovery.id,
            title=discovery.title,
            original_score=discovery.original_score or 0,
            new_score=new_score,
            score_delta=score_delta,
            action=action,
            new_decision=new_decision,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metrics=metrics
        )

        if not dry_run:
            # Update discovery record
            discovery.current_score = new_score
            discovery.last_re_evaluation = result.timestamp
            discovery.re_evaluation_count += 1

            if action == "PROMOTED":
                discovery.promoted = True
                discovery.promoted_to = new_decision
                discovery.promoted_date = result.timestamp
                logger.info(f"PROMOTED: {discovery.title} ({discovery.original_score} -> {new_score})")
                self._create_promotion_notification(discovery, result)

            self.db.update_discovery(discovery)
            self._save_log(result)

        return result

    def _create_promotion_notification(
        self,
        discovery: ScoredDiscovery,
        result: ReEvaluationResult
    ):
        """
        Create notification for promoted discovery.
        Could integrate with GAPS.md, create issue, send notification, etc.
        """
        notification = f"""
================================================================================
DISCOVERY PROMOTED: {discovery.title}
================================================================================
Original Score: {discovery.original_score:.1f} (ARCHIVE)
New Score:      {result.new_score:.1f} ({result.new_decision})
Score Delta:    +{result.score_delta:.1f}

Metrics:
  - GitHub Stars: {result.metrics.get('github_stars', 'N/A')}
  - Citations:    {result.metrics.get('citations', 'N/A')}

URL: {discovery.url}

ACTION REQUIRED: Review for gap creation
================================================================================
"""
        logger.info(notification)

        # Optionally append to a promotions log file
        promotions_log = CLAUDE_DIR / "evaluation" / "data" / "promotions.log"
        with open(promotions_log, 'a') as f:
            f.write(f"\n{datetime.now().isoformat()}\n{notification}")

    def check_all_archives(
        self,
        age_months: int = DEFAULT_AGE_MONTHS,
        dry_run: bool = False
    ) -> List[ReEvaluationResult]:
        """
        Check all ARCHIVE discoveries that are old enough for re-evaluation.

        Args:
            age_months: Minimum age in months
            dry_run: If True, don't update database

        Returns:
            List of ReEvaluationResult
        """
        archives = self.db.get_archives_for_review(age_months)
        logger.info(f"Found {len(archives)} ARCHIVE discoveries for re-evaluation")

        results = []
        for discovery in archives:
            try:
                result = self.re_evaluate_discovery(discovery, dry_run)
                results.append(result)
            except Exception as e:
                logger.error(f"Error re-evaluating {discovery.title}: {e}")

        # Summary
        promoted = sum(1 for r in results if r.action == "PROMOTED")
        increased = sum(1 for r in results if r.action == "SCORE_INCREASED")
        decreased = sum(1 for r in results if r.action == "SCORE_DECREASED")
        no_change = sum(1 for r in results if r.action == "NO_CHANGE")

        logger.info(f"""
Re-evaluation Summary:
  - Total checked: {len(results)}
  - Promoted: {promoted}
  - Score increased: {increased}
  - Score decreased: {decreased}
  - No change: {no_change}
""")

        return results


class DigestParser:
    """
    Parses research digests to extract discovery entries.
    """

    def __init__(self, digests_dir: Path = DIGESTS_DIR):
        self.digests_dir = digests_dir

    def parse_digest(self, digest_path: Path) -> List[Dict]:
        """
        Parse a single digest file for discovery entries.

        Returns list of discovery dictionaries.
        """
        discoveries = []
        current_entry = None

        with open(digest_path, 'r') as f:
            content = f.read()

        # Parse entries (format: - **Title** followed by metadata)
        entry_pattern = re.compile(
            r'- \*\*(.+?)\*\*\n'
            r'  - .* \[(https?://[^\]]+)\]\([^\)]+\)\n'
            r'  - .* (\d{4}-\d{2}-\d{2})\n'
            r'  - .* Source: (\w+)\n'
            r'  - .* (.+?)(?:\n|$)',
            re.MULTILINE
        )

        for match in entry_pattern.finditer(content):
            title, url, date, source, description = match.groups()
            discoveries.append({
                "title": title.strip(),
                "url": url.strip(),
                "date_discovered": date.strip(),
                "source": source.strip(),
                "description": description.strip()[:200]
            })

        return discoveries

    def get_all_digests(self) -> List[Path]:
        """Get all digest files sorted by date."""
        if not self.digests_dir.exists():
            return []
        return sorted(self.digests_dir.glob("digest_*.md"))


def import_from_digests(
    db: ScoredDiscoveryDatabase,
    parser: DigestParser,
    score_all: bool = False
):
    """
    Import discoveries from digest files into database.

    Args:
        db: Database to import into
        parser: Digest parser
        score_all: If True, score all discoveries (expensive)
    """
    digests = parser.get_all_digests()
    logger.info(f"Found {len(digests)} digest files")

    imported = 0
    skipped = 0

    for digest_path in digests:
        logger.info(f"Parsing: {digest_path.name}")
        discoveries = parser.parse_digest(digest_path)

        for d in discoveries:
            discovery_id = hashlib.sha256(
                f"{d['title']}|{d['url']}".encode()
            ).hexdigest()[:16]

            if discovery_id in db.discoveries:
                skipped += 1
                continue

            # Create discovery record
            # Default to ARCHIVE score (need manual scoring for accurate)
            discovery = ScoredDiscovery(
                id=discovery_id,
                title=d["title"],
                url=d["url"],
                source=d["source"],
                date_discovered=d["date_discovered"],
                original_score=20.0,  # Default low score
                original_decision="ARCHIVE",  # Default to archive
                github_url=d["url"] if "github.com" in d["url"] else None,
                arxiv_id=extract_arxiv_id(d["url"]) if "arxiv.org" in d["url"] else None
            )

            db.add_discovery(discovery)
            imported += 1

    logger.info(f"Imported {imported} discoveries, skipped {skipped} existing")


def extract_arxiv_id(url: str) -> Optional[str]:
    """Extract arXiv ID from URL."""
    match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', url)
    return match.group(1) if match else None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Research Archive Re-evaluator"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check and re-evaluate old ARCHIVE discoveries"
    )
    parser.add_argument(
        "--discovery", "-d",
        help="Re-evaluate specific discovery by title (partial match)"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show database statistics"
    )
    parser.add_argument(
        "--import-digests",
        action="store_true",
        help="Import discoveries from digest files"
    )
    parser.add_argument(
        "--age-months",
        type=int,
        default=DEFAULT_AGE_MONTHS,
        help=f"Minimum age in months for re-evaluation (default: {DEFAULT_AGE_MONTHS})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (no database changes)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-evaluation regardless of age"
    )

    args = parser.parse_args()

    # Initialize database
    db = ScoredDiscoveryDatabase()
    evaluator = ArchiveReEvaluator(db)
    digest_parser = DigestParser()

    # Import digests if requested
    if args.import_digests:
        import_from_digests(db, digest_parser)
        return

    # Show statistics
    if args.stats:
        stats = db.get_statistics()
        print("[SCORED DISCOVERIES DATABASE STATISTICS]")
        print(f"  Total discoveries: {stats['total']}")
        print(f"  Average score: {stats['average_score']}")
        print(f"  Promoted: {stats['promoted']}")
        print(f"  Re-evaluated: {stats['re_evaluated']}")
        print("\n  By decision:")
        for decision, count in sorted(stats["by_decision"].items()):
            print(f"    - {decision}: {count}")
        return

    # Re-evaluate specific discovery
    if args.discovery:
        # Find by title (partial match)
        found = None
        for d in db.discoveries.values():
            if args.discovery.lower() in d.title.lower():
                found = d
                break

        if not found:
            print(f"Discovery not found: {args.discovery}")
            sys.exit(1)

        result = evaluator.re_evaluate_discovery(found, args.dry_run)
        print(f"\n[RE-EVALUATION RESULT]")
        print(f"  Title: {result.title}")
        print(f"  Original Score: {result.original_score}")
        print(f"  New Score: {result.new_score}")
        print(f"  Delta: {result.score_delta:+.1f}")
        print(f"  Decision: {result.new_decision}")
        print(f"  Action: {result.action}")
        print(f"\n  Metrics:")
        for k, v in result.metrics.items():
            print(f"    - {k}: {v}")
        return

    # Check all archives
    if args.check:
        age = 0 if args.force else args.age_months
        results = evaluator.check_all_archives(age, args.dry_run)

        if results:
            print("\n[RE-EVALUATION RESULTS]")
            for r in results:
                status = f"[{r.action}]"
                print(f"  {status:15} {r.title[:50]:50} {r.original_score:5.1f} -> {r.new_score:5.1f} ({r.score_delta:+.1f})")
        else:
            print("No ARCHIVE discoveries found for re-evaluation")
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
