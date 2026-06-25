#!/usr/bin/env python3
"""
44-ФЗ Technical Specification Checker

Validates technical specifications (ТЗ) for compliance with 44-ФЗ requirements:
- Required sections present (предмет закупки, НМЦК обоснование, сроки, etc.)
- Common mistakes and missing elements
- Quality checks for specification completeness

Usage:
    python fz44_spec_checker.py --file tz.txt
    python fz44_spec_checker.py --file tz.docx --json
    python fz44_spec_checker.py --file tz.pdf --verbose
"""

import argparse
import sys
import json
import re
from typing import Dict, List, Set
from pathlib import Path


class FZ44SpecChecker:
    """Validates 44-ФЗ technical specifications."""

    # Required sections according to 44-ФЗ
    REQUIRED_SECTIONS = {
        "предмет закупки": [
            "предмет закупки", "предмет контракта", "наименование закупки"
        ],
        "технические характеристики": [
            "технические характеристики", "требования к товару",
            "технические требования", "характеристики"
        ],
        "НМЦК обоснование": [
            "нмцк", "начальная максимальная цена контракта",
            "обоснование нмцк", "обоснование начальной"
        ],
        "сроки поставки": [
            "срок поставки", "срок выполнения", "срок оказания",
            "график поставки", "график выполнения"
        ],
        "требования к участникам": [
            "требования к участникам", "квалификационные требования",
            "требования к поставщикам"
        ],
        "критерии оценки": [
            "критерии оценки", "критерии определения победителя",
            "порядок оценки заявок"
        ],
        "условия приемки": [
            "приемка", "порядок приемки", "условия приемки",
            "акт приемки", "приемо-передаточный акт"
        ],
        "гарантийные обязательства": [
            "гарантия", "гарантийный срок", "гарантийные обязательства",
            "срок гарантии"
        ]
    }

    # Common mistakes to check
    COMMON_MISTAKES = {
        "указание на бренд": [
            r"apple\s+(?:macbook|iphone)", r"microsoft\s+(?:windows|office)",
            r"cisco", r"samsung", r"hp\s+(?:proliant|pavilion)"
        ],
        "без эквивалента": [
            r"без\s+эквивалент", r"не\s+допускается\s+эквивалент",
            r"только\s+\w+\s+(?:бренд|производитель)"
        ],
        "неизмеримые требования": [
            r"высокое\s+качество", r"современный", r"надежный",
            r"профессиональный", r"качественный"
        ],
        "отсутствие единиц измерения": [
            r"\d+\s+(?:оперативной памяти|процессор|диск)\b(?!\s*(?:гб|тб|мгц|ггц))"
        ]
    }

    # Helpful patterns to check
    GOOD_PATTERNS = {
        "эквивалент разрешен": [
            r"или\s+эквивалент", r"аналог", r"функциональн(?:ый|ые)\s+аналог"
        ],
        "ГОСТ стандарты": [
            r"гост\s+\d+", r"гост\s+р\s+\d+"
        ],
        "измеримые характеристики": [
            r"\d+\s*(?:гб|тб|мб)", r"\d+\s*(?:ггц|мгц)", r"\d+\s*(?:см|мм|м)\b"
        ]
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.info = []

    def log_error(self, message: str):
        """Add error message."""
        self.errors.append(message)
        if self.verbose:
            print(f"❌ ERROR: {message}", file=sys.stderr)

    def log_warning(self, message: str):
        """Add warning message."""
        self.warnings.append(message)
        if self.verbose:
            print(f"⚠️  WARNING: {message}", file=sys.stderr)

    def log_info(self, message: str):
        """Add info message."""
        self.info.append(message)
        if self.verbose:
            print(f"ℹ️  INFO: {message}", file=sys.stderr)

    def validate_file(self, filepath: str) -> Dict:
        """
        Validate 44-ФЗ specification file.

        Args:
            filepath: Path to specification file (TXT, DOCX, PDF)

        Returns:
            Dict with validation results
        """
        path = Path(filepath)
        if not path.exists():
            self.log_error(f"File not found: {filepath}")
            return self._get_result()

        # Read file content
        try:
            content = self._read_file(path)
        except Exception as e:
            self.log_error(f"Failed to read file: {e}")
            return self._get_result()

        if not content or len(content) < 100:
            self.log_error("File content is too short to be a valid specification")
            return self._get_result()

        # Normalize content
        content_lower = content.lower()

        # Validate required sections
        self._validate_required_sections(content_lower)

        # Check for common mistakes
        self._check_common_mistakes(content_lower)

        # Check for good practices
        self._check_good_practices(content_lower)

        # Validate NMCK section in detail
        self._validate_nmck(content_lower)

        # Check completeness
        self._check_completeness(content, content_lower)

        return self._get_result()

    def _read_file(self, path: Path) -> str:
        """Read file content based on extension."""
        suffix = path.suffix.lower()

        if suffix in [".txt", ".md"]:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif suffix == ".docx":
            try:
                import docx
                doc = docx.Document(path)
                return "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                self.log_error("python-docx not installed. Install: pip install python-docx")
                return ""
        elif suffix == ".pdf":
            try:
                import PyPDF2
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    return "\n".join([page.extract_text() for page in reader.pages])
            except ImportError:
                self.log_error("PyPDF2 not installed. Install: pip install PyPDF2")
                return ""
        else:
            # Try as text
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

    def _validate_required_sections(self, content: str):
        """Check all required sections are present."""
        missing = []
        found = []

        for section_name, patterns in self.REQUIRED_SECTIONS.items():
            section_found = any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)
            if section_found:
                found.append(section_name)
                self.log_info(f"✓ Found section: {section_name}")
            else:
                missing.append(section_name)
                self.log_error(f"Missing required section: {section_name}")

        if not missing:
            self.log_info("All required sections present")

    def _check_common_mistakes(self, content: str):
        """Check for common 44-ФЗ specification mistakes."""
        # Brand names without equivalents
        brand_matches = []
        for pattern in self.COMMON_MISTAKES["указание на бренд"]:
            matches = re.findall(pattern, content, re.IGNORECASE)
            brand_matches.extend(matches)

        if brand_matches:
            unique_brands = list(set(brand_matches))[:3]
            self.log_warning(f"Brand names found: {', '.join(unique_brands)}... "
                           "Ensure 'или эквивалент' is specified (44-ФЗ ч.1 ст.33)")

        # No equivalent allowed
        for pattern in self.COMMON_MISTAKES["без эквивалента"]:
            if re.search(pattern, content, re.IGNORECASE):
                self.log_error("Specification prohibits equivalents - likely violates 44-ФЗ ч.1 ст.33")

        # Non-measurable requirements
        vague_count = 0
        for pattern in self.COMMON_MISTAKES["неизмеримые требования"]:
            vague_count += len(re.findall(pattern, content, re.IGNORECASE))

        if vague_count > 3:
            self.log_warning(f"Found {vague_count} vague/non-measurable requirements "
                           "(e.g., 'качественный', 'надежный'). Use measurable criteria.")

        # Missing units
        missing_units = re.findall(self.COMMON_MISTAKES["отсутствие единиц измерения"][0],
                                   content, re.IGNORECASE)
        if missing_units:
            self.log_warning(f"Numbers without units of measurement found: {len(missing_units)} cases")

    def _check_good_practices(self, content: str):
        """Check for good specification practices."""
        # Equivalents allowed
        equiv_found = any(re.search(pattern, content, re.IGNORECASE)
                         for pattern in self.GOOD_PATTERNS["эквивалент разрешен"])
        if equiv_found:
            self.log_info("✓ Equivalents allowed (good practice)")
        else:
            self.log_warning("No 'или эквивалент' clauses found - may limit competition")

        # GOST standards
        gost_count = sum(len(re.findall(pattern, content, re.IGNORECASE))
                        for pattern in self.GOOD_PATTERNS["ГОСТ стандарты"])
        if gost_count > 0:
            self.log_info(f"✓ GOST standards referenced: {gost_count} times")
        else:
            self.log_info("No GOST standards found (consider adding for technical requirements)")

        # Measurable characteristics
        measurable_count = sum(len(re.findall(pattern, content, re.IGNORECASE))
                              for pattern in self.GOOD_PATTERNS["измеримые характеристики"])
        if measurable_count > 5:
            self.log_info(f"✓ Measurable characteristics found: {measurable_count}")

    def _validate_nmck(self, content: str):
        """Validate NMCK (price) section in detail."""
        # Check if NMCK is mentioned
        nmck_patterns = self.REQUIRED_SECTIONS["НМЦК обоснование"]
        nmck_found = any(re.search(pattern, content, re.IGNORECASE) for pattern in nmck_patterns)

        if not nmck_found:
            return  # Already reported in required sections

        # Check for price methodology
        methodologies = [
            r"метод\s+сопоставимых\s+(?:рыночных\s+)?цен",
            r"затратн(?:ый|ого)\s+метод",
            r"тарифн(?:ый|ого)\s+метод",
            r"проектно-сметн(?:ый|ого)\s+метод"
        ]

        method_found = any(re.search(method, content, re.IGNORECASE) for method in methodologies)
        if method_found:
            self.log_info("✓ NMCK methodology specified")
        else:
            self.log_warning("NMCK methodology not clearly specified (required by 44-ФЗ ст.22)")

        # Check for price sources
        sources = [
            r"коммерческ(?:ое|их)\s+предложени(?:е|й)",
            r"прайс-?лист",
            r"сайт\s+производителя",
            r"каталог"
        ]

        source_found = any(re.search(src, content, re.IGNORECASE) for src in sources)
        if source_found:
            self.log_info("✓ NMCK sources mentioned")
        else:
            self.log_warning("NMCK sources not mentioned (should document price justification)")

    def _check_completeness(self, content: str, content_lower: str):
        """Check overall completeness of specification."""
        # Word count
        word_count = len(content.split())
        if word_count < 500:
            self.log_warning(f"Specification is short ({word_count} words). "
                           "Consider adding more detail.")
        elif word_count > 10000:
            self.log_info(f"Specification is detailed ({word_count} words)")

        # Check for structured format (numbered sections)
        numbered_sections = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
        if numbered_sections > 5:
            self.log_info(f"✓ Structured format with {numbered_sections} numbered sections")
        else:
            self.log_warning("Specification lacks clear numbered structure")

        # Check for tables (common in good specs)
        table_indicators = content_lower.count("┌") + content_lower.count("│") + \
                          content_lower.count("таблица")
        if table_indicators > 5:
            self.log_info("✓ Contains tables (good for technical characteristics)")

    def _get_result(self) -> Dict:
        """Get validation result."""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }


def main():
    parser = argparse.ArgumentParser(description="Validate 44-ФЗ technical specifications")
    parser.add_argument("--file", required=True, help="Path to specification file (TXT/DOCX/PDF)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    checker = FZ44SpecChecker(verbose=args.verbose)
    result = checker.validate_file(args.file)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print(f"44-ФЗ Specification Validation: {args.file}")
        print(f"{'='*60}\n")

        if result["valid"]:
            print("✅ VALID: Specification meets minimum 44-ФЗ requirements\n")
        else:
            print("❌ INVALID: Specification has errors\n")

        if result["errors"]:
            print(f"🔴 ERRORS ({len(result['errors'])}):")
            for err in result["errors"]:
                print(f"   - {err}")
            print()

        if result["warnings"]:
            print(f"⚠️  WARNINGS ({len(result['warnings'])}):")
            for warn in result["warnings"]:
                print(f"   - {warn}")
            print()

        if result["info"] and args.verbose:
            print(f"ℹ️  INFO:")
            for info in result["info"]:
                print(f"   - {info}")
            print()

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
