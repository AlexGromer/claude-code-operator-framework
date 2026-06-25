#!/usr/bin/env python3
"""
Web Validation Module for Known Facts
Extension for hallucination_detector.py and known_facts_manager.py

Provides web-based validation for:
- arXiv IDs (via arXiv API)
- DOIs (via CrossRef API)
- Python/Node.js version releases (via official APIs)

Usage:
    from web_validator import WebValidator

    validator = WebValidator()

    # Validate arXiv ID
    result = validator.validate_arxiv("2301.12345")
    # Returns: {'valid': True, 'title': '...', 'authors': [...], ...}

    # Validate DOI
    result = validator.validate_doi("10.1038/s41586-021-03819-2")

    # Check latest Python version
    result = validator.get_latest_python_version()
    # Returns: {'version': '3.13.1', 'release_date': '2024-12-03'}
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of web validation."""
    source: str  # 'arxiv', 'doi', 'python', 'nodejs'
    identifier: str
    is_valid: bool
    confidence: float  # 0-1
    metadata: Dict[str, Any]
    error: Optional[str] = None
    response_time_ms: int = 0


class WebValidator:
    """
    Web-based validator for known facts.

    Uses public APIs to validate:
    - arXiv papers (arXiv.org API)
    - DOIs (CrossRef API)
    - Python versions (python.org JSON API)
    - Node.js versions (nodejs.org JSON API)
    """

    # API endpoints
    ARXIV_API = "http://export.arxiv.org/api/query"
    CROSSREF_API = "https://api.crossref.org/works"
    PYTHON_RELEASES_API = "https://www.python.org/api/v2/downloads/release/"
    NODEJS_RELEASES_API = "https://nodejs.org/dist/index.json"

    # Cache settings
    CACHE_DIR = Path.home() / ".claude" / "evaluation" / "data" / "cache"
    CACHE_TTL = 86400  # 24 hours

    def __init__(self, use_cache: bool = True):
        """Initialize validator with optional caching."""
        self.use_cache = use_cache
        self.cache_dir = self.CACHE_DIR
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, source: str, identifier: str) -> Path:
        """Get cache file path for given source and identifier."""
        safe_id = identifier.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{source}_{safe_id}.json"

    def _read_cache(self, source: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Read from cache if available and not expired."""
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(source, identifier)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)

            # Check TTL
            cached_time = cached.get('cached_at', 0)
            if time.time() - cached_time > self.CACHE_TTL:
                return None

            return cached.get('data')
        except (json.JSONDecodeError, IOError):
            return None

    def _write_cache(self, source: str, identifier: str, data: Dict[str, Any]):
        """Write to cache."""
        if not self.use_cache:
            return

        cache_path = self._get_cache_path(source, identifier)
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    'cached_at': time.time(),
                    'data': data
                }, f, indent=2)
        except IOError:
            pass

    def validate_arxiv(self, arxiv_id: str) -> ValidationResult:
        """
        Validate arXiv paper ID.

        Args:
            arxiv_id: arXiv ID (e.g., "2301.12345" or "cs.AI/0601001")

        Returns:
            ValidationResult with paper metadata
        """
        start = time.time()

        # Check cache
        cached = self._read_cache('arxiv', arxiv_id)
        if cached:
            return ValidationResult(
                source='arxiv',
                identifier=arxiv_id,
                is_valid=True,
                confidence=1.0,
                metadata=cached,
                response_time_ms=int((time.time() - start) * 1000)
            )

        try:
            # Query arXiv API
            response = requests.get(
                self.ARXIV_API,
                params={'id_list': arxiv_id, 'max_results': 1},
                timeout=10
            )
            response.raise_for_status()

            # Parse XML response (simplified - arXiv returns Atom XML)
            content = response.text

            # Check if paper found
            if '<entry>' not in content:
                return ValidationResult(
                    source='arxiv',
                    identifier=arxiv_id,
                    is_valid=False,
                    confidence=0.95,
                    metadata={},
                    error="arXiv ID not found",
                    response_time_ms=int((time.time() - start) * 1000)
                )

            # Extract metadata (simplified XML parsing)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)

            # arXiv uses Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)

            if entry is None:
                return ValidationResult(
                    source='arxiv',
                    identifier=arxiv_id,
                    is_valid=False,
                    confidence=0.9,
                    metadata={},
                    error="Could not parse arXiv response",
                    response_time_ms=int((time.time() - start) * 1000)
                )

            title = entry.find('atom:title', ns)
            published = entry.find('atom:published', ns)
            authors = entry.findall('atom:author', ns)

            metadata = {
                'title': title.text.strip() if title is not None else '',
                'published': published.text if published is not None else '',
                'authors': [
                    author.find('atom:name', ns).text
                    for author in authors
                    if author.find('atom:name', ns) is not None
                ],
                'url': f"https://arxiv.org/abs/{arxiv_id}"
            }

            # Cache result
            self._write_cache('arxiv', arxiv_id, metadata)

            return ValidationResult(
                source='arxiv',
                identifier=arxiv_id,
                is_valid=True,
                confidence=1.0,
                metadata=metadata,
                response_time_ms=int((time.time() - start) * 1000)
            )

        except requests.RequestException as e:
            return ValidationResult(
                source='arxiv',
                identifier=arxiv_id,
                is_valid=False,
                confidence=0.5,
                metadata={},
                error=f"API request failed: {str(e)}",
                response_time_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return ValidationResult(
                source='arxiv',
                identifier=arxiv_id,
                is_valid=False,
                confidence=0.3,
                metadata={},
                error=f"Validation failed: {str(e)}",
                response_time_ms=int((time.time() - start) * 1000)
            )

    def validate_doi(self, doi: str) -> ValidationResult:
        """
        Validate DOI via CrossRef API.

        Args:
            doi: DOI identifier (e.g., "10.1038/s41586-021-03819-2")

        Returns:
            ValidationResult with paper metadata
        """
        start = time.time()

        # Check cache
        cached = self._read_cache('doi', doi)
        if cached:
            return ValidationResult(
                source='doi',
                identifier=doi,
                is_valid=True,
                confidence=1.0,
                metadata=cached,
                response_time_ms=int((time.time() - start) * 1000)
            )

        try:
            # Query CrossRef API
            response = requests.get(
                f"{self.CROSSREF_API}/{doi}",
                timeout=10
            )

            if response.status_code == 404:
                return ValidationResult(
                    source='doi',
                    identifier=doi,
                    is_valid=False,
                    confidence=0.95,
                    metadata={},
                    error="DOI not found",
                    response_time_ms=int((time.time() - start) * 1000)
                )

            response.raise_for_status()
            data = response.json()

            message = data.get('message', {})

            metadata = {
                'title': message.get('title', [''])[0] if message.get('title') else '',
                'authors': [
                    f"{a.get('given', '')} {a.get('family', '')}"
                    for a in message.get('author', [])
                ],
                'published': message.get('published', {}).get('date-parts', [[]])[0],
                'journal': message.get('container-title', [''])[0] if message.get('container-title') else '',
                'url': message.get('URL', f"https://doi.org/{doi}")
            }

            # Cache result
            self._write_cache('doi', doi, metadata)

            return ValidationResult(
                source='doi',
                identifier=doi,
                is_valid=True,
                confidence=1.0,
                metadata=metadata,
                response_time_ms=int((time.time() - start) * 1000)
            )

        except requests.RequestException as e:
            return ValidationResult(
                source='doi',
                identifier=doi,
                is_valid=False,
                confidence=0.5,
                metadata={},
                error=f"API request failed: {str(e)}",
                response_time_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return ValidationResult(
                source='doi',
                identifier=doi,
                is_valid=False,
                confidence=0.3,
                metadata={},
                error=f"Validation failed: {str(e)}",
                response_time_ms=int((time.time() - start) * 1000)
            )

    def get_latest_python_version(self) -> Optional[Dict[str, Any]]:
        """
        Get latest Python version from python.org.

        Returns:
            Dict with version and release_date, or None if failed
        """
        # Check cache
        cached = self._read_cache('python', 'latest')
        if cached:
            return cached

        try:
            # Python.org provides a downloads page with latest releases
            # Alternative: scrape https://www.python.org/downloads/ or use GitHub API
            # For now, use a fallback approach with known structure

            response = requests.get(
                "https://endoflife.date/api/python.json",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Get latest release (first in list)
            if data and len(data) > 0:
                latest = data[0]
                result = {
                    'version': latest.get('cycle'),
                    'release_date': latest.get('releaseDate'),
                    'eol_date': latest.get('eol'),
                    'latest': latest.get('latest')
                }

                # Cache result
                self._write_cache('python', 'latest', result)
                return result

            return None

        except Exception:
            return None

    def get_latest_nodejs_version(self) -> Optional[Dict[str, Any]]:
        """
        Get latest Node.js version from nodejs.org.

        Returns:
            Dict with version and release_date, or None if failed
        """
        # Check cache
        cached = self._read_cache('nodejs', 'latest')
        if cached:
            return cached

        try:
            response = requests.get(
                self.NODEJS_RELEASES_API,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Get latest LTS or current release
            if data and len(data) > 0:
                latest = data[0]
                result = {
                    'version': latest.get('version', '').lstrip('v'),
                    'release_date': latest.get('date'),
                    'lts': latest.get('lts', False)
                }

                # Cache result
                self._write_cache('nodejs', 'latest', result)
                return result

            return None

        except Exception:
            return None


def main():
    """CLI interface for web validator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Web Validator for Known Facts"
    )
    parser.add_argument("--arxiv", type=str, help="Validate arXiv ID")
    parser.add_argument("--doi", type=str, help="Validate DOI")
    parser.add_argument("--python", action="store_true", help="Get latest Python version")
    parser.add_argument("--nodejs", action="store_true", help="Get latest Node.js version")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")

    args = parser.parse_args()

    validator = WebValidator(use_cache=not args.no_cache)

    if args.arxiv:
        result = validator.validate_arxiv(args.arxiv)
        print(f"\n📄 arXiv Validation:")
        print(f"  ID: {result.identifier}")
        print(f"  Valid: {'✅ Yes' if result.is_valid else '❌ No'}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Response Time: {result.response_time_ms}ms")
        if result.is_valid:
            print(f"  Title: {result.metadata.get('title', 'N/A')}")
            print(f"  Authors: {', '.join(result.metadata.get('authors', []))}")
            print(f"  Published: {result.metadata.get('published', 'N/A')}")
            print(f"  URL: {result.metadata.get('url', 'N/A')}")
        else:
            print(f"  Error: {result.error}")

    elif args.doi:
        result = validator.validate_doi(args.doi)
        print(f"\n🔗 DOI Validation:")
        print(f"  DOI: {result.identifier}")
        print(f"  Valid: {'✅ Yes' if result.is_valid else '❌ No'}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Response Time: {result.response_time_ms}ms")
        if result.is_valid:
            print(f"  Title: {result.metadata.get('title', 'N/A')}")
            print(f"  Authors: {', '.join(result.metadata.get('authors', []))}")
            print(f"  Journal: {result.metadata.get('journal', 'N/A')}")
            print(f"  Published: {result.metadata.get('published', 'N/A')}")
            print(f"  URL: {result.metadata.get('url', 'N/A')}")
        else:
            print(f"  Error: {result.error}")

    elif args.python:
        result = validator.get_latest_python_version()
        print(f"\n🐍 Latest Python Version:")
        if result:
            print(f"  Version: {result.get('version', 'N/A')}")
            print(f"  Latest Patch: {result.get('latest', 'N/A')}")
            print(f"  Release Date: {result.get('release_date', 'N/A')}")
            print(f"  EOL Date: {result.get('eol_date', 'N/A')}")
        else:
            print(f"  ❌ Failed to fetch latest version")

    elif args.nodejs:
        result = validator.get_latest_nodejs_version()
        print(f"\n📗 Latest Node.js Version:")
        if result:
            print(f"  Version: {result.get('version', 'N/A')}")
            print(f"  Release Date: {result.get('release_date', 'N/A')}")
            print(f"  LTS: {'Yes' if result.get('lts') else 'No'}")
        else:
            print(f"  ❌ Failed to fetch latest version")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
