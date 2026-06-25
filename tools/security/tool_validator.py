#!/usr/bin/env python3
"""
MCP Tool Validator
OWASP LLM07 Automation: Validate tool definitions for security risks

Version: 1.0.0
Task: Tasks 20-28 Automation (Task 27 - LLM07)

Usage:
    python tool_validator.py --definition tool.json
    python tool_validator.py --scan-dir tools/
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of tool validation."""
    tool_name: str
    is_safe: bool
    risk_score: float  # 0-10, higher = more risky
    findings: List[Dict[str, Any]]
    recommendations: List[str]


class ToolValidator:
    """
    Validates MCP tool definitions for security risks.

    Checks:
    1. Command injection patterns
    2. Path traversal risks
    3. SSRF vulnerabilities
    4. Excessive permissions
    5. Tool poisoning indicators
    """

    # Dangerous patterns in tool definitions
    DANGEROUS_PATTERNS = {
        "command_injection": [
            r"\$\{.*\}",  # Shell variable expansion
            r"`.*`",      # Backtick execution
            r"\$\(.*\)",  # Command substitution
            r";\s*",      # Command chaining
            r"\|\s*",     # Pipe to another command
            r"&&",        # AND chaining
            r"\|\|",      # OR chaining
            r"\beval\b",  # eval() calls
            r"\bexec\b",  # exec() calls
            r"\bsystem\b", # system() calls
        ],
        "path_traversal": [
            r"\.\./",     # Parent directory
            r"\.\.\\",    # Windows parent directory
            r"/etc/",     # System configs
            r"/root/",    # Root home
            r"/var/log/", # System logs
            r"~root",     # Root home expansion
        ],
        "ssrf": [
            r"localhost",
            r"127\.0\.0\.1",
            r"0\.0\.0\.0",
            r"169\.254\.",  # Link-local
            r"10\.\d+\.",   # Private network
            r"192\.168\.",  # Private network
            r"172\.(1[6-9]|2\d|3[01])\.", # Private network
            r"file://",    # Local file access
            r"gopher://",  # Gopher protocol
        ],
        "sensitive_data": [
            r"password",
            r"secret",
            r"api[_-]?key",
            r"token",
            r"credential",
            r"auth",
            r"bearer",
        ]
    }

    # Suspicious tool behaviors
    SUSPICIOUS_BEHAVIORS = [
        "modify system files",
        "access credentials",
        "connect to external",
        "download",
        "upload",
        "execute arbitrary",
        "run command",
        "shell access",
        "root access",
        "sudo",
        "admin",
    ]

    def __init__(self):
        self.findings = []

    def validate_tool(self, tool_definition: Dict[str, Any]) -> ValidationResult:
        """Validate a single tool definition."""
        findings = []
        recommendations = []
        risk_score = 0.0

        tool_name = tool_definition.get("name", "unknown")

        # 1. Check tool description for suspicious patterns
        description = tool_definition.get("description", "")
        for behavior in self.SUSPICIOUS_BEHAVIORS:
            if behavior.lower() in description.lower():
                findings.append({
                    "type": "suspicious_behavior",
                    "severity": "MEDIUM",
                    "description": f"Tool description mentions: '{behavior}'",
                    "location": "description"
                })
                risk_score += 1.0

        # 2. Check input schema for dangerous patterns
        input_schema = tool_definition.get("inputSchema", {})
        schema_str = json.dumps(input_schema)

        for category, patterns in self.DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, schema_str, re.IGNORECASE):
                    severity = "HIGH" if category in ["command_injection", "ssrf"] else "MEDIUM"
                    findings.append({
                        "type": category,
                        "severity": severity,
                        "description": f"Dangerous pattern found in input schema: {pattern}",
                        "location": "inputSchema"
                    })
                    risk_score += 2.0 if severity == "HIGH" else 1.0

        # 3. Check for overly permissive schemas
        properties = input_schema.get("properties", {})
        for prop_name, prop_def in properties.items():
            # Check for string without pattern/format constraints
            if prop_def.get("type") == "string":
                if not prop_def.get("pattern") and not prop_def.get("format"):
                    if any(kw in prop_name.lower() for kw in ["path", "file", "url", "command", "cmd"]):
                        findings.append({
                            "type": "unconstrained_input",
                            "severity": "MEDIUM",
                            "description": f"Property '{prop_name}' lacks validation constraints",
                            "location": f"inputSchema.properties.{prop_name}"
                        })
                        risk_score += 1.5
                        recommendations.append(f"Add 'pattern' or 'format' constraint to '{prop_name}'")

        # 4. Check for tool poisoning indicators
        if self._check_tool_poisoning(tool_definition):
            findings.append({
                "type": "tool_poisoning",
                "severity": "CRITICAL",
                "description": "Tool definition shows signs of poisoning",
                "location": "definition"
            })
            risk_score += 5.0

        # 5. Check permissions (if specified)
        permissions = tool_definition.get("permissions", [])
        dangerous_perms = ["write", "execute", "admin", "root", "system"]
        for perm in permissions:
            if any(dp in str(perm).lower() for dp in dangerous_perms):
                findings.append({
                    "type": "excessive_permission",
                    "severity": "HIGH",
                    "description": f"Tool requests dangerous permission: {perm}",
                    "location": "permissions"
                })
                risk_score += 2.0

        # Generate recommendations
        if not recommendations:
            if findings:
                recommendations.append("Review and address all findings before enabling tool")
            else:
                recommendations.append("Tool appears safe for use")

        # Cap risk score at 10
        risk_score = min(10.0, risk_score)

        is_safe = risk_score < 3.0 and not any(f["severity"] == "CRITICAL" for f in findings)

        return ValidationResult(
            tool_name=tool_name,
            is_safe=is_safe,
            risk_score=risk_score,
            findings=findings,
            recommendations=recommendations
        )

    def _check_tool_poisoning(self, tool_def: Dict[str, Any]) -> bool:
        """Check for tool poisoning indicators."""
        poisoning_indicators = 0

        description = tool_def.get("description", "")

        # Check for hidden instructions in description
        hidden_patterns = [
            r"ignore\s+(previous|above|all)",
            r"disregard\s+",
            r"forget\s+(everything|instructions)",
            r"new\s+instructions?",
            r"actually\s+do",
            r"instead\s+of",
            r"override",
        ]

        for pattern in hidden_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                poisoning_indicators += 1

        # Check for base64 encoded content
        if re.search(r"[A-Za-z0-9+/]{50,}={0,2}", description):
            poisoning_indicators += 1

        # Check for URL obfuscation
        if re.search(r"(0x[0-9a-f]+\.){3}0x[0-9a-f]+", description, re.IGNORECASE):
            poisoning_indicators += 1

        return poisoning_indicators >= 2

    def scan_directory(self, directory: Path) -> List[ValidationResult]:
        """Scan directory for tool definitions and validate all."""
        results = []

        for json_file in directory.rglob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Handle both single tool and array of tools
                tools = data if isinstance(data, list) else [data]

                for tool in tools:
                    if "name" in tool:  # Looks like a tool definition
                        result = self.validate_tool(tool)
                        result.tool_name = f"{json_file.name}:{result.tool_name}"
                        results.append(result)

            except (json.JSONDecodeError, IOError):
                continue

        return results

    def generate_report(self, results: List[ValidationResult], output_path: Optional[Path] = None) -> str:
        """Generate validation report."""
        total = len(results)
        safe = sum(1 for r in results if r.is_safe)
        unsafe = total - safe

        report = f"""# MCP Tool Security Validation Report

**Date:** {__import__('datetime').datetime.now().isoformat()}
**Tools Scanned:** {total}
**Safe:** {safe}
**Unsafe:** {unsafe}

## Summary

| Tool | Risk Score | Status |
|------|------------|--------|
"""
        for result in results:
            status = "SAFE" if result.is_safe else "UNSAFE"
            report += f"| {result.tool_name} | {result.risk_score:.1f}/10 | {status} |\n"

        report += "\n## Findings\n\n"

        for result in results:
            if result.findings:
                report += f"### {result.tool_name}\n\n"
                for finding in result.findings:
                    report += f"- **[{finding['severity']}]** {finding['description']}\n"
                report += "\n"

        report += """
## OWASP LLM07 Compliance

This report validates tools against OWASP LLM07:2025 (Insecure Plugin/Tool Design) requirements:
- Input validation
- Command injection prevention
- Path traversal protection
- SSRF mitigation
- Tool poisoning detection

---
*Generated by tool_validator.py v1.0.0*
"""

        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)

        return report


def main():
    parser = argparse.ArgumentParser(description="MCP Tool Security Validator")
    parser.add_argument("--definition", type=Path, help="Single tool definition JSON file")
    parser.add_argument("--scan-dir", type=Path, help="Directory to scan for tool definitions")
    parser.add_argument("--output", type=Path, help="Output report path")

    args = parser.parse_args()

    validator = ToolValidator()

    if args.definition:
        with open(args.definition, 'r') as f:
            tool_def = json.load(f)
        result = validator.validate_tool(tool_def)
        print(f"Tool: {result.tool_name}")
        print(f"Safe: {result.is_safe}")
        print(f"Risk Score: {result.risk_score}/10")
        if result.findings:
            print("Findings:")
            for f in result.findings:
                print(f"  [{f['severity']}] {f['description']}")

    elif args.scan_dir:
        results = validator.scan_directory(args.scan_dir)
        report = validator.generate_report(results, args.output)
        print(report)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
