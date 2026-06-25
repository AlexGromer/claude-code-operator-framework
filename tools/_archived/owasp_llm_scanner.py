#!/usr/bin/env python3
"""
OWASP LLM Top 10 Scanner (GAP-SECURITY-AGENT-001)

Scans for OWASP LLM Top 10 vulnerabilities in prompts, configs, and code.
Based on OWASP Top 10 for LLM Applications 2025.

Usage:
    python owasp_llm_scanner.py --scan-prompt "prompt text"
    python owasp_llm_scanner.py --scan-config ~/.claude/settings.json
    python owasp_llm_scanner.py --full-audit
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RESULTS_FILE = DATA_DIR / "owasp_scan_results.jsonl"

# OWASP LLM Top 10 (2025 version)
OWASP_LLM_TOP_10 = {
    "LLM01": {
        "name": "Prompt Injection",
        "severity": "CRITICAL",
        "description": "Manipulating LLM via crafted inputs to bypass safety",
        "patterns": [
            r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions?",
            r"(?i)disregard\s+(all\s+)?(previous\s+)?",
            r"(?i)you\s+are\s+now\s+(a\s+)?",
            r"(?i)\[SYSTEM\]|\[ADMIN\]|\[OVERRIDE\]",
            r"(?i)```\s*(system|admin|root)",
        ],
    },
    "LLM02": {
        "name": "Insecure Output Handling",
        "severity": "HIGH",
        "description": "Failing to validate/sanitize LLM outputs",
        "patterns": [
            r"(?i)eval\s*\(",
            r"(?i)exec\s*\(",
            r"(?i)os\.system\s*\(",
            r"(?i)subprocess\.(run|call|Popen)",
            r"(?i)innerHTML\s*=",
            r"(?i)document\.write\s*\(",
        ],
    },
    "LLM03": {
        "name": "Training Data Poisoning",
        "severity": "HIGH",
        "description": "Manipulating training data to introduce vulnerabilities",
        "patterns": [
            r"(?i)train\s+on\s+this",
            r"(?i)learn\s+from\s+this\s+example",
            r"(?i)remember\s+this\s+as\s+correct",
        ],
    },
    "LLM04": {
        "name": "Model Denial of Service",
        "severity": "MEDIUM",
        "description": "Resource exhaustion through expensive operations",
        "patterns": [
            r"(?i)repeat\s+\d{4,}\s+times",
            r"(?i)generate\s+\d{6,}\s+(words|tokens|characters)",
            r"(?i)infinite\s+(loop|recursion)",
            r"(?i)while\s+true",
        ],
    },
    "LLM05": {
        "name": "Supply Chain Vulnerabilities",
        "severity": "HIGH",
        "description": "Risks from third-party components, plugins, models",
        "patterns": [
            r"(?i)pip\s+install\s+--index-url",
            r"(?i)npm\s+install\s+--registry",
            r"(?i)curl\s+.*\|\s*(bash|sh)",
            r"(?i)wget\s+.*\|\s*(bash|sh)",
        ],
    },
    "LLM06": {
        "name": "Sensitive Information Disclosure",
        "severity": "CRITICAL",
        "description": "LLM revealing sensitive data in responses",
        "patterns": [
            r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]+['\"]",
            r"(?i)BEGIN\s+(RSA\s+)?PRIVATE\s+KEY",
            r"(?i)aws[_-]?(access[_-]?key|secret)",
            r"\b[A-Za-z0-9+/]{40,}\b",  # Base64 encoded secrets
        ],
    },
    "LLM07": {
        "name": "Insecure Plugin Design",
        "severity": "HIGH",
        "description": "Plugins with insufficient access controls",
        "patterns": [
            r"(?i)plugin.*without.*auth",
            r"(?i)allow.*all.*permissions",
            r"(?i)disable.*security",
            r"(?i)trust.*all.*inputs",
        ],
    },
    "LLM08": {
        "name": "Excessive Agency",
        "severity": "HIGH",
        "description": "LLM given too much autonomy or capability",
        "patterns": [
            r"(?i)auto[_-]?approve",
            r"(?i)no[_-]?confirm(ation)?",
            r"(?i)skip[_-]?review",
            r"(?i)autonomous[_-]?mode",
        ],
    },
    "LLM09": {
        "name": "Overreliance",
        "severity": "MEDIUM",
        "description": "Excessive dependence on LLM without oversight",
        "patterns": [
            r"(?i)always\s+trust\s+(the\s+)?AI",
            r"(?i)no\s+human\s+review",
            r"(?i)AI\s+is\s+always\s+correct",
        ],
    },
    "LLM10": {
        "name": "Model Theft",
        "severity": "HIGH",
        "description": "Unauthorized extraction of model or data",
        "patterns": [
            r"(?i)extract\s+(the\s+)?model",
            r"(?i)dump\s+(the\s+)?weights",
            r"(?i)copy\s+(the\s+)?training\s+data",
            r"(?i)reverse\s+engineer",
        ],
    },
}


@dataclass
class ScanFinding:
    """Individual scan finding."""
    vuln_id: str
    name: str
    severity: str
    match: str
    location: str
    line_number: int = None


def scan_text(text: str, source: str = "input") -> List[ScanFinding]:
    """Scan text for OWASP LLM vulnerabilities."""
    findings = []

    lines = text.split("\n")
    for line_num, line in enumerate(lines, 1):
        for vuln_id, vuln in OWASP_LLM_TOP_10.items():
            for pattern in vuln["patterns"]:
                matches = re.findall(pattern, line)
                if matches:
                    for match in matches:
                        findings.append(ScanFinding(
                            vuln_id=vuln_id,
                            name=vuln["name"],
                            severity=vuln["severity"],
                            match=match if isinstance(match, str) else str(match),
                            location=source,
                            line_number=line_num,
                        ))

    return findings


def scan_file(filepath: str) -> Dict:
    """Scan a file for vulnerabilities."""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    try:
        content = path.read_text()
    except Exception as e:
        return {"error": f"Cannot read file: {e}"}

    findings = scan_text(content, source=str(path))

    return {
        "file": str(path),
        "size_bytes": len(content),
        "lines": len(content.split("\n")),
        "findings": [asdict(f) for f in findings],
        "total_findings": len(findings),
        "by_severity": count_by_severity(findings),
    }


def scan_directory(dirpath: str, extensions: List[str] = None) -> Dict:
    """Scan directory recursively."""
    if extensions is None:
        extensions = [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md"]

    path = Path(dirpath)
    if not path.exists():
        return {"error": f"Directory not found: {dirpath}"}

    results = {
        "directory": str(path),
        "files_scanned": 0,
        "total_findings": 0,
        "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0},
        "files": [],
    }

    for ext in extensions:
        for file in path.rglob(f"*{ext}"):
            if ".git" in str(file):
                continue

            file_result = scan_file(str(file))
            if "error" not in file_result:
                results["files_scanned"] += 1
                results["total_findings"] += file_result["total_findings"]

                for sev, count in file_result["by_severity"].items():
                    results["by_severity"][sev] = results["by_severity"].get(sev, 0) + count

                if file_result["total_findings"] > 0:
                    results["files"].append(file_result)

    return results


def count_by_severity(findings: List[ScanFinding]) -> Dict[str, int]:
    """Count findings by severity."""
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def calculate_risk_score(findings: List[ScanFinding]) -> Tuple[int, str]:
    """Calculate overall risk score (0-100)."""
    if not findings:
        return 0, "LOW"

    score = 0
    for f in findings:
        if f.severity == "CRITICAL":
            score += 30
        elif f.severity == "HIGH":
            score += 15
        elif f.severity == "MEDIUM":
            score += 5

    score = min(100, score)

    if score >= 70:
        level = "CRITICAL"
    elif score >= 40:
        level = "HIGH"
    elif score >= 20:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score, level


def full_audit() -> Dict:
    """Run full OWASP audit on Claude configuration."""
    claude_dir = Path.home() / ".claude"

    results = {
        "timestamp": datetime.now().isoformat(),
        "audit_type": "full",
        "directories": [],
        "summary": {
            "total_findings": 0,
            "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0},
            "risk_score": 0,
            "risk_level": "LOW",
        },
    }

    # Scan key directories
    for subdir in ["rules", "modules", "hooks", "tools", "evaluation"]:
        dir_path = claude_dir / subdir
        if dir_path.exists():
            dir_result = scan_directory(str(dir_path))
            results["directories"].append(dir_result)

            results["summary"]["total_findings"] += dir_result.get("total_findings", 0)
            for sev, count in dir_result.get("by_severity", {}).items():
                results["summary"]["by_severity"][sev] += count

    # Scan config files
    for config in ["settings.json", "CLAUDE.md", "CORE_INSTRUCTIONS.md"]:
        config_path = claude_dir / config
        if config_path.exists():
            file_result = scan_file(str(config_path))
            if "error" not in file_result and file_result["total_findings"] > 0:
                results["directories"].append(file_result)
                results["summary"]["total_findings"] += file_result["total_findings"]

    # Calculate overall risk
    all_findings = []
    for d in results["directories"]:
        for f in d.get("findings", []) if "findings" in d else []:
            all_findings.append(ScanFinding(**f) if isinstance(f, dict) else f)
        for file in d.get("files", []):
            for f in file.get("findings", []):
                all_findings.append(ScanFinding(**f) if isinstance(f, dict) else f)

    results["summary"]["risk_score"], results["summary"]["risk_level"] = calculate_risk_score(all_findings)

    return results


def save_results(results: Dict):
    """Save scan results."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(results) + "\n")


