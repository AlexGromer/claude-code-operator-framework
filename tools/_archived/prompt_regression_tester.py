#!/usr/bin/env python3
"""
Prompt Regression Tester (GAP-TEST-UNIT-002)

Tests prompts for regression, tracks versions, compares outputs.
Supports A/B testing and prompt versioning.

Usage:
    python prompt_regression_tester.py --test prompt_name
    python prompt_regression_tester.py --compare v1 v2
    python prompt_regression_tester.py --report
"""

import argparse
import json
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
PROMPTS_DIR = DATA_DIR / "prompts"
RESULTS_DIR = DATA_DIR / "prompt_tests"


@dataclass
class PromptVersion:
    """Prompt version metadata."""
    name: str
    version: str
    template: str
    variables: List[str]
    created: str
    hash: str


@dataclass
class PromptTestCase:
    """Test case for a prompt."""
    name: str
    inputs: Dict
    expected_contains: List[str] = None
    expected_not_contains: List[str] = None
    expected_format: str = None  # json, markdown, code


@dataclass
class PromptTestResult:
    """Result of prompt test."""
    prompt_name: str
    version: str
    test_name: str
    passed: bool
    output: str
    checks: Dict
    timestamp: str
    duration_ms: int


# Built-in test prompts
BUILTIN_PROMPTS = {
    "code_review": {
        "v1": {
            "template": "Review this code for bugs and improvements:\n\n{code}\n\nProvide feedback.",
            "variables": ["code"],
        },
        "v2": {
            "template": "You are a senior code reviewer. Review this code:\n\n```\n{code}\n```\n\nCheck for:\n1. Bugs\n2. Security issues\n3. Performance\n4. Style\n\nFormat as markdown.",
            "variables": ["code"],
        },
    },
    "summarize": {
        "v1": {
            "template": "Summarize this text:\n\n{text}",
            "variables": ["text"],
        },
        "v2": {
            "template": "Provide a concise summary (max 3 sentences) of:\n\n{text}\n\nKey points only.",
            "variables": ["text"],
        },
    },
    "extract_json": {
        "v1": {
            "template": "Extract data as JSON:\n\n{text}",
            "variables": ["text"],
        },
        "v2": {
            "template": "Extract structured data from the text below. Return ONLY valid JSON, no explanation.\n\nText: {text}\n\nJSON:",
            "variables": ["text"],
        },
    },
}

# Test cases for built-in prompts
BUILTIN_TESTS = {
    "code_review": [
        PromptTestCase(
            name="basic_python",
            inputs={"code": "def add(a, b):\n    return a + b"},
            expected_contains=["function", "return"],
        ),
        PromptTestCase(
            name="security_issue",
            inputs={"code": "import os\nos.system(user_input)"},
            expected_contains=["security", "injection"],
        ),
    ],
    "summarize": [
        PromptTestCase(
            name="short_text",
            inputs={"text": "The quick brown fox jumps over the lazy dog."},
            expected_contains=["fox", "dog"],
        ),
    ],
    "extract_json": [
        PromptTestCase(
            name="simple_extract",
            inputs={"text": "Name: John, Age: 30, City: NYC"},
            expected_format="json",
        ),
    ],
}


def ensure_dirs():
    """Ensure directories exist."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def compute_hash(text: str) -> str:
    """Compute hash of prompt template."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def get_prompt(name: str, version: str = None) -> Optional[PromptVersion]:
    """Get prompt by name and version."""
    if name in BUILTIN_PROMPTS:
        versions = BUILTIN_PROMPTS[name]
        if version is None:
            version = max(versions.keys())  # Latest version
        if version in versions:
            data = versions[version]
            return PromptVersion(
                name=name,
                version=version,
                template=data["template"],
                variables=data["variables"],
                created="builtin",
                hash=compute_hash(data["template"]),
            )

    # Check custom prompts
    prompt_file = PROMPTS_DIR / f"{name}.json"
    if prompt_file.exists():
        data = json.loads(prompt_file.read_text())
        if version is None:
            version = data.get("latest", "v1")
        if version in data.get("versions", {}):
            v = data["versions"][version]
            return PromptVersion(
                name=name,
                version=version,
                template=v["template"],
                variables=v.get("variables", []),
                created=v.get("created", "unknown"),
                hash=compute_hash(v["template"]),
            )

    return None


def render_prompt(prompt: PromptVersion, inputs: Dict) -> str:
    """Render prompt with inputs."""
    result = prompt.template
    for var in prompt.variables:
        if var in inputs:
            result = result.replace(f"{{{var}}}", str(inputs[var]))
    return result


def simulate_llm_response(rendered_prompt: str) -> str:
    """Simulate LLM response for testing."""
    # In production, this would call actual LLM
    # For testing, we return a mock response
    if "security" in rendered_prompt.lower() or "injection" in rendered_prompt.lower():
        return "Security issue detected: potential command injection vulnerability."
    if "json" in rendered_prompt.lower():
        return '{"name": "John", "age": 30, "city": "NYC"}'
    if "summary" in rendered_prompt.lower() or "summarize" in rendered_prompt.lower():
        return "The text describes a fox jumping over a dog."
    return "Code review: The function looks correct. Consider adding type hints."


def check_output(output: str, test: PromptTestCase) -> Dict:
    """Check output against test expectations."""
    checks = {
        "contains": {"passed": True, "details": []},
        "not_contains": {"passed": True, "details": []},
        "format": {"passed": True, "details": []},
    }

    # Check expected_contains
    if test.expected_contains:
        for term in test.expected_contains:
            if term.lower() not in output.lower():
                checks["contains"]["passed"] = False
                checks["contains"]["details"].append(f"Missing: {term}")

    # Check expected_not_contains
    if test.expected_not_contains:
        for term in test.expected_not_contains:
            if term.lower() in output.lower():
                checks["not_contains"]["passed"] = False
                checks["not_contains"]["details"].append(f"Found unwanted: {term}")

    # Check format
    if test.expected_format == "json":
        try:
            json.loads(output)
        except Exception:
            checks["format"]["passed"] = False
            checks["format"]["details"].append("Invalid JSON")

    return checks


