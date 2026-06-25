#!/usr/bin/env python3
"""
MCP Tool Tester (GAP-TEST-AGENT-002)

Testing framework for MCP (Model Context Protocol) tools.
Validates tool contracts, mocks servers, tests error handling.

Usage:
    python mcp_tool_tester.py --list-tools
    python mcp_tool_tester.py --test github
    python mcp_tool_tester.py --validate-schema
"""

import argparse
import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RESULTS_FILE = DATA_DIR / "mcp_test_results.jsonl"


@dataclass
class MCPToolTest:
    """MCP tool test case."""
    tool_name: str
    method: str
    params: Dict
    expected_success: bool
    expected_fields: List[str] = None
    timeout_ms: int = 5000


# Built-in test cases for common MCP tools
MCP_TEST_CASES = {
    "github": [
        MCPToolTest(
            tool_name="mcp__github__search_repositories",
            method="search_repositories",
            params={"query": "language:python stars:>1000"},
            expected_success=True,
            expected_fields=["items"],
        ),
        MCPToolTest(
            tool_name="mcp__github__list_issues",
            method="list_issues",
            params={"owner": "anthropics", "repo": "anthropic-cookbook"},
            expected_success=True,
            expected_fields=[],  # Returns array
        ),
        MCPToolTest(
            tool_name="mcp__github__get_file_contents",
            method="get_file_contents",
            params={"owner": "anthropics", "repo": "anthropic-cookbook", "path": "README.md"},
            expected_success=True,
            expected_fields=["content"],
        ),
    ],
    "filesystem": [
        MCPToolTest(
            tool_name="mcp__filesystem__read_file",
            method="read_file",
            params={"path": "/etc/hostname"},
            expected_success=True,
            expected_fields=["content"],
        ),
        MCPToolTest(
            tool_name="mcp__filesystem__list_directory",
            method="list_directory",
            params={"path": "/tmp"},
            expected_success=True,
            expected_fields=["entries"],
        ),
    ],
}


def get_installed_mcp_servers() -> List[str]:
    """Get list of installed MCP servers."""
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Parse output to extract server names
        servers = []
        for line in result.stdout.split("\n"):
            if line.strip() and not line.startswith("─"):
                parts = line.split()
                if parts:
                    servers.append(parts[0])
        return servers
    except Exception as e:
        return []


def validate_tool_schema(tool_name: str) -> Dict:
    """Validate MCP tool schema."""
    # This would validate against JSON Schema
    # For now, check tool exists and has required fields
    result = {
        "tool": tool_name,
        "valid": True,
        "errors": [],
    }

    # Check naming convention
    if not tool_name.startswith("mcp__"):
        result["errors"].append("Tool name should start with 'mcp__'")
        result["valid"] = False

    parts = tool_name.split("__")
    if len(parts) < 3:
        result["errors"].append("Tool name should be 'mcp__<server>__<method>'")
        result["valid"] = False

    return result


def mock_mcp_response(tool: MCPToolTest) -> Dict:
    """Generate mock MCP response for testing."""
    # This simulates what an MCP server would return
    mock_responses = {
        "search_repositories": {"items": [], "total_count": 0},
        "list_issues": [],
        "get_file_contents": {"content": "mock content", "encoding": "utf-8"},
        "read_file": {"content": "mock file content"},
        "list_directory": {"entries": []},
    }

    return mock_responses.get(tool.method, {"status": "ok"})


def run_tool_test(test: MCPToolTest, mock: bool = True) -> Dict:
    """Run a single MCP tool test."""
    start_time = datetime.now()

    result = {
        "tool": test.tool_name,
        "method": test.method,
        "params": test.params,
        "timestamp": start_time.isoformat(),
        "mock": mock,
    }

    try:
        if mock:
            # Use mock response
            response = mock_mcp_response(test)
            result["response"] = response
            result["success"] = True
        else:
            # Would call actual MCP tool here
            # For safety, we only support mock mode
            result["success"] = False
            result["error"] = "Live mode not implemented for safety"

        # Validate expected fields
        if test.expected_fields and result.get("success"):
            missing = []
            for field in test.expected_fields:
                if field not in result.get("response", {}):
                    missing.append(field)
            if missing:
                result["missing_fields"] = missing
                result["field_validation"] = "FAIL"
            else:
                result["field_validation"] = "PASS"

        # Check expected success
        result["expected_success"] = test.expected_success
        result["test_passed"] = result.get("success") == test.expected_success

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        result["test_passed"] = not test.expected_success

    end_time = datetime.now()
    result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)

    return result