def print_results(results: Dict):
    """Print human-readable results."""
    print("\n" + "="*60)
    print("OWASP LLM TOP 10 SCAN RESULTS")
    print("="*60)

    if "error" in results:
        print(f"ERROR: {results['error']}")
        return

    summary = results.get("summary", results)
    print(f"\nTimestamp: {results.get('timestamp', 'N/A')}")
    print(f"Total Findings: {summary.get('total_findings', 0)}")
    print(f"Risk Score: {summary.get('risk_score', 0)}/100")
    print(f"Risk Level: {summary.get('risk_level', 'UNKNOWN')}")

    print("\nBy Severity:")
    for sev, count in summary.get("by_severity", {}).items():
        print(f"  {sev}: {count}")

    # Print findings by vulnerability
    findings_by_vuln = {}
    for d in results.get("directories", [results]):
        for f in d.get("findings", []):
            vuln_id = f.get("vuln_id", "UNKNOWN")
            if vuln_id not in findings_by_vuln:
                findings_by_vuln[vuln_id] = []
            findings_by_vuln[vuln_id].append(f)
        for file in d.get("files", []):
            for f in file.get("findings", []):
                vuln_id = f.get("vuln_id", "UNKNOWN")
                if vuln_id not in findings_by_vuln:
                    findings_by_vuln[vuln_id] = []
                findings_by_vuln[vuln_id].append(f)

    if findings_by_vuln:
        print("\nFindings by Vulnerability:")
        for vuln_id in sorted(findings_by_vuln.keys()):
            vuln_name = OWASP_LLM_TOP_10.get(vuln_id, {}).get("name", "Unknown")
            print(f"\n  {vuln_id}: {vuln_name}")
            for f in findings_by_vuln[vuln_id][:5]:  # Limit to 5 per vuln
                loc = f.get("location", "unknown")
                line = f.get("line_number", "?")
                print(f"    - {loc}:{line}: {f.get('match', '')[:50]}")
            if len(findings_by_vuln[vuln_id]) > 5:
                print(f"    ... and {len(findings_by_vuln[vuln_id]) - 5} more")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="OWASP LLM Top 10 Scanner")
    parser.add_argument("--scan-prompt", "-p", help="Scan prompt text")
    parser.add_argument("--scan-file", "-f", help="Scan file")
    parser.add_argument("--scan-dir", "-d", help="Scan directory")
    parser.add_argument("--full-audit", "-a", action="store_true", help="Full Claude config audit")
    parser.add_argument("--list-vulns", "-l", action="store_true", help="List OWASP LLM Top 10")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save results")

    args = parser.parse_args()

    if args.list_vulns:
        print("\nOWASP LLM Top 10 (2025):")
        for vuln_id, vuln in OWASP_LLM_TOP_10.items():
            print(f"  {vuln_id} [{vuln['severity']}]: {vuln['name']}")
            print(f"    {vuln['description']}")
        return 0

    if args.scan_prompt:
        findings = scan_text(args.scan_prompt, "prompt")
        score, level = calculate_risk_score(findings)
        results = {
            "timestamp": datetime.now().isoformat(),
            "source": "prompt",
            "findings": [asdict(f) for f in findings],
            "total_findings": len(findings),
            "by_severity": count_by_severity(findings),
            "summary": {"risk_score": score, "risk_level": level},
        }
    elif args.scan_file:
        results = scan_file(args.scan_file)
        results["timestamp"] = datetime.now().isoformat()
    elif args.scan_dir:
        results = scan_directory(args.scan_dir)
        results["timestamp"] = datetime.now().isoformat()
    elif args.full_audit:
        results = full_audit()
    else:
        parser.print_help()
        return 0

    if args.save:
        save_results(results)
        print(f"Results saved to: {RESULTS_FILE}")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)

    # Exit code based on risk level
    risk_level = results.get("summary", {}).get("risk_level", "LOW")
    if risk_level == "CRITICAL":
        return 2
    elif risk_level in ["HIGH", "MEDIUM"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