def run_test(prompt_name: str, version: str, test: PromptTestCase) -> PromptTestResult:
    """Run a single prompt test."""
    start_time = datetime.now()

    prompt = get_prompt(prompt_name, version)
    if not prompt:
        return PromptTestResult(
            prompt_name=prompt_name,
            version=version,
            test_name=test.name,
            passed=False,
            output="",
            checks={"error": "Prompt not found"},
            timestamp=start_time.isoformat(),
            duration_ms=0,
        )

    rendered = render_prompt(prompt, test.inputs)
    output = simulate_llm_response(rendered)
    checks = check_output(output, test)

    end_time = datetime.now()

    all_passed = all(c["passed"] for c in checks.values() if isinstance(c, dict) and "passed" in c)

    return PromptTestResult(
        prompt_name=prompt_name,
        version=version,
        test_name=test.name,
        passed=all_passed,
        output=output[:500],  # Truncate for storage
        checks=checks,
        timestamp=start_time.isoformat(),
        duration_ms=int((end_time - start_time).total_seconds() * 1000),
    )


def run_all_tests(prompt_name: str, version: str = None) -> Dict:
    """Run all tests for a prompt."""
    tests = BUILTIN_TESTS.get(prompt_name, [])
    if not tests:
        return {"error": f"No tests found for prompt: {prompt_name}"}

    results = {
        "prompt": prompt_name,
        "version": version or "latest",
        "timestamp": datetime.now().isoformat(),
        "tests": [],
        "passed": 0,
        "failed": 0,
    }

    for test in tests:
        result = run_test(prompt_name, version, test)
        results["tests"].append(asdict(result))
        if result.passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

    results["total"] = len(results["tests"])
    results["pass_rate"] = f"{(results['passed']/results['total']*100):.1f}%" if results["total"] > 0 else "N/A"

    return results


def compare_versions(prompt_name: str, v1: str, v2: str) -> Dict:
    """Compare two prompt versions."""
    p1 = get_prompt(prompt_name, v1)
    p2 = get_prompt(prompt_name, v2)

    if not p1 or not p2:
        return {"error": "One or both versions not found"}

    comparison = {
        "prompt": prompt_name,
        "v1": {"version": v1, "hash": p1.hash, "length": len(p1.template)},
        "v2": {"version": v2, "hash": p2.hash, "length": len(p2.template)},
        "changes": {
            "hash_changed": p1.hash != p2.hash,
            "length_diff": len(p2.template) - len(p1.template),
        },
    }

    # Run tests on both versions
    tests = BUILTIN_TESTS.get(prompt_name, [])
    if tests:
        r1 = run_all_tests(prompt_name, v1)
        r2 = run_all_tests(prompt_name, v2)

        comparison["v1"]["pass_rate"] = r1.get("pass_rate", "N/A")
        comparison["v2"]["pass_rate"] = r2.get("pass_rate", "N/A")
        comparison["v1"]["passed"] = r1.get("passed", 0)
        comparison["v2"]["passed"] = r2.get("passed", 0)

    return comparison


def save_results(results: Dict):
    """Save test results."""
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f"prompt_test_{timestamp}.json"
    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)
    return result_file


def print_results(results: Dict):
    """Print human-readable results."""
    print("\n" + "="*60)
    print("PROMPT REGRESSION TEST RESULTS")
    print("="*60)

    if "error" in results:
        print(f"ERROR: {results['error']}")
        return

    print(f"\nPrompt: {results.get('prompt', 'N/A')}")
    print(f"Version: {results.get('version', 'N/A')}")
    print(f"Total Tests: {results.get('total', 0)}")
    print(f"Passed: {results.get('passed', 0)}")
    print(f"Failed: {results.get('failed', 0)}")
    print(f"Pass Rate: {results.get('pass_rate', 'N/A')}")

    print("\nTest Details:")
    for test in results.get("tests", []):
        status = "✅" if test.get("passed") else "❌"
        print(f"  {status} {test['test_name']}")
        if not test.get("passed"):
            for check_name, check_data in test.get("checks", {}).items():
                if isinstance(check_data, dict) and not check_data.get("passed", True):
                    print(f"      {check_name}: {check_data.get('details', [])}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Prompt Regression Tester")
    parser.add_argument("--test", "-t", help="Test specific prompt")
    parser.add_argument("--version", "-v", help="Prompt version to test")
    parser.add_argument("--compare", "-c", nargs=2, metavar=("V1", "V2"), help="Compare two versions")
    parser.add_argument("--prompt", "-p", help="Prompt name for comparison")
    parser.add_argument("--list", "-l", action="store_true", help="List available prompts")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save results")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable prompts:")
        for name, versions in BUILTIN_PROMPTS.items():
            print(f"  {name}: {list(versions.keys())}")
            if name in BUILTIN_TESTS:
                print(f"    Tests: {len(BUILTIN_TESTS[name])}")
        return 0

    if args.compare:
        if not args.prompt:
            print("--prompt required for comparison")
            return 1
        results = compare_versions(args.prompt, args.compare[0], args.compare[1])
    elif args.test:
        results = run_all_tests(args.test, args.version)
    else:
        parser.print_help()
        return 0

    if args.save:
        result_file = save_results(results)
        print(f"Results saved: {result_file}")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)

    return 0 if results.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