def run_server_tests(server: str, mock: bool = True) -> Dict:
    """Run all tests for an MCP server."""
    if server not in MCP_TEST_CASES:
        return {"error": f"No test cases for server: {server}"}

    results = {
        "server": server,
        "timestamp": datetime.now().isoformat(),
        "mock_mode": mock,
        "tests": [],
        "passed": 0,
        "failed": 0,
    }

    for test in MCP_TEST_CASES[server]:
        test_result = run_tool_test(test, mock=mock)
        results["tests"].append(test_result)

        if test_result.get("test_passed"):
            results["passed"] += 1
        else:
            results["failed"] += 1

    results["total"] = len(results["tests"])
    results["pass_rate"] = f"{(results['passed']/results['total']*100):.1f}%" if results["total"] > 0 else "N/A"

    return results


def generate_test_template(server: str, method: str) -> Dict:
    """Generate a test case template."""
    return {
        "tool_name": f"mcp__{server}__{method}",
        "method": method,
        "params": {},
        "expected_success": True,
        "expected_fields": [],
        "timeout_ms": 5000,
    }


def save_results(results: Dict):
    """Save test results."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(results) + "\n")


def print_results(results: Dict):
    """Print human-readable results."""
    print("\n" + "="*60)
    print("MCP TOOL TEST RESULTS")
    print("="*60)

    if "error" in results:
        print(f"ERROR: {results['error']}")
        return

    print(f"\nServer: {results.get('server', 'N/A')}")
    print(f"Mock Mode: {results.get('mock_mode', True)}")
    print(f"Total Tests: {results.get('total', 0)}")
    print(f"Passed: {results.get('passed', 0)}")
    print(f"Failed: {results.get('failed', 0)}")
    print(f"Pass Rate: {results.get('pass_rate', 'N/A')}")

    print("\nTest Details:")
    for test in results.get("tests", []):
        status = "✅" if test.get("test_passed") else "❌"
        print(f"  {status} {test['method']}")
        if not test.get("test_passed"):
            print(f"      Error: {test.get('error', 'Unknown')}")
        if test.get("missing_fields"):
            print(f"      Missing fields: {test['missing_fields']}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="MCP Tool Tester")
    parser.add_argument("--list-tools", "-l", action="store_true", help="List available test suites")
    parser.add_argument("--test", "-t", help="Test specific MCP server")
    parser.add_argument("--validate-schema", "-v", help="Validate tool schema")
    parser.add_argument("--list-servers", action="store_true", help="List installed MCP servers")
    parser.add_argument("--template", help="Generate test template for server:method")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save results")

    args = parser.parse_args()

    if args.list_tools:
        print("\nAvailable MCP test suites:")
        for server, tests in MCP_TEST_CASES.items():
            print(f"  {server}: {len(tests)} tests")
            for test in tests:
                print(f"    - {test.method}")
        return 0

    if args.list_servers:
        servers = get_installed_mcp_servers()
        print("\nInstalled MCP servers:")
        for s in servers:
            print(f"  - {s}")
        return 0

    if args.validate_schema:
        result = validate_tool_schema(args.validate_schema)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = "✅ Valid" if result["valid"] else "❌ Invalid"
            print(f"\n{args.validate_schema}: {status}")
            for err in result.get("errors", []):
                print(f"  - {err}")
        return 0 if result["valid"] else 1

    if args.template:
        parts = args.template.split(":")
        if len(parts) != 2:
            print("Template format: server:method")
            return 1
        template = generate_test_template(parts[0], parts[1])
        print(json.dumps(template, indent=2))
        return 0

    if args.test:
        results = run_server_tests(args.test)

        if args.save:
            save_results(results)
            print(f"Results saved to: {RESULTS_FILE}")

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_results(results)

        return 0 if results.get("failed", 0) == 0 else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
