#!/usr/bin/env python3
"""
Sigma Rule Validator

Validates Sigma detection rules (YAML format) for common errors:
- Missing required fields (title, status, logsource, detection)
- Invalid logsource categories
- Syntax errors in detection logic
- Common mistakes in rule structure

Usage:
    python sigma_validator.py --file rule.yml
    python sigma_validator.py --file rule.yml --json
    python sigma_validator.py --file rule.yml --verbose
"""

import argparse
import sys
import yaml
import json
from typing import Dict, List, Tuple
from pathlib import Path


class SigmaValidator:
    """Validates Sigma detection rules."""

    # Valid logsource categories (common ones)
    VALID_CATEGORIES = {
        "process_creation", "network_connection", "file_event", "registry_event",
        "image_load", "pipe_event", "dns_query", "webserver", "proxy",
        "firewall", "ps_script", "ps_module", "ps_classic_provider"
    }

    # Valid logsource products
    VALID_PRODUCTS = {
        "windows", "linux", "macos", "azure", "aws", "gcp", "m365",
        "okta", "cisco", "paloalto", "fortinet"
    }

    # Valid status values
    VALID_STATUS = {"stable", "test", "experimental", "deprecated", "unsupported"}

    # Valid levels
    VALID_LEVELS = {"low", "medium", "high", "critical", "informational"}

    # Required fields
    REQUIRED_FIELDS = {"title", "status", "logsource", "detection"}

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
        Validate Sigma rule file.

        Args:
            filepath: Path to Sigma rule YAML file

        Returns:
            Dict with validation results
        """
        path = Path(filepath)
        if not path.exists():
            self.log_error(f"File not found: {filepath}")
            return self._get_result()

        # Load YAML
        try:
            with open(path, 'r', encoding='utf-8') as f:
                rule = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.log_error(f"YAML parsing error: {e}")
            return self._get_result()
        except Exception as e:
            self.log_error(f"Failed to read file: {e}")
            return self._get_result()

        if not isinstance(rule, dict):
            self.log_error("Rule is not a valid YAML dictionary")
            return self._get_result()

        # Validate structure
        self._validate_required_fields(rule)
        self._validate_title(rule)
        self._validate_status(rule)
        self._validate_level(rule)
        self._validate_logsource(rule)
        self._validate_detection(rule)
        self._validate_references(rule)
        self._validate_tags(rule)
        self._validate_falsepositives(rule)

        return self._get_result()

    def _validate_required_fields(self, rule: Dict):
        """Check all required fields are present."""
        missing = self.REQUIRED_FIELDS - set(rule.keys())
        if missing:
            self.log_error(f"Missing required fields: {', '.join(missing)}")
        else:
            self.log_info("All required fields present")

    def _validate_title(self, rule: Dict):
        """Validate title field."""
        title = rule.get("title")
        if not title:
            return  # Already caught by required fields check

        if not isinstance(title, str):
            self.log_error("Title must be a string")
        elif len(title) < 10:
            self.log_warning("Title is very short (< 10 chars)")
        elif len(title) > 100:
            self.log_warning("Title is very long (> 100 chars)")

    def _validate_status(self, rule: Dict):
        """Validate status field."""
        status = rule.get("status")
        if not status:
            return

        if status not in self.VALID_STATUS:
            self.log_error(f"Invalid status '{status}'. Valid: {', '.join(self.VALID_STATUS)}")

        if status == "experimental":
            self.log_warning("Rule status is 'experimental' - not production-ready")

    def _validate_level(self, rule: Dict):
        """Validate level field."""
        level = rule.get("level")
        if not level:
            self.log_warning("Missing 'level' field (severity)")
            return

        if level not in self.VALID_LEVELS:
            self.log_error(f"Invalid level '{level}'. Valid: {', '.join(self.VALID_LEVELS)}")

    def _validate_logsource(self, rule: Dict):
        """Validate logsource section."""
        logsource = rule.get("logsource")
        if not logsource:
            return

        if not isinstance(logsource, dict):
            self.log_error("Logsource must be a dictionary")
            return

        # Check category
        category = logsource.get("category")
        if category and category not in self.VALID_CATEGORIES:
            self.log_warning(f"Uncommon logsource category: '{category}'")

        # Check product
        product = logsource.get("product")
        if product and product not in self.VALID_PRODUCTS:
            self.log_warning(f"Uncommon logsource product: '{product}'")

        # Must have at least one of: category, product, service
        if not any(k in logsource for k in ["category", "product", "service"]):
            self.log_error("Logsource must have at least one: category, product, service")

    def _validate_detection(self, rule: Dict):
        """Validate detection section."""
        detection = rule.get("detection")
        if not detection:
            return

        if not isinstance(detection, dict):
            self.log_error("Detection must be a dictionary")
            return

        # Must have 'condition' field
        if "condition" not in detection:
            self.log_error("Detection missing required 'condition' field")
            return

        condition = detection["condition"]
        if not isinstance(condition, str):
            self.log_error("Detection condition must be a string")
            return

        # Parse condition and check all referenced selections exist
        self._validate_condition(condition, detection)

        # Check for common mistakes
        if len(detection) == 1:
            self.log_warning("Detection has only condition, no selection blocks")

    def _validate_condition(self, condition: str, detection: Dict):
        """Validate detection condition references."""
        import re

        # Extract selection names from condition (simple parsing)
        # e.g., "selection1 and not filter" -> ["selection1", "filter"]
        tokens = re.findall(r'\b(?!and\b|or\b|not\b|all\b|1\b|of\b)\w+\b', condition)

        for token in tokens:
            if token not in detection:
                self.log_error(f"Condition references undefined selection '{token}'")

        # Check for always-true/false conditions
        if condition.strip() in ["1 of *", "all of them"]:
            # Valid but check if there are selections
            selections = [k for k in detection.keys() if k != "condition"]
            if not selections:
                self.log_error("Condition uses wildcards but no selections defined")

    def _validate_references(self, rule: Dict):
        """Validate references field."""
        references = rule.get("references")
        if not references:
            self.log_info("No references field (recommended to add)")
            return

        if not isinstance(references, list):
            self.log_warning("References should be a list")
            return

        for ref in references:
            if not isinstance(ref, str):
                self.log_warning("Each reference should be a string (URL)")
            elif not ref.startswith(("http://", "https://")):
                self.log_warning(f"Reference doesn't look like a URL: {ref}")

    def _validate_tags(self, rule: Dict):
        """Validate tags field."""
        tags = rule.get("tags")
        if not tags:
            self.log_info("No tags field (recommended for categorization)")
            return

        if not isinstance(tags, list):
            self.log_warning("Tags should be a list")
            return

        # Common tag namespaces
        valid_namespaces = {"attack.", "detection.", "cve.", "tlp."}
        for tag in tags:
            if not isinstance(tag, str):
                self.log_warning(f"Tag should be a string: {tag}")
                continue

            # Check if tag has a namespace
            if "." not in tag:
                self.log_warning(f"Tag '{tag}' has no namespace (e.g., attack.t1234)")

    def _validate_falsepositives(self, rule: Dict):
        """Validate falsepositives field."""
        fp = rule.get("falsepositives")
        if not fp:
            self.log_info("No falsepositives field (recommended)")
            return

        if not isinstance(fp, list):
            self.log_warning("Falsepositives should be a list")

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
    parser = argparse.ArgumentParser(description="Validate Sigma detection rules")
    parser.add_argument("--file", required=True, help="Path to Sigma rule YAML file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    validator = SigmaValidator(verbose=args.verbose)
    result = validator.validate_file(args.file)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print(f"Sigma Rule Validation: {args.file}")
        print(f"{'='*60}\n")

        if result["valid"]:
            print("✅ VALID: Rule passed all checks\n")
        else:
            print("❌ INVALID: Rule has errors\n")

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
